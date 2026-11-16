#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-private: no text a push would publish may carry his private infrastructure (P61).

    b-private                         # the tree around the cwd
    b-private REPO                    # the one repo holding REPO, no superproject or submodule
    b-private -s REF [-T TIP] [REPO]  # what pushing TIP (HEAD by default) over REF sends

FINDINGS on a hit; FAILED when a file is unscanned and nothing hit, the
scan has nothing to look for or nowhere to look, REF or TIP does not resolve
to a commit, git cannot list or log a repo, or the commits since REF hold a
merge of more than two parents; USAGE for `--since` over more than one
scanned repo, since REF resolves per repo.

checked: this machine's LAN ipv4 addresses on its physical interfaces; when
`tailscale` is on PATH, the tailnet's domain, every node's full name and
tailnet addresses, and this machine's WAN addresses (every globally routable
endpoint tailscale reports for it); and every value declared in
`$XDG_CONFIG_HOME/aav/private.toml` (`~/.config/aav/private.toml` by default).

not checked, and printed as `limits:` after every scan: short hostnames and
other machines' LAN ips unless declared; this machine's ipv6 LAN addresses;
usernames; device ids; encoded forms (base64, url-escaped). then what the scan
read is bounded by its source, also printed:

- the tree scan reads the files of the working tree, never their names, the
  git index or history. the tree is the outermost repo around the cwd and
  every submodule under it. an untracked file that is not ignored counts: a
  new test stays untracked until the commit that would publish it. a symlink
  is scanned as its link text, which is what git pushes. a file that cannot
  be read, or one too large to read whole, is UNSCANNED and fails the scan.
- `--since` reads each commit TIP reaches and REF does not: its raw object
  (author, committer, message, a merged signed tag, a signature) and every
  line its patch adds, so a value one commit added and a later one removed
  still hits. a merge counts only for what its resolution changed. it never
  reads the working tree, the index, commits REF already holds, file names,
  tags, or a value this machine held before but no longer reports - so a
  commit an origin rewrite dropped is caught only while its value is still
  checked.

two places are exempt, because P61 is where those values belong: the brain's
private-data submodule (wherever the brain's own `.gitmodules` puts its
`logs` entry), and an untracked file under a repo's top-level `plans/` - a TRACKED one is
pushed, so it is scanned; under `--since` it is moot, as every committed file
is pushed. `b-verify -r` runs the tree scan as one of its checks.

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
from brainlib import Args, Exit, Flag, Layout, PrivateScan, RepoTree, ScanScope, Tool, UsageError, XdgLayout

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))


def main(args: Args) -> Exit:
    """scan what a push would publish from the named repo alone, or from the tree around the cwd.

    the scope is settled before any probe runs, so a refusal costs nothing

    # Arguments

    * `args` - the parsed command line; the first positional names the repo to
      scan, and `--since REF` scans the commits a push of HEAD, or of
      `--tip TIP`, over REF sends instead of files

    # Returns

    the exit status of the scan over the settled source
    """
    # --------------------------------------------------
    # a name git lists need not be utf-8: print its bytes back as listed rather than fail on them
    # --------------------------------------------------
    PrivateScan.name_safe_stdout()
    # --------------------------------------------------
    # a tip names the far end of a range, so it needs the near end
    # --------------------------------------------------
    since = args.value(Flag.SINCE)
    if args.has(Flag.TIP) and not since:
        raise UsageError(f"{Flag.TIP.spelling} needs {Flag.SINCE.spelling}")
    # --------------------------------------------------
    # the repos, then what of them is read: the commits since a ref, or the files
    # --------------------------------------------------
    named = args.positional()
    scope = ScanScope.of(RepoTree.containing(Path(named[0])) if named else RepoTree.around(Path.cwd()))
    source = scope.source(since, args.value(Flag.TIP, "HEAD"))
    # --------------------------------------------------
    # say what the scan covers, then gather the values and scan
    # --------------------------------------------------
    scope.announce(source)
    return PrivateScan.gather(XdgLayout.private_toml()).run(source)


if __name__ == "__main__":
    Tool.of(TOOL, __doc__, positionals=(0, 1)).run(main)
