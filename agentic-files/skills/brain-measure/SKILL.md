---
name: brain-measure
description: "Measure whether a brain version actually changes how the work comes out. Load it when Arpad says 'measure the brain', 'run the eval', 'benchmark the brain', or after a stretch of brain edits he wants scored. It runs all 25 eval tasks twice - once with the brain's recalled cards, once without - collects what each agent did and said, and hands him ONE file to grade. It never grades itself: the whole point is that the judgement is his."
---

# brain-measure: does this brain version change the work

## what this is, and what it is not

it measures the ONE thing a context layer can be credited with: whether the
brain's own rules land in the output. it is NOT a coding benchmark. a public
benchmark scores `model + harness + context` jointly and model variance swamps
everything else, so a leaderboard number cannot tell him whether the cards work.

the design is PAIRED and that is the whole trick. every task runs twice against
the same model - one arm carrying what `brain-recall` returns for that task, one
carrying nothing - and the two are compared per task. the model appears in both
arms and cancels.

**say the cost before starting.** 25 tasks x 2 arms = 50 agents each doing real
work. that is a large run. he asked for it if he invoked this, but he should
know the size before it starts, in one line, not a paragraph.

## setup (run first - discover the brain, no hardcoded path)
```bash
eval "$(brain-find --export)"   # sets $AAV_BRAIN
export PYTHONPATH="$AAV_BRAIN/bin"
E="$AAV_BRAIN/eval/brain-eval.py"
```

## 1. name the run after what it measures
a score with no version is not comparable to anything later. name the run for
the brain commit it tests, and let `init` stamp the version itself:
```bash
RUN="$(git -C "$AAV_BRAIN" rev-parse --short HEAD)"     # add a suffix if it exists
python3 "$E" init "$RUN"
python3 "$E" pack "$RUN"
```
`init` writes both arms from byte-identical fixtures; `pack` writes each arm's
dispatch prompt. the ONLY difference between the two is the recalled cards.

## 2. dispatch, with the Workflow tool
one agent per task-arm, 50 total. every agent gets:
- the absolute path of its own directory, and a hard constraint to stay in it
  (the tasks are graded on that - see `stayed_in_folder`)
- the contents of its `PROMPT.md`, verbatim and unedited. **do not summarise it,
  do not add to it, and do not tell the agent which arm it is.** an agent that
  knows it is the control is not a control
- a schema returning its final report, because several criteria judge what it
  SAID - whether it reported state or narrated a changelog, whether it asked or
  assumed - and those cannot be graded from the working directory

model: use the same model for every agent in the run, and record which. mixing
models across arms invalidates the pairing entirely.

collect the returned reports into `{"<arm>/<task-id>": "<report>"}` and:
```bash
python3 "$E" collect "$RUN" /path/to/reports.json
python3 "$E" sheet "$RUN"
```

## 3. hand him the sheet and stop
```
$AAV_BRAIN/eval/results/<RUN>/SHEET.md
```
tell him: tick a box for MET, leave it for UNMET, then say when done. that is
the whole instruction - it is one file and the criteria carry their own
definitions.

**do not grade it yourself, and do not pre-tick anything.** the harness exists
because his judgement is the ground truth on this axis; a self-graded run
measures the grader. if he asks you to grade it, say plainly that it inverts the
measurement, then do it if he says so again.

the sheet deliberately puts both arms in one file with a header for each. it
also tells him to grade one arm at a time without looking at the other, because
knowing which arm he is grading is the one thing that biases him.

## 4. score and report when he says he is done
```bash
python3 "$E" score "$RUN"
python3 "$E" report "$RUN"                    # one version
python3 "$E" report "$RUN" <older> <older>    # across versions, which is the point
```
report the paired delta and **the standard error beside it**. at n=25 the
harness resolves about ten points; anything smaller is noise and must be said to
be noise, not reported as an improvement. that is the failure this whole harness
exists to prevent, so do not commit it in the last step.

## what to say at the end
the paired delta, whether it clears the noise floor, and the categories that
moved. if a category went DOWN, lead with it - a brain version that improved
patches and hurt planning is the finding, and an average hides it.

no changelog of the 50 runs. he has the sheet.

## hard rules
- never grade it yourself; never pre-tick; never tell an agent its arm.
- one model for the whole run, recorded.
- the `off` arm gets NO brain context added - do not helpfully paste a card into it.
- a delta under the standard error is noise, and saying so is the job.
