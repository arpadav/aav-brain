#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-extract: distill my interaction fingerprint into the brain store.

distilled from raw agent transcripts, stdlib only, safe to run any time

    uv run brain-extract.py              (or: python3 brain-extract.py)
    uv run brain-extract.py --out DIR    (default: the XDG data dir, $XDG_DATA_HOME/aav-brain/evidence)
    uv run brain-extract.py --archive    (also cold-store the raw transcripts first)

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
# this file, alone in bin/, walks raw transcript json whose shape no schema
# describes - a content block is whatever the harness wrote that day. the
# Unknown-type family is suppressed HERE and nowhere else, so the rest of the
# tools keep it (P34: the records are untrusted input, hence the isinstance
# guards below rather than a trusted shape)
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import ENCODING, DataLayout, Env, Flag, Ledger, MergeCount, clip, find_archive, iso_now, write_text

# --------------------------------------------------
# external
# --------------------------------------------------
import argparse
import gzip
import json
import re
import shutil
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------
# constants
# --------------------------------------------------
# home directory root, used to locate every transcript source. portable -
# resolves to whatever machine this runs on, not a hardcoded path
HOME = Path.home()
# transcript sources as (root, tool-label). the label is a fact about
# which tool produced the turn, not a coupling to that tool
SOURCES = [
    (HOME / ".claude/projects", "claude"),
    (HOME / ".codex/sessions", "codex"),
    (HOME / ".codex/archived_sessions", "codex"),
]
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
# permission-denial marker emitted by the claude harness in a tool_result
RE_DENY = re.compile(
    r"(doesn't want to (proceed|take this action)|user (rejected|doesn't want|has interrupted)|"
    r"rejected the|user chose not)", re.IGNORECASE)
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
# turns whose text is harness noise rather than a human prompt
RE_NOISE = re.compile(r"^\s*<(task-notification|local-command-stdout|post-tool|system-reminder|bash-)", re.IGNORECASE)
# codex wrappers that are environment scaffolding, not a prompt
RE_WRAP = re.compile(r"^\s*<(environment_context|user_instructions|task-notification|system-reminder)", re.IGNORECASE)
# emphasis tokens i reserve for hard constraints
RE_CAPS = re.compile(r"\b(NOT|DO NOT|DONT|NEVER|ALWAYS|MUST|ONLY|EXACTLY|IMPORTANT|JUST|STOP)\b")

def short_proj(name: str) -> str:
    """shorten an encoded project-dir name to a readable label.

    # Arguments
    * `name` - the path-encoded project directory name

    # Returns
    a short label with the common home/repo prefixes stripped
    """
    # discover the home prefix instead of hardcoding a username (P32): claude/codex
    # encode an abs path as `/`->`-`, so $HOME (e.g. the user home dir) maps the same way
    home = str(Path.home()).replace("/", "-")
    return (name.replace(f"{home}-repos-personal-", "")
                .replace(f"{home}-repos-", "")
                .replace(f"{home}-", "")[:28]) or name


# a pattern that contributes one label whenever it matches, with no extra
# condition. the labels needing a second test stay spelled out in classify()
CLASS_PATTERNS = (
    (RE_PLAN, "plan"),
    (RE_BUILD, "build"),
    (RE_DECIDE, "decision"),
    (RE_DEPLOY, "deploy"),
    (RE_NAMING, "naming"),
    (RE_SEQ, "sequencing"),
    (RE_CAPS, "emphasis"),
    (RE_HEAT, "heat"),
)
# the primary bucket is the first of these a turn qualifies for
BUCKET_PRIORITY = ("heat", "rejection", "approval", "interruption", "plan", "build", "decision", "question")
# an approval is a SHORT turn; past this length it is a directive that happens to agree
SHORT_APPROVAL = 70
# a turn this long is a directive even when it carries no other signal
LONG_TURN = 900
# a turn under this length counts as terse in the tone histogram
TERSE_TURN = 40

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
    """reads one transcript file, yielding human turns and collecting denials.

    `at` / `session` track the record currently being read
    """

    path: Path
    proj: str
    src: str
    last_asst: str = ""
    pend: bool = False
    denials: list[dict[str, str]] = field(default_factory=list)
    at: str = ""
    session: str = ""

    def turns(self) -> "Iterator[Turn]":
        """yield every human Turn in the file, in order.

        # Returns
        an iterator of Turn objects; the interrupt flag is consumed by the
        next real turn after an interruption marker
        """
        try:
            raw = self.path.read_text(encoding=ENCODING, errors="replace")
        except OSError:
            return
        for line in raw.split("\n"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            # --------------------------------------------------
            # stamp the record being read: both tools write a top-level iso-8601
            # `timestamp`. the session id is per-record on claude and encoded in
            # the rollout filename on codex, so the file stem is the fallback
            # --------------------------------------------------
            self.at = str(obj.get("timestamp") or "")
            self.session = str(obj.get("sessionId") or obj.get("session_id") or "") or self.path.stem
            result = self._read_claude(obj) if self.src == "claude" else self._read_codex(obj)
            if result is None:
                continue
            text, from_plan = result
            interrupted = self.pend
            self.pend = False
            yield Turn(self.proj, self.src, text, interrupted, from_plan, self.at, self.session)

    def _remember_assistant(self, obj: dict[str, Any]) -> bool:
        """keep the last assistant turn, which gives an interruption its context.

        # Arguments
        * `obj` - the parsed jsonl object

        # Returns
        true when the record was an assistant turn and is now consumed
        """
        if obj.get("type") != "assistant" or not isinstance(obj.get("message"), dict):
            return False
        content = obj["message"].get("content")
        if isinstance(content, list):
            blocks: list[Any] = content
            spoken = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            if spoken.strip():
                self.last_asst = spoken
        return True

    def _collect_denials(self, content: Any) -> None:  # noqa: ANN401 - a transcript content field has no schema
        """record every permission denial carried by a tool_result block.

        # Arguments
        * `content` - the user message's content field, straight off json
        """
        if not isinstance(content, list):
            return
        blocks: list[Any] = content
        for block in blocks:
            if block.get("type") != "tool_result":
                continue
            note: Any = block.get("content", "")
            if isinstance(note, list):
                note = " ".join(x.get("text", "") for x in note)
            if isinstance(note, str) and RE_DENY.search(note):
                self.denials.append({"ts": self.at, "session": self.session, "proj": self.proj, "src": self.src,
                                     "was": clip(self.last_asst, 140), "note": clip(note, 180)})

    @staticmethod
    def _human_text(content: Any) -> str:  # noqa: ANN401 - a transcript content field has no schema
        """the spoken text of a user record, whether string or block list.

        # Arguments
        * `content` - the user message's content field, straight off json

        # Returns
        the text, empty when the record carries none
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            blocks: list[Any] = content
            return "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return ""

    @staticmethod
    def _slash_command(text: str) -> tuple[str, bool] | None:
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

    def _read_claude(self, obj: dict[str, Any]) -> tuple[str, bool] | None:
        """extract a human turn from one claude jsonl record.

        # Arguments
        * `obj` - the parsed jsonl object

        # Returns
        a (text, from_plan) tuple, or None for a non-human record
        """
        if self._remember_assistant(obj):
            return None
        if obj.get("type") != "user" or not isinstance(obj.get("message"), dict):
            return None
        content = obj["message"].get("content")
        self._collect_denials(content)
        text = self._human_text(content)
        if not text.strip():
            return None
        # --------------------------------------------------
        # interruption marker: arm the flag for the next real turn
        # --------------------------------------------------
        if re.search(r"\[Request interrupted by user", text):
            self.pend = True
            self.last_asst = clip(self.last_asst, 170)
            return None
        if obj.get("isMeta") or RE_NOISE.search(text):
            return None
        if re.match(r"^\s*<command-name>", text):
            return self._slash_command(text)
        return text.strip(), False

    def _read_codex(self, obj: dict[str, Any]) -> tuple[str, bool] | None:
        """extract a human turn from one codex rollout record.

        # Arguments
        * `obj` - the parsed rollout object

        # Returns
        a (text, from_plan) tuple, or None for a non-human record
        """
        payload = obj.get("payload", {})
        # --------------------------------------------------
        # aborted turn: the next user turn is an interruption
        # --------------------------------------------------
        if payload.get("type") in ("turn_aborted", "task_aborted"):
            self.pend = True
            return None
        # --------------------------------------------------
        # assistant text: remember it for interruption context
        # --------------------------------------------------
        if (payload.get("type") == "message" and payload.get("role") == "assistant"
                and isinstance(payload.get("content"), list)):
            spoken = " ".join(c.get("text", "") for c in payload["content"])
            if spoken.strip():
                self.last_asst = spoken
            return None
        # --------------------------------------------------
        # human text, minus environment scaffolding
        # --------------------------------------------------
        if (payload.get("type") == "message" and payload.get("role") == "user"
                and isinstance(payload.get("content"), list)):
            text = "\n".join(c.get("text", "") for c in payload["content"]).strip()
            if not text or RE_WRAP.match(text):
                return None
            return text, False
        return None


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
            classes.add("plan")
        if "?" in text:
            classes.add("question")
        if RE_NO_START.search(text) or RE_REJECT.search(text):
            classes.add("rejection")
        if RE_APPROVE.search(text) and length < SHORT_APPROVAL:
            classes.add("approval")
        if interrupted:
            classes.add("interruption")
        # --------------------------------------------------
        # primary bucket: the first priority that applies. vetoes (heat,
        # rejection) lead and are never length-gated; directive is the
        # long-turn fallback
        # --------------------------------------------------
        fallback = "directive" if length >= LONG_TURN else "plain"
        bucket = next((b for b in BUCKET_PRIORITY if b in classes), fallback)
        return bucket, sorted(classes)

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

    def stats(self) -> dict[str, Any]:
        """assemble the corpus-stats dict.

        # Returns
        the full statistics dict
        """
        total = len(self.prompts)
        lens = sorted(p.get("len", 0) for p in self.prompts)
        stamps = sorted(p["ts"] for p in self.prompts if p.get("ts"))
        return {
            "generated_at": iso_now(),
            "covers": {"first_turn": stamps[0] if stamps else "", "last_turn": stamps[-1] if stamps else "",
                        "dated": len(stamps), "undated": total - len(stamps)},
            "totals": {"human_turns": total, "sources_scanned": "codex+claude"},
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

    def fingerprint_md(self) -> str:
        """render the quantitative fingerprint tables from the stats.

        these tables are the one source of truth for the numbers; the
        fingerprint doc references this generated file instead of hardcoding
        figures that drift (the served_by-is-derived move, applied - P20)

        # Returns
        a markdown string with the totals, tone, and class-count tables
        """
        stats = self.stats()
        total = stats["totals"]["human_turns"]
        src = stats["by_source"]
        # --------------------------------------------------
        # header and totals
        # --------------------------------------------------
        lines = ["# fingerprint stats (generated by brain-extract.py - do not hand-edit)", "",
                 f"turns: {total}  (codex {src.get('codex', 0)} / claude {src.get('claude', 0)})", ""]
        # --------------------------------------------------
        # tone table
        # --------------------------------------------------
        lines += ["## tone", "", "| signal | value |", "|---|---|"]
        for key, val in stats["tone"].items():
            lines.append(f"| {key} | {val}% |")
        # --------------------------------------------------
        # class counts (multi-label), excluding the bucket tally keys
        # --------------------------------------------------
        lines += ["", "## classes (multi-label, % of turns)", "", "| class | count | pct |", "|---|---|---|"]
        for key, val in stats["class_counts"].items():
            if key.endswith(":bucket"):
                continue
            lines.append(f"| {key} | {val} | {round(100 * val / total)}% |")
        # --------------------------------------------------
        # sequencing connectives and opening verbs
        # --------------------------------------------------
        seq = ", ".join(f"{k} {v}" for k, v in stats["sequencing_hist"].items())
        verbs = ", ".join(f"{k} {v}" for k, v in list(stats["opening_verbs"].items())[:10])
        lines += ["", f"sequencing: {seq}", "", f"opening verbs: {verbs}", ""]
        return "\n".join(lines)

    def write(self, out: Path) -> dict[str, MergeCount]:
        """merge this run's records into the evidence store and rebuild the aggregates.

        the two canonical corpora (prompts, denials) are MERGED - they are the
        durable record and may only grow. everything else is DERIVED from the
        merged prompts and overwritten, so a view can never drift away from the
        corpus it claims to project

        # Arguments
        * `out` - the resolved output directory

        # Returns
        a dict of file-name -> MergeCount for the merged corpora
        """
        out.mkdir(parents=True, exist_ok=True)
        # --------------------------------------------------
        # the canonical corpora: merged, never dropped
        # --------------------------------------------------
        counts = {"prompts.jsonl": Ledger(out / "prompts.jsonl").merge(self.prompts),
                  "denials.jsonl": Ledger(out / "denials.jsonl").merge(self.denials)}
        # --------------------------------------------------
        # re-read the merged corpus: everything below projects the DURABLE set,
        # which is a superset of what this run happened to see
        # --------------------------------------------------
        durable = self.from_records(Ledger(out / "prompts.jsonl").read())
        # --------------------------------------------------
        # back-compat views, derived; heat joins the rejection corpus too
        # --------------------------------------------------
        views = {"rejections.jsonl": ("rejection", "heat"), "heat.jsonl": ("heat",),
                 "interruptions.jsonl": ("interruption",), "approvals.jsonl": ("approval",),
                 "directives.jsonl": ("directive",)}
        for name, buckets in views.items():
            Ledger(out / name).write(self._view(p) for p in durable.prompts if p.get("bucket") in buckets)
        # --------------------------------------------------
        # stats json + the generated fingerprint tables, over the durable corpus
        # --------------------------------------------------
        write_text(out / "corpus-stats.json", json.dumps(durable.stats(), indent=2))
        write_text(out / "fingerprint-stats.md", durable.fingerprint_md())
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
            corpus.fold(row)
        return corpus

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


@dataclass
class Transcript:
    """one located transcript file: where it is, and whose session it was.

    `rel` is the path relative to its source root, so the archiver can mirror
    the source layout instead of flattening it - the project directory IS the
    `proj` label, and a flat archive would throw it away
    """

    path: Path
    rel: Path
    proj: str
    src: str


@dataclass(frozen=True)
class Transcripts:
    """the authoritative source set - the ONE definition of a session transcript.

    both the extractor and the archiver walk this, so they cannot disagree about
    what exists. SUBAGENT transcripts (`<session>/subagents/*.jsonl`) are
    deliberately excluded: their human turns are agent dispatch prompts, not his
    words, and mining them would break the prime rule
    """

    roots: Sequence[tuple[Path, str]]

    def files(self) -> "Iterator[Transcript]":
        """yield every session transcript across all sources, in stable order.

        dispatch is by tool LABEL, not list position, so the source order is
        not a magic contract: claude lays out one project dir per repo with
        flat jsonl inside; codex nests date-rollout trees under each root

        # Returns
        an iterator of Transcript
        """
        for root, label in self.roots:
            if not root.exists():
                continue
            # --------------------------------------------------
            # claude: one project dir per repo, sessions flat inside it. the
            # non-recursive glob is what excludes the subagents/ subtree
            # --------------------------------------------------
            if label == "claude":
                for project in sorted(root.iterdir()):
                    if not project.is_dir():
                        continue
                    for path in sorted(project.glob("*.jsonl")):
                        yield Transcript(path, path.relative_to(root), short_proj(project.name), "claude")
            # --------------------------------------------------
            # codex: date-nested rollout trees under each session root
            # --------------------------------------------------
            else:
                for path in sorted(root.rglob("*.jsonl")):
                    yield Transcript(path, path.relative_to(root), "codex", label)


@dataclass(frozen=True)
class Archiver:
    """gzips each session transcript into cold storage, mirroring the source layout.

    extraction keeps only what the classifiers matched; claude deletes its
    transcripts at roughly 26 days, so without a raw copy a better classifier
    could never be re-run over old material
    """

    transcripts: Transcripts
    root: Path

    def run(self) -> tuple[int, int, int]:
        """archive every unseen or grown transcript.

        a transcript still being appended to is re-archived once it grows; an
        unchanged one is skipped, so this is cheap to run repeatedly

        # Returns
        an (archived, skipped, bytes_written) tuple
        """
        archived, skipped, written = 0, 0, 0
        for item in self.transcripts.files():
            target = self.root / item.src / item.rel.with_suffix(".jsonl.gz")
            # --------------------------------------------------
            # skip only when the archived copy already covers the live file
            # --------------------------------------------------
            if target.exists() and target.stat().st_mtime >= item.path.stat().st_mtime:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with item.path.open("rb") as src, gzip.open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            except OSError:
                continue
            written += target.stat().st_size
            archived += 1
        return archived, skipped, written


@dataclass(frozen=True)
class Extractor:
    """walks the transcript sources and feeds every human turn to a Corpus."""

    transcripts: Transcripts

    def run(self) -> "Corpus":
        """read every file into a fresh Corpus.

        # Returns
        the populated Corpus
        """
        corpus = Corpus()
        for item in self.transcripts.files():
            reader = Reader(item.path, item.proj, item.src)
            for turn in reader.turns():
                corpus.add(turn)
            corpus.denials.extend(reader.denials)
        return corpus


def main() -> None:
    """extract every transcript into the evidence store and print a summary."""
    # --------------------------------------------------
    # argparse, so an unrecognised flag errors instead of silently extracting
    # --------------------------------------------------
    parser = argparse.ArgumentParser(prog="brain-extract", description=(__doc__ or "").split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(Flag.OUT, type=Path, default=None,
                        help=f"evidence dir (default: ${Env.XDG_DATA_HOME}/aav-brain/evidence)")
    parser.add_argument(Flag.ARCHIVE, action="store_true",
                        help="cold-store the raw transcripts before extracting")
    parser.add_argument(Flag.ARCHIVE_DIR, type=Path, default=None,
                        help=f"cold-storage root (default: ${Env.XDG_DATA_HOME}/aav-brain-archive, OUTSIDE git)")
    args = parser.parse_args()
    data = DataLayout.discover()
    out = (args.out or data.evidence).resolve()
    transcripts = Transcripts(SOURCES)
    # --------------------------------------------------
    # archive first: the source must be preserved BEFORE anything reads it
    # --------------------------------------------------
    if args.archive:
        root = (args.archive_dir or find_archive()).resolve()
        archived, skipped, size = Archiver(transcripts, root).run()
        print(f"brain-extract archive -> {root}\n"
              f"  archived: {archived} | unchanged: {skipped} | {size / 1e6:.1f} MB written")
    # --------------------------------------------------
    # extract + merge
    # --------------------------------------------------
    corpus = Extractor(transcripts).run()
    counts = corpus.write(out)
    buckets = Counter(p["bucket"] for p in corpus.prompts)
    print("brain-extract done ->", out)
    print(f"  scanned: {len(corpus.prompts)} turns | " + " ".join(f"{k}:{v}" for k, v in buckets.most_common()))
    for name, count in sorted(counts.items()):
        print(f"  {name:<22} +{count.added:<5} -> {count.total}")


if __name__ == "__main__":
    main()
