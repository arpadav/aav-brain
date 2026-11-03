#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-open-items: stamp open-item files and report which ones he edited.

an open item is one file, `plans/open-items/<ID>-<slug>.md`, ending in a footer
that holds the sha256 of everything above it. the brain writes the item and
stamps it; he edits it (usually under `## Your call`); a hash that no longer
matches is how the brain knows, without asking, which items carry his answer

    b-open-items stamp FILE...  write or refresh the footer
    b-open-items status [DIR]   list each item as edited | unchanged | unstamped
                                (DIR defaults to plans/open-items)

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Layout, Tool, UsageError

# --------------------------------------------------
# external
# --------------------------------------------------
import hashlib
import re

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
DEFAULT_DIR = Path("plans/open-items")
# the footer line; an html comment so it does not render
FOOTER = "<!-- sha256: {} -->"
# matched anywhere, so an answer typed below the footer still reads as an edit
FOOTER_RE = re.compile(r"^<!-- sha256: ([0-9a-f]{64}) -->[ \t]*$", re.MULTILINE)


def split(text: str) -> tuple[str, str | None]:
    r"""the item body and its stamped hash.

    # Arguments

    * `text` - the whole file

    # Returns

    (body with the footer line removed, the stamped hex or None when unstamped)

    # Example

        >>> split("# Q01: x\n\n<!-- sha256: " + "a" * 64 + " -->\nB\n")[0]
        '# Q01: x\n\nB'
        >>> split("# Q01: x\n")
        ('# Q01: x', None)
    """
    if match := FOOTER_RE.search(text):
        body = text[: match.start()].rstrip() + "\n\n" + text[match.end():].strip()
        return body.strip(), match.group(1)
    return text.rstrip(), None


def digest(body: str) -> str:
    r"""the sha256 of a body, trailing whitespace normalised.

    # Arguments

    * `body` - the item text above the footer

    # Returns

    the hex digest

    # Example

        >>> digest("a\n") == digest("a")
        True
    """
    return hashlib.sha256(body.rstrip().encode()).hexdigest()


def stamp(path: Path) -> None:
    """rewrite the file with a footer matching its current body.

    # Arguments

    * `path` - the item file
    """
    body, _ = split(path.read_text())
    path.write_text(f"{body}\n\n{FOOTER.format(digest(body))}\n")


def status(path: Path) -> str:
    """whether the item changed since it was stamped.

    # Arguments

    * `path` - the item file

    # Returns

    edited | unchanged | unstamped
    """
    body, stamped = split(path.read_text())
    if stamped is None:
        return "unstamped"
    return "unchanged" if stamped == digest(body) else "edited"


def main(args: Args) -> None:
    """dispatch the subcommand: `stamp FILE...` or `status [DIR]`.

    # Arguments

    * `args` - the parsed command line; the first positional is the subcommand,
      the rest are the files to stamp or the open-items directory to list

    # Raises

    UsageError for an unknown or incomplete subcommand, or a directory that does not exist
    """
    command, *rest = args.positional()
    # --------------------------------------------------
    # stamp: one footer per named file
    # --------------------------------------------------
    if command == "stamp" and rest:
        for name in rest:
            stamp(Path(name))
            print(f"stamped {name}")
        return
    # --------------------------------------------------
    # status: edited first, the ones carrying his answer
    # --------------------------------------------------
    if command == "status":
        folder = Path(rest[0]) if rest else DEFAULT_DIR
        if not folder.is_dir():
            raise UsageError(f"no open-items dir at {folder}")
        rows = sorted((status(item), item.name) for item in folder.glob("*.md"))
        for state, name in rows:
            print(f"{state:<10} {name}")
        return
    raise UsageError(f"unknown or incomplete command {command!r}")


if __name__ == "__main__":
    Tool.of(TOOL, __doc__, positionals=(1, None)).run(main)
