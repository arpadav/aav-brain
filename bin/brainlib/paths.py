"""brainlib.paths: every path the brain reads or writes, spelled exactly once.

a directory name re-spelled at each call site is a rename that has to be
found by grep and is silently wrong wherever the grep missed. here each name
appears once, as a property, so a move is one edit and every tool follows.
Layout holds the paths inside a brain repo. XdgLayout holds those in his
per-machine config folder, the install copy, and the edit copy's brain that
the folder's repos.toml leads to, which every tool keeps its data in.
DataLayout holds the paths of that data: the edit brain's private-data
submodule, with LocalLayout its never-committed per-machine `local/`

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.repo.tree import git
from brainlib.text import Json, read_text, write_text
from brainlib.vocab import Env, NoVerdict

# --------------------------------------------------
# external
# --------------------------------------------------
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Self

# --------------------------------------------------
# constants
# --------------------------------------------------
# the name the brain's `.gitmodules` gives its private-data submodule; its path is read from that entry
DATA_SUBMODULE = "logs"
# the file his declared private values live in, under his config folder
PRIVATE_TOML = "private.toml"
# the file naming where his checkouts live, under his config folder; repos.nix reads it too
REPOS_TOML = "repos.toml"
# the roots searched when repos.toml sets no `roots`; repos.nix spells the same default
DEFAULT_ROOTS = ("~/repos/personal",)
# the home repo's directory: under a root for the edit copy, under his config folder for the install copy
HOME_REPO = "home"
# the legacy install copy location under $HOME, which sy migrates from; repos.nix spells the same
HM_HOME = Path(".config", "home-manager")
# the install copy under $HOME, the value install-copy.nix holds
INSTALL_HOME = Path(".config", "aav", HOME_REPO)
# the brain's folder inside a home checkout
HOME_BRAIN = "brain"
# the per-machine folder inside the data dir
LOCAL = "local"
# the folder inside LOCAL holding one dir of session logs per tool
SESSIONS = "sessions"
# the self-ignoring .gitignore every writer of LOCAL puts in it first, as a tool cache does
LOCAL_GITIGNORE = "# self-ignoring: per-machine brain data, never committed\n*\n"
# the prefix every brain command carries, before its script's stem past `brain-`
COMMAND_PREFIX = "b-"
# the interpreter flag every brain command runs under: no PYTHON* variables, no user site, no script dir on sys.path
ISOLATED = "-I"
# the folders under bin/ that hold no script: the shared library, and python's bytecode cache
NOT_SCRIPT_DIRS = ("brainlib", "__pycache__")


class EditCopyMissing(NoVerdict):
    """no edit copy on this machine, so no brain to keep data in: the tool refuses rather than guess a path.

    a NoVerdict, so `Tool.run` prints the message and exits Exit.FAILED

    # Example

        >>> str(EditCopyMissing())
        'no edit copy - run /home-setup'
    """

    def __init__(self) -> None:
        """the one message: what is missing, and the skill that makes it."""
        super().__init__("no edit copy - run /home-setup")


@dataclass(frozen=True)
class Layout:
    """every path inside the brain repo, derived from the discovered root.

    # Example

        layout = Layout.discover()
        principles = layout.principles.glob("*.md")
    """

    root: Path

    # the scripts other code names, relative to `bin`
    RECALL: ClassVar[Path] = Path("run", "brain-recall.py")
    WALK: ClassVar[Path] = Path("run", "brain-walk.py")
    PRIVATE: ClassVar[Path] = Path("check", "brain-private.py")

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
        """the store: the knowledge itself, its principles and interests.

        # Returns

        `<root>/brain`
        """
        return self.root / "brain"

    @property
    def principles(self) -> Path:
        """the principles.

        # Returns

        `<root>/brain/principles`
        """
        return self.store / "principles"

    @property
    def intents(self) -> Path:
        """the interests: the why behind the principles.

        # Returns

        `<root>/brain/intents`
        """
        return self.store / "intents"

    @property
    def store_dirs(self) -> tuple[Path, Path]:
        """the two directories of the store's documents: the principles, then the interests.

        # Returns

        `(principles, intents)`, the order b-principles lints them in
        """
        return (self.principles, self.intents)

    @property
    def index(self) -> Path:
        """the principle index loaded at session start.

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

    @staticmethod
    def command(script: Path) -> str:
        """the command a brain script runs as: `b-`, then its stem past `brain-`.

        module.nix writes each script's command under this name, so a tool's
        messages name it as he would type it

        # Arguments

        * `script` - the script, by any path

        # Returns

        the command name

        # Example

            >>> Layout.command(Path("bin/run/brain-walk.py")), Layout.command(Path("bin/check/brain-lint.py"))
            ('b-walk', 'b-lint')
        """
        return f"{COMMAND_PREFIX}{script.stem.removeprefix('brain-')}"

    @property
    def scripts(self) -> list[Path]:
        """every brain script: a `brain-?*.py` file in bin/ or a folder directly under it, NOT_SCRIPT_DIRS aside.

        module.nix makes each one a command by this rule, spelled again in
        nix, which cannot call this. nix's `readDir` types a symlink as
        neither a directory nor a file, so a symlinked folder or script is
        none here either. a bare `brain-.py` is none, since it would run as `b-`

        # Returns

        the scripts, sorted

        # Example

            >>> Layout.discover().recall_script in Layout.discover().scripts
            True
        """
        dirs = [self.bin, *(d for d in self.bin.iterdir()
                            if d.is_dir() and not d.is_symlink() and d.name not in NOT_SCRIPT_DIRS)]
        return sorted(script for d in dirs for script in d.glob("brain-?*.py")
                      if script.is_file() and not script.is_symlink())

    def script_for(self, command: str) -> Path | None:
        """the script this brain runs as `command`, found among `scripts` by `command`'s rule.

        # Arguments

        * `command` - the command, COMMAND_PREFIX included (`b-walk`)

        # Returns

        the script, or None when no script of this brain runs as `command`

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     layout = Layout(Path(tmp))
            ...     (layout.bin / "run").mkdir(parents=True)
            ...     (layout.bin / "run" / "brain-walk.py").touch()
            ...     layout.script_for("b-walk").relative_to(layout.bin).as_posix(), layout.script_for("walk")
            ('run/brain-walk.py', None)
        """
        return next((script for script in self.scripts if self.command(script) == command), None)

    @property
    def recall_script(self) -> Path:
        """the script that serves principles for a task.

        # Returns

        `<root>/bin/run/brain-recall.py`
        """
        return self.bin / self.RECALL

    @property
    def private_script(self) -> Path:
        """the script that scans a tree for his private infrastructure.

        # Returns

        `<root>/bin/check/brain-private.py`
        """
        return self.bin / self.PRIVATE

    @property
    def private_command(self) -> tuple[str, ...]:
        """how a brain tool runs b-private as a process of its own (b-verify): this interpreter, isolated.

        ISOLATED drops every PYTHON* variable, the user site with its `.pth`
        files, and the script's own dir from `sys.path`. module.nix, which
        cannot call this, spells the flag again twice: in the wrapper every
        command runs through, and in the activation that compiles the codex
        agents

        # Returns

        the argv prefix; the scan's own flags and paths follow it
        """
        return (sys.executable, ISOLATED, str(self.private_script))

    @property
    def data_submodule(self) -> Path | None:
        r"""where the private-data submodule is checked out: its path in the brain's own `.gitmodules`.

        read from the brain repo's own `.gitmodules`, so the answer names the
        gitlink of this checkout, whichever copy it is

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


class XdgLayout:
    """every path in his per-machine config folder, the install copy, and the edit copy's brain.

    the folder holds his private values and repos.toml. the install copy, a
    home checkout, is always `~/.config/aav/home`, whatever XDG_CONFIG_HOME
    says; the edit copy is a home checkout outside both, found through
    repos.toml

    the folder is `$XDG_CONFIG_HOME/aav`, else `~/.config/aav`; a relative XDG
    variable is ignored, per the XDG spec. each path is read at call time, so a
    shell opened before a switch never holds a stale one. no dir is created here

    # Example

        >>> import os
        >>> from unittest import mock
        >>> with mock.patch.dict(os.environ, {"HOME": "/h", Env.XDG_CONFIG_HOME: ""}):
        ...     [str(path) for path in (XdgLayout.private_toml(), XdgLayout.repos_toml(), XdgLayout.install_home())]
        ['/h/.config/aav/private.toml', '/h/.config/aav/repos.toml', '/h/.config/aav/home']
    """

    @staticmethod
    def config() -> Path:
        """his per-machine config folder.

        # Returns

        `$XDG_CONFIG_HOME/aav`, else `~/.config/aav`
        """
        return Env.XDG_CONFIG_HOME.directory(Path.home() / ".config") / "aav"

    @classmethod
    def private_toml(cls) -> Path:
        """the file his declared private values live in; the private scan reads it, b-sync warns when it is absent.

        # Returns

        PRIVATE_TOML under `config()`
        """
        return cls.config() / PRIVATE_TOML

    @classmethod
    def repos_toml(cls) -> Path:
        """the file naming the roots his checkouts live under, and the edit copy when it is under none.

        # Returns

        REPOS_TOML under `config()`
        """
        return cls.config() / REPOS_TOML

    @classmethod
    def install_home(cls) -> Path:
        """the install copy: the home checkout every skill, agent and command runs from, never edited.

        always under `$HOME`, never `XDG_CONFIG_HOME`: the home repo's
        `install-copy.nix` names it relative to `$HOME`, and nix and python
        must name the same directory

        # Returns

        `$HOME/.config/aav/home`
        """
        return Path.home() / INSTALL_HOME

    @classmethod
    def edit_brain(cls) -> Path:
        r"""the edit copy's brain: where the brain is edited, and where every tool keeps its data.

        the candidates are repos.toml's `edit` when set and not empty, else
        `<root>/home` for every one of its `roots` in order (DEFAULT_ROOTS
        when it sets none), `~` expanded in each. the first candidate that
        holds a brain and does not resolve to an install copy,
        `install_home()` or the older HM_HOME, is the edit copy; a declared
        `edit` that does not qualify is refused, never passed over. repos.nix
        resolves `AVE` from the same candidates in the same order, but matches
        an install copy by its path string, unresolved, and refuses nothing.
        the file is read on every call

        # Returns

        `<edit copy>/brain`, symlinks resolved

        # Raises

        EditCopyMissing when no root's home qualifies; NoVerdict, naming the
        value and repos.toml, when a declared `edit` holds no brain or is an
        install copy, and when repos.toml cannot be read, is not of that shape,
        or names a relative path

        # Example

            >>> import os, tempfile
            >>> from unittest import mock
            >>> with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"HOME": tmp}):
            ...     os.environ[Env.XDG_CONFIG_HOME] = ""
            ...     home = Path(tmp).resolve()
            ...     def brain(at: str) -> None:
            ...         Layout(home / at / HOME_BRAIN).bin.mkdir(parents=True)
            ...     def edit(toml: str) -> str:
            ...         _ = XdgLayout.repos_toml().write_text(toml)
            ...         try:
            ...             return XdgLayout.edit_brain().relative_to(home).as_posix()
            ...         except NoVerdict as refused:
            ...             return str(refused).replace(tmp, "~")
            ...     brain(".config/aav/home")
            ...     brain(".config/home-manager")
            ...     (home / "half" / HOME_REPO / HOME_BRAIN).mkdir(parents=True)
            ...     absent = edit("")
            ...     brain("repos/personal/home")
            ...     brain("else/home")
            ...     edit(""), edit('roots = ["~/.config/aav", "~/half", "~/repos/personal"]\n'), edit('edit = ""\n')
            ...     edit('edit = "~/else/home"\n'), absent
            ...     edit('edit = "~/.config/home-manager"\n')
            ...     edit('edit = "~/half/home"\n')
            ...     edit('roots = "~"\n')
            ...     edit('edit = "else/home"\n')
            ('repos/personal/home/brain', 'repos/personal/home/brain', 'repos/personal/home/brain')
            ('else/home/brain', 'no edit copy - run /home-setup')
            '~/.config/aav/repos.toml: `edit` = ~/.config/home-manager is an install copy, never the edit copy'
            '~/.config/aav/repos.toml: `edit` = ~/half/home holds no brain'
            '~/.config/aav/repos.toml: `roots` takes a list of paths and `edit` one path'
            '~/.config/aav/repos.toml: `roots` and `edit` take absolute paths, `~` expanded; else/home is not'
        """
        # --------------------------------------------------
        # the declared roots and edit copy; an absent file declares neither
        # --------------------------------------------------
        repos = cls.repos_toml()
        declared: dict[str, object]
        try:
            declared = tomllib.loads(read_text(repos))
        except FileNotFoundError:
            declared = {}
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as broken:
            raise NoVerdict(f"{repos} unreadable ({broken})") from broken
        # --------------------------------------------------
        # each root must be a path, as must the edit copy, an empty one unset; another shape is refused, never skipped
        # --------------------------------------------------
        roots, edit = declared.get("roots", list(DEFAULT_ROOTS)), declared.get("edit")
        edit = None if edit == "" else edit
        named = [root for root in Json.members(roots) if isinstance(root, str)]
        if not isinstance(edit, str | None) or not Json.is_array(roots) or len(named) != len(roots):
            raise NoVerdict(f"{repos}: `roots` takes a list of paths and `edit` one path")
        # --------------------------------------------------
        # every declared path absolute once `~` is expanded: a relative one would resolve against the cwd
        # --------------------------------------------------
        edits = [] if edit is None else [edit]
        if relative := [path for path in (*named, *edits) if not Path(path).expanduser().is_absolute()]:
            raise NoVerdict(f"{repos}: `roots` and `edit` take absolute paths, `~` expanded; "
                            f"{', '.join(relative)} is not")
        # --------------------------------------------------
        # the declared edit copy alone, else every root's home; the first holding a brain that no install copy is
        # --------------------------------------------------
        candidates = [Path(edit)] if edit is not None else [Path(root) / HOME_REPO for root in named]
        installs = {cls.install_home().resolve(), (Path.home() / HM_HOME).resolve()}
        found = next((home for candidate in candidates
                      if (home := candidate.expanduser().resolve()) not in installs
                      and Layout(home / HOME_BRAIN).bin.is_dir()), None)
        if found is not None:
            return found / HOME_BRAIN
        # --------------------------------------------------
        # no root's home qualifying is no edit copy; a declared one not qualifying is a mistake in the file
        # --------------------------------------------------
        if edit is None:
            raise EditCopyMissing
        why = ("is an install copy, never the edit copy" if Path(edit).expanduser().resolve() in installs
               else "holds no brain")
        raise NoVerdict(f"{repos}: `edit` = {edit} {why}")


@dataclass(frozen=True)
class DataLayout:
    """every path inside the brain's private data dir: the edit brain's `logs/` submodule.

    the same rule as Layout, for the half that is never committed to the public
    repo: the decision trace and the extracted evidence corpus, versioned in
    the private submodule, and LocalLayout's per-machine files beside them

    # Example

        data = DataLayout.discover()
        rows = Ledger(data.decisions).read()
    """

    root: Path

    @classmethod
    def discover(cls) -> "DataLayout":
        """the layout rooted at the edit brain's private data dir.

        # Returns

        a DataLayout over the edit brain's `Layout.data_submodule`

        # Raises

        EditCopyMissing when this machine has no edit copy; NoVerdict when its
        `.gitmodules` names no DATA_SUBMODULE, or that submodule is not checked
        out, since a file written into the bare dir would block its init
        """
        brain = XdgLayout.edit_brain()
        if (root := Layout(brain).data_submodule) is None:
            raise NoVerdict(f"{brain}/.gitmodules names no `{DATA_SUBMODULE}` submodule")
        if not (root / ".git").exists():
            raise NoVerdict(f"{root} is not checked out; run "
                            f"`git -C {brain} submodule update --init {root.relative_to(brain)}`")
        return cls(root)

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

    @property
    def local(self) -> "LocalLayout":
        """the per-machine files: never committed, never pushed.

        # Returns

        the LocalLayout over `<data>/local`
        """
        return LocalLayout(self.root / LOCAL)


@dataclass(frozen=True)
class LocalLayout:
    """every per-machine path inside the data dir: raw transcripts, gate state, session logs.

    bulk or per-run, so none of it is versioned. the dir ignores itself: a
    writer takes its paths off `writable()`, which writes LOCAL_GITIGNORE into
    the dir when absent, so nothing a tool writes here can be staged, even
    when the data checkout's own ignore rules are behind. a reader takes them
    off the layout as it is and creates nothing; a dir not yet written reads
    as empty. `archive` cannot be rebuilt once the harnesses prune their
    transcripts, so the dir is never cleaned

    # Example

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     local = DataLayout(Path(tmp)).local
        ...     paths = (local.archive, local.gate, local.session_log("b-recall"), local.session_log("b-gate"))
        ...     [path.relative_to(tmp).as_posix() for path in paths]
        ...     read = local.root.exists()
        ...     read, (local.writable().root / ".gitignore").read_text() == LOCAL_GITIGNORE
        ['local/archive', 'local/gate', 'local/sessions/recall', 'local/sessions/gate']
        (False, True)
    """

    root: Path

    def writable(self) -> Self:
        """this layout, its dir made and its self-ignoring .gitignore written when absent: the step every writer takes.

        # Returns

        this layout, `<local>` holding LOCAL_GITIGNORE as `.gitignore`

        # Raises

        OSError when the .gitignore cannot be written
        """
        gitignore = self.root / ".gitignore"
        if not gitignore.is_file():
            write_text(gitignore, LOCAL_GITIGNORE)
        return self

    @property
    def archive(self) -> Path:
        """the cold store for RAW transcripts, gzipped by `b-extract --archive`.

        curated evidence is versioned knowledge and belongs in the data dir's
        `evidence`; raw transcripts are bulk cache (hundreds of MB, growing
        forever) and stay out of that git history

        # Returns

        `<local>/archive`
        """
        return self.root / "archive"

    @property
    def gate(self) -> Path:
        """the review-gate state, one file per checkout under review.

        never in the repo under review, so a finished run leaves nothing in
        the tree (CLEANUP deletes its file)

        # Returns

        `<local>/gate`
        """
        return self.root / "gate"

    @property
    def sessions(self) -> Path:
        """every tool's session logs, one dir per tool, apart from `archive` and `gate` so no tool's name collides.

        # Returns

        `<local>/sessions`
        """
        return self.root / SESSIONS

    def session_log(self, tool: str) -> Path:
        """the dir of one tool's session logs (brainlib.session); nothing prunes it.

        one dir per tool, so one tool's call is never read as another's

        # Arguments

        * `tool` - the tool's command (`Layout.command`)

        # Returns

        `<local>/sessions/<tool past COMMAND_PREFIX>`

        # Example

            >>> LocalLayout(Path("/d")).session_log("b-x")
            PosixPath('/d/sessions/x')
        """
        return self.sessions / tool.removeprefix(COMMAND_PREFIX)


@dataclass(frozen=True)
class EvidenceLayout:
    """every file of the extracted evidence corpus, in whichever directory holds it.

    b-extract writes all of them and the other tools read them, so each
    name is spelled here once. the root is the data dir's `evidence/`, or the
    directory `b-extract --out` names

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

    the brain is ONE repo: principles, scripts (`bin/`), and the agentic files
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
