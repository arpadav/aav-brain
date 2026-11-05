---
name: brain-open-items
description: "Write, stamp, answer, park and resolve open items (P66: one file each in plans/open-items/), and watch them for Arpad's answers. Load it whenever an agent writes or stamps an open item, acts on an edited one, or waits on his answer. When `stamp` prints `no watch: <command>`, the agent runs that command in the background; each time watch wakes it, it acts, stamps or resolves, then watches again, until Arpad says stop. When `life` is on PATH every item is a todo on his board, and the script keeps the two in step."
---

# brain-open-items

An item is one file, `plans/open-items/<ID>-<slug>.md`, written per P66 (`$AVB/brain/principles/principle-66-open-items-are-one-file-each.md`). The script owns its format: the `## Your call` section, the sha256 footer, and the note, the text under the item's last `## Your call` heading. The note is his answer, followed by the line that says where the item stands, when there is one: `Parked.`, or under life `closed on the board: ...`.

```bash
B="$AVB/agentic-files/skills/brain-open-items/brain-open-items.py"   # a shell older than the switch: eval "$(b-find -e)" first
```

## commands

- `python3 "$B" stamp <item>...`: asks life, then writes the footer; prints `no watch: <command>` when no watch holds the folder.
- `python3 "$B" status [<dir>]`: each item, `edited`, `new`, `parked` or `unchanged`.
- `python3 "$B" question <item>`: prints what the item asks, without `## Your call` and the footer.
- `python3 "$B" answer <item> < section.md`: replaces `## Your call`; refuses an item that does not exist, and empty stdin.
- `python3 "$B" clear <item>`: empties `## Your call`; refuses an item that does not exist.
- `python3 "$B" new <path> < body.md`: an unstamped item; refuses empty stdin.
- `python3 "$B" resolve <item>`: life's resolve, then deletes the item; exit 1 when life refuses, the item kept and life's reason on stderr.
- `python3 "$B" park <item>`, `python3 "$B" unpark <item>`: exit 1 when life refuses, as for `resolve`.
- `python3 "$B" watch [--dir <dir>]... [--every <seconds>]`: prints each new or edited item that is not parked, with its note, then exits; `already watching`, exit 5, when another watch holds a folder; exit 1 when it cannot watch, its folder gone among the reasons.

## the loop

1. At plan or execute start, run `status`. An `edited` item carries his answer. A `new` item the agent did not write is input too: a `U-` one he made on the board, or an `M-` one life made for a malformed todo, resolved once the todo is fixed. A `parked` one waits.
2. Write the item, then `stamp` it.
3. `stamp` printed `no watch: <command>`: run that command in the background. Only a background job of your own wakes you.
4. `watch` exits with an item: act on its note.
   - with life on PATH: `life open-item work <item>` first; exit 9 naming another assignee: someone else has it, leave it.
   - the item's todo id: `life open-item id "$(realpath <item>)"` prints it; exit 5: the item has no todo.
   - while working a todo: its overview is a checklist (`- [ ]` / `- [x]`), written when you start and ticked as you go (`life overview <id>` from stdin); the board's progress bar reads it.
5. After acting, `stamp` the item (a follow-up question, or a reply through `life open-item ask <item> "<reply>"`), or fold the decision into the docs it affects and `resolve` it. A refused `resolve` leaves the item open: say why, and leave it.
   - finished work on a todo: `life move <id> review` in the same step as the reply. Never move a todo to `done`; that is arpad's.
6. Run `watch` again, in the background. `watch` exiting 1: say why, and stop watching.
7. Stop only when arpad says so.
