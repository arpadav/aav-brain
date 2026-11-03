#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-register: flag conversational filler in docs (P57, textbook / ICD register).

a doc heading is a noun phrase and an instruction is an imperative. the flagged
forms, each from his corrections: "Now the bytes" -> "Bytes", "The struct" ->
"Struct", "Run it" -> "Run this example", "No length: the example" ->
"Example: without length". prose is checked for a closed set of filler phrases.
fenced code is skipped. a hit is a finding to rewrite, never an auto-fix

    b-register [FILE...]  lint the named .md files; with none,
                          every changed or untracked .md in the repo

FINDINGS when anything is flagged

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Exit, Layout, RepoTree, Tool, find_repo_root

# --------------------------------------------------
# external
# --------------------------------------------------
import re

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
# an atx heading line; the group is its text without the leading and any closing hashes
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
# the line that opens or closes a fenced code block, backtick or tilde
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
# every filler phrase as one alternation
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


def changed_docs() -> list[Path]:
    """the changed and untracked .md files in the current repo; none outside a repo.

    # Returns

    absolute paths, sorted

    # Raises

    RepoError when git cannot list the repo
    """
    root = find_repo_root()
    changed = RepoTree((root,) if root else ()).changed()
    return sorted(p for p in changed if p.suffix == ".md" and p.is_file())


def main(args: Args) -> Exit:
    """lint the files and report.

    each finding prints as `file:line: rule: text`; the tally goes to stderr so
    stdout stays a clean list of findings

    # Arguments

    * `args` - the parsed command line; positionals are the markdown files to
      lint, defaulting to the docs the working tree has changed

    # Returns

    `Exit.FINDINGS` when any file has a finding, else `Exit.OK`
    """
    files = [Path(name) for name in args.positional()] or changed_docs()
    total = 0
    for name in files:
        for number, rule, text in lint_text(name.read_text()):
            print(f"{name}:{number}: {rule}: {text}")
            total += 1
    print(f"{TOOL}: {total} finding(s) in {len(files)} file(s)", file=sys.stderr)
    return Exit.FINDINGS if total else Exit.OK


if __name__ == "__main__":
    Tool.of(TOOL, __doc__, positionals=(0, None)).run(main)
