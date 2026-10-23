---
name: brain-edit
description: "A small follow-up change to work a previous run already planned and built - without restarting the plan. Load this when he says 'just change X', 'one more thing', 'tweak that', 'add a small', 'follow up on that', or asks for an edit right after a brain-execute run. A user ENTRY skill: it reconstructs what the last run built, asks him ONCE how much checking the edit warrants, enters the flow at EDIT (regime execute-through), and hands the walk to brain-meta-drive. It is NOT a plan - if the ask needs phases, it hands off to brain-plan instead."
---

# brain-edit: a small change, still inside the brain

the gap this fills is measured, not theoretical. after a build there are two bad options and he was
taking both: talk to the agent directly and it goes rogue - no recall, no style gate, no trace entry,
nothing learned - or re-run `brain-execute` and sit through plan -> sanction -> impl -> cold gate ->
style for a two-line change. brain-edit is the third door: the same rails, minus the planning.

it does NOT walk the flow by hand - the walk is `brain-meta-drive`'s job. this entry reconstructs
where the last run left off, sets the start node and the regime, and gets out of the way.

## setup (run first - discover the brain, no hardcoded path)
```bash
eval "$(brain-find --export)"   # sets $AAV_BRAIN
```
read `$AAV_BRAIN/brain/CONSTITUTION.md`.

## 1. reconstruct - what did the last run build? (the engine reconstructs NOTHING)
an edit with no memory of the build it follows is exactly the rogue turn this skill exists to
replace. read, in this order, and stop as soon as the picture is sufficient:
```bash
git -C . log --oneline -15                      # what landed, most recent first
git -C . status --short && git -C . diff --stat  # what is still uncommitted
ls plans/ 2>/dev/null                            # the plan the last build followed, if this repo has one
python3 $AAV_BRAIN/bin/store/brain-trace.py --against | grep -A2 "$(basename "$PWD")" | head -40  # what that run DECIDED
```
the trace is the part that is easy to skip and expensive to lose: it names the forks the last run
already resolved. **an edit that reverses one of them without saying so is the failure mode.** if his
ask contradicts a logged decision, say which one, in one line, before you touch anything - he may be
deliberately reversing it, and then it gets a `--supersedes` entry rather than a silent flip.

if this session already ran brain-plan / brain-execute / brain-edit, that transcript IS the
reconstruction and the commands above are confirmation, not discovery.

## 2. is this actually a plan? (the honest escape hatch)
brain-edit is for a change to something that ALREADY EXISTS. it is the wrong door when the ask needs
phases, introduces a new module or type, or has a worked example worth tracing before it is built.
say so plainly in one line and load `brain-plan` instead - do not quietly grow an edit into a build.
the tell is not line count, it is whether you can name the finished state without designing it first.

## 3. ask him ONE question: how much checking does this edit warrant?
the rigor dial is HIS and it is asked BEFORE the edit, never inferred from how small the change looks
(P41 - rigor is set by what the artifact is FOR, and you cannot read that off the diff). one question,
plain english, whole shapes not parameters, with the middle one recommended (P42):

| what he picks | the event you emit | what he gets |
|---|---|---|
| build + test it, then report | `edited` | VERIFY runs the real build/test. **the default** - recommend this |
| review it properly first | `gated` | PHASEGATE puts a cold reviewer on the diff, then VERIFY |
| just do it | `unchecked` | straight to STYLE - no build, no test, no reviewer |

ask it once, in his words, not as flag names. all three still ride `STYLE -> RECORD -> CURATE`, so
whichever he picks the brain still learns from the edit - that is the whole point of the third door.

## 4. set the entry
- `$STATE` = `EDIT`.
- `$REGIME` = `execute-through` - the work being edited was already sanctioned, so this does not
  re-ask for permission to proceed. post-sanction rules apply: a decision he'd want = ask; mechanical
  detail = proceed.
- `$MODE` = `edit`. this is not cosmetic: `VERIFY --more_phases--> DOCTRINE`
  is guarded `build`, so a `build` walk would let a two-line edit be sent back for a phase that does
  not exist, and `EDIT --unchecked--> STYLE` is guarded `edit`, so the skip-verification dial only
  exists when you pass it.

handoff: with `$STATE`/`$REGIME` set and `$MODE` = `edit`, call `Skill(brain-meta-drive)` and run `python3 $AAV_BRAIN/bin/run/brain-walk.py --state "$STATE" --mode edit` (paste the output) - the handoff contract lives in brain-meta-drive.

## 5. log the edit to the trace
an edit that leaves no trace entry is invisible to the next brain-edit and to the next self-refine,
which is how a small change becomes a decision nobody can find later:
```bash
python3 $AAV_BRAIN/bin/store/brain-trace.py --skill brain-edit \
  --decision 'what he asked for' --chosen 'what you did' --affects 'path/to/file'
```
SINGLE-quote every value. his ask routinely contains backticks, `$(...)`, `!` and quotes, and in a
double-quoted argument the shell expands them before the tool ever sees the string - a decision text
is data, never something to evaluate. set `--confidence` to what the call actually warrants; leaving
it at the default `medium` is fine and is what makes `--low-confidence` mean something. add
`--supersedes <ts>` when the edit reverses a decision step 1 surfaced.

## stops
a transition to a `blocked`/ASK state is the only sanctioned pause. post-sanction, never assume - a
decision he'd want = ask; mechanical detail = proceed.

## reporting
STATE, not a changelog (P43): is it done, what is left. he reads the diff for the rest. lowercase,
terse, ends on the next action.

## hard rules
never grow an edit into a build without saying so. never reverse a logged decision silently. never
commit/push unless told. never trample his manual edits.
