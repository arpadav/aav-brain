"""brainlib.paths: every path inside the brain, spelled exactly once.

a directory name re-spelled at each call site is a rename that has to be
found by grep and is silently wrong wherever the grep missed. here each name
appears once, as a property, so a move is one edit and every tool follows

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.repos import git
from brainlib.vocab import Env

# --------------------------------------------------
# external
# --------------------------------------------------
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# the name the brain's `.gitmodules` gives its private-data submodule
DATA_SUBMODULE = "logs"


@dataclass(frozen=True)
class Layout:
    """every path inside the brain repo, derived from the discovered root.

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

    @classmethod
    def root_of(cls, path: Path) -> Path | None:
        """the brain root a path sits inside, however deep.

        a root is identified by its constitution file, so this walks up rather
        than counting parents - a count re-spells the tree's depth and goes
        silently wrong when a directory moves

        # Arguments

        * `path` - a resolved path inside the brain

        # Returns

        the nearest enclosing brain root, or None when there is none

        # Example

            >>> Layout.root_of(Path(__file__).resolve()) == find_brain()
            True
            >>> Layout.root_of(Path("/")) is None
            True
        """
        return next((root for root in path.parents if cls(root).constitution.exists()), None)

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
        """where the knowledge graph is exported.

        # Returns

        `<root>/brain/graph`
        """
        return self.store / "graph"

    @property
    def recall_script(self) -> Path:
        """the script that serves cards for a task.

        # Returns

        `<root>/bin/run/brain-recall.py`
        """
        return self.bin / "run" / "brain-recall.py"

    @property
    def private_script(self) -> Path:
        """the script that scans a tree for his private infrastructure.

        # Returns

        `<root>/bin/check/brain-private.py`
        """
        return self.bin / "check" / "brain-private.py"

    @property
    def data_submodule(self) -> Path | None:
        r"""where the private-data submodule is checked out: its path in the brain's own `.gitmodules`.

        read from the brain repo, never from where XDG points, so the answer
        names the gitlink whatever `$XDG_DATA_HOME` says

        # Returns

        `<root>/<path>` of the DATA_SUBMODULE entry; None when `.gitmodules`
        holds no such entry or cannot be read

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     root = Path(tmp)
            ...     before = Layout(root).data_submodule
            ...     _ = (root / ".gitmodules").write_text(f'[submodule "{DATA_SUBMODULE}"]\n\tpath = private/logs\n')
            ...     before, Layout(root).data_submodule == root / "private" / "logs"
            (None, True)
        """
        path = git(self.root, "config", "--file", ".gitmodules", "--get", f"submodule.{DATA_SUBMODULE}.path")
        return None if path is None else self.root / path.removesuffix("\n")

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
    def evidence(self) -> "EvidenceLayout":
        """the extracted evidence corpus.

        # Returns

        the EvidenceLayout over `<data>/evidence`
        """
        return EvidenceLayout(self.root / "evidence")


@dataclass(frozen=True)
class EvidenceLayout:
    """every file of the extracted evidence corpus, in whichever directory holds it.

    brain-extract writes all of them and the other tools read them, so each
    name is spelled here once. the root is the data dir's `evidence/`, or the
    directory `brain-extract --out` names

    # Example

        evidence = DataLayout.discover().evidence
        rows = Ledger(evidence.heat).read()
    """

    root: Path

    @property
    def prompts(self) -> Path:
        """every human turn of his, classified: the canonical corpus every view projects.

        # Returns

        `<evidence>/prompts.jsonl`
        """
        return self.root / "prompts.jsonl"

    @property
    def denials(self) -> Path:
        """the permission prompts he refused.

        # Returns

        `<evidence>/denials.jsonl`
        """
        return self.root / "denials.jsonl"

    @property
    def heat(self) -> Path:
        """his turns that carried heat: a hard rule had just been broken.

        # Returns

        `<evidence>/heat.jsonl`
        """
        return self.root / "heat.jsonl"

    @property
    def interruptions(self) -> Path:
        """his turns that cut a run off mid-step.

        # Returns

        `<evidence>/interruptions.jsonl`
        """
        return self.root / "interruptions.jsonl"

    @property
    def rejections(self) -> Path:
        """his turns that rejected or corrected what was done, heat included.

        # Returns

        `<evidence>/rejections.jsonl`
        """
        return self.root / "rejections.jsonl"

    @property
    def approvals(self) -> Path:
        """his short turns that approved what was done.

        # Returns

        `<evidence>/approvals.jsonl`
        """
        return self.root / "approvals.jsonl"

    @property
    def directives(self) -> Path:
        """his long turns that carried no other signal.

        # Returns

        `<evidence>/directives.jsonl`
        """
        return self.root / "directives.jsonl"

    @property
    def corpus_stats(self) -> Path:
        """the aggregate statistics over the prompts.

        # Returns

        `<evidence>/corpus-stats.json`
        """
        return self.root / "corpus-stats.json"


def plain_name(name: str) -> bool:
    """whether an id names one file in a directory and nothing else.

    an id read from the environment or a log becomes a file name; one that is
    empty, `..`, or carries a separator would name a directory or escape it

    # Arguments

    * `name` - the id about to become a file name

    # Returns

    True when the id is a single path component naming an entry, not `.` or `..`

    # Example

        >>> plain_name("fbffe8d9-cd2b"), plain_name(""), plain_name("../etc"), plain_name("a/b"), plain_name("..")
        (True, False, False, False, False)
    """
    return name not in ("", "..") and Path(name).name == name


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
    # self-location: this module sits inside the checkout it belongs to. a
    # miss here falls through to the skill symlink below, resolution step 2
    # --------------------------------------------------
    if root := Layout.root_of(Path(__file__).resolve()):
        return root
    # --------------------------------------------------
    # follow a known skill symlink: ~/.agents first, then ~/.claude. a skill
    # lives inside the brain, so its resolved dir sits under the root
    # --------------------------------------------------
    for base in (Path.home() / ".agents", Path.home() / ".claude"):
        link = base / "skills" / "brain-plan"
        if link.exists() and (root := Layout.root_of(link.resolve())):
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
    root = find_repo_root(start)
    return root.name if root else ""


def find_repo_root(start: Path | None = None) -> Path | None:
    """the root of the git repository `start` sits in.

    # Arguments

    * `start` - where to start walking up from; the cwd when omitted

    # Returns

    the resolved repo directory, or None outside a repository

    # Example

        >>> find_repo_root(Path("/")) is None
        True
    """
    here = (start or Path.cwd()).resolve()
    return next((d for d in (here, *here.parents) if (d / ".git").exists()), None)


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


def find_config() -> Path:
    """his per-machine config folder, never in a repo.

    # Returns
    `$XDG_CONFIG_HOME/aav`, else `~/.config/aav`
    """
    return Env.XDG_CONFIG_HOME.directory(Path.home() / ".config") / "aav"


def find_served() -> Path:
    """where recall logs what it served each session (brainlib.served), a sibling of find_data().

    durable, so the misses report can read it, and unversioned and per
    machine, so a recall never dirties a repo; nothing prunes it

    # Returns
    the served-log root Path (created on demand by its writer)
    """
    return _xdg_data() / "aav-brain-served"


def _xdg_data() -> Path:
    """the XDG data root: `$XDG_DATA_HOME`, else `~/.local/share`.

    # Returns

    an absolute directory path; it is not created
    """
    return Env.XDG_DATA_HOME.directory(Path.home() / ".local" / "share")
