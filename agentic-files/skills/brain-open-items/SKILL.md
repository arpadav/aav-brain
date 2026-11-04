---
name: brain-open-items
description: "Write, stamp, answer, park and resolve open items (P66: one file each in plans/open-items/), and watch them for Arpad's answers. Load it whenever an agent writes or stamps an open item, acts on an edited one, or waits on his answer. After a stamp the agent runs `watch` in the background; each time watch wakes it, it acts, stamps or resolves, then watches again, until Arpad says stop. When `life` is on PATH every item is a todo on his board, and the script keeps the two in step."
---

# brain-open-items

An item is one file, `plans/open-items/<ID>-<slug>.md`, written per P66 (`$AVB/brain/principles/principle-66-open-items-are-one-file-each.md`). The script owns its format: the `## Your call` section, the sha256 footer, the note.

```bash
B="$AVB/agentic-files/skills/brain-open-items/brain-open-items.py"   # a shell older than the switch: eval "$(b-find -e)" first
```

## commands

- `python3 "$B" stamp <item>...`: asks life, then writes the footer; prints `no watch: <command>` when no watch holds the folder.
- `python3 "$B" status [<dir>]`: each item, `edited`, `unchanged` or `new`.
- `python3 "$B" answer <item> < section.md`: replaces `## Your call`; refuses an item that does not exist.
- `python3 "$B" new <path> < body.md`: an unstamped item.
- `python3 "$B" resolve <item>`: life's resolve, then deletes the item.
- `python3 "$B" park <item>`, `python3 "$B" unpark <item>`.
- `python3 "$B" watch --dir <dir>... [--every <seconds>]`: prints each new or edited item with its note, then exits; `already watching`, exit 5, when another watch holds a folder.

## the loop

1. Write the item, then `stamp` it.
2. `stamp` printed `no watch: <command>`: run that command in the background. Only a background job of your own wakes you.
3. `watch` exits with an item: act on its note.
   - with life on PATH: `life open-item work <item>` first; exit 9 naming another assignee: someone else has it, leave it.
   - while working a todo: its overview is a checklist (`- [ ]` / `- [x]`), written when you start and ticked as you go (`todo overview <id>` from stdin); the board's progress bar reads it.
4. After acting, `stamp` the item (a follow-up question, or a reply through `life open-item ask <item> "<reply>"`), or fold the decision into the docs it affects and `resolve` it.
   - finished work on a todo: `todo move <id> review` in the same step as the reply. Never move a todo to `done`; that is arpad's.
5. Run `watch` again, in the background.
6. Stop only when arpad says so.
