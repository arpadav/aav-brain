#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-fmt: deterministic comment + separator hygiene over source files.

a recurring style sweep, committed because it runs on every style pass and its
ruleset is worth versioning (P19). two idempotent rules:
- strip a single trailing period from a plain `# ` line comment (not doc lines,
  not urls, not `...`).
- a separator line of 3+ hyphens is normalised to exactly 50.

casing is deliberately NOT touched: a separator label can legitimately carry an
identifier or proper noun (a state name, `$AAV_BRAIN`, `P29`), so force-lowering
it would corrupt meaning. label casing stays the author's call.

    python3 brain-fmt.py path [path ...]      rewrite in place
    python3 brain-fmt.py --check path [...]    exit 1 if any file would change

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import re
import sys
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# a full-width comment separator is exactly fifty hyphens
SEP = "-" * 50
# a run of three-or-more hyphens after a comment marker is a separator to fix
SEP_RE = re.compile(r"^(\s*)#\s*-{3,}\s*$")
# a plain one-# prose comment, candidate for a trailing-period trim
COMMENT_RE = re.compile(r"^(\s*#\s+.*?[A-Za-z0-9])\.\s*$")

# --------------------------------------------------
# helpers (pure)
# --------------------------------------------------
def fmt_line(line):
    """apply the two hygiene rules to one line.

    # Arguments
    * `line` - the source line, without its trailing newline.

    # Returns
    the reformatted line.
    """
    # --------------------------------------------------
    # separator: collapse any 3+ hyphen rule to exactly fifty
    # --------------------------------------------------
    match = SEP_RE.match(line)
    if match:
        return f"{match.group(1)}# {SEP}"
    # --------------------------------------------------
    # prose comment: trim one trailing period, leave `...` and urls
    # --------------------------------------------------
    if COMMENT_RE.match(line) and not line.rstrip().endswith("..") and "://" not in line:
        return line.rstrip()[:-1].rstrip()
    return line


def fmt_text(text):
    """run fmt_line over every line of a file's contents.

    # Arguments
    * `text` - the full file contents.

    # Returns
    the reformatted text.
    """
    return "\n".join(fmt_line(line) for line in text.split("\n"))


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """rewrite (or --check) every path argument."""
    args = sys.argv[1:]
    check = bool(args) and args[0] == "--check"
    paths = args[1:] if check else args
    if not paths:
        sys.exit("usage: brain-fmt.py [--check] path [path ...]")
    changed = 0
    for raw in paths:
        path = Path(raw)
        before = path.read_text(encoding="utf-8")
        after = fmt_text(before)
        if before != after:
            changed += 1
            if not check:
                path.write_text(after, encoding="utf-8")
    if check and changed:
        sys.exit(f"brain-fmt: {changed} file(s) need formatting - run without --check")
    print(f"brain-fmt: {changed} file(s) {'would change' if check else 'rewritten'}")


if __name__ == "__main__":
    main()
