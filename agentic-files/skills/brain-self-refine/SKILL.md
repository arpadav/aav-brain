---
name: brain-self-refine
description: "Turn the brain's review lens on the brain itself. Load it when Arpad says 'refine the brain', 'self-refine', 'what would you improve about the brain', or after a stretch of brain edits. It first refreshes the evidence corpus (archive + merge + re-stamp, before the expiring transcripts prune), scans the store deterministically, asks the brain (not a hardcoded list) what Arpad would interrogate, and brings FINDINGS + QUESTIONS only - never implementation detail - for him to select and annotate. On his completion it kicks off exactly those edits and logs each to the decision trace. This is the meta-loop that produced its own existence."
---

# brain-self-refine: the brain reviews the brain

the same prompts arpad uses to sharpen the brain ("are there hardcoded paths?", "should this be a
script?", "are these principles independent?", "why am i generating this?") are now a command. this
skill runs that interrogation ON the brain and brings him the findings + questions, NOT a plan. he
decides; then it builds.

this is P29 (interrogate the work) pointed inward: the artifact under review IS the brain.

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"` (sets `$AAV_BRAIN`).

## 0. REFRESH THE CORPUS FIRST (every invocation, before the scan)
this command is the scheduled refresh point. the transcript sources EXPIRE -
claude prunes `~/.claude/projects` at roughly 26 days - so evidence not captured
before then is gone from every source forever. run this first, always:
```bash
python3 $AAV_BRAIN/bin/brain-extract.py --archive   # cold-store raw transcripts, then merge + re-stamp
```
`--archive` gzips any unseen transcript into `$XDG_DATA_HOME/aav-brain-archive`
(deliberately OUTSIDE the logs submodule - raw transcripts are bulk, not
versioned knowledge) so a better classifier can always be re-run over old
material. the extract itself is a MERGE keyed on a content hash: it only ever
adds, it re-stamps `corpus-stats.json` with a fresh `generated_at`, and running
it twice is a no-op. it is safe to run unconditionally.

the same refresh belongs after any long run, for the same reason: the window
closes on its own schedule, not yours.

## entry - hand the walk to the engine
brain-self-refine is the self-refine ENTRY: set `$STATE` = `SR_SCAN`, `$REGIME` = `ask-first` and
`$MODE` = `--self-refine`, then load `brain-meta-drive` to walk

    SR_SCAN -> SR_FINDINGS -> SR_ASK -> EDIT -> VERIFY -> STYLE -> RECORD -> CURATE -> DONE

only the first three are refine-specific; from EDIT it rejoins the SHARED tail every build uses.
that is deliberate - EDIT writes code, and before the fold a refine run reached neither the style
gate nor the verifier, so brain scripts edited here were gated only when someone remembered to do it
by hand. `SR_GATE` and `SR_LOG` are gone: they were VERIFY and CURATE under other names.

`EDIT` is SHARED, not refine-owned: `brain-edit` enters the same state directly for a small
follow-up change to a previous build. same act, same rails, one state. its outbound event is the
rigor dial, and only two of its three edges are open here: a refine run emits `edited` and rides
VERIFY, or `gated` for a cold pass first. `unchecked` is guarded to brain-edit.

`$MODE` is what makes the shared tail behave: `VERIFY --more_phases--> DOCTRINE` is guarded `build`,
because a refine run has no phases. drop the flag and the walk takes the build branch. `EDIT
--unchecked--> STYLE` is guarded `edit` for the same reason in reverse: a refine run has just
written brain code, so skipping the verifier is not one of its options.

the trampoline is the engine's; the steps below are this skill's per-state work
(0-1=SR_SCAN, 2-3=SR_FINDINGS, 4=SR_ASK, 5=EDIT, then the shared tail). ask-first throughout -
SR_ASK blocks on his selection (a pre-sanction ASK gate, never auto-applied). step 0 is the ONE
exception and needs no consent: it only preserves and merges evidence, never edits the brain.

<!-- GENERATED: handoff (brain-flow.py) - do not hand-edit -->

this hands off to `brain-meta-drive`. the handoff has TWO steps and both are
mandatory - a summary of what the engine does is NOT a substitute for running it:

```bash
python3 $AAV_BRAIN/bin/brain-walk.py --state "$STATE" $MODE   # paste the output
```

`$MODE` is `--self-refine` for the self-refine entry, `--edit` for brain-edit,
and EMPTY for plan/execute/review. it is not cosmetic: a guarded edge resolves
differently by mode, so a walk that drops it takes the build branch and a
phase-less run can be sent back to DOCTRINE for a phase that does not exist.
set it once at the entry and pass it on every walk call - the engine forwards
it verbatim and never infers it.

**you may not proceed until that output is in the transcript.** it names the
state's owner and its transitions; if it is absent, the walk did not happen.
then, and only then:

```
Skill(brain-meta-drive)          # the literal tool call, not a Read
```

the engine steps `flow.json`, recalls per state, dispatches each owner, and
loops the gates to a terminal. you do not re-implement that loop here.

every state the engine reaches prints its own directive the same way - a
`Skill(...)` or `Agent(...)` line under the state. make that call before doing
the state's work; the owner skill IS the method, and hand-rolling it inline
looks identical in the transcript while discarding it.
<!-- END GENERATED: handoff -->

## 1. scan deterministically (EXECUTE the checks, do not eyeball)
run the scripted checks and collect their output - this is the machine pass, it must be reproducible:
```bash
python3 $AAV_BRAIN/bin/brain-cards.py            # structural errors: dangling links, missing frontmatter, INDEX gaps
python3 $AAV_BRAIN/bin/brain-graph.py --check    # graph drift from the cards
python3 $AAV_BRAIN/bin/brain-flow.py --check     # flow + flowchart drift from flow.toml
python3 $AAV_BRAIN/bin/compile.py --check        # codex agents + the global preamble drift from their sources
python3 $AAV_BRAIN/bin/brain-lint.py             # every installed python checker, each on its pinned config
python3 $AAV_BRAIN/bin/brain-fmt.py --stale $AAV_BRAIN/bin/*.py   # comments naming a symbol the file lost (P37)
python3 $AAV_BRAIN/bin/brain-trace.py --against        # decisions that rejected an option
python3 $AAV_BRAIN/bin/brain-trace.py --low-confidence # decisions worth revisiting
python3 $AAV_BRAIN/bin/brain-trace.py --stale-candidates # entries whose affects resolves to nothing
grep -rn -- '/home/[a-z]\|-home-[a-z]' "$AAV_BRAIN/bin" "$AAV_BRAIN/agentic-files"  # hardcoded paths incl hyphen-encoded form (P32)
find "$AAV_BRAIN/agentic-files" -type l -lname '*../*'          # layout-baking symlinks: the P32 costume case grep cannot see
# traceability (CONSTITUTION rule): skills that have NEVER logged a fork. judge which gaps are real -
# retrieval/util skills (brain-find) legitimately have none; decision-making
# entries + meta (plan, execute, edit, review, self-refine, meta-intent, meta-curate, meta-commit,
# meta-author-prompt) with zero entries is a violation. the sed GRANDFATHERS pre-rename tags so a
# skill that logged under its OLD name isn't falsely flagged after the brain-meta-* rename. --pruned
# is unioned in because a PRUNED entry still proves the skill logged a fork - reading only --against
# would report a CONSTITUTION violation the moment a skill's last entry was pruned.
comm -13 <({ python3 $AAV_BRAIN/bin/brain-trace.py --against; python3 $AAV_BRAIN/bin/brain-trace.py --pruned; } \
  | grep -oE '\[brain-[a-z-]+\]' | tr -d '[]' \
  | sed -E 's/^brain-(intent|recall|style|curate|commit|author-prompt|learn)$/brain-meta-\1/; s/^brain-continue$/brain-meta-drive/' \
  | sort -u) \
  <(ls "$AAV_BRAIN/agentic-files/skills" | sort -u)
```
also sweep the structural smells the brain reviews for elsewhere: a datatype/helper defined in 2+
files (P31), free-function logic that should live on a type (P26), a recurring deterministic op done
by hand that should be a script (P19), a card that overlaps another (P29 orthogonality).

## 2. read the trace and let it drive (the knowledge trace, point of the log)
for every decided-AGAINST entry, ask: do the `--reject` reasons still hold?
- still hold -> the finding is "reinforce": strengthen the card/prompt wording so it isn't re-litigated.
- no longer hold -> the finding is "revise": the entry's `affects` pointer says exactly WHERE to change
  the card / graph link / flow / prompt. that precision is why the trace exists.
- genuinely unsure -> that becomes a QUESTION for arpad, not a silent edit.

### pruning the trace - ONLY here, and only by marking
this is the one session that may make the brain forget. an entry about an architecture the brain has
since left is read by every `--against` sweep from now on and costs judgement every time.
`--stale-candidates` narrows the trace to entries whose `affects` resolves to nothing; that is a
SHORTLIST TO READ, never a verdict. the tool cannot tell stale from elsewhere - `plans/01-scaffold.md`
is a live file in the repo that run happened in - so it tags each entry `this repo` / a repo name /
`unattributed`, and judging it is the work. an `unattributed` entry predates the `repo` field and can
only be judged by reading what it decided.

each prune is a FINDING for step 4, never a silent edit. only what he selects gets:
```bash
python3 $AAV_BRAIN/bin/brain-trace.py --prune <ts>   # marks stale; every reader skips it
```
the line stays on disk. `brain-learner` reverses it with `--restore <ts>` when a later run shows the
topic is live again, and a restore PINS the entry against any future prune. cards and docs have no
such staging - they are versioned, so git is their undo.

## 3. generate the questions - ASK THE BRAIN, do not hardcode them (point 7, the hard rule)
do NOT ship a fixed checklist. for each finding (and for the store as a whole), pull the cards it
touches with `python3 $AAV_BRAIN/bin/brain-recall.py "<finding>"` and ask, in context: "what would arpad ask
about this?" the recalled principles + tells generate the questions. examples the brain has produced
before (illustrative, NOT the list): "why does this artifact exist - is it consumed, or dead output?",
"should this be read instead of generated?", "is this its own principle or an expansion of an existing
one?", "is this path hardcoded?", "would i write this file this way?". the set is situational; derive
it every run.

## 4. present FINDINGS + QUESTIONS only (NOT implementation detail)
bring him a tight list. each item = the finding (what you noticed) + the question (what to decide) +
where it surfaced (script output / trace entry). do NOT bring a diff, a rewrite, or a plan - he hasn't
chosen yet, and pre-building biases the choice. use AskUserQuestion (or a numbered list he can mark
up): he selects which items are relevant and annotates each with a note. "other" + his note is always
valid. the brain proposes the questions; arpad owns the answers.

## 5. execute the selected edits, then log them
only AFTER he selects + annotates:
- for each chosen item, make the brain edit through the right skill (brain-meta-curate for cards/INDEX,
  brain-meta-style for prose/idiom, direct edits to flow.toml / bin scripts), honoring his note.
- rebuild what the edit touches. the gating is VERIFY's job now, not this skill's: emit `edited`
  and let the walk carry you into VERIFY (drift gates + `brain-lint.py`), STYLE, RECORD and CURATE.
- for each PRUNE he approved, mark it here. this is the only step that applies one, and a prune
  surfaced in step 2 but never run is a finding he approved and did not get:
  ```bash
  python3 $AAV_BRAIN/bin/brain-trace.py --prune '<ts>' --prune '<ts>'
  ```
- log each decision to the trace so the NEXT self-refine sees it:
  ```bash
  python3 $AAV_BRAIN/bin/brain-trace.py --skill brain-self-refine --decision '<what>' --chosen '<what won>' \
    --reject '<option>=<why>' --affects '<path>' --principle P29
  ```
  SINGLE-quote every value: a decision text carrying a backtick or `$(...)` is data, and a
  double-quoted shell argument evaluates it before the tool sees it.

## hard rules
- findings + questions to him, implementation after. never present a built solution as the question.
- questions are GENERATED from the brain each run, never a frozen list (else the brain stops learning).
- consent is explicit (P-curate): his selection is the go signal; an unselected finding is dropped, not
  quietly done anyway.
- the scan is scripted and the gates must pass; never hand-wave drift.

## output
the findings+questions list (step 4), then - after he chooses - STATE, not a changelog (P43): is it
done, and what is left. he reads the diff for what changed. name a blocker first if one is open, and
say which prunes were applied, since those are the one edit git does not show as a diff. lowercase,
terse.
