---
name: principle-18-skills-over-agents
kind: principle
rule: skills are the unit. a null agent + one loaded skill = a standalone agent. keep an agent only when cold cleared-context dispatch is the whole point.
interest: [intent-craft, intent-efficiency]
confidence: high
evidence_count: 1
tells: ["less agents and more skills is stronger", "null agent with 1 skill loaded = stand alone agent", "compiling together a bag of skills", "no need for cold review garing inthis project", "semantic architecture reviewer checked"]
---

# P18 - skills over agents

## rule
prefer skills. a skill is composable and re-usable: load one into an empty agent and you have a
standalone specialist; bag several together and you have a workflow. keep a dedicated AGENT only
where a separate, cleared-context dispatch is the actual product (cold reviewers, the honest
verifier) - those must NOT share the author's context.

## why
skills compose, agents dont. craft (clean re-use) + efficiency (one skill, many call sites). a
nine-agent zoo is more surface than a bag of skills that any null agent can load.

## how to apply
- a "role the current loop should adopt" = skill (intent, plan, author-prompt, style, curate, commit).
- a "fresh independent opinion that must not see my framing" = agent (review-gate, verifier).
- orchestrators (kickoff, continue) are themselves thin skills that compose smaller skills and
  dispatch the few cold agents. thats the bag of skills.
- dont write a bespoke agent when a null agent + skill does it.

## anti-pattern
a brain-supervisor agent whose job is just "load the loop" - the loop is a skill (brain-meta-drive);
a null agent loading it IS the supervisor. nine agents where two would do.

**"no agents" is SCOPED, never global (2026-08-17).** On the laptop-perf-per-watt run he declined
cold review gating outright - *"no need for cold review garing inthis project"* - and then, two turns
later, named the reviewer he wanted: *"style checked, semantic architecture reviewer checked"*.
Both are true at once. Declining a STANDING mechanism (every phase gets a cold gate) does not
decline a NAMED request (run this reviewer on the finished tree). Read a refusal as narrow as it was
spoken: it retires the default, not the tool. When he later names an agent, dispatch it without
re-asking whether he meant it, and do not cite the earlier refusal back at him.
