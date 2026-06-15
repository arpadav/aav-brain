#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brainlib: shared datatypes and helpers for the brain tools.

the five brain scripts (extract, graph, recall, flow, walk) do NOT each
redefine their own node/edge/state/transition or their own drift-gate. they
import the one definition from here, so a datatype written by one tool is the
same datatype read by another (graph writes Node.to_dict, recall reads
Node.from_dict). that is the library: scripts helping one another by sharing
structs, not duplicating them.

contents:
- pure helpers: clip, parse_frontmatter.
- shared constants: KIND_RANK.
- the knowledge datatypes: Node, Edge.
- the execution datatypes: State, Transition.
- the build harness: Artifact (build / --check / drift-gate), reused by every
  builder so the "committed artifact must equal a fresh build" invariant lives
  in exactly one place.

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# rank order of node kinds, the tie-break shared by graph build + recall
KIND_RANK = {"principle": 0, "interest": 1}

# --------------------------------------------------
# helpers (pure)
# --------------------------------------------------
def clip(text, limit):
    """collapse whitespace and truncate text for storage.

    # Arguments
    * `text` - the raw text.
    * `limit` - the maximum number of characters to keep.

    # Returns
    the whitespace-collapsed, length-capped text.
    """
    return re.sub(r"\s+", " ", text).strip()[:limit]


def parse_frontmatter(text):
    """parse a card's yaml-ish frontmatter without a yaml dependency.

    handles scalars, bare lists ([a, b]) for interest/tension, and quoted
    lists (["a, b"]) for tells.

    # Arguments
    * `text` - the full card file contents.

    # Returns
    a dict of frontmatter fields, or an empty dict if there is none.
    """
    # --------------------------------------------------
    # isolate the block between the leading --- fences
    # --------------------------------------------------
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fields = {}
    # --------------------------------------------------
    # parse one key: value per line
    # --------------------------------------------------
    for line in text[3:end].split("\n"):
        match = re.match(r"^([a-z_]+):\s*(.*)$", line.strip())
        if not match:
            continue
        key, rest = match.group(1), match.group(2).strip()
        if key == "tells":
            fields[key] = re.findall(r'"([^"]*)"', rest)
        elif rest.startswith("["):
            fields[key] = [t.strip() for t in rest.strip("[]").split(",") if t.strip()]
        else:
            fields[key] = rest
    return fields


# --------------------------------------------------
# knowledge datatypes (the graph: cards + relationships)
# --------------------------------------------------
@dataclass
class Node:
    """one card as a graph node. written by brain-graph, read by brain-recall."""

    id: str
    kind: str
    headline: str
    interest: list
    confidence: str
    tells: list
    tension: list
    body_links: list
    path: str

    def to_dict(self):
        """serialise to the committed node shape (tension stays edge-only).

        # Returns
        an ordered dict with the human-meaningful field order.
        """
        return dict(id=self.id, kind=self.kind, headline=self.headline, interest=self.interest,
                    confidence=self.confidence, tells=self.tells, body_links=self.body_links, path=self.path)

    @classmethod
    def from_dict(cls, data):
        """reconstruct a Node from a committed graph.json entry.

        # Arguments
        * `data` - a node dict from graph.json (no tension field).

        # Returns
        a Node with tension defaulted to empty.
        """
        return cls(id=data["id"], kind=data["kind"], headline=data["headline"], interest=data["interest"],
                   confidence=data["confidence"], tells=data["tells"], tension=[],
                   body_links=data["body_links"], path=data["path"])


@dataclass(frozen=True, order=True)
class Edge:
    """one derived relationship. field order (type, src, dst) IS the sort order."""

    type: str
    src: str
    dst: str

    def to_dict(self):
        """serialise to the committed edge shape.

        # Returns
        a dict with keys src, dst, type.
        """
        return dict(src=self.src, dst=self.dst, type=self.type)

    @classmethod
    def from_dict(cls, data):
        """reconstruct an Edge from a committed graph.json entry.

        # Arguments
        * `data` - an edge dict from graph.json.

        # Returns
        an Edge.
        """
        return cls(type=data["type"], src=data["src"], dst=data["dst"])


# --------------------------------------------------
# execution datatypes (the flow: states + transitions)
# --------------------------------------------------
@dataclass(frozen=True)
class State:
    """one execution state. written by brain-flow, read by brain-walk.

    `recall` is the single coupling to the graph: when true, the walker fires
    brain-recall to load context before the owner runs. `terminal` marks an end
    state with no exit. `entry` marks a multi-entry start node (an entry skill
    seeds the walker here); `regime` is the autonomy that entry establishes
    (ask-first | execute-through), read from the entry, NOT inferred from the
    SANCTION crossing - review and self-refine reach a terminal without it.
    """

    id: str
    kind: str
    owner: str
    recall: bool
    doc: str
    terminal: bool = False
    entry: bool = False
    regime: str = ""

    def to_dict(self):
        """serialise to the committed state shape.

        # Returns
        an ordered dict with the state's fields.
        """
        return dict(id=self.id, kind=self.kind, owner=self.owner, recall=self.recall,
                    terminal=self.terminal, entry=self.entry, regime=self.regime, doc=self.doc)

    @classmethod
    def from_dict(cls, data):
        """reconstruct a State from a committed flow.json or a flow.toml table.

        # Arguments
        * `data` - a state mapping; optional keys default.

        # Returns
        a State.
        """
        return cls(id=data["id"], kind=data["kind"], owner=data["owner"], recall=data["recall"],
                   doc=data["doc"], terminal=data.get("terminal", False),
                   entry=data.get("entry", False), regime=data.get("regime", ""))


@dataclass(frozen=True)
class Transition:
    """one guarded edge: from `src`, on outcome `on`, go to `dst`.

    `boundary` marks the single sanction transition that flips the regime.
    """

    src: str
    on: str
    dst: str
    guard: str = ""
    boundary: bool = False

    def to_dict(self):
        """serialise to the committed transition shape.

        # Returns
        a dict with keys src, dst, on, guard, boundary.
        """
        return dict(src=self.src, dst=self.dst, on=self.on, guard=self.guard, boundary=self.boundary)

    @classmethod
    def from_dict(cls, data):
        """reconstruct a Transition from flow.json or a flow.toml table.

        # Arguments
        * `data` - a transition mapping; optional keys default.

        # Returns
        a Transition.
        """
        return cls(src=data["src"], on=data["on"], dst=data["dst"],
                   guard=data.get("guard", ""), boundary=data.get("boundary", False))


# --------------------------------------------------
# the build harness (one drift-gate for every builder)
# --------------------------------------------------
@dataclass
class Artifact:
    """base for a built, committed, drift-checked artifact.

    a builder subclass implements `targets()` (the files it owns, as
    (path, content) pairs) and `summary()` (a one-line status). this base
    provides the byte-identical drift check and the build/--check harness, so
    that invariant - committed output must equal a fresh build - lives once.
    """

    out_dir: Path

    def targets(self):
        """the artifact files this builder owns.

        # Returns
        a list of (path, content-string) pairs. subclass responsibility.
        """
        raise NotImplementedError

    def summary(self):
        """a one-line build summary.

        # Returns
        a status string. subclass responsibility.
        """
        raise NotImplementedError

    def is_current(self):
        """check whether every committed target matches a fresh build.

        # Returns
        true if all targets are byte-identical on disk.
        """
        for path, content in self.targets():
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                return False
        return True

    def run(self, argv, label):
        """the build / --check harness shared by every builder.

        # Arguments
        * `argv` - sys.argv.
        * `label` - the tool name, for messages.
        """
        # --------------------------------------------------
        # check mode: fail loudly on drift, write nothing
        # --------------------------------------------------
        if "--check" in argv:
            if self.is_current():
                print(f"{label}: artifacts are current")
                sys.exit(0)
            print(f"{label}: DRIFT - stale, re-run `python3 {label}.py`")
            sys.exit(1)
        # --------------------------------------------------
        # build mode: write every target, then summarise
        # --------------------------------------------------
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for path, content in self.targets():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        print(self.summary())


def load_json(path, label):
    """read a committed json artifact, exiting with a hint if it is missing.

    # Arguments
    * `path` - the json file path.
    * `label` - the tool that should have built it, for the hint.

    # Returns
    the parsed json.
    """
    if not path.exists():
        sys.exit(f"no {path.name} - run `python3 {label}.py` first")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------
# discovery (locate the brain repos without a hardcoded path)
# --------------------------------------------------
def find_brain():
    """locate the aav-brain repo root, no env var, no hardcode.

    the brain is ONE repo: cards, scripts (`bin/`), and the agentic files
    (`agentic-files/{agents,skills}`) all live under a single root. discovery
    returns that root; everything else derives from it (`<root>/bin`,
    `<root>/agentic-files/agents`, `<root>/agentic-files/skills`).

    resolution order, first hit wins:
    1. this file's own location (brainlib lives in <root>/bin/) - authoritative
       when called from a brain script.
    2. a known brain-skill symlink under ~/.agents, then ~/.claude: readlink
       resolves the home-manager -> nix-store -> live-repo chain.
    3. a relative fallback assuming the conventional checkout path.

    # Returns
    the resolved aav-brain root Path; raises FileNotFoundError if it cannot be
    located (fail loud, never guess).
    """
    # --------------------------------------------------
    # self-location: brainlib.py is <root>/bin/brainlib.py
    # --------------------------------------------------
    here = Path(__file__).resolve().parent.parent
    if (here / "brain" / "CONSTITUTION.md").exists():
        return here
    # --------------------------------------------------
    # follow a known skill symlink: ~/.agents first, then ~/.claude. skills live
    # at <root>/agentic-files/skills/<skill>, so the root is three parents up from
    # the resolved skill dir (skill -> skills -> agentic-files -> root).
    # --------------------------------------------------
    for base in (Path.home() / ".agents", Path.home() / ".claude"):
        link = base / "skills" / "brain-plan"
        if link.exists():
            root = link.resolve().parents[2]
            if (root / "brain" / "CONSTITUTION.md").exists():
                return root
    # --------------------------------------------------
    # relative fallback: the conventional checkout path
    # --------------------------------------------------
    guess = Path.home() / "repos" / "personal" / "aav-brain"
    if (guess / "brain" / "CONSTITUTION.md").exists():
        return guess
    raise FileNotFoundError("cannot locate aav-brain via __file__, ~/.agents, ~/.claude, or the fallback path")


def find_data():
    """the brain's PRIVATE memory dir (trace + evidence), OUTSIDE the repo.

    private data - the decision trace and the extracted evidence corpus - must
    NEVER live in the committable brain repo. it lands in the XDG data dir
    (`$XDG_DATA_HOME/aav-brain`, else `~/.local/share/aav-brain`), which is
    typically a symlink to the private `aav-brain-private` submodule. resolved
    with no brain-specific env var (XDG is the standard, not a bespoke anchor).

    # Returns
    the aav-brain private-data root Path (created on demand by its writers).
    """
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "aav-brain"


# --------------------------------------------------
# decision trace (append-only reasoning history)
# --------------------------------------------------
@dataclass
class Decision:
    """one logged decision: what was chosen, what was rejected, what it affects.

    the decided-against entries are the point: a later session that disagrees
    reads `affects` to find exactly where the call was made and reverses it. when
    a call overturns a past one, `supersedes` carries the prior entry's ts so the
    reversal is machine-readable, not buried in the `decision` prose.
    """

    skill: str
    decision: str
    chosen: str
    against: list = field(default_factory=list)
    affects: str = ""
    principle: list = field(default_factory=list)
    confidence: str = "medium"
    reversible: bool = True
    supersedes: str = ""


def trace_decision(decision, session="", ts=""):
    """append one Decision to the trace (find_data()/trace/decisions.jsonl, OUTSIDE the repo; never overwrite).

    # Arguments
    * `decision` - a Decision instance.
    * `session` - the current session id, for transcript correlation.
    * `ts` - an iso utc timestamp; if empty, stamped now.

    # Returns
    the resolved path the entry was appended to.
    """
    path = find_data() / "trace" / "decisions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    # microsecond resolution so ts uniquely identifies an entry - several decisions
    # logged in one second must not collide, since `supersedes` keys on ts.
    stamp = ts or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    entry = {"ts": stamp, "session": session, **vars(decision)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path
