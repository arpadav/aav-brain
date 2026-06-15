---
name: brain-plan
description: "Produce a plan the way Arpad wants it: small in scope, verbose in detail, with a concrete worked example, a baked-in review-gate strategy, written to plans/. Never assume - ask under any ambiguity before finalizing. Load this when starting non-trivial work, when he says 'make a plan' / 'jumping off point', or before any multi-phase build."
---

# brain-plan: small, verbose, worked example, to plans/

he lives in plan mode. a good plan for him is small in scope, verbose in detail, concrete, and
reversible: something to "get my hands dirty with before committing".

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"` (sets `$AAV_BRAIN`).

load: `$AAV_BRAIN/brain/principles/principle-02-plan-before-build.md` and
`principle-01-no-assumptions.md`.

## entry - set the node, hand the walk to the engine (P30)
brain-plan is the planning ENTRY. the sequence is NOT yours to invent and the trampoline is NOT yours to
reimplement - that is `brain-meta-drive`'s job. you only:
- set `$STATE` = `IDEATION` (the planning entry; a fresh request starts here) and `$REGIME` = `ask-first`.
- load `brain-meta-drive` and run it from `$STATE`. it walks the planning region IDEATION -> ... -> PLAN
  -> PLANPROBE -> PLANGATE -> SANCTION, recalling per state and dispatching each owner. brain-plan does
  NOT cross into IMPL - planning ends at SANCTION; execution is brain-execute's job once he blesses it.

at the plan-region states the engine dispatches, brain-plan IS the owner - the rest of this file is that
state-work: **at PLAN** produce the artifact below; **at PLANPROBE** trace it; **at PLANGATE/SANCTION**
gate + log per the flow-state docs.

## new projects vs existing work (folds in the old brain-kickoff ritual)
brain-plan handles BOTH a fresh build ("minimal rust crate that...", "simple N x M slot...") and a change
to existing code. for a NEW project the IDEATION -> INTENT -> ASK front-end does the kickoff
interrogation: decompose his ask into INTERESTS (what does he want this to BE?), mirror his own move
("1. what else am i missing? 2. talk to me and iterate"), and never assume implementation detail under
ambiguity. ASK MORE than feels necessary, and ask it verbosely - he interrogates, he does not just
command ([[principle-24-socratic-mode]]), and a question is cheaper than a wrong plan
([[principle-01-no-assumptions]]). do NOT recite a fixed checklist: GENERATE the questions from the
brain each time ([[principle-29-interrogate-the-work]]) - recall the cards the ask touches and ask
"what would arpad ask here?", then surface them. cover, at minimum, verbosely: what is this FOR and
what is it NOT; what does done look like; what is in scope vs explicitly out; which existing
primitive/crate/file should this reuse or extend rather than reinvent (P05); where should each piece
LIVE (file, folder, module) and is the layout right; what are the failure modes and the error model;
what are the open trade-offs and which way do you lean. and for every artifact, file, folder, and
function the plan proposes, ask the would-arpad question explicitly: "would arpad write THIS file like
this? this folder structure like this? this individual function like this?" (P29) - name the option
and your rec, dont decide it for him. defaults he expects unless told otherwise: smallest correct
thing, only whats critical (no speculative deps/abstractions); reuse before reinvent; canonical
tooling over bespoke (criterion, not a custom harness); idiomatic in the target language;
worlds-simplest deployment; verbose doc comments, terse inline; honest about trade-offs. it is a
dialogue at the start, not a delivery.

## at PLAN: the artifact (write it to plans/NN-name.md)
1. goal. one or two sentences, tight scope. dont over-architect the first cut.
2. worked example FIRST. a concrete instance of the design in use: a struct exercising the new api,
   a sample invocation, a tiny flowchart, with comments. he validates abstractions against
   instances. give him one.
3. phases. atomic, ordered, each independently reviewable. each states: what changes, which files,
   the acceptance check.
4. review-gate strategy, baked in. each phase gated cold/unguided, multi-lens (see the
   brain-review-gate agent): "check the diff between phase X and Y, surface every issue
   biggest-bug-to-smallest-nit, be thorough". converge, fix even single-lens nits, correctness ->
   fix -> style/fmt last.
5. reuse + minimal-surface notes. existing primitives to reuse, smallest viable surface, no
   speculative deps.
6. open decisions. anything ambiguous, as a question with options + a rec - and err toward MORE
   questions, stated verbosely, not fewer (P24, P01). include the would-arpad fidelity questions for
   the artifacts the plan introduces: "would arpad write this file / folder / function like this?"
   (P29), each with the alternative and your lean, for him to settle.

## the hard rule: never assume
under any ambiguity in spec or detail, stop and ask before finalizing. 2-3 options + a rec, let him
choose. a plan on a wrong assumption is worse than no plan.

## the gate states (PLANPROBE -> PLANGATE -> SANCTION) - rules live in the flow-state docs
walk these; the RULE for each lives in its `flow.toml` state doc (single source - dont restate it).
the brain-plan-specific work at each:
- PLANPROBE: trace the plan THROUGH its own worked example, step by step. every step the plan cannot
  produce is a plan-vs-impl gap -> loop back to PLAN and fix it. not one-shot.
- PLANGATE: architectural scrutiny per the PLANGATE state doc (brain-meta-style:plan + the project reviewer
  when one exists). converge both; below_threshold loops to PLAN.
- SANCTION: cross ONLY when open-question-free AND the worked example traces end-to-end. LOG each
  decided-against fork per the SANCTION state doc:
  `python3 $AAV_BRAIN/bin/brain-trace.py --skill brain-plan --decision "<fork>" --chosen "<won>"
  --reject "<opt>=<why>" --affects "<plan path>" --principle <P>`. then STOP - planning ends here;
  execution is brain-execute's job once he blesses it.

## register
lowercase, terse, numbered. name exact files/types. end on the decision you need from him, not a
summary. write the plan to disk so its reviewable and cheap to change.
