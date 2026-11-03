# S01: the over-engineering check asks only about size, and should ask "simplest AND most generic"

Written by an external agent, the Claude session planning `~/repos/active/life-automation`, on 2026-11-02. arpad confirmed the change and asked for this note in place of an edit, because he was editing the brain at the time. No brain file has been changed.

## Problem

Four places tell the brain to check proportion, and all four judge size alone ("would a much simpler thing do this job", "the dumbest version that works"). arpad's test has two halves, and both bind: is this the simplest, AND the most generic, way to do it?

His examples, verbatim in substance:

- simple but hard-coded (not generic) is bad;
- generic but heavier than needed is bad: C++ where a bash script does it, rust where python does it;
- the language follows the real bottleneck: python instead of rust is also wrong when speed IS the bottleneck;
- a generic bash script beats an over-engineered python script.

## Where

- `agentic-files/skills/brain-meta-drive/SKILL.md`, section "reporting", the paragraph that starts "every gate report also answers ONE line, unasked".
- `agentic-files/skills/brain-meta-style/SKILL.md`, plan lens, the "proportion (P14 at the SUBSYSTEM scale)" bullet.
- `agentic-files/skills/brain-plan/SKILL.md`, step 5, "proportion, then reuse + minimal surface".
- `brain/principles/principle-14-minimal-surface.md`, the principle behind all three.

## Proposed text

brain-meta-drive, replacing that paragraph:

    every gate report also answers ONE line, unasked: is this the simplest AND the most generic way to
    do the job? both halves bind. simple but hard-coded (not generic) is bad. generic but heavier than
    needed is bad: C++ where a bash script does it, rust where python does it. the language follows the
    real bottleneck, so python instead of rust is also wrong when speed IS the bottleneck. a generic
    bash script beats an over-engineered python script. the test: if he asked "is this
    over-engineered?" right now and you would agree, you owed him that sentence before he asked. a
    critique produced only on request is an omission.

brain-meta-style, replacing the proportion bullet's first line and adding one sentence at its end:

    - proportion AND generality (P14 at the SUBSYSTEM scale). ... a simple thing that hard-codes what
      should be config, or a generic thing in a heavier language than the bottleneck needs (C++ for a
      bash script, rust for python), is the same finding.

brain-plan step 5 and P14: the same two halves and the same examples, worded to fit arpad's edits in progress.

## Evidence

On 2026-11-02, at the sanction of life-automation plan 01, the brain's size-only check approved a rust todo-list with a bespoke snapshot-and-diff hook system. The two-halves test caught both:

- the language: python plus one dependency does it, and speed is not the bottleneck;
- the hooks: an idempotent reconcile run with the changed file's path replaced the snapshot.

Together they cut the plan from about 2.4k lines to about 1.5k.

## Your call

<!-- sha256: 6f55637c788e587ad85f05844d7a344a725e7352df4228a73f9d6bc310cd5f35 -->
