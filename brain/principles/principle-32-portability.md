---
name: principle-32-portability
kind: principle
tier: narrow
rule: be portable - never hardcode an absolute path and never assume a fixed repo layout. discover the root (b-find, this file's own location, a known skill-symlink anchor) and derive every path from it, so the tooling runs on any machine. a relative symlink that bakes in a sibling layout is a hardcoded path in disguise.
interest: [intent-craft]
confidence: high
evidence_count: 6
tells: ["i want all options combinations to work", "is this path hardcoded?", "use $HOME not /home/arpad", "discover the root, dont assume the layout", "never guess a path", "if i say local, take local architecture. if i say this remote machine, then go into the damn machine and find out its architecture. there should be 0 hard coded architectures or weird architectural constraints on this", "like the local version should simply take the local architecture, thats IT...", "why are you hard-coding x86? why cant you just do a multiarch build say \"get the architecture of current machine?\""]
---

# P32 - be portable: discover paths, never hardcode them

## rule
tooling must not assume where it lives. no `/home/<user>/...` absolute path, no "this repo is a sibling
of that repo" layout assumption. instead discover the root once - from the script's own location
(`__file__`), from a known install anchor (a skill symlink under `~/.claude`/`~/.agents`), or via
`b-find` - and derive every other path from it. the same artifact then runs unchanged on any
machine he controls.

a relative symlink like `scripts -> ../../../../aav-brain/bin` is NOT portable: the `../../../../`
hardcodes the exact directory depth and the sibling layout. it is a hardcoded path wearing a costume.
discovery ([[principle-01-no-assumptions]]: never guess a path) is the portable form.

## why
a hardcoded path is a single-machine assumption that lies the moment the layout changes - a different
clone location, a nix store path, another box. the brain is meant to be his second brain everywhere,
not on one machine ([[intent-craft]] - a durable artifact, not a brittle one). the brain's root is
discovered once: a script finds it from its own location (`find_brain`), and home-manager exports it
under two names set from that one value: `$AAV_BRAIN`, which the flake reads at switch time, and
`$AVB`, the short alias kept for his shell, which skill and agent text also reads a brain file off.
two names for one value are not a second anchor; a second value is. `b-find` prints the discovered
root, and `b-find -e` the export line - one anchor, every other path derived from it, never a
hardcoded var or a fallback that guesses.

## how to apply
- writing a script: resolve the root by discovery (`find_brain`, `__file__`), then build paths off it.
  writing a skill or agent: call a brain script by its command (`b-recall`) and read a brain file off
  `$AVB` (`$AVB/brain/CONSTITUTION.md`), with no fallback line. never paste an absolute path or a
  layout-assuming relative one.
- reviewing: a `/home/<user>/...` literal, or a relative symlink/`..` chain that assumes two repos are
  siblings, is a finding - replace it with discovery.
- the self-refine scan already greps for hardcoded absolute paths under this principle; the costume
  case (layout-assuming symlinks) is the same rule.
- the same holds for platform. never hardcode an architecture, board or os, and never refuse one by fiat:
  probe the machine the work runs on (local, or the remote host via its own probe) and derive what you
  need from it. a missing name is something to derive, not a refusal. `hml deploy --via local` refusing
  anything but x86_64 drew "there should be 0 hard coded architectures or weird architectural
  constraints ... if i say local, take local architecture".
- the same holds for what is present. every installable part - the home config, aedit, the brain - installs
  alone and in any combination, and a missing part is skipped, not assumed: he once pulled `home` without the
  brain and expected his symlinks and aedit to install anyway. a repo with several such parts declares an
  install matrix in its `verify.toml`, so VERIFY proves every combination on a fresh machine rather than this
  one: "i want all options combinations to work ... seperable and can be installed individually and
  independentally".

## provenance
this principle was created by brain-self-refine: two skills (brain-self-refine, brain-meta-style) and the
hardcoded-path scan step all cited a principle "P-portability" that had no file, and the decision
trace had flagged the per-skill `scripts/` symlink as "not portable (one-computer assumption)". the
value was load-bearing in executable scan logic without a home; this principle is that home.

## verbatim tells
- "why are you hard-coding x86? why cant you just do a multiarch build say "get the architecture of current machine?"" (the build takes the architecture of the machine it runs on; no hardcoded x86 (2026-11-03, the coworker on an arm mac))
