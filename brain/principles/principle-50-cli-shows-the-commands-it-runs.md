---
name: principle-50-cli-shows-the-commands-it-runs
kind: principle
rule: a tool that acts on machines (devices, hosts, buckets, docker) says up front what it resolved, lists the exact commands it will run, asks once, then prints `Running: <cmd>` before each - every printed line re-runnable as is.
interest: [intent-comprehension, intent-control, intent-trust]
confidence: medium
evidence_count: 4
binds: [code]
tells: ["i really want whatever language you use to use the following type of output, where its strictly reproducable, says what commands are being run, etc etc. construct the command, guide the user, etc etc", "the output logs are all misaligned", "i need some trt commands I CAN run directly and immediuately because id like to screen record them. like give me various flavors", "i want 1. examples to be in individual blocks, and say 'more examples in deploy.md'", "see @commands-to-run.sh can you make this where it displays all commands and i choose one to execute? like 1-9a-z selection"]
---

# P50 - a cli shows the commands it runs

## rule
his reference is `docker-build-from-scratch.sh`: resolve inputs, print a "please review" block (keys aligned
to one column), print "this will run the following commands..." as a numbered list, confirm (skippable with
`-y`/`--force`), then `Running: <cmd>` before each command, with the command's own output under it. a failure
names the exact command, its tail, and the one line that fixes it. no `[tag    ]` log prefixes, no prose the
operator cannot paste.

## why
[[intent-comprehension]]: he learns a tool by seeing the concrete commands, not a narrative about them.
[[intent-control]]: nothing touches a device or bucket before he has seen the list.
[[intent-trust]]: a printed command that ran is evidence; a log line describing an action is a claim.

## how to apply
- argv, shown with `shlex.join`; the remote side of ssh gets one joined string; stdin files rendered to disk
  first, so `cmd < file` is real.
- secrets (signed urls) live in 0600 files the printed line points at, never in the printed line.
- the same standard binds what the tool's author hands him to demo or document (2026-10-01): commands he can run
  directly and immediately, one flavor per command ("give me various flavors" - refusal, picker, local, one onnx,
  precision override, ssh, balena), with the env they need exported once above them; examples in individual
  blocks, each pasteable alone, with a pointer ("more examples in deploy.md") instead of a wall. the shape he
  built from such a list was a menu of every command with a 1-9a-z key to run one.
- dominates any "pretty logging" urge; yields to [[principle-14-minimal-surface]] on how many lines a block takes.

## anti-pattern
the old `hml deploy`: ragged `[param  ]`/`[fetch  ]` columns, a 300-char paragraph as the last line, a failure
reported as "answered without the frame" instead of ssh's own `Permission denied (publickey)`.
