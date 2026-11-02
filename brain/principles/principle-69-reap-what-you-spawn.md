---
name: principle-69-reap-what-you-spawn
kind: principle
tier: conditional
rule: every process the run starts - a background shell, a dev server, a build, a watcher, a test loop - is the run's to stop. kill each one the moment its output is in hand or it is superseded, keep only as many heavy jobs alive as the machine can carry, and leave nothing running at the end that he did not ask to keep.
interest: [intent-efficiency, intent-control]
confidence: high
evidence_count: 40
tells: ["if the others are leftover, why havent you killed them?", "everytime ive said continue, my laptop breaks. no network connections, no display, no nothing", "just kill it man, unless there is nothing else to do. it keeps waiting on a build", "and now there are 4 shells not 3", "make note of disk incident, to auto clean"]
---

# P69 - reap what you spawn

## rule
a process the run started is the run's to stop. kill it the moment its output is in hand, or the
moment a newer one supersedes it - a rebuild replaces the build still waiting, it does not join it. keep
the number of heavy jobs (builds, test suites, model runs, servers) to what the machine carries, and at
the end nothing the run started is still alive unless he asked to keep it, by name.

## why
the machine is his, and a session that leaves shells behind spends it without asking
([[intent-control]]). it happens by accumulation: each background job is cheap when it is started and
nobody counts the ones already running. the corpus records it rising - about 40 complaints from
2026-07 to 2026-10, monthly 1 / 8 / 11 / 19 - ending in a laptop that lost network, display and power
indicators twice in a day: *"everytime ive said continue, my laptop breaks"*. a `sh -c while :` storm,
a tmux session killed by OOM and a full disk all trace to work nobody stopped. and every leftover is a
question he has to ask instead of work he gets ([[intent-efficiency]]): *"and now there are 4 shells
not 3. if the others are leftover, why havent you killed them?"*

## how to apply
- **track what you start.** keep the id of every background shell, server or agent you launch; before
  launching another of the same kind, check what is already running and stop the one it replaces.
- **done with the output -> stop the process.** a dev server started to take one screenshot is stopped
  after the screenshot. a build that is waiting on a lock another build holds is killed, not queued.
- **budget the heavy ones.** compilers, test suites, docker builds and model runs in parallel multiply
  memory, not just CPU. run them one or two at a time unless the machine has clearly got room, and
  look (`free`, `df`, the process list) before starting a third.
- **resuming after an interruption checks first.** "continue" begins with a look at what the previous
  turn left running, and stops anything orphaned before starting anything new
  ([[principle-64-resume-after-interruption-verifies-then-redispatches]]).
- **the close-out sweep includes processes** - the end-of-run cleanup in
  [[principle-56-close-out-housekeeping]] reaps them alongside worktrees and scratch files, and names in
  one line anything deliberately left running.
- disk is the same resource on a slower clock: build caches, docker images and scratch output the run
  made are cleaned at the close, not left for the next incident.

## orthogonality
[[principle-56-close-out-housekeeping]] is the sweep of files and records at the end of a run; P69 is
the live budget of processes during it, which is where the damage happens - a laptop that has
already hung never reaches the close-out. [[principle-52-parallel-dispatch]] decides what may run
concurrently; P69 decides how long each thing it started gets to live.

## anti-pattern
starting a fresh build while the last one still waits, so two compile the same crate; leaving a dev
server, a `watch` loop and three idle shells behind when reporting "done"; answering "why is my laptop
slow" with a guess before listing what this session launched.
