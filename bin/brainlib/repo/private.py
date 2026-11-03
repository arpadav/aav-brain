"""brainlib.repo.private: the scan for his private infrastructure in what a push would publish (P61).

a PrivateScan holds the values: this machine's and its tailnet's, probed with
`ip` and `tailscale`, and the ones he declares in private.toml. a ScanScope
names the repos a scan covers, less the brain's private-data submodule, and
the source it reads from them: a WorkTree's files or the commits an Outgoing
push sends. b-private runs one scan per process; b-sync gathers the values
once per run and scans every repo it carries with them. what a scan reads and
what it leaves unread is b-private's to say: `b-private -h`

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.paths import Layout
from brainlib.repo.push import Excerpt, Origin, Outgoing
from brainlib.repo.tree import PLANS, RepoTree
from brainlib.text import Json, read_text
from brainlib.vocab import ENCODING, Exit, NoVerdict

# --------------------------------------------------
# external
# --------------------------------------------------
import errno
import io
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import ClassVar

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command every message of a scan opens with, wherever the scan runs
SCANNER = Layout.command(Layout.PRIVATE)
# the one key private.toml holds
DECLARED_KEY = "values"
# how long a probe of this machine (`ip`, `tailscale`) may run before its source is skipped
PROBE_TIMEOUT = 10
# where the kernel lists network interfaces; a physical one carries a `device` link
SYS_NET = Path("/sys/class/net")
# the largest file the scan reads whole; a larger one is UNSCANNED and fails the scan
MAX_BYTES = 8 * 1024 * 1024
# what no source detects, stated with every scan so a pass is not read as more than it is
LIMITS = ("not checked: short hostnames and other machines' lan ips unless in private.toml; ipv6 lan addresses; "
          "usernames; device ids; encoded forms")



class PrivateScanError(NoVerdict):
    """the scan cannot give a verdict: a refusal, an unreadable private.toml, an unlistable repo."""


@dataclass(frozen=True)
class ScanScope:
    """the repos a scan covers: every repo of a tree but those at or under the brain's private-data submodule."""

    tree: RepoTree
    scanned: RepoTree

    @classmethod
    def of(cls, tree: RepoTree) -> "ScanScope":
        """a tree's scope, less the brain's private-data submodule.

        a tree wholly inside that submodule is a scope with no repo to scan,
        since P61 puts the values there: its scan reads nothing, and fails
        only as every scan does when no source gives a value to look for

        # Arguments

        * `tree` - the repos to consider, as found around the cwd or a named repo

        # Returns

        the scope, whose scanned repos are the tree's less the private-data submodule

        # Raises

        PrivateScanError when the tree holds no repo
        """
        # --------------------------------------------------
        # no repo means nothing to scan, which must not read as a clean scan
        # --------------------------------------------------
        if not tree.repos:
            raise PrivateScanError("not inside a git repo; nothing is scanned")
        # --------------------------------------------------
        # the brain's private memory is left out of the scanned set
        # --------------------------------------------------
        data = Layout.discover().data_submodule
        return cls(tree, tree if data is None else tree.without(data))

    def skipped(self) -> list[str]:
        """one line per repo of the tree the scope leaves out.

        # Returns

        a line naming each dropped repo and why P61 lets it hold the values
        """
        return [f"skips {repo}: the brain's private memory, where P61 allows them"
                for repo in self.tree.repos if repo not in self.scanned.repos]

    def source(self, since: str, tip: str) -> "WorkTree | Outgoing":
        """what of the scope a scan reads: the commits a push of `tip` over `since` sends, else the files.

        both ends of a range resolve before any probe runs, in the named repo
        even when the scope exempts it

        # Arguments

        * `since` - the ref the push goes over; "" reads the files instead
        * `tip` - the commit the push sends, the far end of the range

        # Returns

        a resolved Outgoing over the scanned repos, or a WorkTree

        # Raises

        NoVerdict when an end of the range resolves to no commit; UsageError
        for a range over more than one scanned repo
        """
        if not since:
            return WorkTree(self)
        ends = self.scanned if self.scanned.repos else self.tree
        return replace(Outgoing(ends, since, tip).resolved(), tree=self.scanned)

    def announce(self, source: "WorkTree | Outgoing") -> None:
        """print what a scan of this scope through a source covers, and each repo it skips.

        # Arguments

        * `source` - what the scan reads, `source()`

        # Raises

        RepoError when git cannot list a repo
        """
        for line in (*source.covers(), *self.skipped()):
            print(f"{SCANNER}: {line}", flush=True)


@dataclass(frozen=True)
class Unscanned:
    """a file the scan could not read whole, and why."""

    path: Path
    reason: str


@dataclass(frozen=True)
class WorkTree:
    """every file a scope's repos list, read as git would push it; untracked plans/ scratch left out."""

    scope: ScanScope
    # what the excerpts leave out, stated after every scan of them
    unread: ClassVar[str] = "file names, the git index and history"

    @cached_property
    def files(self) -> list[tuple[Path, Path]]:
        """every file the scan reads, with its repo: the tracked files, then the untracked ones not exempt.

        # Returns

        (repo, absolute file) pairs, the tracked files first

        # Raises

        RepoError when git cannot list a repo

        # Example

            >>> import tempfile
            >>> from brainlib import git
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     for name in ("plans/x.md", "src/plans/x.md", "plans/kept.md"):
            ...         (repo / name).parent.mkdir(parents=True, exist_ok=True)
            ...         _ = (repo / name).write_text("x")
            ...     _ = git(repo, "add", "plans/kept.md")
            ...     source = WorkTree(ScanScope.of(RepoTree.around(repo)))
            ...     sorted(p.relative_to(repo).as_posix() for _, p in source.files)
            ['plans/kept.md', 'src/plans/x.md']
        """
        repos = self.scope.scanned.repos
        # --------------------------------------------------
        # tracked files, then the untracked ones that count
        # --------------------------------------------------
        tracked = [(repo, path) for repo in repos for path in RepoTree((repo,)).tracked()]
        untracked = [(repo, path) for repo in repos for path in RepoTree((repo,)).untracked()
                     if not self.exempt(repo, path)]
        return [*tracked, *untracked]

    def covers(self) -> list[str]:
        """what the excerpts cover, one line each; git lists the files, and none is probed or read.

        # Returns

        how many files of how many repos, then the untracked scratch skipped

        # Raises

        RepoError when git cannot list a repo
        """
        return [f"{len(self.files)} listed file(s) of {len(self.scope.scanned.repos)} repo(s)",
                f"skips untracked files under a repo's top-level {PLANS}/: his scratch, where P61 allows them"]

    def excerpts(self) -> Iterator[Excerpt | Unscanned]:
        """each file's content, its first line at line 1 of its path relative to its repo; or why it is unread.

        # Returns

        one Excerpt or one Unscanned per file, in `files` order

        # Raises

        RepoError when git cannot list a repo
        """
        for repo, path in self.files:
            try:
                text = self.content(path)
            except OSError as broken:
                yield Unscanned(path, str(broken.strerror or broken))
                continue
            yield Excerpt(Origin(repo, path.relative_to(repo).as_posix(), 1), text)

    @staticmethod
    def exempt(repo: Path, path: Path) -> bool:
        """whether an untracked file is his scratch: it sits under `plans/` at its repo's top.

        # Arguments

        * `repo` - the repo the file belongs to
        * `path` - the untracked file, as an absolute path under `repo`

        # Returns

        True when the file's first directory under the repo is `plans`

        # Example

            >>> [WorkTree.exempt(Path("/r"), Path(p)) for p in ("/r/plans/a.md", "/r/src/plans/a.md", "/r/plans")]
            [True, False, False]
        """
        return path.parent.relative_to(repo).parts[:1] == (PLANS,)

    @staticmethod
    def content(path: Path) -> str:
        """what git pushes for a file: a symlink's link text, else its bytes decoded leniently.

        decoding never fails, so a value a binary file holds as ascii or utf-8
        bytes is still caught; one held as utf-16 is not

        # Arguments

        * `path` - the file to read, or a symlink whose target text is read

        # Returns

        the text the scan matches against

        # Raises

        OSError when the file cannot be read, or holds more than MAX_BYTES
        """
        # --------------------------------------------------
        # git pushes a symlink's target text, not what it points at
        # --------------------------------------------------
        if path.is_symlink():
            return os.readlink(path)  # noqa: PTH115 - Path.readlink normalises the text; git pushes it exactly
        # --------------------------------------------------
        # a file over the cap is refused rather than skimmed
        # --------------------------------------------------
        if (size := path.stat().st_size) > MAX_BYTES:
            raise OSError(errno.EFBIG, f"{size} bytes, over the {MAX_BYTES} cap")
        return path.read_bytes().decode(ENCODING, errors="replace")


class ValueKind(StrEnum):
    """where a private value came from, which is what a hit reports it as."""

    LAN_IP = "lan ip"
    WAN_IP = "wan ip"
    TAILNET_DOMAIN = "tailnet domain"
    TAILNET_HOST = "tailnet host"
    TAILNET_IP = "tailnet ip"
    DECLARED = "declared"


class Probe(StrEnum):
    """one place the values come from, named by what goes unchecked when it is unavailable."""

    LAN = "lan ips (ip)"
    TAILNET = "tailnet names and ips (tailscale)"
    DECLARED = "declared values (private.toml)"


@dataclass(frozen=True)
class PrivateValue:
    """one string that identifies his infrastructure, and its class."""

    text: str
    kind: ValueKind

    @property
    def pattern(self) -> str:
        """this value as a regex that matches it only as a whole token.

        an ip never matches inside a longer number or dotted quad, a name never
        inside a longer label. a name still matches under a further subdomain:
        `nas.<tailnet>` publishes the tailnet as surely as the tailnet alone

        # Returns

        a regex source string; an ip is bounded by non-address characters, a name by non-label ones

        # Example

            >>> ip = re.compile(PrivateValue("192.0.2.40", ValueKind.DECLARED).pattern)
            >>> [bool(ip.search(s)) for s in ("192.0.2.40", "192.0.2.400", "1192.0.2.40")]
            [True, False, False]
            >>> [bool(ip.search(s)) for s in ("at 192.0.2.40.", "192.0.2.40:8080", "192.0.2.40.7")]
            [True, True, False]
            >>> six = re.compile(PrivateValue("2001:db8::1", ValueKind.TAILNET_IP).pattern)
            >>> [bool(six.search(s)) for s in ("[2001:db8::1]:80", "2001:db8::12", "a2001:db8::1")]
            [True, False, False]
            >>> name = re.compile(PrivateValue("tail1234.ts.net", ValueKind.TAILNET_DOMAIN).pattern, re.IGNORECASE)
            >>> [bool(name.search(s)) for s in ("http://gpu-host.tail1234.ts.net:8080", "TAIL1234.TS.NET")]
            [True, True]
            >>> [bool(name.search(s)) for s in ("xtail1234.ts.net", "my-tail1234.ts.net", "tail1234.ts.network")]
            [False, False, False]
            >>> [bool(name.search(s)) for s in ("x_tail1234.ts.net", "tail1234.ts.net_x", "étail1234.ts.net")]
            [True, True, True]
        """
        # --------------------------------------------------
        # the value is literal text, never a pattern
        # --------------------------------------------------
        token = re.escape(self.text)
        try:
            # --------------------------------------------------
            # a value that parses as an ip address is one, anything else is a name
            # --------------------------------------------------
            version = ipaddress.ip_address(self.text).version
        except ValueError:
            return rf"(?<![A-Za-z0-9-]){token}(?![A-Za-z0-9-])"
        # --------------------------------------------------
        # each address family gets its own boundary, so a value never matches inside a longer address
        # --------------------------------------------------
        if version == 4:  # noqa: PLR2004 - the ip version, not a tunable
            return rf"(?<![\d.]){token}(?!\.?\d)"
        return rf"(?<![\w:]){token}(?![\w:])"


@dataclass(frozen=True)
class Hit:
    """one private value on one line a push would publish."""

    origin: Origin
    value: PrivateValue

    def __str__(self) -> str:
        """`origin: class value (in repo)`, the origin in the form an editor or git jumps to.

        # Returns

        the hit as one line: where it sits, the value's class and the value, then its repo

        # Example

            >>> value, repo = PrivateValue("192.0.2.40", ValueKind.DECLARED), Path("/r")
            >>> commit = "ab12cd34ef56" * 3 + "7890"
            >>> for origin in (Origin(repo, "a.nix", 3), Origin(repo, "a.nix", 3, commit), Origin(repo, "", 6, commit)):
            ...     print(Hit(origin, value))
            a.nix:3: declared 192.0.2.40 (in /r)
            ab12cd34ef56:a.nix:3: declared 192.0.2.40 (in /r)
            ab12cd34ef56:6: declared 192.0.2.40 (in /r)
        """
        return f"{self.origin}: {self.value.kind} {self.value.text} (in {self.origin.repo})"


@dataclass(frozen=True)
class PrivateScan:
    """the private values of this machine and its tailnet, the sources that gave none, and the scan."""

    values: tuple[PrivateValue, ...]
    unavailable: tuple[Probe, ...] = ()

    @classmethod
    def gather(cls, declared: Path) -> "PrivateScan":
        """every value from every source, the declared ones from `declared`; on a duplicate the first source's wins.

        # Arguments

        * `declared` - the path of `private.toml`, which may not exist

        # Returns

        the scan over the merged values, remembering which sources were unavailable

        # Raises

        PrivateScanError when `declared` exists but is not a well-formed private.toml,
        or when every source together gave no value, so a scan would look for nothing
        """
        # --------------------------------------------------
        # ask every source; None marks one that could not be consulted
        # --------------------------------------------------
        sources = {Probe.LAN: cls.lan(), Probe.TAILNET: cls.tailnet(), Probe.DECLARED: cls.declared(declared)}
        # --------------------------------------------------
        # merge the values, one per case-insensitive text
        # --------------------------------------------------
        seen: dict[str, PrivateValue] = {}
        for value in (value for found in sources.values() if found is not None for value in found):
            seen.setdefault(value.text.lower(), value)
        # --------------------------------------------------
        # a scan with nothing to look for would pass vacuously
        # --------------------------------------------------
        if not seen:
            raise PrivateScanError("no source gave a private value; there is nothing to look for")
        return cls(tuple(seen.values()), tuple(source for source, found in sources.items() if found is None))

    @staticmethod
    def name_safe_stdout() -> None:
        """let stdout print a name git lists as its bytes, utf-8 or not, rather than fail on it.

        git lists a path as raw bytes, which python decodes to surrogate escapes
        when the bytes are not utf-8. reconfigures stdout to write those escapes
        back as the original bytes. does nothing when stdout is not a text
        wrapper (a captured or replaced stream)
        """
        if isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout.reconfigure(errors="surrogateescape")

    @staticmethod
    def probe(argv: list[str], source: Probe) -> object:
        """run a json-printing probe of this machine, without a shell and with a timeout.

        # Arguments

        * `argv` - the command and its arguments; the command is looked up on PATH
        * `source` - the probe's name, for the message when it cannot run

        # Returns

        the parsed json, or None with one stderr line when the probe is missing,
        failed or printed no json
        """
        # --------------------------------------------------
        # a missing probe tool skips its source
        # --------------------------------------------------
        found = shutil.which(argv[0])
        if found is None:
            print(f"{SCANNER}: {argv[0]} is not on PATH; {source} are not checked", file=sys.stderr)
            return None
        # --------------------------------------------------
        # run the probe and read its json
        # --------------------------------------------------
        # a probe of this machine with fixed arguments; no shell, no remote input (S603)
        try:
            done = subprocess.run([found, *argv[1:]], capture_output=True, encoding=ENCODING,  # noqa: S603
                                  check=True, timeout=PROBE_TIMEOUT)
            return json.loads(done.stdout)
        # a JSONDecodeError and a UnicodeDecodeError of output that is not utf-8 are both ValueErrors
        except (OSError, subprocess.SubprocessError, ValueError) as broken:
            print(f"{SCANNER}: {' '.join(argv)} failed ({broken}); {source} are not checked", file=sys.stderr)
            return None

    @classmethod
    def lan(cls) -> list[PrivateValue] | None:
        """this machine's ipv4 addresses on its physical interfaces, or None when `ip` cannot run.

        a bridge, a tunnel or loopback has no `device` link in sysfs. their
        addresses are either the same on every machine (docker's 172.17.0.1) or
        another source's (tailscale0's are tailnet ips)

        # Returns

        one value per physical-interface address, or None when `ip` cannot run
        """
        # --------------------------------------------------
        # keep only physical interfaces, the ones with a device link, and their local addresses
        # --------------------------------------------------
        if (found := cls.probe(["ip", "-j", "-4", "addr", "show"], Probe.LAN)) is None:
            return None
        return [PrivateValue(local, ValueKind.LAN_IP)
                for link in map(Json.fields, Json.members(found))
                if (SYS_NET / Json.text(link.get("ifname")) / "device").exists()
                for addr in map(Json.fields, Json.members(link.get("addr_info")))
                if (local := Json.text(addr.get("local")))]

    @classmethod
    def tailnet(cls) -> list[PrivateValue] | None:
        """the tailnet's domain, every node's full name and addresses, and this node's public address.

        a node's short hostname and the tailnet's account name are left out: the
        first is a bare word that appears legitimately everywhere, the second
        embeds his username. of this node's endpoints only the globally routable
        one is taken; the rest are the lan source's or docker's

        # Returns
        the values in source order, or None when `tailscale` cannot run
        """
        # --------------------------------------------------
        # ask tailscale about this node and its peers
        # --------------------------------------------------
        if (found := cls.probe(["tailscale", "status", "--json"], Probe.TAILNET)) is None:
            return None
        # --------------------------------------------------
        # this node and every peer
        # --------------------------------------------------
        status = Json.fields(found)
        me = Json.fields(status.get("Self"))
        nodes = [me, *map(Json.fields, Json.fields(status.get("Peer")).values())]
        # --------------------------------------------------
        # the tailnet domain, each node's host name and each tailnet address
        # --------------------------------------------------
        suffix = Json.text(status.get("MagicDNSSuffix"))
        domain = [PrivateValue(suffix, ValueKind.TAILNET_DOMAIN)] if suffix else []
        hosts = [PrivateValue(name, ValueKind.TAILNET_HOST)
                 for node in nodes if (name := Json.text(node.get("DNSName")).rstrip("."))]
        ips = [PrivateValue(ip, ValueKind.TAILNET_IP)
               for node in nodes for ip in Json.members(node.get("TailscaleIPs")) if isinstance(ip, str)]
        # --------------------------------------------------
        # the public addresses this node is reachable on
        # --------------------------------------------------
        # this node's endpoints are `host:port`, a v6 host in brackets
        wan = [PrivateValue(host, ValueKind.WAN_IP)
               for endpoint in Json.members(me.get("Addrs")) if isinstance(endpoint, str)
               if cls.is_global(host := endpoint.rpartition(":")[0].strip("[]"))]
        # --------------------------------------------------
        # all four kinds in one list
        # --------------------------------------------------
        return [*domain, *hosts, *ips, *wan]

    @staticmethod
    def is_global(host: str) -> bool:
        """whether a host is a globally routable ip address.

        # Arguments

        * `host` - an address as the tailscale status reports it; a name or a malformed address is not one

        # Returns

        True only for a public ip; private, carrier-grade-nat and unparsable hosts are False

        # Example

            >>> [PrivateScan.is_global(h) for h in ("8.8.8.8", "192.0.2.40", "100.64.0.1", "x")]
            [True, False, False, False]
        """
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return False

    @staticmethod
    def declared(path: Path) -> list[PrivateValue] | None:
        """the values he lists in private.toml, or None with one stderr line when it is missing.

        a typo there would otherwise leave a value he believes is checked unchecked

        # Arguments

        * `path` - where `private.toml` is expected

        # Returns

        one value per entry of its `values` list, or None when the file is missing

        # Raises

        PrivateScanError on a file it cannot read or decode, a key other than
        `values`, or a value that is not a non-empty string
        """
        # --------------------------------------------------
        # no declared file means this source is not consulted
        # --------------------------------------------------
        if not path.is_file():
            print(f"{SCANNER}: no {path}; {Probe.DECLARED} are not checked", file=sys.stderr)
            return None
        try:
            # --------------------------------------------------
            # a declared file that exists must parse
            # --------------------------------------------------
            table = tomllib.loads(read_text(path))
        # TOMLDecodeError and UnicodeDecodeError are both ValueErrors
        except (OSError, ValueError) as broken:
            raise PrivateScanError(f"{path}: {broken}") from broken
        # --------------------------------------------------
        # the file holds only the one key, as a list of non-empty strings
        # --------------------------------------------------
        values = table.get(DECLARED_KEY, [])
        listed = Json.members(values)
        kept = [stripped for v in listed if (stripped := Json.text(v).strip())]
        if set(table) - {DECLARED_KEY} or not isinstance(values, list) or len(kept) != len(listed):
            raise PrivateScanError(f'{path}: expected only {DECLARED_KEY} = ["...", ...] of non-empty strings')
        return [PrivateValue(v, ValueKind.DECLARED) for v in kept]

    @cached_property
    def by_group(self) -> dict[str, PrivateValue]:
        """each value under the regex group name the matcher gives it, longest value first.

        # Returns

        the values keyed `v0`, `v1`, ...; the longest comes first so the
        alternation prefers a full hostname to the domain inside it
        """
        # --------------------------------------------------
        # longest first, so a longer value wins over a shorter one it contains
        # --------------------------------------------------
        ordered = sorted(self.values, key=lambda v: len(v.text), reverse=True)
        return {f"v{i}": value for i, value in enumerate(ordered)}

    @cached_property
    def matcher(self) -> re.Pattern[str]:
        """one case-blind regex over every value, each its own named group; one that never matches when empty.

        # Returns

        the compiled alternation of every value's pattern, grouped as `by_group` names them
        """
        # --------------------------------------------------
        # one alternation, a named group per value
        # --------------------------------------------------
        alternation = "|".join(f"(?P<{group}>{value.pattern})" for group, value in self.by_group.items())
        return re.compile(alternation or "(?!)", re.IGNORECASE)

    def hits(self, origin: Origin, text: str) -> list[Hit]:
        r"""every private value in one excerpt's text, in text order, a value repeated on one line reported once.

        a hit names the value by its group, so a case variant the case-blind
        match accepts (a long s for `s`) still names the value it matched

        # Arguments

        * `origin` - where the text's first line sits; each hit's line counts on from it
        * `text` - the excerpt's text

        # Returns

        one hit per line per distinct value, in text order

        # Example

            >>> scan = PrivateScan((PrivateValue("192.0.2.40", ValueKind.LAN_IP),
            ...                     PrivateValue("tail1234.ts.net", ValueKind.TAILNET_DOMAIN),
            ...                     PrivateValue("gpu-host.tail1234.ts.net", ValueKind.TAILNET_HOST)))
            >>> serve, a = Origin(Path("/r"), "tests/serve.rs", 1), Origin(Path("/r"), "a", 1)
            >>> text = ('HOST = "192.0.2.40"\nNOT = "192.0.2.400"\n'
            ...         'assert url == "http://gpu-host.tail1234.ts.net:8080"\nnas ="nas.tail1234.ts.net"\n')
            >>> for hit in scan.hits(serve, text):
            ...     print(hit)
            tests/serve.rs:1: lan ip 192.0.2.40 (in /r)
            tests/serve.rs:3: tailnet host gpu-host.tail1234.ts.net (in /r)
            tests/serve.rs:4: tailnet domain tail1234.ts.net (in /r)
            >>> len(scan.hits(a, "192.0.2.40 and 192.0.2.40 again"))
            1
            >>> print(*scan.hits(a, "nas.TAIL1234.T\u017f.NET"))
            a:1: tailnet domain tail1234.ts.net (in /r)
            >>> PrivateScan(()).hits(a, "192.0.2.40")
            []
            >>> print(*scan.hits(Origin(Path("/r"), "a", 7), "x\n192.0.2.40"))
            a:8: lan ip 192.0.2.40 (in /r)
        """
        found: list[Hit] = []
        line, counted = origin.line, 0
        # --------------------------------------------------
        # matches arrive in text order, so each line count resumes where the last stopped
        # --------------------------------------------------
        for match in self.matcher.finditer(text):
            line += text.count("\n", counted, match.start())
            counted = match.start()
            found.append(Hit(replace(origin, line=line), self.by_group[match.lastgroup or ""]))
        # --------------------------------------------------
        # one hit per line and value
        # --------------------------------------------------
        return list(dict.fromkeys(found))

    def summary(self) -> str:
        """how many values each class holds, and the sources that gave none.

        # Returns

        the one-line summary the scan prints before its verdict

        # Example

            >>> PrivateScan((PrivateValue("a.ts.net", ValueKind.TAILNET_DOMAIN),
            ...              PrivateValue("10.0.0.2", ValueKind.LAN_IP)), (Probe.TAILNET,)).summary()
            '1 lan ip, 1 tailnet domain; UNAVAILABLE: tailnet names and ips (tailscale)'
        """
        # --------------------------------------------------
        # how many values of each kind, then the sources that could not be consulted
        # --------------------------------------------------
        counts = Counter(v.kind for v in self.values)
        held = ", ".join(f"{counts[kind]} {kind}" for kind in ValueKind if counts[kind]) or "no values"
        return f"{held}; UNAVAILABLE: {', '.join(self.unavailable)}" if self.unavailable else held

    def run(self, source: WorkTree | Outgoing) -> Exit:
        r"""scan every excerpt of a source, printing each hit, then the totals and what the scan did not read.

        every excerpt is scanned; a file the source could not read is named on
        stderr and counted UNSCANNED

        # Arguments

        * `source` - the text a push would publish: the working tree's files, or the commits a push sends

        # Returns

        FINDINGS on a hit, else OK

        # Raises

        PrivateScanError when a file went unscanned and nothing hit; NoVerdict
        when the source cannot be read

        # Example

            >>> import tempfile
            >>> from brainlib import git
            >>> scan = PrivateScan((PrivateValue("192.0.2.40", ValueKind.DECLARED),))
            >>> who = ("-c", "user.name=t", "-c", "user.email=t@example.com")
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     (repo / "host").symlink_to("http://192.0.2.40/")
            ...     _ = (repo / "huge.bin").write_bytes(bytes(MAX_BYTES + 1))
            ...     _ = git(repo, "add", "host", "huge.bin")
            ...     scan.run(WorkTree(ScanScope.of(RepoTree.around(repo))))  # doctest: +ELLIPSIS
            + scan for 1 value(s)
            host:1: declared 192.0.2.40 (in ...)
            b-private: 1 hit(s), 1 unscanned; 1 declared
            b-private: limits: ...; file names, the git index and history
            <Exit.FINDINGS: 4>
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     for text in ("base\n", "host = 192.0.2.40\n", "host = gpu-host\n"):
            ...         _ = (repo / "hosts.nix").write_text(text)
            ...         _ = git(repo, "add", "hosts.nix")
            ...         _ = git(repo, *who, "commit", "-qm", text)
            ...     scan.run(Outgoing(ScanScope.of(RepoTree.around(repo)).scanned, "HEAD~2"))  # doctest: +ELLIPSIS
            + scan for 1 value(s)
            ...:6: declared 192.0.2.40 (in ...)
            ...:hosts.nix:1: declared 192.0.2.40 (in ...)
            b-private: 2 hit(s), 0 unscanned; 1 declared
            b-private: limits: ...; the working tree, the index, ...
            <Exit.FINDINGS: 4>
        """
        print(f"+ scan for {len(self.values)} value(s)", flush=True)
        # --------------------------------------------------
        # scan each excerpt; a file that could not be read is counted, never skipped silently
        # --------------------------------------------------
        hits: list[Hit] = []
        unscanned = 0
        for item in source.excerpts():
            match item:
                case Excerpt(origin, text):
                    # --------------------------------------------------
                    # each hit as it is found, so an error later in the scan keeps it
                    # --------------------------------------------------
                    for hit in self.hits(origin, text):
                        print(hit, flush=True)
                        hits.append(hit)
                case Unscanned(path, reason):
                    print(f"{SCANNER}: cannot scan {path}: {reason}", file=sys.stderr)
                    unscanned += 1
        # --------------------------------------------------
        # the totals, and what neither the values nor the source reach
        # --------------------------------------------------
        print(f"{SCANNER}: {len(hits)} hit(s), {unscanned} unscanned; {self.summary()}")
        print(f"{SCANNER}: limits: {LIMITS}; {source.unread}")
        # --------------------------------------------------
        # a hit fails; an unscanned file means no verdict; otherwise clean
        # --------------------------------------------------
        if hits:
            return Exit.FINDINGS
        if unscanned:
            raise PrivateScanError(f"{unscanned} file(s) could not be scanned; no verdict on them")
        return Exit.OK
