# self-compile 2 - deeper, twice

grand plan. terse, my voice. large refactors are ALWAYS welcome here if they make the structure
more maintainable and atomic. update this file if architecture shifts mid-way.

## what this is
use the brain on ALL my history (not just rejections) to catch everything wrong and fit my
fingerprint harder. self-compile twice: once now, once after, driven by my own reworded prompt.

## findings (3 cleared-ctx brain subagents, converged)
1. scripts are NOT in my style. every separator = 67 hyphens (must be 50). zero granular local
   separators inside functions. zero docstrings. no `Author: aav`. file-doc should be a module
   docstring. no labeled import/constants sections. cryptic locals (L, N). title-case bash prose.
2. fingerprint is rejection-biased. record() has no else -> drops 54% of turns (658/1212).
   thrown away: plan-prompts, build-requests, decisions, socratic-questions, naming-prefs, and
   sequencing (41% prevalence - my single biggest tell). codex interruptions impossible (claude-only).
   cards cite evidence that was discarded.
3. the deterministic knowledge graph i asked for is missing. only grep + a handwave doc shipped.

## decisions (adopted from the audits)
- extractor v2: emit prompts.jsonl (EVERY turn, multi-label classes[], never drop) + rich
  corpus-stats (sequencing histogram, opening-verb freq, per-class counts) + source-agnostic
  interruptions. in my code style.
- graph: NO neo4j daemon (infra for 27 cards). build a committed deterministic graph.json +
  graph.cypher export (neo4j door, no dependency). `bin/brain-graph.py` build + --check.
- recall: `bin/brain-recall.py` seed->traverse->rank, deterministic, replaces brain-query.sh
  (superset: same --tells/--all + --neighbors + edge-explained results). delete brain-query.sh.
- all scripts rewritten in my style: 50-hyphen 3-line flush separators, lowercase labels, granular
  per-step, verbose docstrings (# Arguments / # Returns), file-doc ends `Author: aav`.
- new cards from the recovered corpus: P20 refactors-welcome, P21 sequencing, P22 naming-conventions,
  P23 standing-decisions, P24 socratic-mode.
- nix: home.nix mkOutOfStoreSymlink the brain agents + skills into ~/.claude so reload works.

## pass 1 (now) - atomic order
1. rewrite brain-extract.py v2 (all-history, multi-label, rich stats, my style). re-run.
2. write brain-graph.py (build graph.json + graph.cypher + --check, my style). build.
3. write brain-recall.py (deterministic seed/traverse/rank, my style). delete brain-query.sh.
4. add cards P20-P24 from the recovered evidence. update INDEX + CONSTITUTION (now N rules).
5. update FINGERPRINT (full-corpus counts + the affirmative half: sequencing/build/decisions).
6. rewrite optional-graph.md (json-is-the-graph, cypher-is-the-export).
7. repoint INDEX/ARCHITECTURE/recall-skill/learn-skill to brain-recall + brain-graph + prompts.jsonl.
8. nix home.nix wiring for claude. note refactors-welcome in constitution + this log.
9. verify: graph builds byte-identical twice, recall works, scripts match my style, refs resolve.

## pass 2 (after) - reworded prompt
re-run the self-compile once more using my own prompt reworded TWICE->ONCE, irrelevant removed.
re-dispatch brain subagents cleared-ctx on the new tree. fix remainder. dont stop until clean.

## follow-up (separate ask, after both passes)
link skills/agents into ~/.agents (modern convention). if claude vs codex differ in how
skills/agents are written, template+compile in ~/repos/personal/agents and symlink only the
right compiled folders/files per tool.

## the pass-2 prompt (brain-authored: my prompt, TWICE->ONCE, one-time bits removed)
> use the brain skill to self compile: look through ALL chat history from ~/.claude and ~/.codex,
> not just rejections - decisions, plan prompts, wording, everything MUST be utilized. this brain
> task should self compile ONCE. note that large refactor changes ARE ALWAYS welcome if it serves
> the benefit of the structure and architecture to make code more maintainable and atomic. before
> fully continuing, use brain to catch everything wrong with current brain implementation and
> enhance it to fit my fingerprint even more strongly than ever before.

## log
- (pass1) 3 audits converged. built extractor v2 (all turns, multi-label, my style, 50-hyphen seps).
- (pass1) built brain-graph.py (deterministic graph.json + cypher + --check) and brain-recall.py
  (seed/traverse/rank). deleted brain-query.sh. refactored served_by -> derived inverse (0 drift).
- (pass1) added cards P20-P24 from the recovered corpus. updated INDEX/CONSTITUTION (24 rules),
  FINGERPRINT (affirmative half), optional-graph (real graph), schema, recall+learn skills.
- (pass1) nix home.nix: mkOutOfStoreSymlink brain agents + 10 skills into ~/.claude. parses + evals.
  user runs `re` to activate, then reload-plugins/reload-skills.
- (pass1) NOTED: large refactors are ALWAYS welcome when more maintainable/atomic (P20 + this line).
- (pass1) verified: 50-hyphen seps, graph byte-identical, 63 links resolve, no .mjs/brain-query.
- (pass2) re-audited with 2 cleared-ctx brain subagents. fixed: heat/emphasis/deploy classes +
  bucket priority (vetoes outrank directive, no length gates); --check now guards graph.cypher;
  tension edges (P01<->P10, P10<->P24, P20<->P05/P14); P20 confidence -> medium; P23 stat fixed +
  tells enriched (benchmark/parser now recall); added P25 deploy-infra; FINGERPRINT numbers now
  GENERATED (fingerprint-stats.md) not hardcoded - drift class killed like served_by.
- (pass2, user interrupt) caught a big miss: scripts were procedural, not struct-based. added P26
  (struct/class over standalone functions) and refactored all 3 scripts to classes (Turn/Reader/
  Corpus/Extractor, Node/Edge/Graph). identical output verified. now 26 rules, 32 graph nodes.
- (pass2) verified: 50-hyphen seps, classes, graph deterministic+--check, 69 links resolve, compiles.
- DONE both passes. large refactors welcome was honored repeatedly (served_by-derived, struct-based,
  generated fingerprint).
- (follow-up) ~/.agents + codex: skills are universal (raw symlink everywhere). codex has no agents,
  only skills, so agents/brain/bin/compile.py compiles the 2 agents -> codex skills (committed,
  deterministic, --check). nix home.nix now symlinks: claude skills+agents, codex skills+compiled
  agent-skills, ~/.agents shared skills. parses + evals. user runs `re` then reload.
- ALL DONE. verified: 4 class-based scripts (50-hyphen, compile, deterministic), graph+compile
  --check current, 26 cards / 32 nodes / 10 skills / 2 agents, nix parses, recall live.
