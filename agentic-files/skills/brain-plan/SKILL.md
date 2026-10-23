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

handoff: with `$STATE`/`$REGIME` set and `$MODE` = `build`, call `Skill(brain-meta-drive)` and run `python3 $AAV_BRAIN/bin/run/brain-walk.py --state "$STATE" --mode build` (paste the output) - the handoff contract lives in brain-meta-drive.

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
2. worked example FIRST, and it starts with the COMMANDS he would type: run one unit on one input,
   run many, each output. derive the layout from those, never the reverse. then a struct exercising
   the new api, a tiny flowchart, with comments. he validates abstractions against instances.
   before PLANGATE, run the reviewer's three tests on your own plan: extension (add/delete one
   pluggable unit touches only its folder + one config entry), use (one-line run-one command), name
   (every file/folder/type/flag explained in one plain sentence; no near-twins, no path stutter).
   the PLANGATE dispatch quotes his asks verbatim; plan conformance is never the criterion.
3. phases. atomic, ordered. each states: what changes, which files, the acceptance check, and a
   size tag S | M | L (S: a few files, no new types or modules; M: one module's worth, or a new type;
   L: new modules, moved code, or a public surface change). phase count follows the work, never the
   review: a doc fix is one phase, a full doc rewrite may be six.
4. review-gate schedule, baked in. phases and gates are NOT 1-to-1. list where the gates are
   expected from the tags (an L phase gates alone; S phases batch until about one M's worth; the
   last phase always gates). the real call is `brain-gate.py phase` after each phase, on the
   measured diff, which overrides the tags when a phase is bigger than tagged. each gate: one
   brain-review-gate dispatch, 2-6 reviewers sized to the batch, two rounds at most.
5. proportion, then reuse + minimal surface. state the problem in HIS steps, quoted ("pull, send, run
   trt, copy back. thats it"). estimate the dumbest version that works - often a shell script - and
   its size, beside the plan's expected size. if the plan is several times that, each layer above the
   baseline gets a one-line reason it earns its place, or the plan shrinks. then existing primitives
   to reuse, smallest viable surface, no speculative deps.
6. open decisions. anything ambiguous, as a question with options + a rec - and err toward MORE
   questions, stated verbosely, not fewer (P24, P01). a decision that outlives this session (he
   wants to think, or it waits on someone) becomes an open-item file instead, per P66:
   `plans/open-items/<ID>-<slug>.md`, stamped with `brain-open-items.py stamp`. at RECON, recall with
   `--binds plans` and run `brain-open-items.py status`: an `edited` item carries his answer and is input to this plan. include the would-arpad fidelity questions for
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
  `python3 $AAV_BRAIN/bin/store/brain-trace.py --skill brain-plan --decision "<fork>" --chosen "<won>"
  --reject "<opt>=<why>" --affects "<plan path>" --principle <P>`. then STOP - planning ends here;
  execution is brain-execute's job once he blesses it.

## register
lowercase, terse, numbered. name exact files/types. end on the decision you need from him, not a
summary. write the plan to disk so its reviewable and cheap to change.
