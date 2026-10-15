---
name: principle-25-deploy-infra
kind: principle
tier: narrow
rule: deploy the simplest way onto my own infra. worlds-simplest docker, expose on 0.0.0.0, LOCAL on my truenas and reached over my own network, axum for tiny services. no heavy orchestration, and no cloudflared tunnel.
interest: [intent-craft]
confidence: high
evidence_count: 120
tells: ["worlds simplest docker image", "0.0.0.0", "i host local", "truenas", "tailnet", "mount a volume", "expose it to 0.0.0.0", "axum", "docker"]
---

# P25 - deploy to my own infra, simply

## rule
i run my own infra and deploy the minimal way. the recurring shape (deploy/infra is ~10% of turns):
- the worlds-simplest docker image that just runs the binary, with a volume i mount.
- expose on `0.0.0.0` so its reachable; i dont fuss over the exact ssh/port dance ("i literally dont
  care, just expose it to 0.0.0.0").
- LOCAL. it runs on the truenas and i reach it on my own network, including my tailnet. do NOT put it
  on the internet under my domain, and do NOT reach for a cloudflared tunnel - ruled 2026-09-17:
  "drop this cloudflared shit. like EVERYWHERE thats documented is wrong. i host local".
- `axum` for tiny http services. custom 3-line cli over clap ([[principle-14-minimal-surface]]).
- no kubernetes, no heavy orchestration, no multi-stage cathedral - just the binary and a volume.

## why
its my infra and my time ([[intent-craft]]). the simplest thing that serves the file/runs the binary
is the right thing; orchestration is surface i dont need. minimal deploy is the same instinct as
minimal code ([[principle-14-minimal-surface]]).

## how to apply
- need to ship a service? worlds-simplest dockerfile, mount a volume, expose 0.0.0.0.
- reaching it from outside the house? the tailnet it already sits on, not a public tunnel.
- a service holding real data still needs a DOOR, and "local" does not answer who that door admits -
  a tunnel that used to carry the identity check takes the identity check with it when it goes. ask
  which door, dont assume the lan is the answer.
- a tiny service -> axum, custom cli, no framework ceremony.
- dont add logging/observability/infra i didnt ask for; add the one thing that lets me see hits if i
  ask ("more logging similar to python -m http.server so i can see hits").

## anti-pattern
a multi-stage docker cathedral for a single binary; kubernetes for a personal tool; fussing over ssh
port-forwarding when i said just expose 0.0.0.0; clap when a 3-line cli works.
