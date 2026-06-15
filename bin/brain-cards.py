#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-cards: lint the principle/interest cards for structural integrity.

a recurring deterministic check (P19), called by brain-meta-curate and
brain-self-refine. it reports structural errors only (gate-failing under
--check): a dangling [[principle-*]] / [[intent-*]] link, a card missing
required frontmatter (name, kind), or a card not listed in INDEX.md. a `tells`
phrase shared across cards is NOT a finding - one signal can legitimately
evidence two cards (a heat quote belongs to both its topic card and P15), so
cross-cutting tells are allowed by design, not linted.

    python3 brain-cards.py            report structural errors
    python3 brain-cards.py --check    exit 1 if there is an error

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from brainlib import find_brain, parse_frontmatter

# --------------------------------------------------
# types
# --------------------------------------------------
@dataclass
class CardLinter:
    """lints every card under brain/principles and brain/intents.

    `errors` are structural defects that fail the --check gate (dangling links,
    missing frontmatter, INDEX omissions). shared `tells` are not linted.
    """

    store: Path
    errors: list = field(default_factory=list)

    def card_dirs(self):
        """the directories holding cards.

        # Returns
        the principles and intents directory paths.
        """
        return [self.store / "principles", self.store / "intents"]

    def run(self):
        """scan every card and collect structural errors.

        # Returns
        self, for chaining.
        """
        cards = {}
        # --------------------------------------------------
        # load every card's frontmatter + body
        # --------------------------------------------------
        for directory in self.card_dirs():
            for path in sorted(directory.glob("*.md")):
                text = path.read_text(encoding="utf-8")
                front = parse_frontmatter(text)
                name = front.get("name", path.stem)
                cards[name] = (front, text)
                if "name" not in front or "kind" not in front:
                    self.errors.append(f"{name}: missing name/kind frontmatter")
        names = set(cards)
        # --------------------------------------------------
        # dangling links + index membership (errors)
        # --------------------------------------------------
        index = (self.store / "INDEX.md").read_text(encoding="utf-8")
        for name, (front, text) in cards.items():
            for link in re.findall(r"\[\[((?:principle|intent)-[a-z0-9-]+)\]\]", text):
                if link not in names:
                    self.errors.append(f"{name}: dangling link [[{link}]]")
            if f"[[{('principles' if 'principle' in name else 'intents')}/{name}]]" not in index:
                self.errors.append(f"{name}: not listed in INDEX.md")
        return self


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """lint the cards, print structural errors, and gate --check on them."""
    aav_brain = find_brain()
    linter = CardLinter(aav_brain / "brain").run()
    for error in linter.errors:
        print(f"  error: {error}")
    print(f"brain-cards: {len(linter.errors)} error(s)")
    if "--check" in sys.argv and linter.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
