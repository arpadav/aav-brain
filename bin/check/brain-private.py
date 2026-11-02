#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-private: no file git lists may carry his private infrastructure (P61).

    python3 brain-private.py                  # the tree around the cwd
    python3 brain-private.py REPO             # the one repo holding REPO, no superproject or submodule
    python3 brain-private.py --staging REPO   # what `git add -A` would stage there: plans/ included

FINDINGS on a hit; FAILED when a file is unscanned and nothing hit, or the
scan has nothing to look for or nowhere to look.

checked: this machine's LAN ipv4 addresses on its physical interfaces; when
`tailscale` is on PATH, the tailnet's domain, every node's full name and
tailnet addresses, and this machine's WAN address (the globally routable
endpoint tailscale reports for it); and every value declared in
`$XDG_CONFIG_HOME/aav/private.toml` (`~/.config/aav/private.toml` by default).

not checked, and printed as `limits:` after every scan: short hostnames and
other machines' LAN ips unless declared; this machine's ipv6 LAN addresses;
usernames; device ids; encoded forms (base64, url-escaped); the git index and
history - the scan reads the working tree.

the tree is the outermost repo around the cwd and every submodule under it. an
untracked file that is not ignored counts: a new test stays untracked until the
commit that would publish it. a symlink is scanned as its link text, which is
what git pushes. a file that cannot be read, or one too large to read whole, is
UNSCANNED and fails the scan. two places are exempt, because P61 is where those
values belong: the brain's private-data submodule (its path in the brain's own
`.gitmodules`), and an untracked file under a repo's top-level `plans/` - a
TRACKED one is pushed, so it is scanned. `--staging` drops the second exemption,
since `git add -A` stages that file too; brain-sync scans each repo that way
before it commits. `brain-verify.py --run` runs this scan as one of its checks.

    # private.toml
    values = ["gpu-host.lan", "192.0.2.40"]

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import ENCODING, Args, Exit, Flag, Json, Layout, NoVerdict, RepoTree, Tool, find_config, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import errno
import ipaddress
import json
import os
import re
import shutil
import subprocess
import tomllib
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# the file under his config folder that holds the values he declares by hand
PRIVATE_TOML = "private.toml"
# the one key private.toml holds
DECLARED_KEY = "values"
# how long a probe of this machine (`ip`, `tailscale`) may run before its source is skipped
PROBE_TIMEOUT = 10
# where the kernel lists network interfaces; a physical one carries a `device` link
SYS_NET = Path("/sys/class/net")
# the largest file the scan reads whole; a larger one is UNSCANNED and fails the scan
MAX_BYTES = 8 * 1024 * 1024
# the top-level directory name under which an untracked file is his scratch, not a leak
PLANS = "plans"
# what no source detects, stated with every scan so a pass is not read as more than it is
LIMITS = ("not checked: short hostnames and other machines' lan ips unless in private.toml; ipv6 lan addresses; "
          "usernames; device ids; encoded forms; the git index and history")


class PrivateScanError(NoVerdict):
    """the scan cannot give a verdict: a refusal, an unreadable private.toml, an unlistable repo."""


@dataclass(frozen=True)
class Scope:
    """the repos a scan covers: every repo of a tree but those at or under the brain's private-data submodule."""

    tree: RepoTree
    scanned: RepoTree
    # what `git add -A` would stage: an untracked file under plans/ is not exempt
    staging: bool = False

    @classmethod
    def of(cls, tree: RepoTree, *, staging: bool = False) -> "Scope":
        """a tree's scope, less the brain's private-data submodule.

        a tree wholly inside that submodule is a scope with no repo to scan,
        which passes: P61 puts the values there

        # Arguments

        * `tree` - the repos to consider, as found around the cwd or a named repo
        * `staging` - scan as `git add -A` would stage, with no untracked file exempt

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
        return cls(tree, tree if data is None else tree.without(data), staging)

    def files(self) -> list[Path]:
        """every file the scan reads: each scanned repo's tracked files and its untracked ones not exempt.

        under `staging` none is exempt, which is the set `git add -A` stages

        # Returns

        the tracked files first, then the untracked ones that are not exempt

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
            ...     for staging in (False, True):
            ...         scope = Scope.of(RepoTree.around(repo), staging=staging)
            ...         sorted(p.relative_to(repo).as_posix() for p in scope.files())
            ['plans/kept.md', 'src/plans/x.md']
            ['plans/kept.md', 'plans/x.md', 'src/plans/x.md']
        """
        # --------------------------------------------------
        # untracked files count unless they are scratch, and everything counts when staging
        # --------------------------------------------------
        untracked = (path for repo in self.scanned.repos for path in RepoTree((repo,)).untracked()
                     if self.staging or not self.exempt(repo, path))
        # --------------------------------------------------
        # tracked files, then the untracked ones that count
        # --------------------------------------------------
        return [*self.scanned.tracked(), *untracked]

    @staticmethod
    def exempt(repo: Path, path: Path) -> bool:
        """whether an untracked file is his scratch: it sits under `plans/` at its repo's top.

        # Arguments

        * `repo` - the repo the file belongs to
        * `path` - the untracked file, as an absolute path under `repo`

        # Returns

        True when the file's first directory under the repo is `plans`

        # Example

            >>> [Scope.exempt(Path("/r"), Path(p)) for p in ("/r/plans/a.md", "/r/src/plans/a.md", "/r/plans")]
            [True, False, False]
        """
        return path.parent.relative_to(repo).parts[:1] == (PLANS,)

    def listing(self) -> list[str]:
        """what the scan covers and what it skips, one line each; nothing is probed or read.

        # Returns

        the lines to print before the scan: the repos covered, the repos dropped
        from the scope, and whether untracked scratch is scanned or skipped
        """
        # --------------------------------------------------
        # the repos left out, and how untracked files are treated
        # --------------------------------------------------
        skipped = [repo for repo in self.tree.repos if repo not in self.scanned.repos]
        scratch = (f"stages untracked files under a repo's top-level {PLANS}/, so scans them" if self.staging else
                   f"skips untracked files under a repo's top-level {PLANS}/: his scratch, where P61 allows them")
        # --------------------------------------------------
        # the lines a reader needs to judge what a pass covered
        # --------------------------------------------------
        return [f"every listed file of {len(self.scanned.repos)} repo(s)",
                *(f"skips {repo}: the brain's private memory, where P61 allows them" for repo in skipped), scratch]


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
    """one private value found on one line of a file git lists."""

    path: Path
    line: int
    value: PrivateValue

    def __str__(self) -> str:
        """`path:line: class value`, the form an editor jumps to.

        # Returns

        the hit as one line, naming the file, the 1-based line, the value's
        class and the value itself
        """
        return f"{self.path}:{self.line}: {self.value.kind} {self.value.text}"


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
            print(f"{TOOL}: {argv[0]} is not on PATH; {source} are not checked", file=sys.stderr)
            return None
        # --------------------------------------------------
        # run the probe and read its json
        # --------------------------------------------------
        # a probe of this machine with fixed arguments; no shell, no remote input (S603)
        try:
            done = subprocess.run([found, *argv[1:]], capture_output=True, text=True,  # noqa: S603
                                  check=True, timeout=PROBE_TIMEOUT)
            return json.loads(done.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as broken:
            print(f"{TOOL}: {' '.join(argv)} failed ({broken}); {source} are not checked", file=sys.stderr)
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
            print(f"{TOOL}: no {path}; {Probe.DECLARED} are not checked", file=sys.stderr)
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

    def hits(self, path: Path, text: str) -> list[Hit]:
        r"""every private value in one file's text, in file order, a value repeated on one line reported once.

        a hit names the value by its group, so a case variant the case-blind
        match accepts (a long s for `s`) still names the value it matched

        # Arguments

        * `path` - the file the text came from, carried into each hit
        * `text` - the file's content

        # Returns

        one hit per line per distinct value, in file order

        # Example

            >>> scan = PrivateScan((PrivateValue("192.0.2.40", ValueKind.LAN_IP),
            ...                     PrivateValue("tail1234.ts.net", ValueKind.TAILNET_DOMAIN),
            ...                     PrivateValue("gpu-host.tail1234.ts.net", ValueKind.TAILNET_HOST)))
            >>> text = ('HOST = "192.0.2.40"\nNOT = "192.0.2.400"\n'
            ...         'assert url == "http://gpu-host.tail1234.ts.net:8080"\nnas ="nas.tail1234.ts.net"\n')
            >>> for hit in scan.hits(Path("tests/serve.rs"), text):
            ...     print(hit)
            tests/serve.rs:1: lan ip 192.0.2.40
            tests/serve.rs:3: tailnet host gpu-host.tail1234.ts.net
            tests/serve.rs:4: tailnet domain tail1234.ts.net
            >>> len(scan.hits(Path("a"), "192.0.2.40 and 192.0.2.40 again"))
            1
            >>> print(*scan.hits(Path("a"), "nas.TAIL1234.T\u017f.NET"))
            a:1: tailnet domain tail1234.ts.net
            >>> PrivateScan(()).hits(Path("a"), "192.0.2.40")
            []
        """
        # --------------------------------------------------
        # matches arrive in file order, so the line count only moves forward
        # --------------------------------------------------
        found: list[Hit] = []
        line, counted = 1, 0
        # matches arrive in file order, so each line count resumes where the last stopped
        for match in self.matcher.finditer(text):
            line += text.count("\n", counted, match.start())
            counted = match.start()
            found.append(Hit(path, line, self.by_group[match.lastgroup or ""]))
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

    @staticmethod
    def content(path: Path) -> str:
        """what git pushes for a file: a symlink's link text, else its bytes decoded leniently.

        decoding never fails, so a binary file that carries a value is still caught

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

    def run(self, scope: Scope) -> Exit:
        """scan every file of a scope, printing each hit, then the summary and the scan's limits.

        every file is SCANNED or UNSCANNED; an unscanned one is named on stderr

        # Arguments

        * `scope` - the repos and files to scan, from `Scope.of`

        # Returns

        FINDINGS on a hit, else OK

        # Raises

        PrivateScanError when a file went unscanned and nothing hit; RepoError
        when git cannot list a repo of the scope

        # Example

            >>> import tempfile
            >>> from brainlib import git
            >>> scan = PrivateScan((PrivateValue("192.0.2.40", ValueKind.DECLARED),))
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     (repo / "host").symlink_to("http://192.0.2.40/")
            ...     _ = (repo / "huge.bin").write_bytes(bytes(MAX_BYTES + 1))
            ...     _ = git(repo, "add", "host", "huge.bin")
            ...     scan.run(Scope.of(RepoTree.around(repo)))  # doctest: +ELLIPSIS
            + scan 2 file(s) of 1 repo(s) for 1 value(s)
            host:1: declared 192.0.2.40
            brain-private: 1 hit(s), 1 unscanned; 1 declared
            brain-private: limits: ...
            <Exit.FINDINGS: 4>
        """
        # --------------------------------------------------
        # what is about to be scanned
        # --------------------------------------------------
        top = scope.tree.repos[0]
        files = scope.files()
        print(f"+ scan {len(files)} file(s) of {len(scope.scanned.repos)} repo(s) for {len(self.values)} value(s)",
              flush=True)
        # --------------------------------------------------
        # scan each file; an unreadable one is counted, never skipped silently
        # --------------------------------------------------
        hits: list[Hit] = []
        unscanned: list[Path] = []
        for path in files:
            try:
                hits += self.hits(path.relative_to(top), self.content(path))
            except OSError as broken:
                print(f"{TOOL}: cannot scan {path}: {broken.strerror or broken}", file=sys.stderr)
                unscanned.append(path)
        # --------------------------------------------------
        # every hit, then the totals and what no source detects
        # --------------------------------------------------
        for hit in hits:
            print(hit)
        print(f"{TOOL}: {len(hits)} hit(s), {len(unscanned)} unscanned; {self.summary()}")
        print(f"{TOOL}: limits: {LIMITS}")
        # --------------------------------------------------
        # a hit fails; an unscanned file means no verdict; otherwise clean
        # --------------------------------------------------
        if hits:
            return Exit.FINDINGS
        if unscanned:
            raise PrivateScanError(f"{len(unscanned)} file(s) could not be scanned; no verdict on them")
        return Exit.OK


def main(args: Args) -> Exit:
    """scan the named repo alone, or the tree around the cwd.

    the scope is settled before any probe runs, so a refusal costs nothing

    # Arguments

    * `args` - the parsed command line; the first positional names the repo to
      scan, and `--staging` narrows the scan to what `git add -A` would stage

    # Returns

    the exit status of the scan over the settled scope
    """
    # --------------------------------------------------
    # scope: the repo containing the named path, else the repos around the cwd
    # --------------------------------------------------
    named = args.positional()
    tree = RepoTree.containing(Path(named[0])) if named else RepoTree.around(Path.cwd())
    scope = Scope.of(tree, staging=args.has(Flag.STAGING))
    # --------------------------------------------------
    # say what the scan covers
    # --------------------------------------------------
    for line in scope.listing():
        print(f"{TOOL}: {line}")
    # --------------------------------------------------
    # gather the values to look for, then scan
    # --------------------------------------------------
    return PrivateScan.gather(find_config() / PRIVATE_TOML).run(scope)


if __name__ == "__main__":
    Tool(TOOL, __doc__, flags=(Flag.STAGING,), positionals=(0, 1)).run(main)
