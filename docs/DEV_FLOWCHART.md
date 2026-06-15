# my end-to-end dev flowchart (the execution flow)

this is the EXECUTION FLOW - the sequence of how the brain runs a task. it is SEPARATE from the
knowledge GRAPH (brain/graph/graph.json), which is the context fetcher ("which principles apply").
the flow answers "what step is next"; the graph answers "which cards apply". they never conflate, and
the flow uses STATES + TRANSITIONS while the graph uses nodes + edges, so the vocabulary never
overlaps (P30).

the source of truth is `brain/flow/flow.toml` (authored DATA, like the cards are the graph's data).
`bin/brain-flow.py` reads + validates it and builds `brain/flow/flow.json`; `bin/brain-walk.py` steps
flow.json deterministically. this whole file is GENERATED from flow.json by `brain-flow.py` - do NOT
hand-edit it; re-run the builder after editing flow.toml so it can never drift (the drift this file
used to have). it is drift-gated: `brain-flow.py --check` fails if this file is stale. a state may
CALL the graph (its `recall: true` flag fires brain-recall); the graph never calls the flow - one
direction.

## 1. the machine (generated)

```mermaid
stateDiagram-v2
    [*] --> IDEATION
    [*] --> IMPL
    [*] --> REVIEW
    [*] --> SR_SCAN
    IDEATION: IDEATION [entry] raw request received (brain-plan entry)
    INTENT: INTENT [work] position -> interest; surface ambiguity
    ASK: ASK [gate] ask the smallest unblocking question; never guess (pre-sanction clarify)
    RECON: RECON [work] read fs; seed the relevant-file set from the task
    EXPAND: EXPAND [work] grep deps/peripherals; ADD newly-implicated files. the set is mutable
    WOULDIWRITE: WOULDIWRITE [work] per file in the set: would i (arpad) write it like this? mark the no's
    SCRUTINIZE: SCRUTINIZE [work] line-by-line on marked files: idiom, magic values, trim the fat
    SEMANTIC: SEMANTIC [work] does each fn/struct/class LIVE where it belongs? DRY, reuse, library-fy (P05/P31)
    RELOCATE: RELOCATE [work] move fns/structs/classes to their correct module/file
    HIERARCHY: HIERARCHY [gate] judge the tree: flat->tree if a file too long / folder too flat-crowded; tree->flat if a refactor shrank it
    REORG: REORG [work] apply the reshape in the flagged direction; this MUTATES the set -> re-expand
    PLAN: PLAN [work] small+verbose plan with a worked example, to plans/
    PLANPROBE: PLANPROBE [work] trace the plan THROUGH its own worked example; mark every step the plan cannot actually produce (plan-vs-impl gap)
    PLANGATE: PLANGATE [gate] architectural scrutiny (brain-meta-style:plan AND the project-native reviewer when one exists - code-truth lens) + worked-example coherence; emits threshold_met only when plan_open==0 AND the worked example traces end-to-end. loops via below_threshold until then
    SANCTION: SANCTION [boundary] arpad approves; the regime flips to execute-through. LOG the plan's decided-against forks to the trace HERE (not deferred to CURATE - a sanctioned-but-unexecuted plan never reaches it)
    IMPL: IMPL [work] write the worker prompt in my voice; dispatch; implement the phase (brain-execute entry, post-sanction)
    PHASEGATE: PHASEGATE [gate] cold unguided multi-lens review vs the repo; converge; emits threshold_met only when nits_open==0 AND consistent-with-repo. loops via below_threshold -> REMEDIATE
    REMEDIATE: REMEDIATE [work] fix the converged nits IN PLACE (incl local relocations); does NOT leave the impl phase
    VERIFY: VERIFY [gate] build/test/bench honestly; emits sound only when build green AND tests pass AND bench within threshold. loops via unsound -> REMEDIATE
    STYLE: STYLE [work] final style pass: brain-fmt.py, trim fat, verbose docs, separators, fmt last
    RECORD: RECORD [work] categorise by semantics, draft the commit script, stop at the line
    CURATE: CURATE [work] capture every correction/approval/interrupt -> update the store; log the decision trace
    BLOCKED: BLOCKED [halt] post-sanction ambiguity: stop and ask arpad; resume the blocked state on /continue
    DONE: DONE [terminal] work complete
    REVIEW: REVIEW [entry] brain-review entry: cold unguided multi-lens review of the current diff; hand findings into the shared gate loop
    SR_SCAN: SR_SCAN [entry] brain-self-refine entry: run the scripted scan (cards/graph/flow/trace/paths/symlinks/traceability)
    SR_FINDINGS: SR_FINDINGS [work] read the trace + structural smells; GENERATE the questions from the brain (recall-driven, never a frozen list)
    SR_ASK: SR_ASK [gate] present FINDINGS + QUESTIONS only; he selects + annotates. consent is explicit - an unselected finding is dropped
    SR_EDIT: SR_EDIT [work] make ONLY the selected edits, each through the right meta-skill (curate/style/direct)
    SR_GATE: SR_GATE [gate] rebuild what the edit touched; brain-graph/flow/cards --check must pass before logging
    SR_LOG: SR_LOG [work] log each chosen decision to the trace so the next self-refine sees it
    ASK --> INTENT: answered
    CURATE --> DONE: learned
    EXPAND --> EXPAND: set_grew
    EXPAND --> WOULDIWRITE: set_stable
    HIERARCHY --> REORG: reshape_needed
    HIERARCHY --> PLAN: shape_ok
    IDEATION --> INTENT: received
    IMPL --> BLOCKED: ambiguous
    IMPL --> PHASEGATE: implemented
    INTENT --> ASK: ambiguous
    INTENT --> RECON: clear
    PHASEGATE --> REMEDIATE: below_threshold
    PHASEGATE --> VERIFY: threshold_met
    PLAN --> PLANPROBE: drafted
    PLANGATE --> PLAN: below_threshold
    PLANGATE --> ASK: blocked
    PLANGATE --> SANCTION: threshold_met *boundary*
    PLANPROBE --> PLAN: gap_found
    PLANPROBE --> PLANGATE: traced
    RECON --> EXPAND: seeded
    RECORD --> CURATE: prepared
    RELOCATE --> EXPAND: moved
    REMEDIATE --> PHASEGATE: fixed
    REORG --> EXPAND: reshaped
    REVIEW --> PHASEGATE: reviewed
    SANCTION --> IMPL: sanctioned
    SCRUTINIZE --> SEMANTIC: cleaned
    SEMANTIC --> RELOCATE: misplacements_found
    SEMANTIC --> HIERARCHY: placement_ok
    SR_ASK --> DONE: none_selected
    SR_ASK --> SR_EDIT: selected
    SR_EDIT --> SR_GATE: edited
    SR_FINDINGS --> SR_ASK: found
    SR_GATE --> SR_LOG: green
    SR_GATE --> SR_EDIT: red
    SR_LOG --> DONE: logged
    SR_SCAN --> SR_FINDINGS: scanned
    STYLE --> RECORD: styled
    VERIFY --> STYLE: last_phase
    VERIFY --> IMPL: more_phases
    VERIFY --> REMEDIATE: unsound
    WOULDIWRITE --> SEMANTIC: all_pass
    WOULDIWRITE --> SCRUTINIZE: some_marked
    BLOCKED --> [*]
    DONE --> [*]
```

## 2. state -> owner (generated from flow.json)

each state is owned by a brain skill or one of the two cold agents. the boundary state (SANCTION)
flips ask-first -> execute-through; BLOCKED is the only post-sanction stop (ask arpad, resume on
/continue).

| state | kind | entry | regime | owner | recall |
|---|---|---|---|---|---|
| IDEATION | entry | true | ask-first | - | false |
| INTENT | work |  |  | brain-meta-intent | true |
| ASK | gate |  |  | brain-meta-intent | true |
| RECON | work |  |  | brain-meta-recall+brain-plan | true |
| EXPAND | work |  |  | brain-meta-recall | true |
| WOULDIWRITE | work |  |  | brain-meta-style:plan | true |
| SCRUTINIZE | work |  |  | brain-meta-style:style | true |
| SEMANTIC | work |  |  | brain-meta-style:plan | true |
| RELOCATE | work |  |  | worker+brain-review-gate | false |
| HIERARCHY | gate |  |  | brain-meta-style:plan | false |
| REORG | work |  |  | worker+brain-review-gate | false |
| PLAN | work |  |  | brain-plan | true |
| PLANPROBE | work |  |  | brain-plan | true |
| PLANGATE | gate |  |  | brain-meta-style:plan | true |
| SANCTION | boundary |  |  | brain-meta-drive | false |
| IMPL | work | true | execute-through | brain-meta-author-prompt+worker | true |
| PHASEGATE | gate |  |  | brain-review-gate | false |
| REMEDIATE | work |  |  | brain-meta-author-prompt+worker | true |
| VERIFY | gate |  |  | brain-verifier | false |
| STYLE | work |  |  | brain-meta-style:style | true |
| RECORD | work |  |  | brain-meta-commit | false |
| CURATE | work |  |  | brain-meta-curate | true |
| BLOCKED | halt |  |  | brain-meta-intent | false |
| DONE | terminal |  |  | - | false |
| REVIEW | entry | true | ask-first | brain-review-gate | false |
| SR_SCAN | entry | true | ask-first | brain-self-refine | false |
| SR_FINDINGS | work |  |  | brain-self-refine | true |
| SR_ASK | gate |  |  | brain-self-refine | false |
| SR_EDIT | work |  |  | brain-self-refine | true |
| SR_GATE | gate |  |  | brain-self-refine | false |
| SR_LOG | work |  |  | brain-meta-curate | false |

## 3. how brain-meta-drive steps it

brain-meta-drive does not invent the sequence - it queries brain-walk:
1. `brain-walk --state <id>` returns the state's owner + recall flag.
2. if recall: run brain-recall to load the relevant cards (the one call into the graph).
3. run the owner; it yields an outcome event (threshold_met / below_threshold / set_grew / ...).
4. `brain-walk --state <id> --on <event>` returns the single next state - from the data, not judgement.

cyclic refinement is REQUIRED, not optional (P03). three regions LOOP until a metric threshold holds,
then advance exactly one phase:
- RECON..REORG: the per-file scrutiny + bidirectional reorg loop (P29, P27). the relevant-file set
  expands to a fixpoint (EXPAND self-loop) and re-expands after every move/reshape.
- PLAN -> PLANPROBE -> PLANGATE: the plan is traced THROUGH its own worked example; a gap routes back
  to PLAN. PLANGATE emits threshold_met (-> SANCTION) only when the plan is open-question-free and the
  example traces end-to-end, else below_threshold loops back to PLAN.
- IMPL -> PHASEGATE -> VERIFY: PHASEGATE loops below_threshold -> REMEDIATE -> PHASEGATE until the
  review converges (nits zero, consistent with the repo); VERIFY loops unsound -> REMEDIATE (which
  re-enters PHASEGATE) until the build/test/bench is sound. only then does it advance.

the gates never advance dirty: a threshold that is not met routes BACK, never forward.
