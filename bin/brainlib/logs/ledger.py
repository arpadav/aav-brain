"""brainlib.logs.ledger: the append-only logs: one reader and one writer for every corpus that may only grow.

the evidence views and the decision trace both go through Ledger, so the
never-rewrite invariant lives in a single place. the session logs are a
per-machine cache, not a corpus, and keep their own reader and writer
(brainlib.logs.session)

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.enums import ENCODING
from brainlib.file_io import iso_now, read_text, write_text
from brainlib.paths import LogsLayout, find_repo, find_repo_root
from brainlib.repo.tree import git

# --------------------------------------------------
# external
# --------------------------------------------------
import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeGuard

@dataclass(frozen=True)
class MergeCount:
    """the outcome of one merge: how many rows landed, held, and remain."""

    added: int
    kept: int
    total: int


@dataclass(frozen=True)
class Ledger:
    """a jsonl corpus that may only ever grow, deduped by content id.

    owns "a record once captured is never dropped" the same way GeneratedFile owns
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

    # the fields that make two records the same record; empty means the whole
    # payload. a corpus whose rows are re-read by a newer classifier, or copied
    # into a resumed session with the same stamp, names the fields that survive
    # both - otherwise each copy hashes as a new record
    identity: tuple[str, ...] = ()

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
    def is_record(value: object) -> TypeGuard[dict[str, Any]]:
        """whether a parsed json line is an object, the one shape a record has; json keys are always strings.

        # Arguments

        * `value` - one line of a ledger, as `json.loads` returned it

        # Returns

        True for an object, which narrows the type for the caller; False for any other json value

        # Example

            >>> Ledger.is_record({"ts": "2026-01-01"}), Ledger.is_record(["ts"]), Ledger.is_record(None)
            (True, False, False)
        """
        return isinstance(value, dict)

    def record_id(self, record: dict[str, Any]) -> str:
        """the stable content hash identifying one record.

        empty fields are dropped before hashing so a record written before an
        optional field existed collapses onto the same record written after it
        was added but left blank. a record missing one of the `identity` fields
        falls back to its whole payload, since what is left cannot tell two
        different records apart

        # Arguments
        * `record` - a json-serialisable dict

        # Returns
        a 16-hex-char content id

        # Example

            >>> keyed = Ledger(Path("x"), identity=("text", "ts"))
            >>> keyed.record_id({"text": "go", "ts": "1", "session": "a"}) == keyed.record_id({"text": "go", "ts": "1"})
            True
            >>> keyed.record_id({"text": "go", "session": "a"}) == keyed.record_id({"text": "go"})
            False
        """
        keyed = bool(self.identity) and all(record.get(k) for k in self.identity)
        payload = {k: v for k, v in record.items()
                   if (k in self.identity if keyed else k not in Ledger.META) and v not in ("", None, [], {})}
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        # sha1 identifies content here, it does not protect it: the id is a
        # dedup key over rows this machine wrote (S324 reads it as a security hash)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]  # noqa: S324

    def read(self) -> list[dict[str, Any]]:
        r"""read the corpus, skipping any line that is not a json object.

        # Returns
        the parsed records, or an empty list if the file does not exist

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     corpus = Path(tmp) / "c.jsonl"
            ...     _ = corpus.write_text('{"a": 1}\n[1]\n"text"\n{torn\n')
            ...     Ledger(corpus).read()
            [{'a': 1}]
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
            if not self.is_record(row):
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
    supersedes: str = ""

    def trace(self, ledger: "Ledger | None" = None, session: str = "", ts: str = "") -> Path:
        """append this decision to the trace; never overwrite.

        the ledger defaults to the discovered one rather than a path spelled
        here, because `LogsLayout` owns where the trace lives and a second
        spelling is a second thing to keep in step

        # Arguments

        * `ledger` - the corpus to append to; the discovered trace when omitted
        * `session` - the current session id, for transcript correlation
        * `ts` - an iso utc timestamp; stamped now when empty

        # Returns

        the resolved path the entry was appended to
        """
        target = ledger if ledger is not None else Ledger(LogsLayout.discover().decisions)
        entry = {"ts": ts or iso_now(), "session": session, **vars(self)}
        # an unset repo means "the repo this ran in", which only this type knows
        entry["repo"] = entry["repo"] or find_repo()
        entry["affects"] = self.portable(self.affects, find_repo_root())
        return target.append(entry)

    @staticmethod
    def portable(affects: str, root: Path | None) -> str:
        """`affects` with every absolute path inside `root` made relative to it.

        a machine-absolute path in the trace names one checkout on one machine;
        read anywhere else it resolves to nothing, or to a home this user
        cannot open (P32). a path outside the repo is kept as given, since
        there is nothing to make it relative to

        # Arguments

        * `affects` - the comma-separated pointer as passed on the command line
        * `root` - the repo the run happened in, or None outside one

        # Returns

        the same pointer, comma-separated, repo-relative where it could be

        # Example

            >>> Decision.portable("/r/a.md, b.md, /x/c.md", Path("/r"))
            'a.md,b.md,/x/c.md'
            >>> Decision.portable("/r/a.md", None)
            '/r/a.md'
        """
        if root is None:
            return affects
        # resolved, so a path spelled through a symlinked checkout still lands inside it
        paths = [Path(p.strip()) for p in affects.split(",") if p.strip()]
        paths = [p.resolve() if p.is_absolute() else p for p in paths]
        return ",".join(str(p.relative_to(root)) if p.is_relative_to(root) else str(p) for p in paths)
