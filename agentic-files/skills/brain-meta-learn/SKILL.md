---
name: brain-meta-learn
description: "Re-learn Arpad's style from recent history and sharpen the brain store. Load it after a work run, after he corrects or validates an approach, or periodically. Re-runs the transcript extractor over ~/.codex and ~/.claude, then loads the brain-meta-curate skill to distill durable lessons into principle cards - learning ONLY from explicit spoken signal, never from accepted edits."
---

# brain-meta-learn: refresh and sharpen the brain

the brain is a learning model of arpad, not a snapshot. this skill updates it. it composes the
extractor (machine pass) + brain-meta-curate (judgement pass).

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"`. RUN the scripts below
and use their output - the machine pass is deterministic; do not hand-summarise transcripts yourself.

## procedure
1. re-extract the evidence (machine pass) - EXECUTE, do not read transcripts by hand:
   ```bash
   python3 $AAV_BRAIN/bin/brain-extract.py
   # or: uv run $AAV_BRAIN/bin/brain-extract.py
   ```
   rebuilds the evidence corpus (the PRIVATE data dir, `$XDG_DATA_HOME/aav-brain/evidence`, outside the
   repo) from ~/.codex (sessions + archived_sessions) + ~/.claude/projects:
   prompts.jsonl (EVERY turn, bucketed + classed), corpus-stats.json (tone, class counts, sequencing
   histogram, opening verbs), and the back-compat views. explicit signal only - nothing dropped.
2. distill durable lessons (judgement pass). load the brain-meta-curate skill. it reviews:
   - the refreshed evidence/ (new prompts since last run, across ALL classes not just rejections),
   - this session's corrections, validated approaches, and any heat events,
   and writes them back as new/updated principle cards (rule + why + how to apply + tells),
   updating brain/INDEX.md. it does NOT duplicate, it updates existing cards first.
3. rebuild the graph so recall sees the new/edited cards:
   ```bash
   python3 $AAV_BRAIN/bin/brain-graph.py
   ```
4. prune. have brain-meta-curate lower confidence on thinly-evidenced cards and delete/replace any
   contradicted by newer signal. stale rules rot, remove them.

## prime rule
learn only from what he said: prompts, interruptions, rejections, approvals, heat. NEVER infer a
preference from an accepted edit or an auto-approved tool call. consent is explicit.

## what NOT to capture
code structure, file paths, git history, anything readable from the repo, ephemeral task state.
capture the non-obvious preference and its why, not the mechanics.

## output
a short changelog: cards created/updated/pruned this run, the rule each encodes, the evidence counts
that moved. terse.
