#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-cards: lint the principle/interest cards for structural integrity.

a recurring deterministic check (P19), called by brain-meta-curate and
brain-self-refine. it reports structural errors only (gate-failing under
--check): a dangling [[principle-*]] / [[intent-*]] link, a card missing
required frontmatter (name, kind), or a card not listed in INDEX.md. a `tells`
phrase shared across cards is NOT a finding - one signal can legitimately
evidence two cards (a heat quote belongs to both its topic card and P15), so
cross-cutting tells are allowed by design, not linted

    python3 brain-cards.py            report structural errors
    python3 brain-cards.py --check    exit 1 if there is an error

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Confidence, Exit, Flag, Frontmatter, Kind, Layout, parse_frontmatter, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem

@dataclass
class CardLinter:
    """lints every card under brain/principles and brain/intents.

    `errors` are structural defects that fail the --check gate (dangling links,
    missing frontmatter, INDEX omissions). shared `tells` are not linted
    """

    layout: Layout
    errors: list[str] = field(default_factory=list)

    @staticmethod
    def schema_errors(name: str, front: Frontmatter) -> list[str]:
        """check one card's frontmatter against schema/principle-card.md.

        the schema declares `kind` and `confidence` as closed sets and
        `evidence_count` as an integer; nothing enforced them, so a typo in a
        card was invisible until something downstream silently defaulted

        # Arguments

        * `name` - the card's name, for the message
        * `front` - the card's parsed frontmatter

        # Returns

        one message per field that violates the schema
        """
        out: list[str] = []
        if "name" not in front or "kind" not in front:
            out.append(f"{name}: missing name/kind frontmatter")
        kind = front.get("kind", "")
        if kind and kind not in tuple(Kind):
            out.append(f"{name}: kind '{kind}' is not one of {[k.value for k in Kind]}")
        # confidence, evidence_count and tells are principle-only per the schema
        if kind != Kind.PRINCIPLE:
            return out
        confidence = front.get("confidence", "")
        if confidence and confidence not in tuple(Confidence):
            out.append(f"{name}: confidence '{confidence}' is not one of {[c.value for c in Confidence]}")
        count = front.get("evidence_count", "")
        if isinstance(count, str) and count and not count.lstrip("-").isdigit():
            out.append(f"{name}: evidence_count '{count}' is not an integer")
        return out

    def run(self) -> "CardLinter":
        """scan every card and collect structural errors.

        # Returns
        self, for chaining
        """
        cards: dict[str, tuple[Frontmatter, str, Path]] = {}
        # --------------------------------------------------
        # load every card's frontmatter + body
        # --------------------------------------------------
        for directory in self.layout.card_dirs:
            for path in sorted(directory.glob("*.md")):
                text = read_text(path)
                front = parse_frontmatter(text)
                named = front.get("name", path.stem)
                name = named if isinstance(named, str) else path.stem
                cards[name] = (front, text, directory)
                self.errors.extend(self.schema_errors(name, front))
        names = set(cards)
        # --------------------------------------------------
        # dangling links + index membership (errors)
        # --------------------------------------------------
        index = read_text(self.layout.index)
        for name, (_front, text, directory) in cards.items():
            for link in re.findall(r"\[\[((?:principle|intent)-[a-z0-9-]+)\]\]", text):
                if link not in names:
                    self.errors.append(f"{name}: dangling link [[{link}]]")
            if f"[[{directory.name}/{name}]]" not in index:
                self.errors.append(f"{name}: not listed in INDEX.md")
        return self


def main() -> None:
    """lint the cards, print structural errors, and gate --check on them."""
    args = Args.from_argv()
    if unknown := args.unknown(Flag.CHECK):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    linter = CardLinter(Layout.discover()).run()
    for error in linter.errors:
        print(f"  error: {error}")
    print(f"{TOOL}: {len(linter.errors)} error(s)")
    if args.has(Flag.CHECK) and linter.errors:
        sys.exit(Exit.DRIFT)


if __name__ == "__main__":
    main()
