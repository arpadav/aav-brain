#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-register: flag conversational filler in docs (P57, textbook / ICD register).

a doc heading is a noun phrase and an instruction is an imperative. the flagged
forms, each from his corrections: "Now the bytes" -> "Bytes", "The struct" ->
"Struct", "Run it" -> "Run this example", "No length: the example" ->
"Example: without length". prose is checked for a closed set of filler phrases.
fenced code is skipped. a hit is a finding to rewrite, never an auto-fix

    python3 brain-register.py [FILE...]   lint the named .md files; with none,
                                          every changed or untracked .md in the repo

exits 1 when anything is flagged

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Exit

# --------------------------------------------------
# external
# --------------------------------------------------
import re
import subprocess

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
# a heading longer than this is a sentence title (an open item's one-line problem
# statement), which is the right form there; the rules target short fragments
FRAGMENT_WORDS = 6
# (rule, pattern) over a heading's text
HEADING_RULES = (
    ("heading opens with a filler word",
     re.compile(r"^(now|so|next|then|finally|okay|ok|here'?s?|let'?s|time to)\b", re.IGNORECASE)),
    ("heading opens with an article", re.compile(r"^(the|a|an)\s", re.IGNORECASE)),
    ("heading ends on a bare pronoun", re.compile(r"\b(it|them|this|that)$", re.IGNORECASE)),
    ("heading puts an article after its colon", re.compile(r":\s+(the|a|an)\s", re.IGNORECASE)),
    ("heading ends in ! or ?", re.compile(r"[!?]$")),
)
# filler phrases in prose; matched case-insensitively on word boundaries
FILLER = (
    "let's", "let us", "dive in", "deep dive", "under the hood", "the good news", "spoiler",
    "in a nutshell", "here's the thing", "here's what", "it's worth noting", "simply put",
    "the short version", "tl;dr", "buckle up", "voila", "the punchline", "the trick is",
    "turns out", "what i need from you", "game changer", "magic happens",
)
FILLER_RE = re.compile(r"\b(" + "|".join(re.escape(p) for p in FILLER) + r")\b", re.IGNORECASE)


def lint_text(text: str) -> list[tuple[int, str, str]]:
    r"""every register finding in one markdown text.

    # Arguments

    * `text` - the markdown source

    # Returns

    (line number, rule, offending text) per finding, in file order

    # Example

        >>> [r for _, r, _ in lint_text("# Now the bytes\n## Example: without length\n### Run it\n")]
        ['heading opens with a filler word', 'heading ends on a bare pronoun']
        >>> lint_text("# Q11: `tk-syn-macros` has no lints table, so clippy never runs on it\n")
        []
        >>> lint_text("```\n# The struct\n```\nLet's dive in.\n")[0][:2]
        (4, 'filler phrase')
    """
    found: list[tuple[int, str, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        # --------------------------------------------------
        # code fences toggle; nothing inside one is prose
        # --------------------------------------------------
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        # --------------------------------------------------
        # a short heading: the first rule it breaks is enough
        # --------------------------------------------------
        if heading := HEADING_RE.match(line):
            title = heading.group(1)
            if len(title.split()) > FRAGMENT_WORDS:
                continue
            rule = next((name for name, pattern in HEADING_RULES if pattern.search(title)), None)
            if rule:
                found.append((number, rule, title))
            continue
        # --------------------------------------------------
        # prose: filler phrases
        # --------------------------------------------------
        if phrase := FILLER_RE.search(line):
            found.append((number, "filler phrase", phrase.group(1)))
    return found


def changed_docs() -> list[str]:
    """the changed and untracked .md files in the current repo.

    # Returns

    repo-relative paths, sorted
    """
    def lines(*argv: str) -> list[str]:
        done = subprocess.run(["git", *argv], capture_output=True, text=True, check=False)  # noqa: S603, S607
        return done.stdout.splitlines() if done.returncode == 0 else []

    names = set(lines("diff", "--name-only", "HEAD")) | set(lines("ls-files", "--others", "--exclude-standard"))
    return sorted(n for n in names if n.endswith(".md") and Path(n).exists())


def main() -> None:
    """lint the files and report."""
    args = Args.from_argv()
    args.gate(TOOL, __doc__)
    files = args.positional() or changed_docs()
    total = 0
    for name in files:
        for number, rule, text in lint_text(Path(name).read_text()):
            print(f"{name}:{number}: {rule}: {text}")
            total += 1
    print(f"{TOOL}: {total} finding(s) in {len(files)} file(s)", file=sys.stderr)
    sys.exit(Exit.DRIFT if total else Exit.OK)


if __name__ == "__main__":
    main()
