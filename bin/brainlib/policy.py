"""brainlib.policy: the authored policies: numbers read from toml so no tool hardcodes one.

PrunePolicy reads prune.toml, ShapePolicy and DecisionsPolicy read
shape.toml. each falls back to a stated default on a broken file and says so,
so a bad config still measures rather than going silent

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.file_io import read_text
from brainlib.repo.tree import git

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class PrunePolicy:
    """how old a trace entry must be before it is ELIGIBLE to be judged.

    eligibility is an age filter and nothing more. it narrows a several-hundred
    entry trace to the ones worth reading; deciding that any particular one is
    actually stale is a judgement made against what the brain is now, entry by
    entry. a tool that pruned everything past the cutoff would delete the oldest
    and most load-bearing decisions in the store first

    the window follows commit frequency because that is what sets how fast a
    decision goes out of date: a repo being reshaped weekly invalidates a
    three-week-old call, a quiet one does not

    # Example

        policy = PrunePolicy.load(LAYOUT.prune_toml)
        cutoff = policy.cutoff(rate=policy.commit_rate(LAYOUT.root))
    """

    busy_commits_per_week: float = 10.0
    sample_weeks: int = 8
    fast_days: int = 21
    slow_days: int = 60

    @classmethod
    def load(cls, path: Path) -> "PrunePolicy":
        """read the policy, falling back to the defaults when it is absent.

        # Arguments

        * `path` - the prune.toml path

        # Returns

        the policy; the field defaults when the file is absent, unreadable,
        malformed or the wrong shape. a broken config must WIDEN the window to
        the conservative default, never stop the tool - the same file is read
        beside the path that records decisions
        """
        if not path.is_file():
            return cls()
        try:
            window = tomllib.loads(read_text(path)).get("window", {})
            return cls(
                busy_commits_per_week=float(window.get("busy_commits_per_week", cls.busy_commits_per_week)),
                sample_weeks=max(1, int(window.get("sample_weeks", cls.sample_weeks))),
                fast_days=max(1, int(window.get("fast_days", cls.fast_days))),
                slow_days=max(1, int(window.get("slow_days", cls.slow_days))),
            )
        except (tomllib.TOMLDecodeError, AttributeError, TypeError, ValueError, OSError) as broken:
            print(f"prune policy unreadable ({broken}); using defaults", file=sys.stderr)
            return cls()

    def commit_rate(self, repo: Path) -> float:
        """commits per week in this repo over the sample window.

        # Arguments

        * `repo` - the repository to measure

        # Returns

        the rate; 0.0 when git is unavailable or the repo has no commits in the
        window, which selects the slow (more conservative) window
        """
        listed = git(repo, "log", "--since", f"{self.sample_weeks} weeks ago", "--format=%H")
        if listed is None:
            return 0.0
        return len(listed.split()) / self.sample_weeks

    def window_days(self, rate: float) -> int:
        """the eligibility window for a given commit rate.

        # Arguments

        * `rate` - commits per week

        # Returns

        the short window when the repo is busy, the long one otherwise

        # Example

            >>> policy = PrunePolicy()
            >>> policy.window_days(25.0), policy.window_days(1.0)
            (21, 60)
        """
        return self.fast_days if rate >= self.busy_commits_per_week else self.slow_days

    def cutoff(self, rate: float, now: dt.datetime | None = None) -> str:
        """the iso timestamp an entry must predate to be eligible.

        # Arguments

        * `rate` - commits per week, from `commit_rate`
        * `now` - the reference time; utc now when omitted

        # Returns

        an iso-8601 utc timestamp, string-comparable against a record's `ts`

        # Example

            >>> at = dt.datetime(2026, 3, 1, tzinfo=dt.UTC)
            >>> PrunePolicy().cutoff(1.0, at)
            '2025-12-31T00:00:00.000000Z'
        """
        moment = now or dt.datetime.now(dt.UTC)
        back = dt.timedelta(days=self.window_days(rate))
        # microseconds, matching iso_now: a record and this cutoff are compared
        # as STRINGS, and at second precision `.` sorts below `Z`, so a record
        # stamped inside the cutoff second would read as older than it
        return (moment - back).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class ShapePolicy:
    """the numbers behind P27 and P28.

    P27 says a file that is "too long" should split to a tree and P28 says a
    datatype defined twice should merge. both are adjectives, and a worker
    resolves an adjective against its own priors (P40). these fields are what
    make the two principles measurable. the build that forced these numbers is
    recorded once, on principle-27 under `## the measurement`, and is not
    retold here

    a crossing is a FINDING, not a verdict, exactly as PrunePolicy's window is
    eligibility and not a prune: a 2400-line table of sourced constants is one
    coherent file and nothing here may split it

    # Example

        policy = ShapePolicy.load(LAYOUT.shape_toml)
        policy.is_source(Path("src/ledger.rs"))
    """

    file_lines: int = 2000
    folder_files: int = 12
    collapse_files: int = 2
    collapse_lines: int = 120
    exempt: tuple[str, ...] = ()
    duplicate_type_files: int = 2
    suffixes: frozenset[str] = frozenset({".rs", ".py", ".ts", ".tsx", ".js", ".go", ".c", ".h", ".cpp", ".hpp", ".md"})
    excluded: tuple[str, ...] = ("/vendor/", "/node_modules/", "/target/", "/.generated/")
    prose: frozenset[str] = frozenset({".md", ".markdown", ".rst", ".txt"})

    @classmethod
    def load(cls, path: Path) -> "ShapePolicy":
        """read the policy, falling back to the defaults when it is absent.

        # Arguments

        * `path` - the shape.toml path

        # Returns

        the policy; the field defaults when the file is absent, unreadable,
        malformed or the wrong shape. a broken config must still MEASURE, the
        same way a broken prune policy still reports - a tool that goes silent
        on a bad config is the failure this whole principle set exists to prevent
        """
        # --------------------------------------------------
        # no policy file: the same rule the tool follows, never go quiet about a measurement
        # you could not take. a silently-swapped policy scans eleven suffixes
        # where the authored one scans twenty-five, and reports the shortfall
        # as a clean repo
        # --------------------------------------------------
        if not path.is_file():
            print(f"no {path.name} at {path.parent}; measuring against built-in defaults", file=sys.stderr)
            return cls()
        # --------------------------------------------------
        # parse the authored policy, clamping every number to its floor
        # --------------------------------------------------
        try:
            data = tomllib.loads(read_text(path))
            tree, scan = data.get("tree", {}), data.get("scan", {})
            return cls(
                file_lines=max(1, int(tree.get("file_lines", cls.file_lines))),
                folder_files=max(1, int(tree.get("folder_files", cls.folder_files))),
                collapse_files=max(1, int(tree.get("collapse_files", cls.collapse_files))),
                collapse_lines=max(1, int(tree.get("collapse_lines", cls.collapse_lines))),
                exempt=tuple(sorted(cls.listed(tree, "exempt", frozenset(cls.exempt)))),
                duplicate_type_files=max(2, int(tree.get("duplicate_type_files", cls.duplicate_type_files))),
                suffixes=cls.listed(scan, "suffixes", cls.suffixes),
                excluded=tuple(sorted(cls.listed(scan, "excluded", frozenset(cls.excluded)))),
                prose=cls.listed(scan, "prose", cls.prose),
            )
        except (tomllib.TOMLDecodeError, AttributeError, TypeError, ValueError, OSError) as broken:
            print(f"shape policy unreadable ({broken}); using defaults", file=sys.stderr)
            return cls()

    @staticmethod
    def listed(table: Mapping[str, Any], key: str, fallback: frozenset[str]) -> frozenset[str]:
        """one authored list of strings, or the fallback when it is not one.

        a bare `suffixes = "rs"` is a string, and a frozenset of it is the two
        characters `r` and `s` - every file then fails the suffix test and the
        tool reports a clean repo it never measured

        # Arguments

        * `table` - the config table to read
        * `key` - the list-valued key
        * `fallback` - what to use when the key is absent or not a list

        # Returns

        the authored strings, or the fallback

        # Example

            >>> ShapePolicy.listed({"s": "rs"}, "s", frozenset({".rs"}))
            frozenset({'.rs'})
        """
        value: object = table.get(key)
        if not isinstance(value, Sequence) or isinstance(value, str):
            if value is not None:
                print(f"shape policy: {key} is not a list of strings; using defaults", file=sys.stderr)
            return fallback
        strings = frozenset(item for item in value if isinstance(item, str))
        if len(strings) != len(value):
            print(f"shape policy: {key} is not a list of strings; using defaults", file=sys.stderr)
            return fallback
        return strings

    def is_source(self, path: Path) -> bool:
        """whether this path is measured at all.

        # Arguments

        * `path` - a repo-relative path

        # Returns

        true when the suffix is source and no excluded fragment appears in it.
        the fragments are matched with surrounding slashes, so a crate honestly
        named `build-support` is not mistaken for a build output

        # Example

            >>> policy = ShapePolicy()
            >>> policy.is_source(Path("src/ledger.rs")), policy.is_source(Path("target/x.rs"))
            (True, False)
        """
        if path.suffix not in self.suffixes:
            return False
        return not self.matches(path, self.excluded)

    def is_exempt(self, folder: Path) -> bool:
        """whether a folder's fan-out is the deliberate form, not a defect.

        the one place a real crossing may be silenced, so it is authored and
        narrow: a zettelkasten is one file per principle on purpose

        # Arguments

        * `folder` - the folder being judged, repo-relative

        # Returns

        true when an exempt fragment appears in the folder's path

        # Example

            >>> ShapePolicy(exempt=("/store/principles/",)).is_exempt(Path("store/principles"))
            True
        """
        return self.matches(folder, self.exempt)

    @staticmethod
    def matches(path: Path, fragments: tuple[str, ...]) -> bool:
        """whether any fragment appears in this path.

        the path is spelled with leading AND trailing slashes so a fragment
        matches a whole segment: a crate honestly named `build-support` is not
        mistaken for a build output, and `/store/principles/` matches the
        directory itself as well as the files inside it

        # Arguments

        * `path` - a repo-relative path
        * `fragments` - the slash-delimited fragments to look for

        # Returns

        true when any fragment appears

        # Example

            >>> ShapePolicy.matches(Path("src/target/a.rs"), ("/target/",))
            True
        """
        spelled = f"/{path.as_posix()}/"
        return any(fragment in spelled for fragment in fragments)


@dataclass(frozen=True)
class DecisionsPolicy:
    """the authored half of b-decisions' questions, read from shape.toml `[decisions]`.

    `reasons` maps a tracked generated path to WHY it is committed; a path with
    no entry is a finding. `reach_files` is the threshold past which a unit is
    named from too many places
    """

    reasons: dict[str, str]
    reach_files: int

    @classmethod
    def load(cls, path: Path) -> "DecisionsPolicy":
        """read the `[decisions]` table.

        # Arguments

        * `path` - the shape.toml path

        # Returns

        the policy; a missing or malformed table is reported on stderr and
        yields no reasons and a threshold of 1, so it over-reports, never hides
        """
        try:
            # --------------------------------------------------
            # the reason per tracked path, and the reach limit
            # --------------------------------------------------
            table = tomllib.loads(read_text(path)).get("decisions", {})
            return cls({str(k): str(v) for k, v in table.get("tracked", {}).items()},
                       max(1, int(table["reach_files"])))
        except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError, ValueError, AttributeError) as broken:
            # --------------------------------------------------
            # a missing or malformed table degrades to an empty policy that reports every finding, loudly
            # --------------------------------------------------
            print(f"decisions policy: no usable [decisions] in {path.name} ({broken}); every finding reported",
                  file=sys.stderr)
            return cls({}, 1)
