#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""compile: render the brain's claude agents into codex TOML agents.

    python3 compile.py            build .generated/codex/agents/<name>.toml
    python3 compile.py --check    rebuild in memory, fail if it drifts from disk

the brain SKILLS are universal (same SKILL.md in claude, codex, and ~/.agents)
so they need no compilation - they symlink raw. the AGENTS differ per surface:
claude reads the `.md` source directly (frontmatter `model`/`color` + <example>
dispatch blocks), while codex consumes a TOML agent file (`~/.codex/agents/<name>.toml`)
with `name` / `description` / `developer_instructions`. this renders each source
`.md` into that TOML. output is deterministic, so `--check` gates drift (the files
are gitignored - this is an idempotency gate, run on init / in CI, not a committed
artifact diff).

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# the brain's shared library is a sibling in this same bin/. add this dir to the
# path so this build TOOLING shares the Artifact drift-gate instead of hand-rolling
# a second copy (P31).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brainlib import Artifact

# --------------------------------------------------
# constants
# --------------------------------------------------
# the repo root, relative to this script (bin/..).
BRAIN = (Path(__file__).resolve().parent / "..").resolve()
# where the claude agent sources live (recursively, across the category tree),
# and where compiled codex agents land (gitignored).
AGENTS_DIR = BRAIN / "agentic-files" / "agents"
CODEX_OUT = BRAIN / ".generated" / "codex" / "agents"
# a closing frontmatter fence: a line that is exactly `---` (not `----`/`---x`).
FRONT_CLOSE = re.compile(r"\n---[ \t]*(?:\n|$)")
# one `key: value` frontmatter line; keys allow letters/underscores (e.g. model_id).
FRONT_KV = re.compile(r"([A-Za-z_]+):\s*(.*)")


# --------------------------------------------------
# helpers
# --------------------------------------------------
def toml_basic(s):
    """render a single-line TOML basic string.

    escapes the control chars and metacharacters a basic string forbids, so an
    embedded quote/backslash/tab/newline can never break the emitted TOML.

    # Arguments
    * `s` - the raw string value.

    # Returns
    the quoted, escaped TOML scalar.
    """
    out = (s.replace("\\", "\\\\").replace('"', '\\"')
           .replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n"))
    return f'"{out}"'


def toml_multiline(body):
    """render a TOML multi-line string for the agent body.

    prefers a literal (`'''`) so markdown backslashes/quotes need no escaping;
    falls back to a basic (`\"\"\"`) string only if the body itself contains `'''`.
    the body is right-stripped of newlines so the value carries exactly one
    trailing newline (TOML trims the leading one after the opener), keeping the
    output byte-stable build over build.

    # Arguments
    * `body` - the agent's markdown instructions.

    # Returns
    the TOML multi-line string.
    """
    body = body.rstrip("\n")
    if "'''" not in body:
        return f"'''\n{body}\n'''"
    esc = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""\n{esc}\n"""'


# --------------------------------------------------
# types
# --------------------------------------------------
@dataclass
class Agent:
    """one claude agent file, parsed into its parts."""

    name: str
    description: str
    body: str

    @classmethod
    def parse(cls, path):
        """parse an agent .md into name, description, and body.

        fails LOUD on a malformed file (no frontmatter, unterminated fence,
        missing name) rather than silently corrupting the body or emitting an
        empty field - a stray non-agent `.md` in the tree is a build error, not
        a silent half-agent (P04).

        # Arguments
        * `path` - the agent file path.

        # Returns
        an Agent. model/color frontmatter is dropped; codex inherits those.
        """
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        if not text.startswith("---\n"):
            raise ValueError(f"{path}: no opening frontmatter fence")
        close = FRONT_CLOSE.search(text, 3)
        if close is None:
            raise ValueError(f"{path}: unterminated frontmatter")
        front, body = text[4:close.start() + 1], text[close.end():].lstrip("\n")
        # frontmatter is parsed line-by-line: robust to a description that is the
        # LAST key, to underscore/case in the next key, and to inline comments.
        name = desc = None
        for line in front.splitlines():
            kv = FRONT_KV.match(line)
            if kv is None:
                continue
            key, val = kv.group(1), kv.group(2).strip()
            if key == "name" and name is None:
                name = val.strip('"').split(" #", 1)[0].strip().strip('"')
            elif key == "description" and desc is None:
                desc = val[1:-1] if len(val) >= 2 and val[0] == '"' and val[-1] == '"' else val.strip('"')
        if not name:
            raise ValueError(f"{path}: frontmatter has no name")
        return cls(name=name, description=desc or "", body=body)

    def codex_description(self):
        """the trigger sentence, without the claude-only <example> blocks.

        splits on the `<example>` tag regardless of how the surrounding newlines
        are encoded (escaped `\\n` vs real), then collapses whitespace.

        # Returns
        a single-line codex agent description.
        """
        head = self.description.split("<example>")[0]
        return re.sub(r"\s+", " ", head.replace("\\n", " ").replace('\\"', '"')).strip()

    def to_codex_agent(self):
        """render this agent as a codex TOML agent file.

        # Returns
        the full `.toml` text (name + description + developer_instructions),
        trailing newline.
        """
        return (f"name = {toml_basic(self.name)}\n"
                f"description = {toml_basic(self.codex_description())}\n"
                f"developer_instructions = {toml_multiline(self.body)}\n")


@dataclass
class Compiler(Artifact):
    """compiles every claude agent in a tree into codex TOML agents.

    a brainlib.Artifact: it supplies only `targets()` and `summary()`; the
    drift-gate (build / --check / byte-compare) is inherited, not re-rolled.
    """

    agents_dir: Path = None

    def targets(self):
        """the codex agent files, one `.toml` per source `.md` (recursive).

        raises on a duplicate agent `name` across the tree - two sources mapping
        to one output path would otherwise silently overwrite, and `--check`
        would never see the loss.

        # Returns
        a list of (path, content) pairs.
        """
        if self.agents_dir is None:
            raise ValueError("Compiler.agents_dir is required")
        out, seen = [], {}
        for path in sorted(self.agents_dir.rglob("*.md")):
            agent = Agent.parse(path)
            dst = self.out_dir / f"{agent.name}.toml"
            if dst in seen:
                raise ValueError(f"duplicate agent name {agent.name!r}: {seen[dst]} and {path}")
            seen[dst] = path
            out.append((dst, agent.to_codex_agent()))
        return out

    def summary(self):
        """a one-line build summary.

        # Returns
        the directory and the compiled agent names.
        """
        names = sorted(path.stem for path, _ in self.targets())
        return f"compile done -> {self.out_dir}\n  codex agents: {', '.join(names)}"


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """compile the agents to codex TOML, or check them against disk."""
    Compiler(out_dir=CODEX_OUT, agents_dir=AGENTS_DIR).run(sys.argv, "compile")


if __name__ == "__main__":
    main()
