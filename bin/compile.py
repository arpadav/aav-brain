#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""compile: render the brain into the surfaces that consume it.

    python3 compile.py            build the codex agents + the global preamble
    python3 compile.py --check    rebuild in memory, fail if either drifts

two targets. the CODEX AGENTS are described below. the GLOBAL PREAMBLE carries
the handful of rules that must hold in EVERY session, including the ones where
no brain skill is ever loaded and none of the store is reachable: those render
from their cards into a marked block in ~/.claude/CLAUDE.md, so the always-on
copy cannot say something the card does not

the brain SKILLS are universal (same SKILL.md in claude, codex, and ~/.agents)
so they need no compilation - they symlink raw. the AGENTS differ per surface:
claude reads the `.md` source directly (frontmatter `model`/`color` + <example>
dispatch blocks), while codex consumes a TOML agent file (`~/.codex/agents/<name>.toml`)
with `name` / `description` / `developer_instructions`. this renders each source
`.md` into that TOML. output is deterministic, so `--check` gates drift (the files
are gitignored - this is an idempotency gate, run on init / in CI, not a committed
artifact diff)

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Artifact, Layout, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# the brain's shared library is a sibling in this same bin/. add this dir to the
# path so this build TOOLING shares the Artifact drift-gate instead of hand-rolling
# a second copy (P31)
sys.path.insert(0, str(Path(__file__).resolve().parent))

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()
# the cards that bind with no skill loaded, and the always-read file they land in
# home is discovered, never spelled out (P32); a surface whose file is absent is
# skipped rather than created, so this never invents config for a tool he doesn't run
PREAMBLE_CARDS = ("principle-37-comment-the-artifact-not-the-edit",)
PREAMBLE_DIR = Path.home() / ".claude"
PREAMBLE_FILE = PREAMBLE_DIR / "CLAUDE.md"
# only the span between these two lines belongs to the build; every other byte of
# that file is his (P09)
MARK_OPEN = "<!-- GENERATED from the brain - do not hand-edit -->"
MARK_CLOSE = "<!-- END GENERATED -->"
# the `## rule` section of a card, up to the next `##` heading
RULE_SECTION = re.compile(r"^## rule\n(.*?)(?=^## )", re.MULTILINE | re.DOTALL)
# a closing frontmatter fence: a line that is exactly `---` (not `----`/`---x`)
FRONT_CLOSE = re.compile(r"\n---[ \t]*(?:\n|$)")
# one `key: value` frontmatter line; keys allow letters/underscores (e.g. model_id)
FRONT_KV = re.compile(r"([A-Za-z_]+):\s*(.*)")
# the shortest string that can carry BOTH of its surrounding quotes
QUOTED_MIN = 2


def toml_basic(s: str) -> str:
    r"""render a single-line TOML basic string.

    escapes the control chars and metacharacters a basic string forbids, so an
    embedded quote/backslash/tab/newline can never break the emitted TOML

    # Arguments
    * `s` - the raw string value

    # Returns
    the quoted, escaped TOML scalar

    # Example

        >>> toml_basic('a "quoted" value')
        '"a \\"quoted\\" value"'
        >>> toml_basic("tab\there")
        '"tab\\there"'
    """
    out = (s.replace("\\", "\\\\").replace('"', '\\"')
           .replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n"))
    return f'"{out}"'


def toml_multiline(body: str) -> str:
    """render a TOML multi-line string for the agent body.

    prefers a literal (`'''`) so markdown backslashes/quotes need no escaping;
    falls back to a basic (`\"\"\"`) string only if the body itself contains `'''`
    the body is right-stripped of newlines so the value carries exactly one
    trailing newline (TOML trims the leading one after the opener), keeping the
    output byte-stable build over build

    # Arguments
    * `body` - the agent's markdown instructions

    # Returns
    the TOML multi-line string
    """
    body = body.rstrip("\n")
    if "'''" not in body:
        return f"'''\n{body}\n'''"
    esc = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""\n{esc}\n"""'


@dataclass
class Agent:
    """one claude agent file, parsed into its parts."""

    name: str
    description: str
    body: str

    @classmethod
    def parse(cls, path: Path) -> "Agent":
        """parse an agent .md into name, description, and body.

        fails LOUD on a malformed file (no frontmatter, unterminated fence,
        missing name) rather than silently corrupting the body or emitting an
        empty field - a stray non-agent `.md` in the tree is a build error, not
        a silent half-agent (P04)

        # Arguments
        * `path` - the agent file path

        # Returns
        an Agent. model/color frontmatter is dropped; codex inherits those
        """
        # --------------------------------------------------
        # read and normalise the line endings
        # --------------------------------------------------
        text = read_text(path).replace("\r\n", "\n").replace("\r", "\n")
        # --------------------------------------------------
        # locate and validate the frontmatter fences
        # --------------------------------------------------
        if not text.startswith("---\n"):
            raise ValueError(f"{path}: no opening frontmatter fence")
        close = FRONT_CLOSE.search(text, 3)
        if close is None:
            raise ValueError(f"{path}: unterminated frontmatter")
        front, body = text[4:close.start() + 1], text[close.end():].lstrip("\n")
        # --------------------------------------------------
        # scan the frontmatter line-by-line: robust to a description that is the
        # LAST key, to underscore/case in the next key, and to inline comments
        # --------------------------------------------------
        name = desc = None
        for line in front.splitlines():
            kv = FRONT_KV.match(line)
            if kv is None:
                continue
            key, val = kv.group(1), kv.group(2).strip()
            if key == "name" and name is None:
                name = val.strip('"').split(" #", 1)[0].strip().strip('"')
            elif key == "description" and desc is None:
                desc = val[1:-1] if len(val) >= QUOTED_MIN and val[0] == '"' and val[-1] == '"' else val.strip('"')
        # --------------------------------------------------
        # validate what the scan found, then construct
        # --------------------------------------------------
        if not name:
            raise ValueError(f"{path}: frontmatter has no name")
        return cls(name=name, description=desc or "", body=body)

    def codex_description(self) -> str:
        r"""the trigger sentence, without the claude-only <example> blocks.

        splits on the `<example>` tag regardless of how the surrounding newlines
        are encoded (escaped ``\n`` vs real), then collapses whitespace

        # Returns
        a single-line codex agent description
        """
        head = self.description.split("<example>")[0]
        return re.sub(r"\s+", " ", head.replace("\\n", " ").replace('\\"', '"')).strip()

    def to_codex_agent(self) -> str:
        """render this agent as a codex TOML agent file.

        # Returns
        the full `.toml` text (name + description + developer_instructions),
        trailing newline
        """
        return (f"name = {toml_basic(self.name)}\n"
                f"description = {toml_basic(self.codex_description())}\n"
                f"developer_instructions = {toml_multiline(self.body)}\n")


@dataclass
class Compiler(Artifact):
    """compiles every claude agent in a tree into codex TOML agents.

    a brainlib.Artifact: it supplies only `targets()` and `summary()`; the
    drift-gate (build / --check / byte-compare) is inherited, not re-rolled
    """

    agents_dir: Path = Path()

    def targets(self) -> list[tuple[Path, str]]:
        """the codex agent files, one `.toml` per source `.md` (recursive).

        raises on a duplicate agent `name` across the tree - two sources mapping
        to one output path would otherwise silently overwrite, and `--check`
        would never see the loss

        # Returns
        a list of (path, content) pairs
        """
        out: list[tuple[Path, str]] = []
        seen: dict[Path, Path] = {}
        for path in sorted(self.agents_dir.rglob("*.md")):
            agent = Agent.parse(path)
            dst = self.out_dir / f"{agent.name}.toml"
            if dst in seen:
                raise ValueError(f"duplicate agent name {agent.name!r}: {seen[dst]} and {path}")
            seen[dst] = path
            out.append((dst, agent.to_codex_agent()))
        return out

    def summary(self) -> str:
        """a one-line build summary.

        # Returns
        the directory and the compiled agent names
        """
        names = sorted(path.stem for path, _ in self.targets())
        return f"compile done -> {self.out_dir}\n  codex agents: {', '.join(names)}"


@dataclass
class Preamble(Artifact):
    """renders the always-on cards into the global prompt file.

    a brainlib.Artifact, so the drift gate is inherited. it owns ONLY the span
    between the two markers: the surrounding file is hand-written and stays
    untouched, and a file that has no markers yet gets the block appended
    """

    cards_dir: Path = Path()
    cards: tuple[str, ...] = ()

    def block(self) -> str:
        """the generated span, rendered from every named card.

        # Returns
        the marked block, markers included, without a trailing newline
        """
        parts = [MARK_OPEN]
        for name in self.cards:
            text = read_text(self.cards_dir / f"{name}.md")
            match = RULE_SECTION.search(text)
            if not match:
                raise ValueError(f"{name}: no `## rule` section to render")
            rule = match.group(1).strip()
            # a [[card]] link resolves only inside the store; emitting one into a
            # file read with no store loaded hands the reader a dead reference
            if "[[" in rule:
                raise ValueError(f"{name}: the rule section links to another card, so it cannot render standalone")
            parts.append(rule)
        parts.append(MARK_CLOSE)
        return "\n\n".join(parts)

    def targets(self) -> list[tuple[Path, str]]:
        """the global prompt file, with only its generated span replaced.

        # Returns
        a list of one (path, content) pair, or none when the file is absent
        """
        # --------------------------------------------------
        # nothing to merge into when the global file is absent
        # --------------------------------------------------
        if not PREAMBLE_FILE.exists():
            return []
        # --------------------------------------------------
        # render the block, then splice it over the marked span or append it
        # --------------------------------------------------
        text = read_text(PREAMBLE_FILE)
        block = self.block()
        start = text.find(MARK_OPEN)
        end = text.find(MARK_CLOSE)
        if start != -1 and end != -1:
            merged = text[:start] + block + text[end + len(MARK_CLOSE):]
        else:
            merged = text.rstrip("\n") + "\n\n## Comments\n\n" + block + "\n"
        return [(PREAMBLE_FILE, merged)]

    def summary(self) -> str:
        """a one-line build summary.

        # Returns
        the file written and the cards it carries
        """
        if not self.targets():
            return f"{TOOL}: {PREAMBLE_FILE} absent, preamble skipped"
        return f"compile done -> {PREAMBLE_FILE}\n  preamble cards: {', '.join(self.cards)}"


def main() -> None:
    """compile the codex agents and the global preamble, or check both."""
    Artifact.run_all([
        Compiler(out_dir=LAYOUT.codex_agents, agents_dir=LAYOUT.agents),
        Preamble(out_dir=PREAMBLE_DIR, cards_dir=LAYOUT.principles, cards=PREAMBLE_CARDS),
    ], Args.from_argv(), "compile")


if __name__ == "__main__":
    main()
