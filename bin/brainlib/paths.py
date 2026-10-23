"""brainlib.paths: every path inside the brain, spelled exactly once.

a directory name re-spelled at each call site is a rename that has to be
found by grep and is silently wrong wherever the grep missed. here each name
appears once, as a property, so a move is one edit and every tool follows

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------

# --------------------------------------------------
# external
# --------------------------------------------------
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Layout:
    """every path inside the brain repo, derived from the discovered root.

    a directory name re-spelled at each call site is a rename that has to be
    found by grep and is silently wrong wherever the grep missed. here each
    name appears exactly once, so a move is one edit and every tool follows

    # Example

        layout = Layout.discover()
        cards = layout.principles.glob("*.md")
    """

    root: Path

    @classmethod
    def discover(cls) -> "Layout":
        """the layout rooted at the discovered brain.

        # Returns

        a Layout over `find_brain()`
        """
        return cls(find_brain())

    @property
    def bin(self) -> Path:
        """the tool directory.

        # Returns

        `<root>/bin`
        """
        return self.root / "bin"

    @property
    def agentic(self) -> Path:
        """the agent and skill tree.

        # Returns

        `<root>/agentic-files`
        """
        return self.root / "agentic-files"

    @property
    def agents(self) -> Path:
        """the agent definitions.

        # Returns

        `<root>/agentic-files/agents`
        """
        return self.agentic / "agents"

    @property
    def skills(self) -> Path:
        """the skill definitions.

        # Returns

        `<root>/agentic-files/skills`
        """
        return self.agentic / "skills"

    @property
    def store(self) -> Path:
        """the card store: the knowledge itself.

        # Returns

        `<root>/brain`
        """
        return self.root / "brain"

    @property
    def principles(self) -> Path:
        """the principle cards.

        # Returns

        `<root>/brain/principles`
        """
        return self.store / "principles"

    @property
    def intents(self) -> Path:
        """the intent cards.

        # Returns

        `<root>/brain/intents`
        """
        return self.store / "intents"

    @property
    def card_dirs(self) -> tuple[Path, Path]:
        """the two directories a card may live in.

        # Returns

        `(principles, intents)`, the order the graph and the linter walk them
        """
        return (self.principles, self.intents)

    @property
    def index(self) -> Path:
        """the card index loaded at session start.

        # Returns

        `<root>/brain/INDEX.md`
        """
        return self.store / "INDEX.md"

    @property
    def constitution(self) -> Path:
        """the file whose presence identifies a brain root.

        # Returns

        `<root>/brain/CONSTITUTION.md`
        """
        return self.store / "CONSTITUTION.md"

    @property
    def flow_dir(self) -> Path:
        """the flow source and its build output.

        # Returns

        `<root>/brain/flow`
        """
        return self.store / "flow"

    @property
    def flow_toml(self) -> Path:
        """the hand-edited flow source.

        # Returns

        `<root>/brain/flow/flow.toml`
        """
        return self.flow_dir / "flow.toml"

    @property
    def flow_template(self) -> Path:
        """the hand-written frame DEV_FLOWCHART.md is populated from.

        # Returns

        `<root>/docs/templates/DEV_FLOWCHART.md`
        """
        return self.docs / "templates" / "DEV_FLOWCHART.md"

    @property
    def graph_dir(self) -> Path:
        """the built knowledge graph.

        # Returns

        `<root>/brain/graph`
        """
        return self.store / "graph"

    @property
    def graph_json(self) -> Path:
        """the graph recall reads.

        # Returns

        `<root>/brain/graph/graph.json`
        """
        return self.graph_dir / "graph.json"

    @property
    def docs(self) -> Path:
        """the human-facing generated documentation.

        # Returns

        `<root>/docs`
        """
        return self.root / "docs"

    @property
    def prune_toml(self) -> Path:
        """the authored prune policy.

        # Returns

        `<root>/prune.toml`
        """
        return self.root / "prune.toml"

    @property
    def tiers_toml(self) -> Path:
        """the authored tier policy: the rule, its thresholds, its measurement.

        # Returns

        `<root>/tiers.toml`
        """
        return self.root / "tiers.toml"

    @property
    def shape_toml(self) -> Path:
        """the authored shape policy: P27's and P28's numbers.

        # Returns

        `<root>/shape.toml`
        """
        return self.root / "shape.toml"

    @property
    def generated(self) -> Path:
        """the compiled output tree, gitignored.

        # Returns

        `<root>/.generated`
        """
        return self.root / ".generated"

    @property
    def codex_agents(self) -> Path:
        """where compiled codex agents land.

        # Returns

        `<root>/.generated/codex/agents`
        """
        return self.generated / "codex" / "agents"


@dataclass(frozen=True)
class DataLayout:
    """every path inside the brain's private data dir.

    the same rule as Layout, for the half that is never committed to the public
    repo: the decision trace and the extracted evidence corpus

    # Example

        data = DataLayout.discover()
        rows = Ledger(data.decisions).read()
    """

    root: Path

    @classmethod
    def discover(cls) -> "DataLayout":
        """the layout rooted at the private data dir.

        # Returns

        a DataLayout over `find_data()`
        """
        return cls(find_data())

    @property
    def trace(self) -> Path:
        """the decision-trace directory.

        # Returns

        `<data>/trace`
        """
        return self.root / "trace"

    @property
    def decisions(self) -> Path:
        """the append-only decision ledger.

        # Returns

        `<data>/trace/decisions.jsonl`
        """
        return self.trace / "decisions.jsonl"

    @property
    def evidence(self) -> Path:
        """the extracted evidence corpus.

        # Returns

        `<data>/evidence`
        """
        return self.root / "evidence"

    @property
    def corpus_stats(self) -> Path:
        """the corpus summary re-stamped by every extract.

        # Returns

        `<data>/evidence/corpus-stats.json`
        """
        return self.evidence / "corpus-stats.json"


def find_brain() -> Path:
    """locate the aav-brain repo root, no env var, no hardcode.

    the brain is ONE repo: cards, scripts (`bin/`), and the agentic files
    (`agentic-files/{agents,skills}`) all live under a single root. discovery
    returns that root; everything else derives from it (`<root>/bin`,
    `<root>/agentic-files/agents`, `<root>/agentic-files/skills`)

    resolution order, first hit wins:
    1. this file's own location (brainlib lives in <root>/bin/) - authoritative
       when called from a brain script
    2. a known brain-skill symlink under ~/.agents, then ~/.claude: readlink
       resolves the home-manager -> nix-store -> live-repo chain
    there is NO hardcoded-path fallback: a guess at a conventional checkout path
    (P32) would resolve a STALE sibling checkout, so discovery fails loud instead

    # Returns
    the resolved aav-brain root Path; raises FileNotFoundError if it cannot be
    located (fail loud, never guess)
    """
    # --------------------------------------------------
    # self-location: this module is <root>/bin/brainlib/paths.py, so the root is
    # three parents up. it was two while brainlib was a single file, and the
    # split silently made this branch unreachable - every tool then fell through
    # to the symlink below, which is the STALE-sibling resolution the docstring
    # says is deliberately absent. invisible on a machine with one checkout
    # --------------------------------------------------
    here = Path(__file__).resolve().parents[2]
    if (here / "brain" / "CONSTITUTION.md").exists():
        return here
    # --------------------------------------------------
    # follow a known skill symlink: ~/.agents first, then ~/.claude. skills live
    # at <root>/agentic-files/skills/<skill>, so the root is three parents up from
    # the resolved skill dir (skill -> skills -> agentic-files -> root)
    # --------------------------------------------------
    for base in (Path.home() / ".agents", Path.home() / ".claude"):
        link = base / "skills" / "brain-plan"
        if link.exists():
            root = link.resolve().parents[2]
            if (root / "brain" / "CONSTITUTION.md").exists():
                return root
    raise FileNotFoundError("cannot locate aav-brain via __file__ or the ~/.agents / ~/.claude skill symlink")


def find_data() -> Path:
    """the brain's PRIVATE memory dir (trace + evidence).

    private data - the decision trace and the extracted evidence corpus - never
    lives in the public brain's git objects. it lands in the XDG data dir
    (`$XDG_DATA_HOME/aav-brain`, else `~/.local/share/aav-brain`), which home-manager
    symlinks to the `aav-brain-logs` submodule (gitlinked at `logs/`; its content
    lives in a SEPARATE private repo, never in the public brain's history). resolved
    with no brain-specific env var (XDG is the standard, not a bespoke anchor); a
    relative `$XDG_DATA_HOME` is ignored, per the XDG spec

    # Returns
    the aav-brain private-data root Path (created on demand by its writers)
    """
    return _xdg_data() / "aav-brain"


def find_repo(start: Path | None = None) -> str:
    """the NAME of the git repository a decision was made in.

    an `affects` path is relative to the repo the run happened in, so without
    the repo it cannot be resolved later - `plans/01-scaffold.md` reads as
    deleted from anywhere else, which is indistinguishable from stale. the NAME
    and not the path: a machine-absolute path in a committed log is the same
    portability violation anywhere else (P32)

    # Arguments

    * `start` - where to start walking up from; the cwd when omitted

    # Returns

    the repo directory's name, or an empty string outside a repository

    # Example

        >>> find_repo(Path("/"))
        ''
    """
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        if (directory / ".git").exists():
            return directory.name
    return ""


def find_archive() -> Path:
    """the cold store for RAW transcripts, a SIBLING of find_data(), never inside it.

    find_data() resolves into the `aav-brain-logs` submodule. curated evidence is
    versioned knowledge and belongs there; raw transcripts are bulk cache
    (hundreds of MB, growing forever) and must stay out of that git history

    # Returns
    the archive root Path (created on demand by its writer)
    """
    return _xdg_data() / "aav-brain-archive"


def find_gate_state() -> Path:
    """the per-checkout review-gate state dir, a sibling of find_data().

    private run state, never versioned and never in the repo under review, so a
    finished run leaves nothing in the tree (CLEANUP deletes its file)

    # Returns
    the gate-state root Path (created on demand by its writer)
    """
    return _xdg_data() / "aav-brain-gate"


def _xdg_data() -> Path:
    """the XDG data root, ignoring a relative $XDG_DATA_HOME per the spec.

    # Returns
    the resolved data-home Path
    """
    base = Path(os.environ.get("XDG_DATA_HOME", "")).expanduser()
    if not base.is_absolute():
        base = Path.home() / ".local" / "share"
    return base
