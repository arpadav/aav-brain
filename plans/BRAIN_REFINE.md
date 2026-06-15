# brain refine - 7 directives (via /brain-curate + /goal)

## the asks
1. discovery, not hardcoded paths: find brain via ~/.agents/**/*.* (follow symlinks), fallback
   ~/.claude/**/*.*. almost always home-manager symlinks; if not, edit in-line. fix scripts + skills.
2. skills that should call SCRIPTS: recurring deterministic ops (e.g. strip trailing periods from
   comments via regex+grep+sed) -> a committed script the skill calls. review ALL skills/intentions.
3. dont ALWAYS add a new principle by default - gauge whether to EXPAND an existing one. review all
   31 principles, ensure they are truly INDEPENDENT (atomic, orthogonal). merge/consolidate overlaps.
4. a core principle = ASKING QUESTIONS. "would arpad write this?" is one; also "why am i generating
   this artifact, is it used, should i read from it instead?", "has this been defined elsewhere?",
   many "why"s. used PRE- and POST-implementation. DONT hardcode the questions - ask the brain
   "what questions would arpad ask?" with context, then review them.
5. knowledge TRACE: the brain logs its decisions (esp. decided-AGAINST), so /brain-curate / self-
   reflect can read the log: "the brain decided against that HERE -> remove/modify/strengthen wording
   or change graph/flow, or ask arpad". then implement.
6. flow must ALLOW cycles/recursion - iterative refinement is REQUIRED; only after a metric threshold
   is met can it advance. review/check/style nodes are intermediate, cyclic: in plan phase, cycle
   plan-vs-impl reviews until plan good, then next phase; then cycle impl reviews until sound. is it
   done this way? if not, do it.
7. a `brain-self-refine` command: auto-asks exactly these kinds of meta-questions, brings FINDINGS +
   QUESTIONS (NOT implementation detail) to the user; user selects relevant + adds notes; on
   completion, kicks off the task to make those brain edits.

## approach
use the brain. dispatch cleared-ctx subagents to design 3 (independence), 6 (cyclic flow), and
1+2+4+5+7 (discovery/scripts/questioning/trace/self-refine). then implement, verify, log (curate).

## log
- started. dispatching design subagents.
