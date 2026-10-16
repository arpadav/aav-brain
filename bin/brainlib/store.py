"""brainlib.store: the append-only logs and the authored policies over them.

one reader and one writer for every jsonl corpus, so "a log may only ever
grow" lives in a single place; the policies beside it are authored data read
from toml, so no tool hardcodes a number

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.paths import DataLayout, find_repo
from brainlib.text import iso_now, read_text, write_text
from brainlib.vocab import ENCODING, GIT_TIMEOUT

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class MergeCount:
    """the outcome of one merge: how many rows landed, held, and remain."""

    added: int
    kept: int
    total: int


@dataclass(frozen=True)
class Ledger:
    """a jsonl corpus that may only ever grow, deduped by content id.

    owns "a record once captured is never dropped" the same way Artifact owns
    "committed output must equal a fresh build" - the invariant lives here, and
    every corpus (evidence views, the decision trace) writes through this type
    rather than hand-rolling its own reader and writer

    the sources these records come from expire, so a full rebuild would delete
    evidence that can no longer be re-derived from anywhere; merging on content
    makes a re-run purely additive

    forgetting is therefore a MARK, not a delete: `mark` stamps META fields that
    readers filter on, so a corpus can drop a record from view and still restore
    it by clearing the mark. that is the only sanctioned way to shrink a read
    """

    path: Path

    # fields the ledger owns rather than the record: `first_seen` is stamped by a
    # merge, `stale` and `pinned` by a mark. all three are excluded from identity
    # because a marked record is the SAME record - in the payload a mark would
    # dedup as a second row beside the unmarked one
    META: tuple[str, ...] = ("first_seen", "stale", "pinned")

    # the mark lattice, weakest first. merging two copies of a record JOINS their
    # marks by taking the strongest, which is what makes a merge independent of
    # the order two machines happen to sync in. `stale` and `pinned` are outside
    # the content id, so the same record pruned on one machine and untouched on
    # another has one id and two states - and a first-wins rule silently decided
    # which survived by whichever side git merged first
    MARKS: tuple[str, ...] = ("stale", "pinned")

    @classmethod
    def join(cls, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        """one record from two copies of it, taking the stronger mark.

        pinned beats stale beats unmarked, which is the semantics `--restore`
        already claims: restoring an entry PINS it against a later prune. the
        join is commutative and idempotent, so both machines reach the same
        answer whatever order they merge in

        # Arguments

        * `left` - one copy of the record
        * `right` - the other copy

        # Returns

        the merged record, keeping the earliest `first_seen`

        # Example

            >>> Ledger.join({"a": 1, "stale": True}, {"a": 1})["stale"]
            True
            >>> "stale" in Ledger.join({"a": 1, "stale": True}, {"a": 1, "pinned": True})
            False
        """
        out = {**right, **left}
        seen = [str(row["first_seen"]) for row in (left, right) if row.get("first_seen")]
        if seen:
            out["first_seen"] = min(seen)
        # strongest mark wins, and a stronger one CLEARS the weaker: a pinned
        # record is not also stale, or a reader would have to break the tie again
        strongest = max((cls.MARKS.index(m) for m in cls.MARKS
                         if left.get(m) or right.get(m)), default=-1)
        for index, mark in enumerate(cls.MARKS):
            out.pop(mark, None)
            if index == strongest:
                out[mark] = True
        return out

    @staticmethod
    def record_id(record: dict[str, Any]) -> str:
        """the stable content hash identifying one record.

        empty fields are dropped before hashing so a record written before an
        optional field existed collapses onto the same record written after it
        was added but left blank

        # Arguments
        * `record` - a json-serialisable dict

        # Returns
        a 16-hex-char content id
        """
        payload = {k: v for k, v in record.items()
                   if k not in Ledger.META and v not in ("", None, [], {})}
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        # sha1 identifies content here, it does not protect it: the id is a
        # dedup key over rows this machine wrote (S324 reads it as a security hash)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]  # noqa: S324

    def read(self) -> list[dict[str, Any]]:
        """read the corpus, skipping any line that does not parse.

        # Returns
        the parsed records, or an empty list if the file does not exist
        """
        if not self.path.exists():
            return []
        merged: dict[str, dict[str, Any]] = {}
        for line in read_text(self.path).splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            key = self.record_id(row)
            # a union merge of two machines' logs leaves both copies of a record
            # on disk. deduping HERE rather than in a tool means every reader is
            # correct straight after a git merge, on a machine that installed
            # nothing - the invariant belongs to the datatype, not to a hook
            merged[key] = self.join(row, merged[key]) if key in merged else row
        return list(merged.values())

    def append(self, record: dict[str, Any]) -> Path:
        """append one record in O(1), without rewriting the file.

        # Arguments
        * `record` - a json-serialisable dict

        # Returns
        the path written to
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding=ENCODING) as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return self.path

    def merge(self, rows: Iterable[dict[str, Any]]) -> "MergeCount":
        """union `rows` into the corpus, deduped by content id. never truncates.

        # Arguments
        * `rows` - the records to merge in

        # Returns
        a MergeCount
        """
        # --------------------------------------------------
        # whatever is already on disk is authoritative and survives
        # --------------------------------------------------
        merged = {self.record_id(existing): existing for existing in self.read()}
        # --------------------------------------------------
        # union in the new rows; an id already present keeps its first_seen and
        # JOINS its mark, so a prune arriving from another machine is not lost
        # --------------------------------------------------
        kept, added, stamp = len(merged), 0, iso_now()
        for row in rows:
            key = self.record_id(row)
            if key in merged:
                merged[key] = self.join(merged[key], row)
                continue
            merged[key] = {**row, "first_seen": stamp}
            added += 1
        # --------------------------------------------------
        # deterministic order: chronological, id breaking ties for undated rows
        # --------------------------------------------------
        ordered = sorted(merged.items(), key=lambda kv: (str(kv[1].get("ts") or ""), kv[0]))
        self.write(row for _, row in ordered)
        return MergeCount(added, kept, len(merged))

    def unprotected(self) -> str:
        """a warning when git would three-way merge this corpus, or "".

        a set stored as lines conflicts under a line-based merge for no reason,
        and the attribute that prevents it is versioned data that can go missing
        - on a fresh clone of the logs, or a submodule checked out before the
        file existed. saying so beats discovering it during a merge

        # Returns

        a one-line warning, or an empty string when the corpus is protected
        """
        got = git(self.path.parent, "check-attr", "merge", "--", self.path.name)
        if got is None:
            return ""
        verdict = got.strip().rsplit(": ", 1)[-1]
        if verdict == "union":
            return ""
        return (f"{self.path.name}: git would three-way merge this, and it is a SET - "
                f"add `*.jsonl merge=union` to .gitattributes beside it")

    def mark(self, stamps: Mapping[str, Mapping[str, bool]]) -> int:
        """stamp bookkeeping fields on the records named by `ts`, keeping every row.

        this is how a corpus forgets without losing anything: a record marked
        `stale` is skipped by readers but stays on disk, so restoring it is
        clearing the mark rather than recovering it from somewhere. the fields
        are META, which is what keeps a mark out of the content id

        # Arguments

        * `stamps` - the fields to set, keyed by the `ts` of the record to set
          them on. a field set to false is removed rather than written as false,
          so an unmarked record stays byte-identical to one never marked

        # Returns

        the number of records stamped; a `ts` matching nothing is a no-op
        """
        # --------------------------------------------------
        # walk the RAW lines: a line this reader cannot parse is still a record,
        # and `read` skipping it must not become `write` dropping it
        # --------------------------------------------------
        touched = 0
        kept: list[str] = []
        for line in read_text(self.path).splitlines() if self.path.exists() else []:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                kept.append(line)
                continue
            fields = stamps.get(str(row.get("ts", "")))
            if not fields:
                kept.append(line)
                continue
            for name, value in fields.items():
                if value:
                    row[name] = True
                else:
                    row.pop(name, None)
            kept.append(json.dumps(row, ensure_ascii=False))
            touched += 1
        # --------------------------------------------------
        # rewrite only when a stamp actually landed
        # --------------------------------------------------
        if touched:
            write_text(self.path, "".join(f"{line}\n" for line in kept))
        return touched

    def write(self, rows: Iterable[dict[str, Any]]) -> Path:
        """overwrite the corpus with `rows`, one json object per line.

        for DERIVED files only - a projection whose every row is recomputed from
        a canonical corpus. anything append-only must go through merge/append,
        or `mark`, which rewrites the same rows it read and adds none

        # Arguments
        * `rows` - the records to write

        # Returns
        the path written to
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_text(self.path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        return self.path


@dataclass(frozen=True)
class PrunePolicy:
    """how old a trace entry must be before it is ELIGIBLE to be judged.

    eligibility is an age filter and nothing more. it narrows a several-hundred
    entry trace to the ones worth reading; deciding that any particular one is
    actually stale is a judgement made against what the brain is now, entry by
    entry. a tool that pruned everything past the cutoff would delete the oldest
    and most load-bearing decisions in the store first

    the window follows commit frequency because that is what sets how fast a
    decision goes out of date: a repo being reshaped weekly invalidates a
    three-week-old call, a quiet one does not

    # Example

        policy = PrunePolicy.load(LAYOUT.prune_toml)
        cutoff = policy.cutoff(rate=policy.commit_rate(LAYOUT.root))
    """

    busy_commits_per_week: float = 10.0
    sample_weeks: int = 8
    fast_days: int = 21
    slow_days: int = 60

    @classmethod
    def load(cls, path: Path) -> "PrunePolicy":
        """read the policy, falling back to the defaults when it is absent.

        # Arguments

        * `path` - the prune.toml path

        # Returns

        the policy; the field defaults when the file is absent, unreadable,
        malformed or the wrong shape. a broken config must WIDEN the window to
        the conservative default, never stop the tool - the same file is read
        beside the path that records decisions
        """
        if not path.is_file():
            return cls()
        try:
            window = tomllib.loads(read_text(path)).get("window", {})
            return cls(
                busy_commits_per_week=float(window.get("busy_commits_per_week", cls.busy_commits_per_week)),
                sample_weeks=max(1, int(window.get("sample_weeks", cls.sample_weeks))),
                fast_days=max(1, int(window.get("fast_days", cls.fast_days))),
                slow_days=max(1, int(window.get("slow_days", cls.slow_days))),
            )
        except (tomllib.TOMLDecodeError, AttributeError, TypeError, ValueError, OSError) as broken:
            print(f"prune policy unreadable ({broken}); using defaults", file=sys.stderr)
            return cls()

    def commit_rate(self, repo: Path) -> float:
        """commits per week in this repo over the sample window.

        # Arguments

        * `repo` - the repository to measure

        # Returns

        the rate; 0.0 when git is unavailable or the repo has no commits in the
        window, which selects the slow (more conservative) window
        """
        listed = git(repo, "log", "--since", f"{self.sample_weeks} weeks ago", "--format=%H")
        if listed is None:
            return 0.0
        return len(listed.split()) / self.sample_weeks

    def window_days(self, rate: float) -> int:
        """the eligibility window for a given commit rate.

        # Arguments

        * `rate` - commits per week

        # Returns

        the short window when the repo is busy, the long one otherwise

        # Example

            >>> policy = PrunePolicy()
            >>> policy.window_days(25.0), policy.window_days(1.0)
            (21, 60)
        """
        return self.fast_days if rate >= self.busy_commits_per_week else self.slow_days

    def cutoff(self, rate: float, now: dt.datetime | None = None) -> str:
        """the iso timestamp an entry must predate to be eligible.

        # Arguments

        * `rate` - commits per week, from `commit_rate`
        * `now` - the reference time; utc now when omitted

        # Returns

        an iso-8601 utc timestamp, string-comparable against a record's `ts`

        # Example

            >>> at = dt.datetime(2026, 3, 1, tzinfo=dt.UTC)
            >>> PrunePolicy().cutoff(1.0, at)
            '2025-12-31T00:00:00.000000Z'
        """
        moment = now or dt.datetime.now(dt.UTC)
        back = dt.timedelta(days=self.window_days(rate))
        # microseconds, matching iso_now: a record and this cutoff are compared
        # as STRINGS, and at second precision `.` sorts below `Z`, so a record
        # stamped inside the cutoff second would read as older than it
        return (moment - back).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def git(repo: Path, *argv: str) -> str | None:
    """run a read-only git command in a repo and return its stdout.

    the ONE place the brain shells out to git. it was two - a policy method and
    a tool copied its body verbatim, comments included - which is the exact
    duplication P31 forbids, found in the diff that shipped the tool for finding
    it

    None and "" are different answers and the distinction is load-bearing: a
    caller that cannot tell "git said nothing" from "git could not run" reports
    a clean scan of a repo it never opened

    # Arguments

    * `repo` - the repository to run in
    * `argv` - the git subcommand and its arguments

    # Returns

    stdout on success; None when git is missing, the path is not a repo, or the
    command failed
    """
    found = shutil.which("git")
    if found is None:
        return None
    # GIT_DIR and GIT_WORK_TREE outrank -C, so an inherited environment would
    # silently measure a DIFFERENT repo than the one asked for
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    # argv is the caller's own literals plus a discovered repo path; nothing here
    # is remote input, and shell=False keeps it an exec not a shell (S603)
    try:
        done = subprocess.run([found, "-C", str(repo), *argv], capture_output=True,  # noqa: S603
                              text=True, check=False, env=env, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


@dataclass(frozen=True)
class ShapePolicy:
    """the numbers behind P27 and P28, and the secondary change budget.

    P27 says a file that is "too long" should split to a tree and P28 says a
    datatype defined twice should merge. both are adjectives, and a worker
    resolves an adjective against its own priors (P40). the build that forced
    these numbers is recorded once, on principle-27 under `## the measurement`,
    and is not retold here. these fields are what make the two cards
    measurable, and `budget` is
    what decouples the cold review from the phase COUNT and attaches it to the
    phase SIZE. the evidence is stated once, on principle-27 itself, under
    `## the measurement` - not retold here

    a crossing is a FINDING, not a verdict, exactly as PrunePolicy's window is
    eligibility and not a prune: a 2400-line table of sourced constants is one
    coherent file and nothing here may split it

    # Example

        policy = ShapePolicy.load(LAYOUT.shape_toml)
        policy.is_source(Path("src/ledger.rs"))
    """

    file_lines: int = 2000
    folder_files: int = 12
    collapse_files: int = 2
    collapse_lines: int = 120
    exempt: tuple[str, ...] = ()
    duplicate_type_files: int = 2
    changed_files: int = 4
    changed_lines: int = 400
    suffixes: frozenset[str] = frozenset({".rs", ".py", ".ts", ".tsx", ".js", ".go", ".c", ".h", ".cpp", ".hpp", ".md"})
    excluded: tuple[str, ...] = ("/vendor/", "/node_modules/", "/target/", "/.generated/")
    prose: frozenset[str] = frozenset({".md", ".markdown", ".rst", ".txt"})

    @classmethod
    def load(cls, path: Path) -> "ShapePolicy":
        """read the policy, falling back to the defaults when it is absent.

        # Arguments

        * `path` - the shape.toml path

        # Returns

        the policy; the field defaults when the file is absent, unreadable,
        malformed or the wrong shape. a broken config must still MEASURE, the
        same way a broken prune policy still reports - a tool that goes silent
        on a bad config is the failure this whole card set exists to prevent
        """
        if not path.is_file():
            # the same rule the tool follows: never go quiet about a measurement
            # you could not take. a silently-swapped policy scans eleven suffixes
            # where the authored one scans twenty-five, and reports the shortfall
            # as a clean repo
            print(f"no {path.name} at {path.parent}; measuring against built-in defaults", file=sys.stderr)
            return cls()
        try:
            data = tomllib.loads(read_text(path))
            tree, budget, scan = data.get("tree", {}), data.get("budget", {}), data.get("scan", {})
            return cls(
                file_lines=max(1, int(tree.get("file_lines", cls.file_lines))),
                folder_files=max(1, int(tree.get("folder_files", cls.folder_files))),
                collapse_files=max(1, int(tree.get("collapse_files", cls.collapse_files))),
                collapse_lines=max(1, int(tree.get("collapse_lines", cls.collapse_lines))),
                exempt=tuple(sorted(cls.listed(tree, "exempt", frozenset(cls.exempt)))),
                duplicate_type_files=max(2, int(tree.get("duplicate_type_files", cls.duplicate_type_files))),
                changed_files=max(1, int(budget.get("changed_files", cls.changed_files))),
                changed_lines=max(1, int(budget.get("changed_lines", cls.changed_lines))),
                suffixes=cls.listed(scan, "suffixes", cls.suffixes),
                excluded=tuple(sorted(cls.listed(scan, "excluded", frozenset(cls.excluded)))),
                prose=cls.listed(scan, "prose", cls.prose),
            )
        except (tomllib.TOMLDecodeError, AttributeError, TypeError, ValueError, OSError) as broken:
            print(f"shape policy unreadable ({broken}); using defaults", file=sys.stderr)
            return cls()

    @staticmethod
    def listed(table: Mapping[str, Any], key: str, fallback: frozenset[str]) -> frozenset[str]:
        """one authored list of strings, or the fallback when it is not one.

        a bare `suffixes = "rs"` is a string, and a frozenset of it is the two
        characters `r` and `s` - every file then fails the suffix test and the
        tool reports a clean repo it never measured

        # Arguments

        * `table` - the config table to read
        * `key` - the list-valued key
        * `fallback` - what to use when the key is absent or not a list

        # Returns

        the authored strings, or the fallback

        # Example

            >>> ShapePolicy.listed({"s": "rs"}, "s", frozenset({".rs"}))
            frozenset({'.rs'})
        """
        value: object = table.get(key)
        if not isinstance(value, Sequence) or isinstance(value, str):
            if value is not None:
                print(f"shape policy: {key} is not a list of strings; using defaults", file=sys.stderr)
            return fallback
        strings = frozenset(item for item in value if isinstance(item, str))
        if len(strings) != len(value):
            print(f"shape policy: {key} is not a list of strings; using defaults", file=sys.stderr)
            return fallback
        return strings

    def is_source(self, path: Path) -> bool:
        """whether this path is measured at all.

        # Arguments

        * `path` - a repo-relative path

        # Returns

        true when the suffix is source and no excluded fragment appears in it.
        the fragments are matched with surrounding slashes, so a crate honestly
        named `build-support` is not mistaken for a build output

        # Example

            >>> policy = ShapePolicy()
            >>> policy.is_source(Path("src/ledger.rs")), policy.is_source(Path("target/x.rs"))
            (True, False)
        """
        if path.suffix not in self.suffixes:
            return False
        return not self.matches(path, self.excluded)

    def arms(self, path: Path) -> bool:
        """whether this path's churn counts toward the review budget.

        prose is measured for LENGTH like anything else, but it may not ARM a
        cold code review: a handoff document rewritten in place is hundreds of
        changed lines that no reviewer lens reads, and arming on it spends five
        reviewers on a diff with no code in it

        # Arguments

        * `path` - a repo-relative path

        # Returns

        true when the path is measured AND is not prose

        # Example

            >>> policy = ShapePolicy()
            >>> policy.arms(Path("src/ledger.rs")), policy.arms(Path("plan/NEXT-STEPS.md"))
            (True, False)
        """
        return self.is_source(path) and path.suffix not in self.prose

    def is_exempt(self, folder: Path) -> bool:
        """whether a folder's fan-out is the deliberate form, not a defect.

        the one place a real crossing may be silenced, so it is authored and
        narrow: a zettelkasten is one file per card on purpose

        # Arguments

        * `folder` - the folder being judged, repo-relative

        # Returns

        true when an exempt fragment appears in the folder's path

        # Example

            >>> ShapePolicy(exempt=("/brain/principles/",)).is_exempt(Path("brain/principles"))
            True
        """
        return self.matches(folder, self.exempt)

    @staticmethod
    def matches(path: Path, fragments: tuple[str, ...]) -> bool:
        """whether any fragment appears in this path.

        the path is spelled with leading AND trailing slashes so a fragment
        matches a whole segment: a crate honestly named `build-support` is not
        mistaken for a build output, and `/brain/principles/` matches the
        directory itself as well as the files inside it

        # Arguments

        * `path` - a repo-relative path
        * `fragments` - the slash-delimited fragments to look for

        # Returns

        true when any fragment appears

        # Example

            >>> ShapePolicy.matches(Path("src/target/a.rs"), ("/target/",))
            True
        """
        spelled = f"/{path.as_posix()}/"
        return any(fragment in spelled for fragment in fragments)


@dataclass
class Decision:
    """one logged decision: what was chosen, what was rejected, what it affects.

    the decided-against entries are the point: a later session that disagrees
    reads `affects` to find exactly where the call was made and reverses it. when
    a call overturns a past one, `supersedes` carries the prior entry's ts so the
    reversal is machine-readable, not buried in the `decision` prose. `repo`
    is what makes `affects` resolvable at all: the trace spans every repo the
    brain works in, and the same relative path means a different file in each
    """

    skill: str
    decision: str
    chosen: str
    against: list[dict[str, str]] = field(default_factory=list)
    affects: str = ""
    repo: str = ""
    principle: list[str] = field(default_factory=list)
    confidence: str = "medium"
    supersedes: str = ""

    def trace(self, ledger: "Ledger | None" = None, session: str = "", ts: str = "") -> Path:
        """append this decision to the trace; never overwrite.

        the ledger defaults to the discovered one rather than a path spelled
        here, because `DataLayout` owns where the trace lives and a second
        spelling is a second thing to keep in step

        # Arguments

        * `ledger` - the corpus to append to; the discovered trace when omitted
        * `session` - the current session id, for transcript correlation
        * `ts` - an iso utc timestamp; stamped now when empty

        # Returns

        the resolved path the entry was appended to
        """
        target = ledger if ledger is not None else Ledger(DataLayout.discover().decisions)
        entry = {"ts": ts or iso_now(), "session": session, **vars(self)}
        # an unset repo means "the repo this ran in", which only this type knows
        entry["repo"] = entry["repo"] or find_repo()
        return target.append(entry)
