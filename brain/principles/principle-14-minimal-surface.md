---
name: principle-14-minimal-surface
kind: principle
tier: conditional
rule: Build the smallest correct thing that is also the most generic; both halves bind. No dependencies or abstractions you don't need. Only what is critical. Bloat means unnecessary code, never a line count: what he asked for is not bloat.
interest: [intent-craft]
confidence: high
evidence_count: 12
tells: ["no clap, custom cli", "worlds simplest docker image", "do NOT add superfluous things just for the sake of adding them - just what is critical", "investigate bloat in this software, anything redundant or unused which can be pruned?", "bloat", "redundant", "just review as-is, LOC =/= bloat, bloat is unnecessary stuff, but i asked for this, no?", "that's such an edge case tho, im just going to restart agents bruh don't worry about it", "is this the simplest, and most generic, way to accomplish this?", "emphasis on BOTH simplicity AND generic", "i thought onnx runtime would just be in parallel to the trt, a simple if trt then do trt, else do onnx. whats going on?", "i dont know why you asked these questions. i already told you: parallel to the existing double container + icd implementation, but way way way way more minimal", "no need to force cut, again, i mean minimal = most simple but also most general. dont hard code anything"]
---

# P14 - Minimal surface (only what is critical)

**Rule.** Default to the smallest correct implementation that is also the most generic one.
Don't add dependencies, abstractions, flags, or files unless they earn their place. "just what
is critical." Small and generic both bind; small is measured as unnecessary code, never as lines.

**Why.** Surface area is permanent cost ([[intent-craft]]). A 3-line custom CLI he can
read beats pulling `clap`; the simplest Docker image that runs the binary beats a
multi-stage cathedral.

**How to apply.**
- an edge case he sidesteps by hand (restarting an agent, opening a fresh shell) does not earn a
  redesign; name the case and its manual fix in one line and build nothing (2026-11-03).
- "minimal rust crate with axum ... no clap, custom cli that you literally run using
  ./binary /path/to/folder."
- "i need the worlds simplest docker image which just runs the binary and i can mount a
  volume to."
- "do NOT add superfluous things just for the sake of adding them - just what is critical."
- New types/modules must justify themselves; prefer extending an existing primitive
  ([[principle-05-reuse-first]]).
- "is this the simplest, and most generic, way to accomplish this?" both halves bind. simple but
  hard-coded (not generic) is bad; generic but heavier than needed is bad: C++ where a bash script
  does it, rust where python does it. the language follows the real bottleneck, so python instead
  of rust is also wrong when speed IS the bottleneck. a generic bash script beats an over-engineered
  python script (2026-11-02).
- bloat is code nobody needs, not a line count. features he asked for are not bloat however many
  lines they take; a proportion check weighs only the excess beyond the ask (2026-11-02).
- the proportion check runs at EVERY gate report, not once at the end: restate his own one-line ask
  ("a simple if trt then do trt, else do onnx"), count the change against it, and say "this has
  outgrown your ask" unprompted. a reviewer finding that adds structure (a record file, a shared lib,
  per-backend columns) is weighed against that line before it is accepted; a finding that only
  restates the ask's own shape is fine, one that grows it is a design question for him (2026-11-04:
  four review rounds took a ~30-line if/else to ~1900 lines over 34 files and he had to ask).
- minimal is not "cut": framing a review as judging size against "MINIMAL: super small" and favouring
  cuts drew *"no need to force cut, again, i mean minimal = most simple but also most general. dont
  hard code anything"* (2026-11-05). never trade generality for line count; a value a model or
  component decides (labels, thresholds, input sizes, class lists, backends) lives in that model's or
  component's own file and is read from it, never written into the code that uses it.
- a question whose answer follows from an existing convention in the repo is not asked: *"the trt
  question is stupid. make it the same as build.sh which defaults to trt, otherwise can have
  onnx-runtime flag. and both can be cached"* (2026-11-05). find the sibling (build.sh) and mirror it.
  heat again 2026-11-05: four questions asked about the harness release (model fetch, engine bake,
  editable settings, IP checks), all settled by his one line *"parallel to the existing double
  container + icd implementation, but way way way way more minimal, one container, simple run, add a
  README"*: *"i dont know why you asked these questions. i already told you"*. "parallel to X" IS the
  answer to every how-does-it-work question: reuse X's fetch, bake, settings mount and checks; ask
  only what X cannot answer.
- a grain-wrong question while the big picture has drifted is itself the tell: surface the drift first
  (what works / what is left / core vs needed vs gate-added, then "1 finish, 2 cut back").
- This composes with [[principle-07-trim-fat-verbose-docs]]: minimal surface, but the
  docs on that surface are thorough.

**When it is already over-built** the answer is not a patch round but a rebuild from his stated steps -
[[principle-51-spaghetti-is-a-design-fault]]. minimal is also not naive: the edge cases a real run
learned stay ([[principle-60-device-facing-code-is-gated-by-a-live-run]]).

**Anti-pattern.** Reaching for a heavy dependency for a trivial need; speculative
"might need it later" abstractions; config knobs nobody asked for.
