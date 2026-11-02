#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-extract: distill my interaction fingerprint into the brain store.

distilled from raw agent transcripts, stdlib only, safe to run any time

    uv run brain-extract.py                  (or: python3 brain-extract.py)
    uv run brain-extract.py --out DIR        the evidence dir; default: the evidence dir of the
                                             brain's private data dir
    uv run brain-extract.py --archive        also cold-store the raw transcripts first
    uv run brain-extract.py --archive-dir D  the cold-storage root; default: find_archive(),
                                             OUTSIDE git

every human turn is captured into prompts.jsonl with a primary bucket and
a multi-label class set - nothing is dropped. sources are both my codex
and my claude sessions; this is a general agent fingerprint

every write is a MERGE, never a truncate: the transcript sources expire
(claude prunes ~/.claude/projects at roughly 26 days) so a rebuild would
drop evidence no source can re-derive. every record carries the
transcript's own `ts`

prime rule: an applied edit is NOT consent. mine only explicit signal -
the words i actually wrote, never an accepted diff

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import (
    Args,
    Claude,
    DataLayout,
    Denied,
    Driven,
    Event,
    EvidenceLayout,
    Flag,
    Harnesses,
    Interrupted,
    Ledger,
    MergeCount,
    Replied,
    Spoke,
    Tool,
    Transcript,
    TranscriptError,
    clip,
    find_archive,
    iso_now,
    write_text,
)

# --------------------------------------------------
# external
# --------------------------------------------------
import gzip
import json
import re
import shutil
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# negation / disagreement, tuned to my lowercase no-apostrophe register
RE_REJECT = re.compile(
    r"\b(nope|nah|dont|don't|do not|stop|undo|revert|isnt|isn't|wasnt|incorrect|disagree|"
    r"why (did|are|would|do|the hell) you|you (shouldnt|should not|cant|can't|missed|broke|forgot|misunderstood)|"
    r"thats not|that's not|not quite|not what i|get rid|no need|remove that|doesnt|doesn't make|"
    r"bad idea|i dont|that's wrong|thats wrong|wtf|never (do|use|put))\b", re.IGNORECASE)
# blunt openers that signal a correction at the very start of a turn
RE_NO_START = re.compile(r"^\s*(no\b|nope|nah|wrong|stop|pause|wait|actually|hold on|hmm,? no)", re.IGNORECASE)
# terse confirmation, recognised only on short turns so it doesnt over-fire
RE_APPROVE = re.compile(
    r"^\s*(yes\b|yep|yeah|yup|correct\b|perfect|exactly|lgtm|looks good|sounds good|do it|"
    r"go ahead|proceed|ship it|approved|great\b|nice\b|ok\b|okay|love it|👍|💯)", re.IGNORECASE)
# planning intent: the affirmative blueprint, not a rejection
RE_PLAN = re.compile(
    r"\b(make|create|write|draft).{0,24}\bplan\b|jumping off|plan mode|multi-phase plan", re.IGNORECASE)
# a build/feature request, recognised at the start of the turn
RE_BUILD = re.compile(
    r"^\s*(make|build|implement|create|add|write|scaffold|set ?up|generate|convert|refactor)\b", re.IGNORECASE)
# a standing decision or stated preference
RE_DECIDE = re.compile(
    r"\b(instead of|use .{0,30} not\b|lets use|let's use|i want|i prefer|i like|go with|rather than|"
    r"should be|stick with|we use|i use|always use|never use)\b", re.IGNORECASE)
# naming / micro-convention preference
RE_NAMING = re.compile(
    r"\b(name it|call it|rename|combined imports|snake_case|camelcase|kebab|naming|the name|"
    r"doc.?comment|separator|module layout|file name|call this)\b", re.IGNORECASE)
# sequencing / workflow ordering - my single most prevalent tell
RE_SEQ = re.compile(
    r"\b(first|then|next|after that|afterwards|once (you|its|it's|that)|lastly|finally|"
    r"step \d|to start|to begin|^1\.|^\s*\d\.)\b", re.IGNORECASE | re.MULTILINE)
# the sequencing connectives counted into a histogram
SEQ_WORDS = ["first", "then", "next", "after", "once", "lastly", "finally", "before", "afterwards"]
# profanity / heat: my hottest vetoes - a hard rule just broke (P15)
RE_HEAT = re.compile(
    r"\b(idiot|stupid|dumbass|retard|wtf|fuck|fucking|shit|dogshit|bullshit|the hell|"
    r"for the love of god|what the hell|why the fuck)\b", re.IGNORECASE)
# deploy / infra standing preferences - a real recurring cluster
RE_DEPLOY = re.compile(
    r"\b(docker|dockerfile|cloudflared|truenas|0\.0\.0\.0|compose|nginx|deploy|expose|"
    r"port \d|mount a? ?volume|systemd|axum|tunnel)\b", re.IGNORECASE)
# turns in a user slot that the harness wrote, not him: notifications, tool
# echoes, environment scaffolding, injected skill bodies and compaction
# summaries. one pattern for both tools, so a wrapper one of them starts
# emitting is excluded from the corpus once
RE_MACHINE = re.compile(
    r"^\s*(<(task-notification|subagent_notification|turn_aborted|local-command-stdout|post-tool|"
    r"system-reminder|bash-|environment_context|user_instructions|user_shell_command|"
    r"codex_internal_context|skill)\b|# AGENTS\.md instructions for |"
    + re.escape(Claude.COMPACT_OPENING) + ")",
    re.IGNORECASE)
# a slash-command turn: the wrapper is boilerplate, the typed args are his
RE_SLASH = re.compile(r"^\s*<command-(name|message)>")
# the identity of a prompt record: the same words at the same instant are one
# turn, whichever session file a resume copied them into or classifier labelled them
PROMPT_ID = ("text", "ts")
# emphasis tokens i reserve for hard constraints
RE_CAPS = re.compile(r"\b(NOT|DO NOT|DONT|NEVER|ALWAYS|MUST|ONLY|EXACTLY|IMPORTANT|JUST|STOP)\b")
# an approval is a SHORT turn; past this length it is a directive that happens to agree
SHORT_APPROVAL = 70
# a turn this long is a directive even when it carries no other signal
LONG_TURN = 900
# a turn under this length counts as terse in the tone histogram
TERSE_TURN = 40

class Signal(StrEnum):
    """every label the extractor can put on a human turn, named once.

    a turn carries several of these at once (the classes) and exactly one as its
    primary bucket. the vocabulary was spelled as bare strings at each of the
    four sites that use it - the pattern table, the priority order, the
    classifier's extra tests and the view writer - so a new label read as a
    typo at three of them and the set could only be recovered by grep

    # Example

        >>> Signal.bucket({Signal.QUESTION, Signal.HEAT}, Signal.PLAIN)
        <Signal.HEAT: 'heat'>
    """

    HEAT = "heat"
    REJECTION = "rejection"
    APPROVAL = "approval"
    INTERRUPTION = "interruption"
    PLAN = "plan"
    BUILD = "build"
    DECISION = "decision"
    QUESTION = "question"
    DEPLOY = "deploy"
    NAMING = "naming"
    SEQUENCING = "sequencing"
    EMPHASIS = "emphasis"
    DIRECTIVE = "directive"
    PLAIN = "plain"

    @classmethod
    def priority(cls) -> tuple["Signal", ...]:
        """the primary-bucket order: the first of these a turn qualifies for wins.

        the vetoes lead and are never length-gated. the labels absent here are
        classes a turn can carry but never its bucket, and the two fallbacks are
        chosen by turn length rather than by qualifying

        # Returns

        the bucket-eligible labels, most significant first

        # Example

            >>> Signal.priority()[0]
            <Signal.HEAT: 'heat'>
        """
        return (cls.HEAT, cls.REJECTION, cls.APPROVAL, cls.INTERRUPTION,
                cls.PLAN, cls.BUILD, cls.DECISION, cls.QUESTION)

    @classmethod
    def bucket(cls, classes: "Iterable[Signal]", fallback: "Signal") -> "Signal":
        """the one primary bucket for a turn that carries several classes.

        # Arguments

        * `classes` - every label the turn qualified for
        * `fallback` - the bucket when none of the priorities apply

        # Returns

        the highest-priority label present, else the fallback

        # Example

            >>> Signal.bucket({Signal.BUILD, Signal.REJECTION}, Signal.PLAIN)
            <Signal.REJECTION: 'rejection'>
        """
        held = set(classes)
        return next((label for label in cls.priority() if label in held), fallback)


# a pattern that contributes one label whenever it matches, with no extra
# condition. the labels needing a second test stay spelled out in classify()
CLASS_PATTERNS = (
    (RE_PLAN, Signal.PLAN),
    (RE_BUILD, Signal.BUILD),
    (RE_DECIDE, Signal.DECISION),
    (RE_DEPLOY, Signal.DEPLOY),
    (RE_NAMING, Signal.NAMING),
    (RE_SEQ, Signal.SEQUENCING),
    (RE_CAPS, Signal.EMPHASIS),
    (RE_HEAT, Signal.HEAT),
)

@dataclass
class Turn:
    """one human turn pulled from a transcript, before classification."""

    proj: str
    src: str
    text: str
    interrupted: bool = False
    from_plan: bool = False
    ts: str = ""
    session: str = ""


@dataclass
class Reader:
    """reads one transcript, yielding his turns and collecting the prompts he refused.

    what each line says is the harness's to tell (its events); which of his
    words count is this reader's: harness text RE_MACHINE refuses, a slash
    command's typed arguments, the interruption flag carried to his next turn.
    `at` / `session` describe the line being read; `machine` is true once the
    file is known to be a script- or agent-driven session
    """

    transcript: Transcript
    last_asst: str = ""
    pend: bool = False
    denials: list[dict[str, str]] = field(default_factory=list)
    at: str = ""
    session: str = ""
    machine: bool = False

    def events(self) -> "Iterator[Event]":
        """every event of the transcript, in order, stamping the line each came from.

        # Returns
        an iterator of events; `at` and `session` describe the line of the one
        just yielded. raises TranscriptError when the file cannot be read
        """
        for record in self.transcript.records():
            self.at, self.session = record.stamp, record.session
            yield from self.transcript.harness.events(record.data)

    def driven(self) -> bool:
        """whether the file's first line that can say so marks it machine-driven.

        # Returns
        true when that line marks a scripted or agent-driven session; also
        stored on `machine`, with `session` left at that line's
        """
        self.machine = next((event.machine for event in self.events() if isinstance(event, Driven)), False)
        return self.machine

    def turns(self) -> "Iterator[Turn]":
        """yield every human Turn in the file, in order; none from a driven session.

        # Returns
        an iterator of Turn objects; the interrupt flag is consumed by the
        next real turn after an interruption. raises TranscriptError when the
        file cannot be read
        """
        harness = self.transcript.harness
        proj, src = harness.project(self.transcript.path), harness.NAME
        settled = False
        for event in self.events():
            match event:
                # the first line that says who drove the session settles it
                case Driven(machine) if not settled:
                    settled, self.machine = True, machine
                    if machine:
                        return
                case Replied(text):
                    self.last_asst = text
                case Denied(note):
                    self.denials.append({"ts": self.at, "session": self.session, "proj": proj, "src": src,
                                         "was": clip(self.last_asst, 140), "note": clip(note, 180)})
                case Interrupted():
                    self.pend = True
                case Spoke(text) if (said := self.said(text)) is not None:
                    interrupted, self.pend = self.pend, False
                    yield Turn(proj, src, said[0], interrupted, said[1], self.at, self.session)
                case _:
                    pass

    @classmethod
    def said(cls, text: str) -> tuple[str, bool] | None:
        """what of the text in his slot is his.

        # Arguments
        * `text` - the slot's text, as the harness wrote it

        # Returns
        a (text, from_plan) tuple, or None for harness text or an empty slash command

        # Example

            >>> Reader.said("  make it shorter "), Reader.said("<system-reminder>x")
            (('make it shorter', False), None)
        """
        if RE_MACHINE.search(text):
            return None
        if RE_SLASH.match(text):
            return cls.slash_command(text)
        return text.strip(), False

    @staticmethod
    def slash_command(text: str) -> tuple[str, bool] | None:
        """the typed arguments of a slash-command turn.

        the wrapper itself is boilerplate; only what he typed into it is signal,
        and a /plan body is flagged so the classifier can treat it as a plan

        # Arguments
        * `text` - the raw turn text

        # Returns
        an (args, from_plan) tuple, or None when the command carried no args
        """
        name = re.search(r"<command-name>([^<]*)</command-name>", text)
        args = re.search(r"<command-args>([\s\S]*?)</command-args>", text)
        if not args or not args.group(1).strip():
            return None
        return args.group(1).strip(), bool(name and "plan" in name.group(1))


@dataclass
class Corpus:
    """the accumulated, classified corpus and its aggregate statistics."""

    prompts: list[dict[str, Any]] = field(default_factory=list)
    denials: list[dict[str, str]] = field(default_factory=list)
    tone: Counter[str] = field(default_factory=Counter)
    class_counts: Counter[str] = field(default_factory=Counter)
    seq_hist: Counter[str] = field(default_factory=Counter)
    opening_verbs: Counter[str] = field(default_factory=Counter)
    by_source: Counter[str] = field(default_factory=Counter)
    by_proj: Counter[str] = field(default_factory=Counter)
    machine_sessions: set[str] = field(default_factory=set)

    def add(self, turn: "Turn") -> None:
        """classify one turn and fold it into the corpus.

        # Arguments
        * `turn` - the Turn to record
        """
        bucket, classes = self.classify(turn.text, interrupted=turn.interrupted, from_plan=turn.from_plan)
        self.fold({"ts": turn.ts, "session": turn.session, "proj": turn.proj, "src": turn.src,
                       "len": len(turn.text), "bucket": bucket, "classes": classes, "text": clip(turn.text, 500)})

    def fold(self, record: dict[str, Any]) -> None:
        """fold one classified record into every histogram, then store it.

        the single accumulation path: a freshly classified turn and a record
        read back off disk both land here, so a counter added in one place can
        never be missed in the other

        # Arguments
        * `record` - a classified prompt record
        """
        self.tally(record.get("text", ""))
        for cls in record.get("classes", []):
            self.class_counts[cls] += 1
        self.class_counts[record.get("bucket", "plain") + ":bucket"] += 1
        self.by_source[record.get("src", "")] += 1
        self.by_proj[record.get("proj", "")] += 1
        self.prompts.append(record)

    def classify(self, text: str, *, interrupted: bool, from_plan: bool) -> tuple[str, list[str]]:
        """assign one primary bucket and the full multi-label class set.

        # Arguments
        * `text` - the cleaned human turn text
        * `interrupted` - true if this turn cut off a running action
        * `from_plan` - true if this turn was the body of a /plan command

        # Returns
        a (bucket, classes) tuple where classes is a sorted list
        """
        # --------------------------------------------------
        # multi-label classes: a turn can be several at once
        # --------------------------------------------------
        length = len(text)
        classes = {label for pattern, label in CLASS_PATTERNS if pattern.search(text)}
        if from_plan:
            classes.add(Signal.PLAN)
        if "?" in text:
            classes.add(Signal.QUESTION)
        if RE_NO_START.search(text) or RE_REJECT.search(text):
            classes.add(Signal.REJECTION)
        if RE_APPROVE.search(text) and length < SHORT_APPROVAL:
            classes.add(Signal.APPROVAL)
        if interrupted:
            classes.add(Signal.INTERRUPTION)
        # --------------------------------------------------
        # primary bucket: the priority order lives on Signal; directive is the
        # long-turn fallback
        # --------------------------------------------------
        fallback = Signal.DIRECTIVE if length >= LONG_TURN else Signal.PLAIN
        return Signal.bucket(classes, fallback), sorted(classes)

    def tally(self, text: str) -> None:
        """fold one turn into the tone, sequencing, and verb histograms.

        # Arguments
        * `text` - the cleaned human turn text
        """
        # --------------------------------------------------
        # register tone signals
        # --------------------------------------------------
        alpha = re.sub(r"[^a-zA-Z]", "", text)
        if alpha and alpha == alpha.lower():
            self.tone["lower"] += 1
        if "?" in text:
            self.tone["question"] += 1
        if re.search(r"\bplease\b", text, re.IGNORECASE):
            self.tone["please"] += 1
        if RE_CAPS.search(text):
            self.tone["caps"] += 1
        if len(text) < TERSE_TURN:
            self.tone["terse"] += 1
        # --------------------------------------------------
        # sequencing connectives and the opening verb
        # --------------------------------------------------
        low = text.lower()
        for word in SEQ_WORDS:
            if re.search(r"\b" + word + r"\b", low):
                self.seq_hist[word] += 1
        first = re.match(r"^\s*([a-z]+)", low)
        if first:
            self.opening_verbs[first.group(1)] += 1

    def stats(self, harnesses: Harnesses) -> dict[str, Any]:
        """assemble the corpus-stats dict.

        # Arguments
        * `harnesses` - the harnesses whose transcripts were scanned

        # Returns
        the full statistics dict
        """
        total = len(self.prompts)
        # codex first: the order every stored corpus-stats.json spells
        sources = "+".join(harness.NAME for harness in reversed(harnesses.all))
        lens = sorted(p.get("len", 0) for p in self.prompts)
        stamps = sorted(p["ts"] for p in self.prompts if p.get("ts"))
        return {
            "generated_at": iso_now(),
            "covers": {"first_turn": stamps[0] if stamps else "", "last_turn": stamps[-1] if stamps else "",
                        "dated": len(stamps), "undated": total - len(stamps)},
            "totals": {"human_turns": total, "sources_scanned": sources},
            "length_chars": {"p10": self._pct(lens, .1), "p50": self._pct(lens, .5), "p90": self._pct(lens, .9),
                              "p99": self._pct(lens, .99), "max": lens[-1] if lens else 0},
            "tone": {k: round(100 * self.tone[k] / total) if total else 0
                  for k in ("lower", "question", "please", "caps", "terse")},
            "by_source": dict(self.by_source),
            "class_counts": dict(self.class_counts.most_common()),
            "sequencing_hist": dict(self.seq_hist.most_common()),
            "opening_verbs": dict(self.opening_verbs.most_common(20)),
            "top_projects": self.by_proj.most_common(18),
        }

    def write(self, evidence: EvidenceLayout, harnesses: Harnesses) -> dict[Path, MergeCount]:
        """merge this run's records into the evidence store and rebuild the aggregates.

        the two canonical corpora (prompts, denials) are MERGED - they are the
        durable record and may only grow. everything else is DERIVED from the
        merged prompts and overwritten, so a view can never drift away from the
        corpus it claims to project

        # Arguments
        * `evidence` - the evidence files, in the resolved output directory
        * `harnesses` - the harnesses whose transcripts were scanned, for the stats

        # Returns
        a dict of file -> MergeCount for the merged corpora
        """
        evidence.root.mkdir(parents=True, exist_ok=True)
        prompts = Ledger(evidence.prompts, identity=PROMPT_ID)
        # --------------------------------------------------
        # the canonical corpora: merged, never dropped. a stored row today's
        # reader would refuse is MARKED stale rather than deleted - the ledger
        # forgets only by mark - and a slash wrapper stored whole is re-read
        # down to its args first, since its transcript may have expired
        # --------------------------------------------------
        refused: list[dict[str, Any]] = []
        for row in prompts.read():
            if row.get("stale") or not self.refuses(row):
                continue
            refused.append({**row, "stale": True})
            if (slash := Reader.slash_command(row.get("text", ""))) is not None:
                bucket, classes = self.classify(slash[0], interrupted=False, from_plan=slash[1])
                refused.append({**row, "text": clip(slash[0], 500), "len": len(slash[0]),
                                "bucket": bucket, "classes": classes})
        counts = {evidence.prompts: prompts.merge([*self.prompts, *refused]),
                  evidence.denials: Ledger(evidence.denials).merge(self.denials)}
        # --------------------------------------------------
        # re-read the merged corpus: everything below projects the DURABLE set,
        # which is a superset of what this run happened to see
        # --------------------------------------------------
        durable = self.from_records(prompts.read())
        # --------------------------------------------------
        # back-compat views, derived; heat joins the rejection corpus too
        # --------------------------------------------------
        views = {evidence.rejections: (Signal.REJECTION, Signal.HEAT), evidence.heat: (Signal.HEAT,),
                 evidence.interruptions: (Signal.INTERRUPTION,), evidence.approvals: (Signal.APPROVAL,),
                 evidence.directives: (Signal.DIRECTIVE,)}
        for path, buckets in views.items():
            Ledger(path).write(self._view(p) for p in durable.prompts if p.get("bucket") in buckets)
        # --------------------------------------------------
        # stats json, over the durable corpus
        # --------------------------------------------------
        write_text(evidence.corpus_stats, json.dumps(durable.stats(harnesses), indent=2))
        return counts

    @classmethod
    def from_records(cls, rows: Iterable[dict[str, Any]]) -> "Corpus":
        """rebuild a Corpus from already-classified records read back off disk.

        the stored bucket and class labels are reused verbatim; reclassifying
        would let a regex change rewrite history

        # Arguments
        * `rows` - merged prompt records

        # Returns
        a Corpus whose counters describe the whole durable set
        """
        corpus = cls()
        for row in rows:
            if not row.get("stale"):
                corpus.fold(row)
        return corpus

    def refuses(self, row: dict[str, Any]) -> bool:
        """whether today's reader would keep this stored row out of the corpus.

        # Arguments
        * `row` - a prompt record read back off disk

        # Returns
        true for harness text, a stored slash wrapper, or a turn from a session
        this run found to be machine-driven

        # Example

            >>> Corpus().refuses({"text": "<subagent_notification> {}"})
            True
            >>> Corpus().refuses({"text": "make it shorter"})
            False
        """
        text = row.get("text", "")
        return bool(RE_MACHINE.match(text) or RE_SLASH.match(text)) or row.get("session") in self.machine_sessions

    @staticmethod
    def _view(prompt: dict[str, Any]) -> dict[str, str]:
        """project a full prompt record down to the back-compat view shape.

        every field is read defensively: records rescued from the pre-timestamp
        schema carry no `session` at all

        # Arguments
        * `prompt` - a full classified turn record, of any schema vintage

        # Returns
        a small dict with the stamp, project, source, and text
        """
        view = {"ts": prompt.get("ts", ""), "session": prompt.get("session", ""), "proj": prompt.get("proj", ""),
                    "src": prompt.get("src", ""), "text": prompt.get("text", "")}
        # --------------------------------------------------
        # carry the provenance marker so an undated record stays self-describing
        # --------------------------------------------------
        if prompt.get("ts_source"):
            view["ts_source"] = prompt["ts_source"]
        return view

    @staticmethod
    def _pct(values: Sequence[int], quantile: float) -> int:
        """return the value at a quantile of a pre-sorted list.

        # Arguments
        * `values` - a list sorted ascending
        * `quantile` - the quantile in [0, 1]

        # Returns
        the value at that quantile, or 0 for an empty list
        """
        if not values:
            return 0
        return values[min(len(values) - 1, int(quantile * len(values)))]


@dataclass(frozen=True)
class Archiver:
    """gzips each session transcript into cold storage, mirroring the source layout.

    extraction keeps only what the classifiers matched; claude deletes its
    transcripts at roughly 26 days, so without a raw copy a better classifier
    could never be re-run over old material
    """

    harnesses: Harnesses

    def run(self) -> tuple[int, int, int]:
        """archive every unseen or grown transcript.

        a transcript still being appended to is re-archived once it grows; an
        unchanged one is skipped, so this is cheap to run repeatedly

        # Returns
        an (archived, skipped, bytes_written) tuple
        """
        archived, skipped, written = 0, 0, 0
        for transcript in self.harnesses.sessions():
            target = transcript.harness.cold_copy(transcript.path)
            # --------------------------------------------------
            # skip only when the archived copy already covers the live file
            # --------------------------------------------------
            if target.exists() and target.stat().st_mtime >= transcript.path.stat().st_mtime:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with transcript.path.open("rb") as src, gzip.open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            except OSError:
                continue
            written += target.stat().st_size
            archived += 1
        return archived, skipped, written


@dataclass(frozen=True)
class Extractor:
    """walks the transcript sources and feeds every human turn to a Corpus."""

    harnesses: Harnesses

    def run(self) -> "Corpus":
        """read every live transcript into a fresh Corpus.

        a transcript that cannot be read to its end contributes nothing. the
        cold archive is consulted only for WHO drove each session: a row stored
        while its transcript was live outlives that transcript, and the
        archived copy is then the one place that can say it was a script

        # Returns
        the populated Corpus
        """
        corpus = Corpus()
        for transcript in self.harnesses.sessions():
            reader = Reader(transcript)
            try:
                turns = list(reader.turns())
            except TranscriptError:
                continue
            for turn in turns:
                corpus.add(turn)
            corpus.denials.extend(reader.denials)
            if reader.machine:
                corpus.machine_sessions.add(reader.session)
        # --------------------------------------------------
        # the archive, only for which sessions were driven
        # --------------------------------------------------
        for transcript in self.harnesses.archived():
            reader = Reader(transcript)
            try:
                if reader.driven():
                    corpus.machine_sessions.add(reader.session)
            except TranscriptError:
                continue
        return corpus


def main(args: Args) -> None:
    """extract every transcript into the evidence store and print a summary.

    with `--archive`, the live transcripts are copied to the cold archive first,
    so the source is preserved before anything reads it

    # Arguments

    * `args` - the parsed command line; `--out` overrides the evidence directory
      and `--archive-dir` the cold archive
    """
    out, cold = args.value(Flag.OUT), args.value(Flag.ARCHIVE_DIR)
    evidence = EvidenceLayout((Path(out) if out else DataLayout.discover().evidence.root).resolve())
    archive = (Path(cold) if cold else find_archive()).resolve()
    harnesses = Harnesses.discover(archive)
    # --------------------------------------------------
    # archive first: the source must be preserved BEFORE anything reads it
    # --------------------------------------------------
    if args.has(Flag.ARCHIVE):
        archived, skipped, size = Archiver(harnesses).run()
        print(f"{TOOL} archive -> {archive}\n"
              f"  archived: {archived} | unchanged: {skipped} | {size / 1e6:.1f} MB written")
    # --------------------------------------------------
    # extract + merge
    # --------------------------------------------------
    corpus = Extractor(harnesses).run()
    counts = corpus.write(evidence, harnesses)
    buckets = Counter(p["bucket"] for p in corpus.prompts)
    print(f"{TOOL} done ->", evidence.root)
    print(f"  scanned: {len(corpus.prompts)} turns | " + " ".join(f"{k}:{v}" for k, v in buckets.most_common()))
    print(f"  machine-driven sessions excluded: {len(corpus.machine_sessions)}")
    for path, count in sorted(counts.items()):
        print(f"  {path.name:<22} +{count.added:<5} -> {count.total}")
    # a second machine appending to the same corpus is the normal case, and a
    # line-based merge over a set conflicts where no conflict exists
    for warning in sorted({Ledger(path).unprotected() for path in counts}):
        if warning:
            print(f"  warn: {warning}")


if __name__ == "__main__":
    Tool(TOOL, __doc__, flags=(Flag.OUT, Flag.ARCHIVE, Flag.ARCHIVE_DIR)).run(main)
