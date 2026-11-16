"""brainlib.generated: the build-and-drift-check harness every generated, committed file shares.

b-compile, b-flow and b-graph each subclass GeneratedFile, so the invariant
that a committed output equals a fresh build is checked in one place

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.cli import Args
from brainlib.enums import Exit, Flag
from brainlib.file_io import read_text, write_text

# --------------------------------------------------
# external
# --------------------------------------------------
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GeneratedFile:
    """base for a built, committed, drift-checked file.

    a builder subclass implements `targets()` (the files it owns, as
    (path, content) pairs) and `summary()` (a one-line status). this base
    provides the byte-identical drift check and the build/--check harness, so
    that invariant - committed output must equal a fresh build - lives once
    """

    out_dir: Path

    def targets(self) -> list[tuple[Path, str]]:
        """the files this builder owns.

        # Returns
        a list of (path, content-string) pairs. subclass responsibility
        """
        raise NotImplementedError

    def summary(self) -> str:
        """a one-line build summary.

        # Returns
        a status string. subclass responsibility
        """
        raise NotImplementedError

    def is_current(self) -> bool:
        """check whether every committed target matches a fresh build.

        # Returns
        true if all targets are byte-identical on disk

        # Example

            >>> import tempfile
            >>> class One(GeneratedFile):
            ...     def targets(self): return [(self.out_dir / "one.txt", "1")]
            ...     def summary(self): return "one"
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     built = One(Path(tmp) / "out")
            ...     before = built.is_current()
            ...     built.emit()
            ...     before, built.is_current()
            one
            (False, True)
        """
        return all(path.exists() and read_text(path) == content for path, content in self.targets())

    def emit(self) -> None:
        """write every target and print this builder's summary.

        creates the output folder when it is missing, writes each
        `(path, content)` pair `targets` yields, then prints `summary` on
        stdout
        """
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for path, content in self.targets():
            write_text(path, content)
        print(self.summary())

    def run(self, args: Args, label: str) -> Exit:
        """the build / --check harness for a single builder.

        # Arguments

        * `args` - the parsed command line
        * `label` - the tool's command (`Layout.command`), for messages and the rerun it names

        # Returns

        the verdict, as `run_all` gives it
        """
        return self.run_all([self], args, label)

    @staticmethod
    def run_all(files: Sequence["GeneratedFile"], args: Args, label: str) -> Exit:
        """the build / --check harness shared by every builder.

        --check names EVERY stale builder before exiting, so one drifting
        file cannot mask another behind an early exit

        # Arguments

        * `files` - the GeneratedFile instances to build or check
        * `args` - the parsed command line
        * `label` - the tool's command (`Layout.command`), for messages and the rerun it names

        # Returns

        FINDINGS when --check finds a stale builder, else OK
        """
        # --------------------------------------------------
        # check mode: name every stale builder, write nothing
        # --------------------------------------------------
        if args.has(Flag.CHECK):
            stale = [a for a in files if not a.is_current()]
            if not stale:
                print(f"{label}: current")
                return Exit.OK
            for file in stale:
                print(f"{label}: DRIFT in {type(file).__name__} -> {file.out_dir}")
            print(f"{label}: re-run `{label}`")
            return Exit.FINDINGS
        # --------------------------------------------------
        # build mode
        # --------------------------------------------------
        for file in files:
            file.emit()
        return Exit.OK
