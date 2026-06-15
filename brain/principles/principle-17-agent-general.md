---
name: principle-17-agent-general
kind: principle
rule: this is a general agent brain. it reasons over agent transcripts (codex + claude + whatever), not coupled to one tool. dont brand the core as claude-specific.
interest: [intent-craft]
confidence: high
evidence_count: 2
tells: ["i asked you to index codex and claude", "general agent plan not coupled with claude"]
---

# P17 - agent-general, not tool-coupled

## rule
the brain learns from BOTH my codex and my claude sessions, and should work with any agent
transcript. so the core tooling, docs, and architecture talk about "agent sessions / transcripts /
workers" generically. they do NOT frame the whole system as a claude thing.

## why
i index codex and claude. the system is the idea, not the vendor. coupling the core to claude is a
category error and makes it brittle if i move tools.

## how to apply
- core tooling/docs: say "agent transcripts", "worker agents", "agent sessions". not "claude agents".
- a path like `~/.claude/projects` is a real data source. keep it as a factual path. same with
  `~/.codex/sessions`. labeling a source row "claude" vs "codex" is a FACT, fine.
- the agent/skill .md files run inside a specific harness, so naming the harness there is fine
  (peripheral). the rule is about the CORE not privileging one tool.

## anti-pattern
"the brain prompts other Claude agents" in the architecture doc. treating claude as the system
instead of one of two transcript sources.
