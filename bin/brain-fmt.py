#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-fmt: deterministic comment hygiene over source files.

a recurring style sweep, committed because it runs on every style pass and its
ruleset is worth versioning (P19). two independent modes:

    python3 brain-fmt.py path [path ...]           rewrite in place
    python3 brain-fmt.py --check path [...]        exit 1 if any file would change
    python3 brain-fmt.py --stale path [...]        audit comment CONTENT, never rewrites
    python3 brain-fmt.py --stale --since HEAD p    audit only the lines that ref changed

FORMAT (the rewriting mode) applies two idempotent rules:
- strip a single trailing period from a plain `# ` line comment (not doc lines,
  not urls, not `...`)
- a separator line of 3+ hyphens is normalised to exactly 50

casing is deliberately NOT touched: a separator label can legitimately carry an
identifier or proper noun (a state name, `$AAV_BRAIN`, `P29`), so force-lowering
it would corrupt meaning. label casing stays the author's call

STALE (the audit mode) reports two things and rewrites nothing (P37):
- a comment naming an identifier the file does not contain - a leftover from a
  rename, which sends the reader hunting for something that is not there. only
  quoted spans and single letters are resolved, so it stays quiet on prose
- a comment carrying a phrase about a former state of the code. the source
  describes a program; a changelog belongs in the commit message

it reports, it never deletes: which words to cut is a judgement, and half of what
P37 forbids (a comment that restates the request, a comment that says nothing) has
no deterministic signature at all. this catches the half that does. measured on
this repo bin/: 12 raw hits, 1 real, so the rules above are tuned for precision -
it stays silent on an unquoted symbol rather than flag an ordinary word

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Flag, read_text, write_text

# --------------------------------------------------
# external
# --------------------------------------------------
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# a full-width comment separator is exactly fifty hyphens
SEP = "-" * 50
# a run of three-or-more hyphens after a comment marker is a separator to fix
# the marker is a group, not a literal `#`: the style spec is language-
# independent and names C/C++/CUDA explicitly, so a `#`-only pattern silently
# skips every .cu and .cpp it is handed - which is not a no-op, it is a pass
# that reports success having done nothing
SEP_RE = re.compile(r"^(\s*)(#|//)\s*-{3,}\s*$")
# a plain prose comment, candidate for a trailing-period trim
COMMENT_RE = re.compile(r"^(\s*(?:#|//)\s+.*?[A-Za-z0-9])\.\s*$")
# the closed whitelist of GLOBAL separator labels. anything else at file scope
# is an invented label, which the spec forbids outright
GLOBAL_LABELS = frozenset({"mods", "re-exports", "local", "external", "constants", "statics", "workspace"})
# a separator block is bar / label / bar: its two bars are two lines apart

# the line-comment markers of the languages in his stack
MARKERS: tuple[str, ...] = ("#", "//")
# an identifier as any of these languages spells one
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# a token inside a comment worth resolving against the code. precision beats
# recall here: a checker that cries wolf gets turned off, so only two shapes
# count - a quoted span, which is the author declaring "this is code", and a
# single letter, which prose never produces - except beside a slash or plus,
# where it is a language name (C/C++/CUDA) rather than a symbol. an unquoted
# underscored or capitalised word is deliberately NOT resolved: those read as
# jargon in a sentence far more often than as a reference to a symbol
BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
LONE_CAP_RE = re.compile(r"(?<![A-Za-z0-9_`/+])([B-HJ-Z])(?![A-Za-z0-9_`/+])")
# a phrase that can only be about a former state of the code
STRONG_NARRATION = [re.compile(p, re.IGNORECASE) for p in (
    r"\bused to be\b",
    r"\bpreviously\b",
    r"\bformerly\b",
    r"\bchanged (?:from|to)\b",
    r"\brenamed\b",
    r"\bthis replaces\b",
    r"\b(?:was|were|has been|have been) (?:added|removed|renamed|replaced)\b",
    r"\bold (?:version|name|signature|code|behaviou?r)\b",
)]
# a phrase that is ALSO how one documents a live design choice, so it counts
# only alongside a stale referent: "instead of hardcoding a username" states a
# present rule, while the same words beside a dead symbol describe an edit
WEAK_NARRATION = [re.compile(p, re.IGNORECASE) for p in (
    r"\binstead of\b",
    r"\brather than\b",
    r"\bno longer\b",
    r"\bis used here\b",
    r"\bnow (?:uses|takes|returns|accepts|holds|expects)\b",
)]
# a hunk header, for mapping a diff back to post-image line numbers
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class Finding:
    """one auditable defect in one comment."""

    path: str
    lineno: int
    kind: str
    detail: str

    def __str__(self) -> str:
        """the report line, `file:line  kind  detail`.

        # Returns
        the formatted line
        """
        return f"  {self.path}:{self.lineno}  {self.kind} {self.detail}"


@dataclass
class Source:
    """one file, split into its comments and the code around them."""

    path: Path
    text: str

    @classmethod
    def read(cls, path: str | Path) -> "Source":
        """load a file for auditing.

        # Arguments
        * `path` - the file to read, as a string from argv or a Path

        # Returns
        a Source over its full text
        """
        path = Path(path)
        return cls(path=path, text=read_text(path))

    @staticmethod
    def split_comment(line: str) -> tuple[str, str]:
        """separate a line into its code part and its comment part.

        a marker with an odd number of quotes before it is inside a string
        literal, not a comment

        # Arguments
        * `line` - one source line

        # Returns
        a (code, comment) tuple; comment is "" when the line carries none
        """
        for marker in MARKERS:
            index = line.find(marker)
            while index != -1:
                head = line[:index]
                if head.count('"') % 2 == 0 and head.count("'") % 2 == 0:
                    return head, line[index:]
                index = line.find(marker, index + 1)
        return line, ""

    def code_tokens(self) -> set[str]:
        """every identifier the file's CODE contains.

        # Returns
        the set of identifiers appearing outside comments
        """
        tokens: set[str] = set()
        for line in self.text.split("\n"):
            code, _ = self.split_comment(line)
            tokens.update(IDENT_RE.findall(code))
        return tokens

    def comments(self) -> list[tuple[int, str]]:
        """the comment on every line that has one.

        # Returns
        a list of (lineno, comment-text) pairs, 1-indexed
        """
        found: list[tuple[int, str]] = []
        for number, line in enumerate(self.text.split("\n"), start=1):
            _, comment = self.split_comment(line)
            if comment.strip():
                found.append((number, comment))
        return found


@dataclass
class StaleAudit:
    """the comment-content audit: what a comment names, and how it phrases it."""

    findings: list[Finding] = field(default_factory=list)

    @staticmethod
    def named_tokens(comment: str) -> set[str]:
        """the identifiers a comment refers to.

        # Arguments
        * `comment` - the comment text

        # Returns
        the set of tokens shaped like code rather than like prose
        """
        tokens = set(BACKTICK_RE.findall(comment))
        tokens.update(LONE_CAP_RE.findall(comment))
        return tokens

    def audit(self, source: "Source", lines: set[int] | None = None) -> int:
        """collect every finding in one file.

        # Arguments
        * `source` - the Source to audit
        * `lines` - line numbers to restrict to, or None for the whole file

        # Returns
        the number of findings added
        """
        before = len(self.findings)
        code = source.code_tokens()
        name = str(source.path)
        for number, comment in source.comments():
            if lines is not None and number not in lines:
                continue
            # --------------------------------------------------
            # a name the file does not contain
            # --------------------------------------------------
            stale = [t for t in sorted(self.named_tokens(comment)) if t not in code]
            for token in stale:
                self.findings.append(Finding(
                    name, number, "stale referent",
                    f"'{token}' - the comment names it, the file does not contain it"))
            # --------------------------------------------------
            # a phrase about a former state; the weak set needs the stale name
            # beside it to separate an edit from a documented design choice
            # --------------------------------------------------
            patterns = STRONG_NARRATION + WEAK_NARRATION if stale else STRONG_NARRATION
            for pattern in patterns:
                match = pattern.search(comment)
                if match:
                    self.findings.append(Finding(
                        name, number, "narration    ",
                        f'"{match.group(0)}" - describes the change, not the code'))
        return len(self.findings) - before

    def report(self) -> int:
        """print every finding and the action each one calls for.

        # Returns
        the exit code: 1 when anything was found
        """
        if not self.findings:
            print("brain-fmt --stale: no findings")
            return 0
        for finding in self.findings:
            print(finding)
        files = len({f.path for f in self.findings})
        print(f"brain-fmt --stale: {len(self.findings)} finding(s) in {files} file(s)")
        print("cut the named component from the comment; the rest of the comment stands (P37)")
        return 1


@dataclass
class StyleGate:
    """the mechanical half of the style contract, as a pass/fail gate.

    every rule here is countable, so `styled` stops being an assertion and
    becomes a measurement

    it deliberately checks only what a script CAN check. whether a local
    separator is named well is the aav-style-separators lens's job; whether one
    exists at all is arithmetic
    """

    @staticmethod
    def marker_for(path: Path) -> str | None:
        """the line-comment marker for a path's language, or None if unhandled.

        # Arguments
        * `path` - the source file whose language to resolve

        # Returns
        the marker, or None when the suffix is not a commented source
        """
        if path.suffix in {".py", ".sh", ".bash", ".nix", ".toml"}:
            return "#"
        if path.suffix in {".rs", ".c", ".h", ".cc", ".cpp", ".hpp", ".cu", ".cuh", ".ts", ".tsx", ".js"}:
            return "//"
        return None

    @classmethod
    def audit(cls, path: Path) -> list[Finding]:
        """count the three violations a script can see.

        # Arguments
        * `path` - the source file to audit

        # Returns
        one Finding per violation
        """
        marker = cls.marker_for(path)
        if marker is None:
            return []

        lines = read_text(path).split("\n")
        bar = re.compile(rf"^(\s*){re.escape(marker)}\s*-{{40,}}\s*$")
        out: list[Finding] = []

        # --------------------------------------------------
        # locate every separator block: bar / label / bar
        # --------------------------------------------------
        # the label may wrap over several comment lines, so a block is bar,
        # one-or-more comment lines, bar. a lone bar is a rule, not a separator
        comment = re.compile(rf"^\s*{re.escape(marker)}")
        bars = [i for i, line in enumerate(lines) if bar.match(line)]
        blocks: list[tuple[int, int]] = []
        index = 0
        while index < len(bars) - 1:
            head, tail = bars[index], bars[index + 1]
            if tail > head + 1 and all(comment.match(lines[i]) for i in range(head + 1, tail)):
                blocks.append((head, tail))
                index += 2
            else:
                index += 1

        # --------------------------------------------------
        # a separator is never followed by a blank line
        # --------------------------------------------------
        out.extend(
            Finding(str(path), end + 2, "blank-after-separator",
                    "a separator is never followed by an empty line")
            for _start, end in blocks
            if end + 1 < len(lines) and not lines[end + 1].strip()
        )

        # --------------------------------------------------
        # global labels come from the closed whitelist
        # --------------------------------------------------
        for start, end in blocks:
            if lines[start].startswith((" ", "\t")):
                continue
            label = " ".join(lines[i].strip().lstrip(marker).strip() for i in range(start + 1, end))
            if label and label not in GLOBAL_LABELS:
                out.append(Finding(str(path), start + 2, "invented-global-label",
                                   f"'{label}' is not one of {sorted(GLOBAL_LABELS)}"))

        # --------------------------------------------------
        # function bodies carry local separators
        # --------------------------------------------------
        local = sum(1 for start, _end in blocks if lines[start].startswith((" ", "\t")))
        bodies = len(re.findall(r"^\s*def ", "\n".join(lines), re.MULTILINE)) if marker == "#" else \
            len(re.findall(r"^[\w:<>,\s\*&\[\]]+\s+\w+\s*\([^;]*\)\s*\{", "\n".join(lines), re.MULTILINE))
        if bodies and not local:
            out.append(Finding(str(path), 1, "no-local-separators",
                               f"{bodies} function bodies, 0 local separators"))
        return out

    @classmethod
    def run(cls, paths: Sequence[str]) -> int:
        """audit every path and report.

        # Arguments
        * `paths` - the files to audit

        # Returns
        the exit code: 1 when any violation was found, so STYLE emits unstyled
        """
        findings: list[Finding] = []
        for raw in paths:
            findings.extend(cls.audit(Path(raw)))
        for finding in findings:
            print(finding)
        counts: dict[str, int] = {}
        for finding in findings:
            counts[finding.kind] = counts.get(finding.kind, 0) + 1
        summary = ", ".join(f"{kind} {count}" for kind, count in sorted(counts.items())) or "clean"
        print(f"{TOOL}: style gate {'FAIL' if findings else 'PASS'} - {summary}")
        return 1 if findings else 0


@dataclass
class Formatter:
    """the rewriting pass: separators and trailing periods."""

    check: bool = False

    @staticmethod
    def fmt_line(line: str) -> str:
        """apply the two hygiene rules to one line.

        # Arguments
        * `line` - the source line, without its trailing newline

        # Returns
        the reformatted line
        """
        # --------------------------------------------------
        # separator: collapse any 3+ hyphen rule to exactly fifty
        # --------------------------------------------------
        match = SEP_RE.match(line)
        if match:
            return f"{match.group(1)}{match.group(2)} {SEP}"
        # --------------------------------------------------
        # prose comment: trim one trailing period, leave `...` and urls
        # --------------------------------------------------
        if COMMENT_RE.match(line) and not line.rstrip().endswith("..") and "://" not in line:
            return line.rstrip()[:-1].rstrip()
        return line

    @classmethod
    def fmt_text(cls, text: str) -> str:
        """run fmt_line over every line of a file's contents.

        # Arguments
        * `text` - the full file contents

        # Returns
        the reformatted text
        """
        return "\n".join(cls.fmt_line(line) for line in text.split("\n"))

    def run(self, paths: Sequence[str]) -> int:
        """rewrite, or count, every path.

        # Arguments
        * `paths` - the files to process

        # Returns
        the exit code: 1 when --check found work to do
        """
        changed = 0
        for raw in paths:
            path = Path(raw)
            before = read_text(path)
            after = self.fmt_text(before)
            if before != after:
                changed += 1
                if not self.check:
                    write_text(path, after)
        print(f"{TOOL}: {changed} file(s) {'would change' if self.check else 'rewritten'}")
        return 1 if (self.check and changed) else 0


def changed_lines(path: Path, ref: str) -> set[int] | None:
    """the post-image line numbers a diff touched.

    # Arguments
    * `path` - the file to diff
    * `ref` - the git ref to diff against

    # Returns
    the set of 1-indexed line numbers, or None when git cannot answer - in
    which case the caller audits the whole file rather than silently auditing
    nothing (P36)
    """
    command = ["git", "diff", "--unified=0", ref, "--", str(path)]
    # command is this function's own literal argv plus a path and a ref he typed;
    # nothing is remote, and shell=False keeps it an exec not a shell (S603)
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        print(f"{TOOL}: git diff failed for {path}, auditing the whole file", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        return None
    lines: set[int] = set()
    for line in result.stdout.split("\n"):
        match = HUNK_RE.match(line)
        if match:
            start = int(match.group(1))
            count = int(match.group(2) or 1)
            lines.update(range(start, start + count))
    return lines


def main() -> None:
    """dispatch the format pass or the content audit."""
    # --------------------------------------------------
    # parse: every flag is positional-agnostic, matching the other brain scripts
    # a flag accepted only in first position silently becomes a PATH anywhere else
    # --------------------------------------------------
    args = Args.from_argv()
    if unknown := args.unknown(Flag.SINCE, Flag.STALE, Flag.CHECK, Flag.GATE):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    ref = args.value(Flag.SINCE) or None
    paths = args.positional(Flag.SINCE)
    # --------------------------------------------------
    # validate the mode against the arguments
    # --------------------------------------------------
    if not paths:
        sys.exit("usage: brain-fmt.py [--check | --gate | --stale [--since REF]] path [path ...]")
    if ref and not args.has(Flag.STALE):
        sys.exit(f"{TOOL}: --since applies to --stale")
    # --------------------------------------------------
    # dispatch
    # --------------------------------------------------
    if args.has(Flag.GATE):
        sys.exit(StyleGate.run(paths))
    if args.has(Flag.STALE):
        audit = StaleAudit()
        for raw in paths:
            source = Source.read(raw)
            audit.audit(source, changed_lines(source.path, ref) if ref else None)
        sys.exit(audit.report())
    sys.exit(Formatter(check=args.has(Flag.CHECK)).run(paths))


if __name__ == "__main__":
    main()
