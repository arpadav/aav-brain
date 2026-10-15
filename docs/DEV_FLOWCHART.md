# my end-to-end dev flowchart (the execution flow)

this is the EXECUTION FLOW - the sequence of how the brain runs a task. it is SEPARATE from the
knowledge GRAPH (brain/graph/graph.json), which is the context fetcher ("which principles apply").
the flow answers "what step is next"; the graph answers "which cards apply". they never conflate, and
the flow uses STATES + TRANSITIONS while the graph uses nodes + edges, so the vocabulary never
overlaps (P30).

the source of truth is `brain/flow/flow.toml` (authored DATA, like the cards are the graph's data).
`bin/brain-flow.py` reads + validates it and builds `brain/flow/flow.json`; `bin/brain-walk.py` steps
flow.json deterministically. this whole file is GENERATED from flow.json by `brain-flow.py` - do NOT
hand-edit it; re-run the builder after editing flow.toml so it can never drift. it is
drift-gated: `brain-flow.py --check` fails if this file is stale. a state may
CALL the graph (its `recall: true` flag fires brain-recall); the graph never calls the flow - one
direction.

## 1. the machine (generated)

```mermaid
stateDiagram-v2
    [*] --> IDEATION
    [*] --> DOCTRINE
    [*] --> REVIEW
    [*] --> SR_SCAN
    [*] --> EDIT

    state "IDEATION [entry] raw request received (brain-plan entry)" as IDEATION
    state "INTENT [work] position -> interest; surface ambiguity" as INTENT
    state "ASK [gate] ask the smallest unblocking question; never guess (pre-sanction clarify). ORDER IS FIXED: the FIRST question is always about the EXPERIENCE - what using the thing is like, how he will interact with it - offered as whole shapes he can pick between (a watch loop that re-runs on save / a page on localhost / a chat drill), never as parameters. only after that are specifics asked, and each carries a RECOMMENDED DEFAULT so the cheap answer is yes. a specific with an obvious default is not worth a question at all - take it and say which you took. measured failure this repairs: a lab count, a file layout and a progress format were each waved through as mechanical detail, and together they WERE the product - he had to redirect three times mid-build. the test is not is this decision small, it is DOES THIS DECIDE WHAT USING IT FEELS LIKE (P42, P44)" as ASK
    state "RECON [work] read fs; seed the relevant-file set from the task" as RECON
    state "EXPAND [work] grep deps/peripherals; ADD newly-implicated files. the set is mutable" as EXPAND
    state "WOULDIWRITE [work] per file in the set: would i (arpad) write it like this? mark the no's" as WOULDIWRITE
    state "SCRUTINIZE [work] line-by-line on marked files: idiom, magic values, trim the fat" as SCRUTINIZE
    state "SEMANTIC [work] does each fn/struct/class LIVE where it belongs? DRY, reuse, library-fy (P05/P31)" as SEMANTIC
    state "RELOCATE [work] move fns/structs/classes to their correct module/file" as RELOCATE
    state "HIERARCHY [gate] judge the tree: flat->tree if a file too long / folder too flat-crowded; tree->flat if a refactor shrank it" as HIERARCHY
    state "REORG [work] apply the reshape in the flagged direction; this MUTATES the set -> re-expand" as REORG
    state "PLAN [work] small+verbose plan with a worked example, to plans/" as PLAN
    state "PLANPROBE [work] trace the plan THROUGH its own worked example; mark every step the plan cannot actually produce (plan-vs-impl gap)" as PLANPROBE
    state "PLANGATE [gate] architectural scrutiny (brain-meta-style:plan AND the project-native reviewer when one exists - code-truth lens) + worked-example coherence; emits threshold_met only when plan_open==0 AND the worked example traces end-to-end. loops via below_threshold until then" as PLANGATE
    state "SANCTION [boundary] arpad approves; the regime flips to execute-through. LOG the plan's decided-against forks to the trace HERE (not deferred to CURATE - a sanctioned-but-unexecuted plan never reaches it)" as SANCTION
    state "DOCTRINE [gate] resolve the artifact PURPOSE (P41: scratch skip / tutorial light / production exhaustive) and the language row (P06); load the always-load doctrine set plus that language's extras; author the worker prompt carrying P40's before/after exemplars and the find-exhaustively ask. an adjective is not a resolved doctrine - emit unresolved (brain-execute entry, post-sanction)" as DOCTRINE
    state "IMPL [work] dispatch the workers with the prompt DOCTRINE authored; implement the phase (post-sanction). FAN OUT: two to three independent workers issued as PARALLEL TOOL CALLS IN ONE MESSAGE, each on a disjoint file set or in its own worktree, staggered as one returns - a loop of single dispatches is serial and looks identical in the transcript until you count them (P52). the tree-wide build/test/lint command belongs to the OVERSEER and runs one at a time, never to a worker: two builds block on one target lock and two mutation batteries revert over each other. a worker proves its own work with the cheap subset in its own worktree. the worker carries its END GOAL, not just this phase's ask: work beyond the literal ask that moves toward the sanctioned mission is IN, work merely adjacent is out (P45, P50). at the phase boundary, `brain-shape.py <repo> --since <the ref this phase started from>` decides which exit to take: over shape.toml's budget -> `implemented`, the cold gate; under it -> `under_budget`, straight to VERIFY. an unresolvable ref ARMS, because a gate is not cancelled by a typo" as IMPL
    state "PHASEGATE [gate] cold unguided multi-lens review vs the repo; converge; emits threshold_met only when nits_open==0 AND consistent-with-repo. loops via below_threshold -> ADJUDICATE, which is what makes the loop terminating. TWO SCOPES, and running only the first is the measured failure: the correctness and idiom lenses read the DIFF, and a STRUCTURE lens reads the WHOLE TREE - file length, folder fan-out, one datatype defined twice - because none of those is visible in a hunk. run `brain-shape.py <repo>` FIRST and hand its crossings to that lens as its input; P27 and P28 are adjectives without it. what makes this a rule rather than a preference is measured, once, on principle-27 under `## the measurement`: the architecture lens ran at every late phase of a build, on the diff, and passed a 7540-line file every time - not because nobody looked, but because what it was shown could not contain the defect. WHEN IT FIRES is `brain-shape.py --since <phase start>`: armed by the change budget, then held to the next phase boundary so a gate never lands mid-phase. under budget the phase ends at VERIFY and STYLE - a two-line formatter fix does not buy a cold multi-lens review. A DENIED DISPATCH IS A HOLE, NOT A PASS: a lens refused by the permission classifier did not run, so the gate did not measure what that lens was for. retry once; if it still will not go, emit `unmeasurable` and stop - `below_threshold` is the WRONG event for it, because a denial is not a finding and ADJUDICATE would rule the empty set all_invalid and advance" as PHASEGATE
    state "ADJUDICATE [work] a finding is EVIDENCE, not a verdict. classify each against the artifact's stated contract: valid | invalid | deferred-to-a-later-phase. ONLY valid findings reach REMEDIATE. an invalid one is REJECTED with a logged reason (brain-trace.py --reject), never fixed - fixing 'this is incomplete' on a deliberately-incomplete artifact is a loop that cannot terminate" as ADJUDICATE
    state "SUBDESIGN [work] design ONE atomic part, then return. reached only when ADJUDICATE ruled that the finding is not a defect in the patch but a defect in the DESIGN - the tell is that every available fix makes the code worse, so the patch spaghettifies (P51). scope is the part, never the plan: the error model, the id scheme, the one seam the findings keep circling - name it, design it, write it to plans/ as an addendum so a cold reviewer reads it as errata rather than as drift, then hand REMEDIATE a shape to build to. DESTRUCTIVE AND DRASTIC PROPOSALS ARE SANCTIONED HERE and nowhere else in the impl loop: delete the layer, invert the ownership, collapse the two types into one. the size of the change is not an argument against it (P20); the only test is whether the result is more maintainable and more atomic. it is NOT a licence to re-plan the build - a subdesign that reaches for a second part is out of scope and emits ambiguous" as SUBDESIGN
    state "REMEDIATE [work] fix the ADJUDICATED-VALID nits IN PLACE (incl local relocations); does NOT leave the impl phase. a finding ADJUDICATE ruled a DESIGN fault does not arrive here as a patch - it goes to SUBDESIGN first and comes back as a shape to build to. patching around a bad design is what this state must not be used for (P20, P51)" as REMEDIATE
    state "VERIFY [gate] build/test/bench honestly; emits sound only when the build is green AND the artifact's OWN stated bar is met AND the bench is within threshold. the bar is usually 'tests pass' but is NOT hardcoded to it: an artifact that ships deliberately red (a rustlings-style tutorial, a lab with todo!()) declares its real bar - e.g. `--features solutions` green while a bare `cargo test` stays red - and THAT is what soundness means for it. measuring against the wrong bar makes unsound permanent, the same non-terminating loop ADJUDICATE breaks at PHASEGATE. loops via unsound -> REMEDIATE. the pass events REQUIRE a returned brain-verifier report: measured, the agent was dispatched on 9 of ~31 visits, so 7 times in 10 the author verified its own work and advanced. verifying yourself is not verification - emit unverified and dispatch the agent" as VERIFY
    state "STYLE [gate] the style gate, and it is ALWAYS required - only an explicit instruction against it skips it. resolve each language in the tree against the style-contract card, dispatch the aav-style lenses (separators, docs, imports, items) to apply it, then PROVE the result with brain-fmt.py --check. emits styled ONLY when the mechanical checks pass: local separators present inside function bodies, no blank line after any separator, global labels inside the closed whitelist, formatter clean. anything else emits unstyled and loops back. before this gate existed STYLE had a single outbound event, which made a hollow pass and a thorough one indistinguishable to the machine - it ran every time and landed nothing" as STYLE_GATE
    state "RECORD [work] categorise by semantics, draft the commit script, stop at the line" as RECORD
    state "CURATE [work] capture every correction/approval/interrupt -> update the store; log the decision trace" as CURATE
    state "BLOCKED [halt] post-sanction ambiguity: stop and ask arpad; resume the blocked state on /continue" as BLOCKED
    state "DONE [terminal] work complete. the closing line reports STATE, NOT A CHANGELOG (P43): is it done yes/no, and what is left. NEVER a tour of what was fixed, measured or rewritten - he reads git diff for that, and a defect that no longer exists is not information. a how-to is ONE LINE per thing, not a section per thing. surface a number only when it changes what he does next. an unresolved blocker IS state and must be said first. measured: 5 of 77 recorded heat events are him saying the brain wrote too much - it is the single most reliable producer of heat in the corpus. then DISPATCH brain-learner to mine this conversation for durable signal, and say so - e.g. `done. <what is left, if anything>. *note* i have dispatched an agent to learn from this conversation and refine the brain`. measured: IMPL was entered 176 times and CURATE 10, so a run that ends without this never taught the brain anything" as DONE
    state "REVIEW [entry] brain-review entry: cold unguided multi-lens review of the current diff; hand findings into the shared gate loop" as REVIEW
    state "SR_SCAN [entry] brain-self-refine entry: run the scripted scan (cards/graph/flow/trace/paths/symlinks/traceability)" as SR_SCAN
    state "SR_FINDINGS [work] read the trace + structural smells; GENERATE the questions from the brain (recall-driven, never a frozen list)" as SR_FINDINGS
    state "SR_ASK [gate] present FINDINGS + QUESTIONS only; he selects + annotates. consent is explicit - an unselected finding is dropped" as SR_ASK
    state "EDIT [work] make ONLY the selected/asked-for edit, through the right meta-skill (curate/style/direct). the OUTBOUND EVENT IS THE RIGOR DIAL and it is HIS to set, asked before the edit starts, never inferred from how small the change looks (P41): `edited` -> VERIFY builds and tests it, `gated` -> PHASEGATE puts a cold reviewer on the diff first, `unchecked` -> STYLE skips verification entirely. every one of them still rides STYLE -> RECORD -> CURATE, so a small edit is never outside the ecosystem" as EDIT

    ADJUDICATE --> VERIFY: all_invalid
    ADJUDICATE --> VERIFY: deferred
    ADJUDICATE --> SUBDESIGN: design_fault [build]
    ADJUDICATE --> REMEDIATE: valid_remain
    ASK --> INTENT: answered
    CURATE --> DONE: learned
    DOCTRINE --> IMPL: resolved
    DOCTRINE --> BLOCKED: unresolved
    EDIT --> BLOCKED: ambiguous
    EDIT --> VERIFY: edited
    EDIT --> PHASEGATE: gated
    EDIT --> STYLE_GATE: unchecked [edit]
    EXPAND --> EXPAND: set_grew
    EXPAND --> WOULDIWRITE: set_stable
    HIERARCHY --> REORG: reshape_needed
    HIERARCHY --> PLAN: shape_ok
    IDEATION --> INTENT: received
    IMPL --> BLOCKED: ambiguous
    IMPL --> PHASEGATE: implemented
    IMPL --> DOCTRINE: phase_done
    IMPL --> VERIFY: under_budget [build]
    INTENT --> ASK: ambiguous
    INTENT --> RECON: clear
    PHASEGATE --> ADJUDICATE: below_threshold
    PHASEGATE --> VERIFY: threshold_met
    PHASEGATE --> BLOCKED: unmeasurable
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
    SANCTION --> DOCTRINE: sanctioned
    SCRUTINIZE --> SEMANTIC: cleaned
    SEMANTIC --> RELOCATE: misplacements_found
    SEMANTIC --> HIERARCHY: placement_ok
    SR_ASK --> DONE: none_selected
    SR_ASK --> EDIT: selected
    SR_FINDINGS --> SR_ASK: found
    SR_SCAN --> SR_FINDINGS: scanned
    STYLE_GATE --> RECORD: styled
    STYLE_GATE --> STYLE_GATE: unstyled
    SUBDESIGN --> BLOCKED: ambiguous [build]
    SUBDESIGN --> REMEDIATE: designed [build]
    VERIFY --> STYLE_GATE: last_phase
    VERIFY --> DOCTRINE: more_phases [build]
    VERIFY --> REMEDIATE: unsound
    VERIFY --> VERIFY: unverified
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
| RECON | work |  |  | brain-recall+brain-plan | true |
| EXPAND | work |  |  | brain-recall | true |
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
| DOCTRINE | gate | true | execute-through | brain-meta-author-prompt | true |
| IMPL | work |  | execute-through | worker | true |
| PHASEGATE | gate |  |  | brain-review-gate | true |
| ADJUDICATE | work |  |  | brain-meta-style | true |
| SUBDESIGN | work |  |  | brain-meta-author-prompt+aav-semantic-architecture-reviewer | true |
| REMEDIATE | work |  |  | brain-meta-author-prompt+worker | true |
| VERIFY | gate |  |  | brain-verifier | false |
| STYLE | gate |  |  | brain-meta-style:style + aav-style-separators + aav-style-docs + aav-style-imports + aav-style-items | true |
| RECORD | work |  |  | brain-meta-commit | false |
| CURATE | work |  |  | brain-meta-curate | true |
| BLOCKED | halt |  |  | brain-meta-intent | false |
| DONE | terminal |  |  | brain-learner | false |
| REVIEW | entry | true | ask-first | brain-review-gate | false |
| SR_SCAN | entry | true | ask-first | brain-self-refine | false |
| SR_FINDINGS | work |  |  | brain-self-refine | true |
| SR_ASK | gate |  |  | brain-self-refine | false |
| EDIT | work | true | execute-through | brain-self-refine+brain-edit | true |

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
