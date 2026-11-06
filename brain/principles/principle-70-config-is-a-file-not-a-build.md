---
name: principle-70-config-is-a-file-not-a-build
kind: principle
tier: conditional
rule: a tunable value is never compiled into the binary; everything editable or configurable lives in ONE runtime_config.yaml that compose ALWAYS mounts (edit, restart, no rebuild), and everything fixed (what the model/build determines and the runtime reads) is baked into the image with a static human-readable copy in a manifest/ folder marked don't-edit.
interest: [intent-control, intent-efficiency]
confidence: high
evidence_count: 4
binds: [code]
tells: ["a rebuild for a config value change is absolutely crazy", "youre baking in config values? that shouldnt be how this works", "dont bake configs into the binary. if the configs are FILES inside the image, then thats LITERALLY what i want", "NOTHING is mounted. the docker image is self-contained" (2026-11-03, superseded 2026-11-04)", "everything fixed, goes to manifest. everything editable and configurable, goes into runtime_config.yaml. thats it"]
---

# P70 - config is a file, not a build

## rule
the binary holds behaviour; the numbers that tune it (thresholds, windows, gates, weights) are data.
two homes, split by who may change them:
- editable / configurable: ONE `runtime_config.yaml`, always bind-mounted by compose, never baked. the
  operator edits it and restarts; no rebuild, no image patch.
- fixed (determined by the model or build, and read by the runtime - labels, class lists, model
  identity): baked into the image, with a static human-readable copy in a `manifest/` folder whose
  README says don't edit (editing is harmless anyway, the image carries its own).
the test for a value is "may the operator change it?", not "does ATR read it?". a constant in the
source that a deployment might want to change is a defect, whatever its default.

## history
2026-11-03 (superseded, not wrong then): config was a file inside a self-contained image, nothing
mounted, changed by editing in the container or a `FROM <release>` patch. 2026-11-04 he reversed the
mount half: "can we merge the runtime config and the manifest into ONE file, which is ALWAYS mounted
on compose and not baked in?", then refined it to the editable/fixed split above. what survives: no
rebuild for a config value, no constants in the binary.

## why
he tunes on the device ([[intent-control]]) and a C++ rebuild for one number is minutes lost per try
([[intent-efficiency]]). the heat came when a tracker threshold turned out to need a rebuild: "a
rebuild for a config value change is absolutely crazy... any other instances of this happening? please
catch them all before continuing." the 11-03 answer was a file in the image;
on 11-04 he moved the editable part to a mounted file and the fix was moving the last C++ constants (the ID head's IoU gate and class
window) into its params.

## how to apply
- when a value is added, ask who may change it: operator -> runtime_config.yaml (mounted); fixed by
  the model/build -> manifest (baked, don't-edit copy). "recompile" is never the answer.
- when he asks a premise question ("the class stuff is just for tracking, right?"), answer it plainly
  first - here the premise was false, ATR reads labels at runtime, which is why they are baked
  ([[principle-24-the-ask-is-the-scope]]).
- a correction like this is a class ([[principle-58-a-correction-is-a-class]]): sweep every constant
  of the same kind, not only the one he named.
- yields to: secrets and IP (MLflow ids, source paths) stay out of the shipped file; the shipped file
  holds what the runtime reads, nothing more ([[principle-61-private-infra-stays-out-of-tracked-files]]).

## verbatim tells
- "wait, this means rebuild? youre baking in config values? that shouldnt be how this works.... a rebuild for a config value change is absolutely crazy and shouldnt work like this... any other instances of this happenening? please catch them all before continuing. fix this asap" (2026-11-03, bytetrack thresholds)
- "if the settings are in a manifest file, then isnt that what i wanted originally? like you can just change those settings in the image? or do a simple FROM base remove old file CP new file?"
- "can we merge the runtime config and the manifest into ONE file, which is ALWAYS mounted on compose and not baked in? and then inside this, we can say 'do not edit' for sections like the labels" (2026-11-04)
- "if ATR uses it at runtime, then bake that into the model, and then say 'dont edit, but these are baked into image so editing doesnt matter either'" (2026-11-04)
- "ok listen. everything fixed, goes to manifest. everything editable and configurable, goes into runtime_config.yaml. thats it" (2026-11-04)
- "no what im saying is NOTHING is mounted. the docker image is self-contained. im saying, dont bake configs into the binary. if the configs are FILES inside the image, then thats LITERALLY what i want" (2026-11-03, superseded on the mount)

## anti-pattern
saying a config change needs a rebuild without checking whether the value is already a file (it was);
mixing the two homes: fixed model facts in the editable file, or tunables baked where the operator cannot reach them; and (11-03 only) offering a mount, now the correct answer. the first drew heat
([[principle-15-tone-is-signal]]).
