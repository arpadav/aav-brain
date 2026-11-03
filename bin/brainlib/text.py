"""brainlib.text: the pure helpers - read, write, clip, stamp, parse, and total readers over parsed data.

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
from typing import TypeGuard

# --------------------------------------------------
# constants
# --------------------------------------------------
# the line that opens a markdown file's frontmatter block and the line that closes it
FENCE = "---"
# a whole line that is a fence: the fence alone, trailing blanks and a crlf's carriage return allowed
FENCE_LINE = re.compile(rf"{re.escape(FENCE)}[ \t]*\r?")


class Json:
    """total readers over a parsed json or toml value: each answers an empty value of its shape for any other."""

    @staticmethod
    def is_object(value: object) -> TypeGuard[dict[str, object]]:
        """whether a parsed value is an object; json and toml keys are always strings.

        # Arguments

        * `value` - a value as `json.loads` or `tomllib.loads` returned it

        # Returns

        True for an object, which narrows the type for the caller; False for anything else

        # Example

            >>> Json.is_object({"a": 1}), Json.is_object([1]), Json.is_object("a")
            (True, False, False)
        """
        return isinstance(value, dict)

    @staticmethod
    def is_array(value: object) -> TypeGuard[list[object]]:
        """whether a parsed json value is an array.

        # Arguments

        * `value` - a value as `json.loads` returned it

        # Returns

        True for an array, which narrows the type for the caller; False for anything else

        # Example

            >>> Json.is_array([1]), Json.is_array({"a": 1}), Json.is_array("a")
            (True, False, False)
        """
        return isinstance(value, list)

    @staticmethod
    def fields(value: object) -> dict[str, object]:
        """a json object's fields, or none.

        # Arguments

        * `value` - a parsed value of any shape

        # Returns

        the object itself when it is one, else an empty dict

        # Example

            >>> Json.fields({"a": 1}), Json.fields([1])
            ({'a': 1}, {})
        """
        return value if Json.is_object(value) else {}

    @staticmethod
    def members(value: object) -> list[object]:
        """a json array's members, or none.

        # Arguments

        * `value` - a parsed value of any shape

        # Returns

        the array itself when it is one, else an empty list

        # Example

            >>> Json.members([1, 2]), Json.members({"a": 1})
            ([1, 2], [])
        """
        return value if Json.is_array(value) else []

    @staticmethod
    def text(value: object) -> str:
        """a json string, or an empty one.

        # Arguments

        * `value` - a parsed value of any shape

        # Returns

        the string itself when it is one, else an empty string

        # Example

            >>> Json.text("a"), Json.text(3)
            ('a', '')
        """
        return value if isinstance(value, str) else ""


def clip(text: str, limit: int | None = None) -> str:
    r"""collapse whitespace and truncate text for storage.

    # Arguments
    * `text` - the raw text
    * `limit` - the maximum number of characters to keep; None keeps every one

    # Returns
    the whitespace-collapsed, length-capped text

    # Example

        >>> clip("  a   ragged\n  line  ")
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


def parse_iso(stamp: str) -> dt.datetime | None:
    """an iso-8601 stamp as an aware datetime; reads back what `iso_now` writes.

    a stamp with no zone is read as utc, the zone every brain log is stamped in,
    so a hand-typed `2026-10-31` compares against a logged `...Z` stamp

    # Arguments

    * `stamp` - the stamp as stored or typed

    # Returns

    the instant, or None when the stamp is empty or not iso-8601

    # Example

        >>> parse_iso("2026-10-31T17:22:44.644Z")
        datetime.datetime(2026, 10, 31, 17, 22, 44, 644000, tzinfo=datetime.timezone.utc)
        >>> parse_iso("2026-10-31") == parse_iso("2026-10-31T00:00:00Z")
        True
        >>> parse_iso(""), parse_iso("yesterday")
        (None, None)
    """
    try:
        instant = dt.datetime.fromisoformat(stamp)
    except ValueError:
        return None
    return instant if instant.tzinfo else instant.replace(tzinfo=dt.UTC)


def kind_rank(kind: str) -> int:
    """a kind's sort position, tolerating an unknown kind.

    # Arguments

    * `kind` - the kind string as read from a principle's or interest's frontmatter, or the built graph

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


def split_frontmatter(text: str) -> tuple[str, str] | None:
    r"""split a markdown file into its frontmatter block and the body after it.

    the one reader of the fence: a block opens when the file's first line is a
    fence and closes on the next line that is one

    # Arguments

    * `text` - the full file contents

    # Returns

    a (frontmatter, body) pair, the frontmatter being the lines between the
    fences; ("", text) when the file opens on no fence; None when a block opens
    and never closes

    # Example

        >>> split_frontmatter("---\nname: a\n---\n# A\n")
        ('name: a', '# A\n')
        >>> split_frontmatter("---\r\nname: a\r\n--- \r\n# A\r\n")
        ('name: a\r', '# A\r\n')
        >>> split_frontmatter("# no block"), split_frontmatter("----\nname: a\n---\n")
        (('', '# no block'), ('', '----\nname: a\n---\n'))
        >>> split_frontmatter("---\nname: never closed") is None
        True
    """
    lines = text.split("\n")
    if not FENCE_LINE.fullmatch(lines[0]):
        return "", text
    close = next((at for at, line in enumerate(lines[1:], 1) if FENCE_LINE.fullmatch(line)), None)
    if close is None:
        return None
    return "\n".join(lines[1:close]), "\n".join(lines[close + 1:])


def parse_frontmatter(text: str) -> Frontmatter:
    r"""parse a markdown file's yaml-ish frontmatter without a yaml dependency.

    handles scalars, bare lists ([a, b]) for interest/tension, and quoted
    lists (["a, b"]) for tells

    # Arguments
    * `text` - the full file contents

    # Returns
    a dict of frontmatter fields, or an empty dict if there is none or it never closes

    # Example

        >>> parse_frontmatter('---\nname: a\ntells: ["x, y", "z"]\ninterest: [p, q]\n---\nbody')
        {'name': 'a', 'tells': ['x, y', 'z'], 'interest': ['p', 'q']}
    """
    split = split_frontmatter(text)
    if split is None:
        return {}
    front, _ = split
    fields: Frontmatter = {}
    # --------------------------------------------------
    # parse one key: value per line
    # --------------------------------------------------
    for line in front.split("\n"):
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
