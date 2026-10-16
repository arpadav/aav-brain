"""brainlib.text: the pure helpers - read, write, clip, stamp, parse.

no state and no i/o policy beyond the one encoding this repo uses, so every
tool reads and writes bytes the same way

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.vocab import ENCODING, Frontmatter, Kind

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
import os
import re
from pathlib import Path

def clip(text: str, limit: int) -> str:
    r"""collapse whitespace and truncate text for storage.

    # Arguments
    * `text` - the raw text
    * `limit` - the maximum number of characters to keep

    # Returns
    the whitespace-collapsed, length-capped text

    # Example

        >>> clip("  a   ragged\n  line  ", 20)
        'a ragged line'
        >>> clip("truncated hard", 9)
        'truncated'
    """
    return re.sub(r"\s+", " ", text).strip()[:limit]


def iso_now() -> str:
    """the current instant as an iso-8601 utc stamp with microsecond resolution.

    the resolution is load-bearing: a record's ts is part of its identity, and
    `supersedes` keys on it, so two records in one second must not collide

    # Returns
    the stamp, e.g. `2026-08-17T13:24:41.290526Z`
    """
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def kind_rank(kind: str) -> int:
    """a card kind's sort position, tolerating an unknown kind.

    # Arguments

    * `kind` - the kind string as read from a card or the built graph

    # Returns

    the kind's rank, or one past the last known kind when unrecognised

    # Example

        >>> kind_rank("principle"), kind_rank("interest"), kind_rank("bogus")
        (0, 1, 2)
    """
    try:
        return Kind(kind).rank
    except ValueError:
        return len(Kind)


def read_text(path: Path) -> str:
    """read a text file in the repo's encoding.

    # Arguments

    * `path` - the file to read

    # Returns

    the file's decoded contents
    """
    return path.read_text(encoding=ENCODING)


def write_text(path: Path, content: str) -> None:
    """write a text file in the repo's encoding, atomically, creating its parents.

    the write lands on a temporary file in the same directory and is renamed
    over the target, so a reader sees either the whole previous file or the
    whole new one. a direct write truncates first, and a failure between the
    truncate and the last byte leaves a corpus that cannot be recovered - the
    ledger's rewriting paths carry records whose sources have expired

    # Arguments

    * `path` - the file to write
    * `content` - the text to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f"{path.name}.tmp{os.getpid()}")
    try:
        staged.write_text(content, encoding=ENCODING)
        staged.replace(path)
    finally:
        staged.unlink(missing_ok=True)


def parse_frontmatter(text: str) -> Frontmatter:
    """parse a card's yaml-ish frontmatter without a yaml dependency.

    handles scalars, bare lists ([a, b]) for interest/tension, and quoted
    lists (["a, b"]) for tells

    # Arguments
    * `text` - the full card file contents

    # Returns
    a dict of frontmatter fields, or an empty dict if there is none
    """
    # --------------------------------------------------
    # isolate the block between the leading --- fences
    # --------------------------------------------------
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fields: Frontmatter = {}
    # --------------------------------------------------
    # parse one key: value per line
    # --------------------------------------------------
    for line in text[3:end].split("\n"):
        match = re.match(r"^([a-z_]+):\s*(.*)$", line.strip())
        if not match:
            continue
        key, rest = match.group(1), match.group(2).strip()
        if key == "tells":
            fields[key] = re.findall(r'"([^"]*)"', rest)
        elif rest.startswith("["):
            fields[key] = [t.strip() for t in rest.strip("[]").split(",") if t.strip()]
        else:
            fields[key] = rest
    return fields
