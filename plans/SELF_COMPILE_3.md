# self-compile 3 - flow vs graph, per-file scrutiny, reorg

same prompt both passes, no added guidance. re-mine ALL history fresh. large refactors welcome.

## the asks
1. execution FLOWCHART must not be conflated with the knowledge GRAPH (the context fetcher/manager).
   they are SEPARATE. and the brain must deterministically FOLLOW a flowchart when executing. the flow
   (example, improve it): read fs -> find relevant files (set EXPANDS/SHIFTS as work reveals deps) ->
   "would arpad write it like this?" per file -> scrutinize line by line -> check semantic structure ->
   propose moving fns/structs/classes to appropriate locations -> folder/subfolder hierarchy is
   critical -> reorg BOTH directions: flat->tree when a file is too long or a folder has too many flat
   files; tree->flat when a refactor shrinks things and the structure is now overkill. add to brain.
2. brain skills not available in claude (only codex). STATUS: resolved - skills+agents are linked and
   show in a fresh claude session after `re` (they load at session start, not via hot reload). verify.
3. run (1) on the brain itself: "would arpad write this function/file this way?" for LITERALLY EVERY
   file. relevant set EXPANDS as work reveals peripherals. DRY-merge duplicate structs/files even when
   it touches many files - do NOT be dissuaded by volume. only keep separate for a REAL reason beyond
   laziness; else ALWAYS change it. add to brain.
0. double self-compile, all history fresh (done: 1214 turns, graph 32 nodes).

## new cards to add
- P27 organization & bidirectional reorg (hierarchy critical; flat<->tree both ways by threshold).
- P28 DRY-merge despite blast radius (merge dup structs/files even across many peripherals; keep
  separate only for a real reason, never laziness).
- P29 would-arpad-write-this (the per-file/per-function scrutiny lens, applied to every file).
- the deterministic execution flow itself (artifact, separate from graph).

## passes
- pass 1 (now): design flow/graph separation + deterministic flow; add cards; run per-file scrutiny +
  reorg the brain; verify.
- pass 2: same prompt. re-mine fresh again, re-audit the new tree with cleared-ctx brain subagents,
  fix remainder. dont stop until clean.

## log
- (pass1) skills verified available in claude (fresh session). re-mined fresh. 2 design+scrutiny subagents.
- (pass1) flow vs graph: built brain-flow.py + brain-walk.py + flow.json (deterministic, --check,
  --mermaid). flow is SEPARATE from graph (P30). DEV_FLOWCHART now GENERATED from flow.json (no drift).
- (pass1, user msg) flow authored as DATA: flow.toml (read by brain-flow), not hardcoded python.
- (pass1, user msg) portability: env vars AAV_BRAIN/BRAIN_AGENTS in nix; replaced all /home/arpad in
  15 skill/agent files; Path.home() in extract. 0 hardcoded paths left.
- (pass1, user msg) library-fy: brainlib.py shares Node/Edge/State/Transition + Artifact drift-gate +
  clip/parse_frontmatter/KIND_RANK. all 6 scripts import it; recall uses Node.from_dict, walk uses
  State. graph byte-identical after refactor. + the brain failed to catch this (pass-2 subagent argued
  AGAINST a lib) -> P31 + brain-style now checks for duplicate datatypes.
- (pass1) added cards P27-P31 (org/reorg, dry-merge-blast, would-i-write, deterministic-flow, library-fy).
  31 rules. fixed walker post-sanction crash (IMPL->BLOCKED). enhanced flow validate (sink-trap, dup).
  unified drift-gate. gitignore both repos. renamed Graph->GraphBuilder/RecallIndex.
- (pass1) verified: 6 files compile+50-hyphen, graph+flow deterministic+--check, 86 links, 0 abs paths.
- (pass2) cleared-ctx brain subagent re-audited. found the last real dup: compile.py hand-rolled the
  Artifact drift-gate (cross-repo). FIXED: compile.py now subclasses brainlib.Artifact via a relative
  path bridge (tooling shares; agent content stays isolated). also removed the ghost --regime flag from
  brain-continue, cached validate(). flow/graph separation + portability + flow-as-data all CLEAN.
- ALL DONE both passes. verified: 8 symbols each defined ONCE in brainlib; drift-gate only in brainlib,
  3 builders subclass; 7 files compile+50-hyphen; graph+flow+compile --check current+deterministic;
  DEV_FLOWCHART generated (matches --mermaid); 0 hardcoded paths; 31 cards / 37 nodes / 22 states; nix
  parses with AAV_BRAIN/BRAIN_AGENTS env vars.
