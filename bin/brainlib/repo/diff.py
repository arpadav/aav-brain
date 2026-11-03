"""brainlib.repo.diff: git's unified diff text, read for the lines its new side adds.

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import os
import re
from collections.abc import Iterator
from typing import ClassVar

# --------------------------------------------------
# constants
# --------------------------------------------------
# a hunk header of a two-sided diff, capturing the first line of the new side
HUNK = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
# one escape inside a name git quotes: three octal digits for a byte, else one character
QUOTED_ESCAPE = re.compile(rb"\\(?:(?P<octal>[0-7]{3})|(?P<char>.))", re.DOTALL)
# the letter escapes of a quoted name; any other escaped character stands for itself (`\"`, `\\`)
LETTER_ESCAPES = {b"a": b"\a", b"b": b"\b", b"t": b"\t", b"n": b"\n", b"v": b"\v", b"f": b"\f", b"r": b"\r"}


class Patch:
    """git's unified diff text, read for the lines its new side adds."""

    # before the subcommand: a non-ascii name printed as itself, not octal-escaped, and a blank
    # context line kept as one space
    CONFIG: ClassVar[tuple[str, ...]] = ("-c", "core.quotePath=false", "-c", "diff.suppressBlankEmpty=false")
    # after it: plain text, no colour / external diff / textconv, a submodule as its pointer, a/ b/ prefixes
    ARGS: ClassVar[tuple[str, ...]] = ("--no-color", "--no-ext-diff", "--no-textconv", "--submodule=short",
                                       "--src-prefix=a/", "--dst-prefix=b/")

    @classmethod
    def added(cls, text: str) -> Iterator[tuple[str, int, str]]:
        r"""each row a diff adds: (the file's new name, its 1-based new-side line, its text); any number of files.

        a row is read by where it falls: a `diff` header ends the hunk before it,
        a header row outside a hunk may name the file, and inside a hunk an
        added row is kept while it and a context row move the new side's line
        on; a removed row and git's `\ No newline` note do not move it. only a
        two-sided diff is read: a combined diff's `@@@` header opens no hunk

        # Arguments

        * `text` - diff text git printed with `CONFIG` before its subcommand and `ARGS` after it

        # Returns

        the added rows in diff order, each without its `+`

        # Example

            >>> text = ('diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1,2 +1,3 @@\n a\n+x\n-b\n+++y\n'
            ...         '\\ No newline at end of file\n'
            ...         'diff --git "a/m\\303\\251" "b/m\\303\\251"\n--- "a/m\\303\\251"\n+++ "b/m\\303\\251"\n'
            ...         '@@ -0,0 +4,2 @@\n+one\n+two\n')
            >>> list(Patch.added(text))
            [('f', 2, 'x'), ('f', 3, '++y'), ('mé', 4, 'one'), ('mé', 5, 'two')]
        """
        name, line, hunk = "", 0, False
        for row in text.split("\n"):
            # --------------------------------------------------
            # a file opens, closing the hunk before it
            # --------------------------------------------------
            if row.startswith("diff "):
                hunk = False
            # --------------------------------------------------
            # a hunk header sets the new side's first line
            # --------------------------------------------------
            elif opened := HUNK.match(row):
                hunk, line = True, int(opened.group(1))
            # --------------------------------------------------
            # outside a hunk only the new side's name is read
            # --------------------------------------------------
            elif not hunk:
                if row.startswith("+++ "):
                    name = cls.new_name(row)
            # --------------------------------------------------
            # inside a hunk an added row is kept; it and a context row advance the new side
            # --------------------------------------------------
            elif row.startswith("+"):
                yield name, line, row.removeprefix("+")
                line += 1
            elif row.startswith(" ") or not row:
                line += 1

    @classmethod
    def new_name(cls, row: str) -> str:
        r"""the new side's name on a `+++ ` row, as the file is named on disk.

        git ends a name holding a space with a TAB, and wraps a name holding a
        quote, a backslash or a control character in quotes with C escapes

        # Arguments

        * `row` - a diff row opening with `+++ `

        # Returns

        the name relative to its repo, without git's `b/`

        # Example

            >>> [Patch.new_name(row) for row in ('+++ b/my file\t', '+++ "b/qu\\"o\\\\te\\tab"', '+++ b/café')]
            ['my file', 'qu"o\\te\tab', 'café']
        """
        name = row.removeprefix("+++ ").removesuffix("\t")
        if len(name) > 1 and name.startswith('"') and name.endswith('"'):
            name = os.fsdecode(QUOTED_ESCAPE.sub(cls.unescape, os.fsencode(name[1:-1])))
        return name.removeprefix("b/")

    @staticmethod
    def unescape(escape: re.Match[bytes]) -> bytes:
        r"""the byte one escape in a quoted name stands for.

        # Arguments

        * `escape` - a QUOTED_ESCAPE match

        # Returns

        an octal escape's byte, a letter escape's control byte, else the escaped byte itself

        # Example

            >>> [Patch.unescape(m) for m in QUOTED_ESCAPE.finditer(rb'\303\t\"')]
            [b'\xc3', b'\t', b'"']
        """
        if octal := escape["octal"]:
            return bytes([int(octal, 8)])
        return LETTER_ESCAPES.get(char := escape["char"], char)
