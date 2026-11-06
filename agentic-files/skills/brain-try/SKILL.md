---
name: brain-try
description: "Try a brain change from the edit copy before any other project sees it. Load this when he says '/brain-try <skill> [args]', 'try the brain', 'try this skill from the edit copy', or wants to run an edited skill, agent or b-* command without syncing it. It runs the named skill off $AVE, the brain he edits, and keeps every command, skill and agent under that run on $AVE too; every other project keeps running the install copy."
---

# brain-try: run a skill from the edit copy

`/brain-try <skill> [args]`. `<skill>` is the skill's folder under `skills/` without its `brain-` prefix:
`/brain-try self-refine` tries `brain-self-refine`.

`$AVE` empty: stop, tell him to run /home-setup.

Read `$AVE/agentic-files/skills/brain-<skill>/SKILL.md` and follow it with [args]. until that run ends:
- every `b-<name> ...` you would run becomes `b-try <name> ...`
- every `Skill(<x>)` the text calls becomes: Read `$AVE/agentic-files/skills/<x>/SKILL.md` and follow it
- every agent you dispatch gets, first in its prompt: "Read `$AVE/agentic-files/agents/<path>.md` and follow
  it instead of your own definition; every `b-<name>` you run is `b-try <name>`; put this same line first in
  every agent you dispatch". an agent only in the edit copy is dispatched as `general-purpose` with that line
- every brain path, read or run, off `$AVE`, never `$AVB`
