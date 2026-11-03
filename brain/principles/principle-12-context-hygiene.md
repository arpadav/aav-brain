---
name: principle-12-context-hygiene
kind: principle
tier: conditional
rule: Think in code. Use context-mode to derive answers in the sandbox; keep raw bytes out of the window.
interest: [intent-efficiency]
confidence: high
evidence_count: 7
tells: ["exclusively use context mode skill", "think in code", "use the mcp context-mode", "brain-find --export and then $AAV_BRAIN is a lot of tokens when added up - how to reduce CLI length of calls to maximize token efficiency?"]
---

# P12 - Context hygiene (think in code)

**Rule.** When searching, scanning, or processing anything large, **do it in code** in
the context-mode sandbox and surface only the derived answer. Don't read raw logs, large
files, or command dumps directly into the conversation. He mandates this explicitly for
main, implementation, and review agents alike.

**Why.** Every raw byte in the window is reasoning capacity spent ([[intent-efficiency]]).
He has already adopted context-mode as his discipline; the brain must be a model citizen
of it, not a context glutton.

**How to apply.**
- "add ... that main agent, impl agents (sonnet) and review agents should all exclusively
  use context mode skill when searching and executing commands to filter context
  appropriately and 'think in code'."
- Prefer `ctx_execute` / `ctx_batch_execute` over Bash+cat for anything you'll process.
- Read a file to *edit* it; run code over a file to *analyze* it.
- The brain's own calls are context too: a call every skill and agent repeats is paid on every run
  ("how to reduce CLI length of calls to maximize token efficiency?"). Each brain script is a short
  command (`Layout.scripts` in bin/brainlib/paths.py says which file is one). Shorten a recurring invocation once, in the tool, not in each
  prompt that uses it.
- Shortening is compression, not obfuscation: every command and arg gets its short form (`b-*` for
  `brain-*`), the long flags stay as aliases, a lookup table is printed on init for an agent that forgot a
  flag, and each command's inputs/outputs are trimmed too ("think about it like a compression algorithm
  ... dont over obfuscate, but definitely reduce to where its llm/machine compatible").
- When a tool errors pointing at context-mode, use it: "listen to the error: use the mcp
  context-mode."

**Anti-pattern.** `cat`-ing a 150 MB log into context; reading 40 files when a 20-line
script would summarize them; ignoring context-mode and blowing the window.
