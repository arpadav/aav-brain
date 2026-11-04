---
name: principle-70-config-is-a-file-not-a-build
kind: principle
tier: conditional
rule: a tunable value lives in a config file shipped inside the artifact, read at run time, never compiled into the binary; changing it means editing that file (in a running container, or a two-line FROM image that replaces it), never a rebuild - and nothing is mounted to get it there.
interest: [intent-control, intent-efficiency]
confidence: high
evidence_count: 3
binds: [code]
tells: ["a rebuild for a config value change is absolutely crazy", "youre baking in config values? that shouldnt be how this works", "dont bake configs into the binary. if the configs are FILES inside the image, then thats LITERALLY what i want", "NOTHING is mounted. the docker image is self-contained"]
---

# P70 - config is a file, not a build

## rule
the binary holds behaviour; the numbers that tune it (thresholds, windows, gates, weights) are a file
inside the image it ships in, parsed at start. the image stays self-contained: no bind mount, no
volume, no env var standing in for the file. to change a value he either edits the file in a running
container and restarts it, or patches the image: `FROM <release>`, remove the old file, `COPY` the new
one. a constant in the source that a deployment might want to change is a defect, whatever its default.

## why
he tunes on the device ([[intent-control]]) and a C++ rebuild for one number is minutes lost per try
([[intent-efficiency]]). the heat came when a tracker threshold turned out to need a rebuild: "a
rebuild for a config value change is absolutely crazy... any other instances of this happening? please
catch them all before continuing." the answer he wanted was already half there - the manifest was a
file in the image - and the fix was moving the last C++ constants (the ID head's IoU gate and class
window) into its params.

## how to apply
- when a value is added, ask where a deployment changes it; if the answer is "recompile", move it to
  the config the artifact already ships, validated at load like its siblings.
- a correction like this is a class ([[principle-58-a-correction-is-a-class]]): sweep every constant
  of the same kind, not only the one he named.
- yields to: secrets and IP (MLflow ids, source paths) stay out of the shipped file; the shipped file
  holds what the runtime reads, nothing more ([[principle-61-private-infra-stays-out-of-tracked-files]]).

## verbatim tells
- "wait, this means rebuild? youre baking in config values? that shouldnt be how this works.... a rebuild for a config value change is absolutely crazy and shouldnt work like this... any other instances of this happenening? please catch them all before continuing. fix this asap" (2026-11-03, bytetrack thresholds)
- "if the settings are in a manifest file, then isnt that what i wanted originally? like you can just change those settings in the image? or do a simple FROM base remove old file CP new file?"
- "no what im saying is NOTHING is mounted. the docker image is self-contained. im saying, dont bake configs into the binary. if the configs are FILES inside the image, then thats LITERALLY what i want"

## anti-pattern
saying a config change needs a rebuild without checking whether the value is already a file (it was);
offering a bind-mounted config as the fix when he wants a self-contained image. both drew heat
([[principle-15-tone-is-signal]]).
