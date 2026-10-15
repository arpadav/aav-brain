---
name: principle-60-device-facing-code-is-gated-by-a-live-run
kind: principle
tier: conditional
rule: code whose job is to act on a real device, host or bucket is not done when mocked tests pass; it is done when the agent has run his real command against the real target and read the result. tests stay local and never perform a real remote deployment.
interest: [intent-trust, intent-craft]
confidence: medium
evidence_count: 3
tells: ["i want commands tried and executed", "i want `HAVOC_BALENA_CLI=~/Downloads/balena/bin/balena uv run hml deploy --output s3://havoc-dev-triton-zoo/.output/migrations/tmp --via balena --device $BALENA_DEVICE_1` with BALENA_DEVICE_{1,2,3,4} tried (sometimes some arent available)", "i want <lan ssh host> ssh tried", "i dont want tests to try straight up remote deployment like this", "learn from this comment", "correctness run on a device. The live runs found every real bug today", "wheel size ? and confirmation that an independent docker container (with trt) can run hml deploy ? id like to see that"]
tension: [principle-03-review-gate]
---

# P60 - device-facing code is gated by a live run

## rule
the proof that a deploy tool works is the deploy, run for real. a green suite against fakes proves the fakes. he
pasted a post-mortem and told the next run to learn from it: about 2,500 tests passed while the day's real bug
(`--fp16` on TensorRT 11) went straight through, because no test ran against a TensorRT 11 device - the live runs
found every real bug, the review rounds mostly added findings.

## why
[[intent-trust]]: a claim about hardware is only evidence once the hardware has answered ([[principle-04-anti-fabrication]]).
[[intent-craft]]: tests that deploy to real machines are slow, flaky and unsafe to run casually, so the real run
belongs to the agent at the gate, once, deliberately - and the suite stays cheap and local.

## how to apply
- run HIS literal command, as he wrote it, against each target he lists (balena devices 1-4, the ssh host, local
  docker). he says some are not always available: try each, report which worked and which refused and why, never
  paper over a missing one.
- the live run is the phase gate for the device layer. the cold review still runs on the diff, but a climbing
  finding count stops and the live run decides ([[principle-03-review-gate]], bound the loop; [[principle-51-spaghetti-is-a-design-fault]]).
- the real host he names is for the run, not for the repo: fixtures and docs written from the run use a
  placeholder ([[principle-61-private-infra-stays-out-of-tracked-files]]).
- tests: fakes at the process boundary, a small budget, no test shells out to a real device or bucket.
- a live run is the pipeline end to end, not an inspection of the machine: nothing is run on a device that is not
  a step of the tool under test, and no destructive action (these were production vessels, per his own stop on
  2026-09-30: "i dont want any sort of destructive action done on the devices").
- verification keeps the failure channel visible ([[principle-36-verify-with-stderr-visible]]); a live failure goes
  into the report verbatim.
- a portability claim is shown, not asserted: "runs without torch / installs on its own" is proven by installing it
  in the real target environment (the runner's own base image, `--gpus all`, read-only mounts) and showing him the
  output - "confirmation that an independent docker container (with trt) can run hml deploy? id like to see that".
  state up front which step will stop and why when a later phase owns it.

## anti-pattern
declaring a transport done on 2,500 passing tests; a test that SSHes somewhere; running a hand-rewritten
"equivalent" command instead of his; hiding an unavailable device behind a mock and calling it covered.
