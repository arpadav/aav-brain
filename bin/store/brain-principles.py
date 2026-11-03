#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-principles: lint the principles and interests for structural integrity.

a recurring deterministic check (P19), called by brain-meta-curate and
brain-self-refine. it reports structural errors only (gate-failing under
--check): a dangling [[principle-*]] / [[intent-*]] link, a principle or interest
missing required frontmatter (name, kind), or one not listed in INDEX.md. a `tells`
phrase shared across principles is NOT a finding - one signal can legitimately
evidence two principles (a heat quote belongs to both its topic principle and P15), so
cross-cutting tells are allowed by design, not linted

    b-principles     report structural errors
    b-principles -c  FINDINGS when there is an error

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Confidence, Exit, Flag, Frontmatter, Kind, Layout, Tier, Tool, parse_frontmatter, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import re
import tomllib
from dataclasses import dataclass, field

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))


@dataclass
class StoreLinter:
    """lints the store: every principle under brain/principles and every interest under brain/intents.

    `errors` are structural defects that fail the --check gate (dangling links,
    missing frontmatter, INDEX omissions). shared `tells` are not linted
    """

    layout: Layout
    errors: list[str] = field(default_factory=list)

    @staticmethod
    def schema_errors(name: str, front: Frontmatter) -> list[str]:
        """check one principle's or interest's frontmatter against schema/principle.md.

        the schema declares `kind` and `confidence` as closed sets and
        `evidence_count` as an integer; nothing enforced them, so a typo in a
        principle was invisible until something downstream silently defaulted

        # Arguments

        * `name` - the principle's or interest's name, for the message
        * `front` - its parsed frontmatter

        # Returns

        one message per field that violates the schema
        """
        # --------------------------------------------------
        # name and kind must be present, and kind must be a known one
        # --------------------------------------------------
        out: list[str] = []
        if "name" not in front or "kind" not in front:
            out.append(f"{name}: missing name/kind frontmatter")
        kind = front.get("kind", "")
        if kind and kind not in tuple(Kind):
            out.append(f"{name}: kind '{kind}' is not one of {[k.value for k in Kind]}")
        # --------------------------------------------------
        # confidence, evidence_count and tells are principle-only per the schema
        # --------------------------------------------------
        if kind != Kind.PRINCIPLE:
            return out
        confidence = front.get("confidence", "")
        if confidence and confidence not in tuple(Confidence):
            out.append(f"{name}: confidence '{confidence}' is not one of {[c.value for c in Confidence]}")
        # --------------------------------------------------
        # the tier decides whether the principle reaches an agent
        # --------------------------------------------------
        tier = front.get("tier", "")
        if not tier:
            out.append(f"{name}: no tier - it decides whether the principle ever reaches an agent, and "
                       f"an absent one silently defaults to {Tier.CONDITIONAL.value}")
        elif tier not in tuple(Tier):
            out.append(f"{name}: tier '{tier}' is not one of {[t.value for t in Tier]}")
        # --------------------------------------------------
        # evidence_count must be an integer when present
        # --------------------------------------------------
        count = front.get("evidence_count", "")
        if isinstance(count, str) and count and not count.lstrip("-").isdigit():
            out.append(f"{name}: evidence_count '{count}' is not an integer")
        return out

    def tier_drift(self, documents: dict[str, Frontmatter]) -> list[str]:
        """every principle whose tier disagrees with the authored measurement.

        the frontmatter is what recall reads and tiers.toml is what produced it.
        checking them against each other is what stops a tier being hand-promoted
        - the failure the policy file was written to prevent

        # Arguments

        * `documents` - each principle's and interest's frontmatter, keyed by name

        # Returns

        one message per disagreement, and one per principle the policy never measured
        """
        # --------------------------------------------------
        # the policy file must exist and parse
        # --------------------------------------------------
        path = self.layout.tiers_toml
        if not path.is_file():
            return [f"no {path.name} - the tier of every principle is then unexplained"]
        try:
            policy = tomllib.loads(read_text(path))
        except (tomllib.TOMLDecodeError, OSError) as broken:
            return [f"{path.name} unreadable ({broken})"]
        # --------------------------------------------------
        # compare each principle against its measured row
        # --------------------------------------------------
        measured = policy.get("principles", {})
        out: list[str] = []
        for name, front in sorted(documents.items()):
            if front.get("kind") != Kind.PRINCIPLE:
                continue
            row = measured.get(name)
            if row is None:
                out.append(f"{name}: not in {path.name} - its tier rests on nothing recorded")
            elif row.get("tier") != front.get("tier"):
                out.append(f"{name}: tier '{front.get('tier')}' but {path.name} measured "
                           f"'{row.get('tier')}' - re-derive, do not hand-edit either side")
        # --------------------------------------------------
        # report measured rows that no principle owns
        # --------------------------------------------------
        out.extend(f"{path.name} measures {name}, which is not a principle"
                   for name in sorted(set(measured) - set(documents)))
        return out

    def interest_errors(self, documents: dict[str, Frontmatter]) -> list[str]:
        """every `interest:` naming a document that does not exist.

        intents are not graph nodes, so no other tool resolves the field and a
        typo would pass every tool

        # Arguments

        * `documents` - each principle's and interest's frontmatter, keyed by name

        # Returns

        one message per unresolvable interest name
        """
        known = {path.stem for path in self.layout.intents.glob("*.md")}
        out: list[str] = []
        for name, front in sorted(documents.items()):
            raw = front.get("interest", [])
            named = raw if isinstance(raw, list) else [raw]
            out.extend(f"{name}: interest '{one}' has no document in {self.layout.intents.name}/"
                       for one in named if one and one not in known)
        return out

    def run(self) -> "StoreLinter":
        """scan every principle and interest and collect structural errors.

        # Returns
        self, for chaining
        """
        documents: dict[str, tuple[Frontmatter, str, Path]] = {}
        # --------------------------------------------------
        # load every principle's and interest's frontmatter + body
        # --------------------------------------------------
        for directory in self.layout.store_dirs:
            for path in sorted(directory.glob("*.md")):
                text = read_text(path)
                front = parse_frontmatter(text)
                named = front.get("name", path.stem)
                name = named if isinstance(named, str) else path.stem
                documents[name] = (front, text, directory)
                self.errors.extend(self.schema_errors(name, front))
        names = set(documents)
        fronts = {n: f for n, (f, _t, _d) in documents.items()}
        self.errors.extend(self.tier_drift(fronts))
        self.errors.extend(self.interest_errors(fronts))
        # --------------------------------------------------
        # dangling links + index membership (errors)
        # --------------------------------------------------
        index = read_text(self.layout.index)
        for name, (_front, text, directory) in documents.items():
            for link in re.findall(r"\[\[((?:principle|intent)-[a-z0-9-]+)\]\]", text):
                if link not in names:
                    self.errors.append(f"{name}: dangling link [[{link}]]")
            if f"[[{directory.name}/{name}]]" not in index:
                self.errors.append(f"{name}: not listed in INDEX.md")
        return self


def main(args: Args) -> Exit:
    """lint the principles and interests, print structural errors, and gate --check on them.

    # Arguments

    * `args` - the parsed command line; `--check` turns an error into a failing status

    # Returns

    `Exit.FINDINGS` under `--check` when any principle or interest has a structural error, else `Exit.OK`
    """
    linter = StoreLinter(Layout.discover()).run()
    for error in linter.errors:
        print(f"  error: {error}")
    print(f"{TOOL}: {len(linter.errors)} error(s)")
    return Exit.FINDINGS if args.has(Flag.CHECK) and linter.errors else Exit.OK


if __name__ == "__main__":
    Tool.of(TOOL, __doc__).run(main)
