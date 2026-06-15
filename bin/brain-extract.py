#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-extract: distill my full interaction fingerprint from raw agent
transcripts into the queryable brain store. stdlib only. run any time.

    uv run brain-extract.py            (or: python3 brain-extract.py)
    uv run brain-extract.py --out DIR  (default: the XDG data dir, $XDG_DATA_HOME/aav-brain/evidence)

every human turn is captured into prompts.jsonl with a primary bucket and
a multi-label class set - nothing is dropped. sources are both my codex
and my claude sessions; this is a general agent fingerprint.

prime rule: an applied edit is NOT consent. mine only explicit signal -
the words i actually wrote, never an accepted diff.

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from brainlib import clip, find_data

# --------------------------------------------------
# constants
# --------------------------------------------------
# home directory root, used to locate every transcript source. portable -
# resolves to whatever machine this runs on, not a hardcoded path
HOME = Path.home()
# this script's directory, used to resolve the default output path
HERE = Path(__file__).resolve().parent
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
    r"bad idea|i dont|that's wrong|thats wrong|wtf|never (do|use|put))\b", re.I)
# blunt openers that signal a correction at the very start of a turn
RE_NO_START = re.compile(r"^\s*(no\b|nope|nah|wrong|stop|pause|wait|actually|hold on|hmm,? no)", re.I)
# terse confirmation, recognised only on short turns so it doesnt over-fire
RE_APPROVE = re.compile(
    r"^\s*(yes\b|yep|yeah|yup|correct\b|perfect|exactly|lgtm|looks good|sounds good|do it|"
    r"go ahead|proceed|ship it|approved|great\b|nice\b|ok\b|okay|love it|👍|💯)", re.I)
# permission-denial marker emitted by the claude harness in a tool_result
RE_DENY = re.compile(
    r"(doesn't want to (proceed|take this action)|user (rejected|doesn't want|has interrupted)|"
    r"rejected the|user chose not)", re.I)
# planning intent: the affirmative blueprint, not a rejection
RE_PLAN = re.compile(r"\b(make|create|write|draft).{0,24}\bplan\b|jumping off|plan mode|multi-phase plan", re.I)
# a build/feature request, recognised at the start of the turn
RE_BUILD = re.compile(r"^\s*(make|build|implement|create|add|write|scaffold|set ?up|generate|convert|refactor)\b", re.I)
# a standing decision or stated preference
RE_DECIDE = re.compile(
    r"\b(instead of|use .{0,30} not\b|lets use|let's use|i want|i prefer|i like|go with|rather than|"
    r"should be|stick with|we use|i use|always use|never use)\b", re.I)
# naming / micro-convention preference
RE_NAMING = re.compile(
    r"\b(name it|call it|rename|combined imports|snake_case|camelcase|kebab|naming|the name|"
    r"doc.?comment|separator|module layout|file name|call this)\b", re.I)
# sequencing / workflow ordering - my single most prevalent tell
RE_SEQ = re.compile(
    r"\b(first|then|next|after that|afterwards|once (you|its|it's|that)|lastly|finally|"
    r"step \d|to start|to begin|^1\.|^\s*\d\.)\b", re.I | re.M)
# the sequencing connectives counted into a histogram
SEQ_WORDS = ["first", "then", "next", "after", "once", "lastly", "finally", "before", "afterwards"]
# profanity / heat: my hottest vetoes - a hard rule just broke (P15).
RE_HEAT = re.compile(
    r"\b(idiot|stupid|dumbass|retard|wtf|fuck|fucking|shit|dogshit|bullshit|the hell|"
    r"for the love of god|what the hell|why the fuck)\b", re.I)
# deploy / infra standing preferences - a real recurring cluster
RE_DEPLOY = re.compile(
    r"\b(docker|dockerfile|cloudflared|truenas|0\.0\.0\.0|compose|nginx|deploy|expose|"
    r"port \d|mount a? ?volume|systemd|axum|tunnel)\b", re.I)
# turns whose text is harness noise rather than a human prompt
RE_NOISE = re.compile(r"^\s*<(task-notification|local-command-stdout|post-tool|system-reminder|bash-)", re.I)
# codex wrappers that are environment scaffolding, not a prompt
RE_WRAP = re.compile(r"^\s*<(environment_context|user_instructions|task-notification|system-reminder)", re.I)
# emphasis tokens i reserve for hard constraints
RE_CAPS = re.compile(r"\b(NOT|DO NOT|DONT|NEVER|ALWAYS|MUST|ONLY|EXACTLY|IMPORTANT|JUST|STOP)\b")

# --------------------------------------------------
# helpers (pure)
# --------------------------------------------------


def short_proj(name):
    """shorten an encoded project-dir name to a readable label.

    # Arguments
    * `name` - the path-encoded project directory name.

    # Returns
    a short label with the common home/repo prefixes stripped.
    """
    # discover the home prefix instead of hardcoding a username (P32): claude/codex
    # encode an abs path as `/`->`-`, so $HOME (e.g. the user home dir) maps the same way.
    home = str(Path.home()).replace("/", "-")
    return (name.replace(f"{home}-repos-personal-", "")
                .replace(f"{home}-repos-", "")
                .replace(f"{home}-", "")[:28]) or name


# --------------------------------------------------
# types
# --------------------------------------------------
@dataclass
class Turn:
    """one human turn pulled from a transcript, before classification."""

    proj: str
    src: str
    text: str
    interrupted: bool = False
    from_plan: bool = False


@dataclass
class Reader:
    """reads one transcript file, yielding human turns and collecting denials."""

    path: Path
    proj: str
    src: str
    last_asst: str = ""
    pend: bool = False
    denials: list = field(default_factory=list)

    def turns(self):
        """yield every human Turn in the file, in order.

        # Returns
        an iterator of Turn objects; the interrupt flag is consumed by the
        next real turn after an interruption marker.
        """
        try:
            raw = self.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for line in raw.split("\n"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            result = self._read_claude(obj) if self.src == "claude" else self._read_codex(obj)
            if result is None:
                continue
            text, from_plan = result
            interrupted = self.pend
            self.pend = False
            yield Turn(self.proj, self.src, text, interrupted, from_plan)

    def _read_claude(self, obj):
        """extract a human turn from one claude jsonl record.

        # Arguments
        * `obj` - the parsed jsonl object.

        # Returns
        a (text, from_plan) tuple, or None for a non-human record.
        """
        # --------------------------------------------------
        # assistant text: remember it for interruption context
        # --------------------------------------------------
        if obj.get("type") == "assistant" and isinstance(obj.get("message"), dict):
            content = obj["message"].get("content")
            if isinstance(content, list):
                spoken = " ".join(b.get("text", "") for b in content if b.get("type") == "text")
                if spoken.strip():
                    self.last_asst = spoken
            return None
        if obj.get("type") != "user" or not isinstance(obj.get("message"), dict):
            return None
        content = obj["message"].get("content")
        # --------------------------------------------------
        # permission denial: capture it as its own signal
        # --------------------------------------------------
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result":
                    note = block.get("content", "")
                    if isinstance(note, list):
                        note = " ".join(x.get("text", "") for x in note)
                    if isinstance(note, str) and RE_DENY.search(note):
                        self.denials.append(dict(proj=self.proj, was=clip(self.last_asst, 140), note=clip(note, 180)))
        # --------------------------------------------------
        # human text: string content or joined text blocks
        # --------------------------------------------------
        text = content if isinstance(content, str) else (
            "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
            if isinstance(content, list) else "")
        if not text or not text.strip():
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
        # --------------------------------------------------
        # slash command: keep the typed args, flag /plan bodies
        # --------------------------------------------------
        if re.match(r"^\s*<command-name>", text):
            name = re.search(r"<command-name>([^<]*)</command-name>", text)
            args = re.search(r"<command-args>([\s\S]*?)</command-args>", text)
            if not args or not args.group(1).strip():
                return None
            return args.group(1).strip(), bool(name and "plan" in name.group(1))
        return text.strip(), False

    def _read_codex(self, obj):
        """extract a human turn from one codex rollout record.

        # Arguments
        * `obj` - the parsed rollout object.

        # Returns
        a (text, from_plan) tuple, or None for a non-human record.
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
        if payload.get("type") == "message" and payload.get("role") == "assistant" and isinstance(payload.get("content"), list):
            spoken = " ".join(c.get("text", "") for c in payload["content"])
            if spoken.strip():
                self.last_asst = spoken
            return None
        # --------------------------------------------------
        # human text, minus environment scaffolding
        # --------------------------------------------------
        if payload.get("type") == "message" and payload.get("role") == "user" and isinstance(payload.get("content"), list):
            text = "\n".join(c.get("text", "") for c in payload["content"]).strip()
            if not text or RE_WRAP.match(text):
                return None
            return text, False
        return None


@dataclass
class Corpus:
    """the accumulated, classified corpus and its aggregate statistics."""

    prompts: list = field(default_factory=list)
    denials: list = field(default_factory=list)
    tone: Counter = field(default_factory=Counter)
    class_counts: Counter = field(default_factory=Counter)
    seq_hist: Counter = field(default_factory=Counter)
    opening_verbs: Counter = field(default_factory=Counter)
    by_source: Counter = field(default_factory=Counter)
    by_proj: Counter = field(default_factory=Counter)

    def add(self, turn):
        """classify and tally one turn into the corpus.

        # Arguments
        * `turn` - the Turn to record.
        """
        self.tally(turn.text)
        bucket, classes = self.classify(turn.text, turn.interrupted, turn.from_plan)
        for cls in classes:
            self.class_counts[cls] += 1
        self.class_counts[bucket + ":bucket"] += 1
        self.by_source[turn.src] += 1
        self.by_proj[turn.proj] += 1
        self.prompts.append(dict(proj=turn.proj, src=turn.src, len=len(turn.text), bucket=bucket,
                                 classes=classes, text=clip(turn.text, 500)))

    def classify(self, text, interrupted, from_plan):
        """assign one primary bucket and the full multi-label class set.

        # Arguments
        * `text` - the cleaned human turn text.
        * `interrupted` - true if this turn cut off a running action.
        * `from_plan` - true if this turn was the body of a /plan command.

        # Returns
        a (bucket, classes) tuple where classes is a sorted list.
        """
        # --------------------------------------------------
        # multi-label classes: a turn can be several at once
        # --------------------------------------------------
        classes = set()
        length = len(text)
        if from_plan or RE_PLAN.search(text):
            classes.add("plan")
        if RE_BUILD.search(text):
            classes.add("build")
        if RE_DECIDE.search(text):
            classes.add("decision")
        if RE_DEPLOY.search(text):
            classes.add("deploy")
        if "?" in text:
            classes.add("question")
        if RE_NAMING.search(text):
            classes.add("naming")
        if RE_SEQ.search(text):
            classes.add("sequencing")
        if RE_CAPS.search(text):
            classes.add("emphasis")
        if RE_NO_START.search(text) or RE_REJECT.search(text):
            classes.add("rejection")
        if RE_HEAT.search(text):
            classes.add("heat")
        if RE_APPROVE.search(text) and length < 70:
            classes.add("approval")
        if interrupted:
            classes.add("interruption")
        # --------------------------------------------------
        # primary bucket: vetoes (heat, rejection) outrank all and
        # are never length-gated; directive is the long-turn fallback
        # --------------------------------------------------
        if "heat" in classes:
            bucket = "heat"
        elif "rejection" in classes:
            bucket = "rejection"
        elif "approval" in classes:
            bucket = "approval"
        elif interrupted:
            bucket = "interruption"
        elif "plan" in classes:
            bucket = "plan"
        elif "build" in classes:
            bucket = "build"
        elif "decision" in classes:
            bucket = "decision"
        elif "question" in classes:
            bucket = "question"
        elif length >= 900:
            bucket = "directive"
        else:
            bucket = "plain"
        return bucket, sorted(classes)

    def tally(self, text):
        """fold one turn into the tone, sequencing, and verb histograms.

        # Arguments
        * `text` - the cleaned human turn text.
        """
        # --------------------------------------------------
        # register tone signals
        # --------------------------------------------------
        alpha = re.sub(r"[^a-zA-Z]", "", text)
        if alpha and alpha == alpha.lower():
            self.tone["lower"] += 1
        if "?" in text:
            self.tone["question"] += 1
        if re.search(r"\bplease\b", text, re.I):
            self.tone["please"] += 1
        if RE_CAPS.search(text):
            self.tone["caps"] += 1
        if len(text) < 40:
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

    def stats(self):
        """assemble the corpus-stats dict.

        # Returns
        the full statistics dict.
        """
        total = len(self.prompts)
        lens = sorted(p["len"] for p in self.prompts)
        return dict(
            generated_at_note="timestamp intentionally omitted; re-run to refresh",
            totals=dict(human_turns=total, sources_scanned="codex+claude"),
            length_chars=dict(p10=self._pct(lens, .1), p50=self._pct(lens, .5), p90=self._pct(lens, .9),
                              p99=self._pct(lens, .99), max=lens[-1] if lens else 0),
            tone={k: round(100 * self.tone[k] / total) if total else 0
                  for k in ("lower", "question", "please", "caps", "terse")},
            by_source=dict(self.by_source),
            class_counts=dict(self.class_counts.most_common()),
            sequencing_hist=dict(self.seq_hist.most_common()),
            opening_verbs=dict(self.opening_verbs.most_common(20)),
            top_projects=self.by_proj.most_common(18),
        )

    def fingerprint_md(self):
        """render the quantitative fingerprint tables from the stats.

        these tables are the one source of truth for the numbers; the
        fingerprint doc references this generated file instead of hardcoding
        figures that drift (the served_by-is-derived move, applied - P20).

        # Returns
        a markdown string with the totals, tone, and class-count tables.
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

    def write(self, out):
        """write prompts.jsonl, the views, the stats, and the generated tables.

        # Arguments
        * `out` - the resolved output directory.
        """
        out.mkdir(parents=True, exist_ok=True)
        # --------------------------------------------------
        # the canonical corpus: every turn, never dropped
        # --------------------------------------------------
        self._write_jsonl(out / "prompts.jsonl", self.prompts)
        # --------------------------------------------------
        # back-compat views; heat joins the rejection corpus too
        # --------------------------------------------------
        self._write_jsonl(out / "rejections.jsonl", [self._view(p) for p in self.prompts if p["bucket"] in ("rejection", "heat")])
        self._write_jsonl(out / "heat.jsonl", [self._view(p) for p in self.prompts if p["bucket"] == "heat"])
        self._write_jsonl(out / "interruptions.jsonl", [self._view(p) for p in self.prompts if p["bucket"] == "interruption"])
        self._write_jsonl(out / "approvals.jsonl", [self._view(p) for p in self.prompts if p["bucket"] == "approval"])
        self._write_jsonl(out / "directives.jsonl", [self._view(p) for p in self.prompts if p["bucket"] == "directive"])
        self._write_jsonl(out / "denials.jsonl", self.denials)
        # --------------------------------------------------
        # stats json + the generated fingerprint tables
        # --------------------------------------------------
        (out / "corpus-stats.json").write_text(json.dumps(self.stats(), indent=2), encoding="utf-8")
        (out / "fingerprint-stats.md").write_text(self.fingerprint_md(), encoding="utf-8")

    @staticmethod
    def _view(prompt):
        """project a full prompt record down to the back-compat view shape.

        # Arguments
        * `prompt` - a full classified turn record.

        # Returns
        a small dict with the project, source, and text only.
        """
        return dict(proj=prompt["proj"], src=prompt["src"], text=prompt["text"])

    @staticmethod
    def _write_jsonl(path, rows):
        """write a list of dicts as one json object per line.

        # Arguments
        * `path` - the destination file path.
        * `rows` - the list of json-serialisable dicts.
        """
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    @staticmethod
    def _pct(values, quantile):
        """return the value at a quantile of a pre-sorted list.

        # Arguments
        * `values` - a list sorted ascending.
        * `quantile` - the quantile in [0, 1].

        # Returns
        the value at that quantile, or 0 for an empty list.
        """
        if not values:
            return 0
        return values[min(len(values) - 1, int(quantile * len(values)))]


@dataclass
class Extractor:
    """walks the transcript sources and feeds every human turn to a Corpus."""

    sources: list

    def files(self):
        """yield every transcript file across all sources, in stable order.

        dispatch is by tool LABEL, not list position, so the source order is
        not a magic contract: claude lays out one project dir per repo with
        flat jsonl inside; codex nests date-rollout trees under each root.

        # Returns
        an iterator of (path, project-label, tool-label) tuples.
        """
        for root, label in self.sources:
            if not root.exists():
                continue
            # --------------------------------------------------
            # claude: one project dir per repo, flat jsonl inside
            # --------------------------------------------------
            if label == "claude":
                for project in sorted(root.iterdir()):
                    if project.is_dir():
                        for path in sorted(project.glob("*.jsonl")):
                            yield path, short_proj(project.name), "claude"
            # --------------------------------------------------
            # codex: date-nested rollout trees under each session root
            # --------------------------------------------------
            else:
                for path in sorted(root.rglob("*.jsonl")):
                    yield path, "codex", label

    def run(self):
        """read every file into a fresh Corpus.

        # Returns
        the populated Corpus.
        """
        corpus = Corpus()
        for path, proj, src in self.files():
            reader = Reader(path, proj, src)
            for turn in reader.turns():
                corpus.add(turn)
            corpus.denials.extend(reader.denials)
        return corpus


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """extract every transcript into the evidence store and print a summary."""
    corpus = Extractor(SOURCES).run()
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else find_data() / "evidence"
    out = out.resolve()
    corpus.write(out)
    buckets = Counter(p["bucket"] for p in corpus.prompts)
    print("brain-extract done ->", out)
    print(f"  turns: {len(corpus.prompts)} | " + " ".join(f"{k}:{v}" for k, v in buckets.most_common()))


if __name__ == "__main__":
    main()
