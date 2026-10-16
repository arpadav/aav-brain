#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-shape: measure a repo's SHAPE, so P27 and P28 stop being adjectives.

a recurring deterministic check (P19), and the one measurement the phase gate
never had. it reports four crossings against shape.toml - a file past
`file_lines`, a folder past `folder_files`, a folder small enough to collapse
back to flat, and a type name declared in `duplicate_type_files` or more files
- plus, under --since, the SECONDARY change budget (brain-gate.py decides whether
a phase boundary buys a cold review).

it exists because a review scoped to a diff cannot see any of them. a phase that
adds 800 lines to a 6700-line file produces a diff that reads fine; the FILE is
the defect and no reviewer is ever shown it. the evidence behind that is stated
once, in principle-27-organization-reorg, rather than retold here

a crossing is a FINDING, never a verdict. it says look here; whether the file
should actually split is a judgement made against what the file IS

it refuses rather than reassures: if the tree cannot be listed, or a --since ref
does not resolve, it says so and exits non-zero. a scan that reports CLEAN
having measured nothing is the failure this tool was written to end

    python3 brain-shape.py [PATH]              report every crossing
    python3 brain-shape.py [PATH] --check      exit 1 if anything crossed
    python3 brain-shape.py [PATH] --since REF  the secondary change budget since a ref

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Exit, Flag, Layout, ShapePolicy, git, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem

# every path inside the brain, spelled once (brainlib.Layout)
LAYOUT = Layout.discover()

# a NOMINAL type declaration, per language family. three restrictions carry this
# tool's signal-to-noise, and each one is a measured false positive: functions
# are never matched, because two files declaring `fn new` is how impl blocks
# work while two declaring `struct Ledger` is the duplication P31 forbids; a
# declaration must be FOLLOWED by an opening delimiter, which excludes both a
# c++ forward declaration `class Widget;` and a rust `type Err = ...` alias; and
# prose suffixes are never scanned, so a card discussing `class Foo` does not
# read as a definition of one
TYPE_DECL = (
    # rust, c/c++, java, kotlin, swift, ts - the keyword leads the declaration
    re.compile(
        r"^[ \t]*(?:pub(?:\([^)]*\))?[ \t]+|export[ \t]+|public[ \t]+|private[ \t]+|internal[ \t]+"
        r"|abstract[ \t]+|final[ \t]+|sealed[ \t]+|static[ \t]+)*"
        r"(?:struct|enum|trait|class|interface|protocol|record|union|data class)[ \t]+"
        r"([A-Za-z_][A-Za-z0-9_]*)[ \t]*(?:<[^;{]*>[ \t]*)?[:({]",
        re.MULTILINE,
    ),
    # go and zig - the NAME leads and the keyword follows it
    re.compile(
        r"^[ \t]*(?:pub[ \t]+)?(?:type|const|var)[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*=?[ \t]*"
        r"(?:struct|interface|enum|union|opaque)[ \t]*[({]",
        re.MULTILINE,
    ),
    # a c typedef, whose tag lands after the body: `} Foo;`
    re.compile(r"^[ \t]*\}[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*;", re.MULTILINE),
)

class Axis(StrEnum):
    """the four axes this tool measures, named once.

    a bare string per axis is a fixed set wearing a `str`, which is what P06
    has a StrEnum for - and it was compared by hand at the report site
    """

    FILE = "file"
    DIR = "dir"
    FLAT = "flat"
    TYPE = "type"


@dataclass(frozen=True)
class Crossing:
    """one threshold crossed: what was measured, against what, and where.

    it carries its own NUMBER because that is the whole point of this tool -
    "ledger.rs is long" is the sentence twelve gate commits already failed to
    act on, and "ledger.rs 7540 lines, limit 2000" is not

    it is deliberately NOT named `Finding`: bin/check/brain-fmt.py already has a
    `Finding`, of a different shape, and two datatypes sharing a name is the
    collision this tool reports on other people's code
    """

    axis: Axis
    where: str
    measured: int
    limit: int
    note: str

    def line(self) -> str:
        """this finding as one report line.

        # Returns

        the rendered line, limit included

        # Example

            >>> Crossing(Axis.FILE, "a.rs", 7540, 2000, "split").line()
            '  file   a.rs  7540 (limit 2000) - split'
        """
        return f"  {self.axis.value:<5}  {self.where}  {self.measured} (limit {self.limit}) - {self.note}"


@dataclass(frozen=True)
class Budget:
    """how much a phase changed, and whether that arms a cold gate.

    `armed` is deliberately true when the change could NOT be measured: an
    unresolvable ref must buy the review, never cancel it. a typo that silently
    disarms a gate is the same defect class this whole tool exists to report
    """

    files: int
    lines: int
    armed: bool
    measured: bool

    def line(self, ref: str) -> str:
        """this budget as one report line.

        # Arguments

        * `ref` - the ref the phase started from, for the message

        # Returns

        the rendered line, verdict included

        # Example

            >>> Budget(0, 0, armed=True, measured=False).line("HEAD~9").endswith("by a typo")
            True
        """
        if not self.measured:
            unmeasured = "NOT MEASURABLE (the ref does not resolve) -> ARMED, a gate is not cancelled by a typo"
            return f"{TOOL}: since {ref}: {unmeasured}"
        armed = "ARMED - the next phase boundary buys a cold gate"
        under = "under budget - VERIFY and STYLE only"
        verdict = armed if self.armed else under
        return f"{TOOL}: since {ref}: {self.files} file(s), {self.lines} changed line(s) -> {verdict}"


@dataclass
class Shape:
    """the measured shape of one repo, against one policy.

    `crossings` accumulate across the tree measurements and fail the --check
    gate together; the budget is reported separately because it is not a defect
    at all, it is the question of whether the next gate is worth dispatching
    """

    root: Path
    policy: ShapePolicy
    crossings: list[Crossing] = field(default_factory=list)

    def sources(self) -> list[Path] | None:
        """every source file git knows about, repo-relative, deduplicated.

        tracked AND untracked-but-not-ignored: a gitignored vendor tree is not
        this repo's shape, but a file written five minutes ago is - and counting
        only tracked files under-measured exactly the phases most worth gating.
        unmerged paths list once per stage, so the set is deduplicated or one
        conflict triples every finding

        # Returns

        the paths shape.toml admits, sorted; None when the tree cannot be listed
        at all, which is NOT the same answer as an empty repo
        """
        listed = git(self.root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        if listed is None:
            return None
        named = {Path(name) for name in listed.split("\0") if name}
        return sorted(path for path in named if self.policy.is_source(path))

    def measure(self) -> bool:
        """run the tree measurements and collect their crossings.

        # Returns

        true when the tree was measured; false when it could not be listed, so
        a caller never renders an empty crossing list as a clean repo
        """
        paths = self.sources()
        if paths is None:
            return False
        per_folder: dict[Path, list[int]] = defaultdict(list)
        per_type: dict[str, set[str]] = defaultdict(set)
        self.lengths(paths, per_folder, per_type)
        self.folders(per_folder)
        self.duplicates(per_type)
        return True

    def lengths(self, paths: list[Path], per_folder: dict[Path, list[int]], per_type: dict[str, set[str]]) -> None:
        """measure each file's length, and collect what each file declares.

        # Arguments

        * `paths` - the source files to read
        * `per_folder` - filled with each folder's direct file line counts
        * `per_type` - filled with each type name's defining files
        """
        for path in paths:
            try:
                text = read_text(self.root / path)
            except (OSError, UnicodeDecodeError):
                # a tracked file deleted from the worktree, or a non-utf8 blob
                # neither is a shape defect, and neither may crash a gate's input
                continue
            lines = len(text.splitlines())
            per_folder[path.parent].append(lines)
            if lines > self.policy.file_lines:
                self.crossings.append(Crossing(
                    Axis.FILE, path.as_posix(), lines, self.policy.file_lines,
                    "candidate for flat -> tree (P27)",
                ))
            if path.suffix in self.policy.prose:
                continue
            for pattern in TYPE_DECL:
                for name in pattern.findall(text):
                    per_type[name].add(path.as_posix())

    def folders(self, per_folder: dict[Path, list[int]]) -> None:
        """judge each folder's fan-out, in both of P27's directions.

        # Arguments

        * `per_folder` - each folder's direct source file line counts
        """
        for folder, sizes in sorted(per_folder.items()):
            if self.policy.is_exempt(folder):
                continue
            where = folder.as_posix() or "."
            if len(sizes) > self.policy.folder_files:
                self.crossings.append(Crossing(
                    Axis.DIR, where, len(sizes), self.policy.folder_files,
                    "too many flat files, split to a subtree (P27)",
                ))
            elif self.hollow(folder, sizes, per_folder):
                self.crossings.append(Crossing(
                    Axis.FLAT, where, sum(sizes), self.policy.collapse_lines,
                    f"{len(sizes)} file(s), candidate for tree -> flat (P27)",
                ))

    def duplicates(self, per_type: dict[str, set[str]]) -> None:
        """report each type name declared in more files than the policy allows.

        # Arguments

        * `per_type` - each type name's defining files
        """
        for name, files in sorted(per_type.items()):
            if len(files) >= self.policy.duplicate_type_files:
                self.crossings.append(Crossing(
                    Axis.TYPE, f"{name} in {', '.join(sorted(files))}", len(files),
                    self.policy.duplicate_type_files, "one datatype, several definitions (P31)",
                ))

    def hollow(self, folder: Path, sizes: list[int], tree: dict[Path, list[int]]) -> bool:
        """whether this folder is a level that adds nothing over its parent.

        small alone is not hollow. `agentic-files/skills/brain-plan/SKILL.md` is
        one 90-line file in its own folder and that is the deliberate form - the
        first draft of this rule reported six of them, which is the cry-wolf
        failure the whole tool exists to avoid. the level is only pointless when
        the PARENT already holds source files directly, so collapsing loses no
        separation - and never when it has folders of its own, whose grouping
        collapsing would spill into the parent (`bin/` over `store/ run/ check/`)

        # Arguments

        * `folder` - the folder being judged
        * `sizes` - its direct source files' line counts
        * `tree` - every folder's line counts, to look the parent up

        # Returns

        true when the folder is small, has no measured subfolder, AND its
        parent already holds source
        """
        if folder.as_posix() in {"", "."}:
            return False
        if any(other.parent == folder for other in tree):
            return False
        if len(sizes) > self.policy.collapse_files or sum(sizes) > self.policy.collapse_lines:
            return False
        return bool(tree.get(folder.parent))

    def budget(self, ref: str) -> Budget:
        """the change accumulated since a git ref, and whether it arms a gate.

        this is the secondary half of the gate measurement; brain-gate.py
        decides. PHASEGATE fired once per phase whether the phase was 5885 new
        lines or two lines of formatter appeasement, so the same cold
        multi-lens review was spent on both

        counted the way the tree is counted: only files shape.toml admits, only
        under the measured path, and untracked new files included. a regenerated
        graph must not arm a review, and five new untracked source files must

        PROSE IS EXCLUDED HERE and nowhere else - it is still measured for
        length by the tree scan. a rewritten handoff document is hundreds of
        changed lines that no code lens reads

        # Arguments

        * `ref` - the git ref the current phase started from

        # Returns

        the Budget; `measured` false when the ref does not resolve, which ARMS
        """
        if git(self.root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}") is None:
            return Budget(0, 0, armed=True, measured=False)
        files = 0
        changed = 0
        for row in (git(self.root, "diff", "--numstat", ref, "--", ".") or "").splitlines():
            added, removed, name = (*row.split("\t", 2), "", "", "")[:3]
            if not name or not self.policy.arms(Path(name)):
                continue
            files += 1
            # a binary file reports `-` for both counts: a changed file that
            # contributes no lines. a removal counts as change - a phase that
            # deletes 5000 lines is not a phase that changed nothing
            if added.isdigit() and removed.isdigit():
                changed += int(added) + int(removed)
        for name in (git(self.root, "ls-files", "-z", "--others", "--exclude-standard") or "").split("\0"):
            if not name or not self.policy.arms(Path(name)):
                continue
            files += 1
            try:
                changed += len(read_text(self.root / name).splitlines())
            except (OSError, UnicodeDecodeError):
                continue
        armed = files >= self.policy.changed_files or changed >= self.policy.changed_lines
        return Budget(files, changed, armed=armed, measured=True)


def main() -> None:
    """measure the named repo, report every crossing, and gate --check on them.

    `--since REF` adds the SECONDARY change budget; brain-gate.py decides whether
    a phase boundary buys a cold review
    """
    args = Args.from_argv()
    args.gate(TOOL, __doc__, Flag.CHECK, Flag.SINCE)
    if starved := args.starved(Flag.SINCE):
        print(f"{TOOL}: {starved[0]} needs a ref", file=sys.stderr)
        sys.exit(Exit.USAGE)
    positional = args.positional()
    root = Path(positional[0]).resolve() if positional else Path.cwd()
    shape = Shape(root, ShapePolicy.load(LAYOUT.shape_toml))
    if not shape.measure():
        print(f"{TOOL}: cannot list {root} - not a git repo, or git is unavailable", file=sys.stderr)
        print(f"{TOOL}: refusing to report a clean scan of a tree it never read", file=sys.stderr)
        sys.exit(Exit.USAGE)
    for crossing in shape.crossings:
        print(crossing.line())
    print(f"{TOOL}: {len(shape.crossings)} crossing(s) in {root.name}")
    # --------------------------------------------------
    # the arming question, asked only when a ref is named
    # --------------------------------------------------
    if since := args.value(Flag.SINCE):
        print(shape.budget(since).line(since))
    if args.has(Flag.CHECK) and shape.crossings:
        sys.exit(Exit.DRIFT)


if __name__ == "__main__":
    main()
