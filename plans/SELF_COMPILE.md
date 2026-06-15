# self-compile - review the brain with the brain, twice

grand plan. terse, his voice. update this file if architecture shifts mid-way.

## what this is
use the brain to review the brain. two passes. dont stop until every line is accounted for
and im satisfied. atomic, one thing at a time, deep. brain subagents (cleared context) for
second opinions.

## hard findings (evidence, not vibes)
- script-creation asks by lang: rust 21, bash 11, python 2, **node 0**. ".mjs" in history: **0**.
  -> `brain-extract.mjs` is off-stack. kill it.
- system indexes codex AND claude. 784 codex vs 322 claude mentions. its a GENERAL agent brain.
  -> decouple core tooling/docs from "claude" branding. keep ~/.claude as a factual data path only.
- 125 em-dashes + essay prose in docs/scripts/architecture. thats my voice not his.
  -> rewrite all TOOLING + SCRIPTS + ARCHITECTURE + DOCS in his voice. agent-speak stays only in
    the agent/skill .md peripherals.
- 9 agents / 4 skills. he wants skills-first: null agent + skill = standalone, skills compose.
  -> invert. skills are the unit. agents become thin shells (or drop most).

## new principles this review revealed (curator must add)
- P16 tooling in my stack & voice (rust/bash, never node/mjs; terse voice in tooling+docs).
- P17 agent-general, not claude-coupled (reason over codex+claude+any transcripts).
- P18 skills over agents (composable; null-agent+skill = standalone).
- P19 obvious recurring ops = think-in-code skills, not committed scripts.

## pass 1 - review USING the brain, then adjust
1. dispatch brain subagents (cleared ctx) on the brain files: style-critic (voice+stack+claude),
   architect/intent (extractor lang + agent->skill rearch), review-gate (cold voice read).
2. decide extractor: rust vs bash vs python vs think-in-code skill. (lean: his stack, min surface)
3. add P16-P19 cards via curator.
4. fix atomically, one item at a time:
   a. extractor -> his stack / skill
   b. decouple claude in core tooling/docs
   c. rewrite docs+architecture+scripts in his voice (kill em-dash essays)
   d. invert agents->skills
5. re-point every reference to renamed/removed files. account for every line.

## pass 2 - review the NEW brain, adjust again
1. re-query the updated brain. re-dispatch brain subagents cleared-ctx on the new tree.
2. fix whatever pass 1 missed. dont stop until clean.

## done = 
- no node/mjs anywhere. no stray "claude" coupling in core. docs/scripts/architecture in his voice.
- skills-first architecture. every cross-reference resolves. brain subagents sign off.

## locked decisions (from 3 cleared-ctx brain subagents, converged)
- extractor: python stdlib via uv -> `bin/brain-extract.py`. kill .mjs. brain-query.sh stays bash.
- arch: 10 skills, 2 agents. 7 agents -> skills. keep agents: brain-review-gate, brain-verifier
  (cold cleared-context dispatch IS their value). supervisor dissolves into brain-continue skill.
  - brain-intent-translator -> skills/brain-intent
  - brain-socratic-planner -> skills/brain-plan
  - brain-prompt-author -> skills/brain-author-prompt
  - brain-style-critic -> skills/brain-style
  - brain-curator -> skills/brain-curate
  - brain-commit-steward -> skills/brain-commit
  - keep skills: brain-recall, brain-learn, brain-kickoff, brain-continue
- voice: rewrite all docs his register. rank: fingerprint, architecture, intent_map, prior_art,
  readme, dev_flowchart, agents/brain/readme. kill 209 em-dashes + banned set.
- claude-decouple: README:7, ARCHITECTURE:6/64, DEV_FLOWCHART:106. keep factual data-paths/citations.

## log (append as we go)
- (pass1) evidence gathered, 3 brain subagents dispatched + converged, decisions locked.
- (pass1) added P16-P19 cards. ported brain-extract.mjs -> brain-extract.py (stdlib, verified same
  counts: 1211 turns / 188 rej / 49 int / 88 deny). deleted .mjs.
- (pass1) inverted arch: 9 agents -> 2 agents (brain-review-gate, brain-verifier) + 10 skills.
  dissolved brain-supervisor into brain-continue. rewrote brain-continue/kickoff/learn to compose.
- (pass1) rewrote all docs in his voice: README x2, ARCHITECTURE, FINGERPRINT, INTENT_MAP,
  DEV_FLOWCHART, PRIOR_ART, CONSTITUTION, INDEX, schema/*. killed 209 em-dashes + banned set +
  third-person bio. decoupled claude from core framing.
- (pass1) verified: 0 em-dash/glyph, 0 banned word, 48 inter-card links resolve, 0 dangling refs.
- (pass2) re-dispatched 2 cleared-ctx brain subagents on the NEW tree. both signed off:
  trees CLEAN, composition graph zero-dangling, 4 intents served. one nit: docs omitted
  ~/.codex/archived_sessions -> fixed in ARCHITECTURE + brain-learn.
- DONE. every line accounted for, twice. brain reviewed and re-shaped itself.
