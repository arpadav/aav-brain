---
name: principle-32-portability
kind: principle
rule: be portable - never hardcode an absolute path and never assume a fixed repo layout. discover the root (brain-find, this file's own location, a known skill-symlink anchor) and derive every path from it, so the tooling runs on any machine. a relative symlink that bakes in a sibling layout is a hardcoded path in disguise.
interest: [intent-craft]
confidence: high
evidence_count: 2
tells: ["is this path hardcoded?", "use $HOME not /home/arpad", "discover the root, dont assume the layout", "never guess a path"]
---

# P32 - be portable: discover paths, never hardcode them

## rule
tooling must not assume where it lives. no `/home/<user>/...` absolute path, no "this repo is a sibling
of that repo" layout assumption. instead discover the root once - from the script's own location
(`__file__`), from a known install anchor (a skill symlink under `~/.claude`/`~/.agents`), or via
`brain-find` - and derive every other path from it. the same artifact then runs unchanged on any
machine he controls.

a relative symlink like `scripts -> ../../../../aav-brain/bin` is NOT portable: the `../../../../`
hardcodes the exact directory depth and the sibling layout. it is a hardcoded path wearing a costume.
discovery ([[principle-01-no-assumptions]]: never guess a path) is the portable form.

## why
a hardcoded path is a single-machine assumption that lies the moment the layout changes - a different
clone location, a nix store path, another box. the brain is meant to be his second brain everywhere,
not on one machine ([[intent-craft]] - a durable artifact, not a brittle one). `brain-find` exists
precisely so a skill resolves `$AAV_BRAIN` (and `$AAV_BRAIN/bin`, derived) the same way anywhere -
one discovered anchor, every other path derived from it, never a second hardcoded or duplicated var.

## how to apply
- writing a script/skill: resolve the root by discovery (`find_brain`, `__file__`, `brain-find
  --export`), then build paths off it. never paste an absolute path or a layout-assuming relative one.
- reviewing: a `/home/<user>/...` literal, or a relative symlink/`..` chain that assumes two repos are
  siblings, is a finding - replace it with discovery.
- the self-refine scan already greps for hardcoded absolute paths under this principle; the costume
  case (layout-assuming symlinks) is the same rule.

## provenance
this card was created by brain-self-refine: two skills (brain-self-refine, brain-meta-style) and the
hardcoded-path scan step all cited a principle "P-portability" that had no card, and the decision
trace had flagged the per-skill `scripts/` symlink as "not portable (one-computer assumption)". the
value was load-bearing in executable scan logic without a home; this card is that home.
