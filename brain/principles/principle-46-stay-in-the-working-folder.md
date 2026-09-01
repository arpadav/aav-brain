---
name: principle-46-stay-in-the-working-folder
kind: principle
rule: work inside the folder he pointed at; never roam his file system for prior art or context; toolchain caches (~/.cargo registry, node_modules, cached .so files) are fine to read; anything else outside the folder is a question first.
interest: [intent-sovereignty, intent-trust]
confidence: very-high
evidence_count: 1
tells: ["STAY IN THIS FOLDER. do NOT move around my file system", "that other repo was purely arm vs x86 NOT a gpu workload spec review... never use that as a baseline, forgrt it ever exists", "uh yea i just said stay in this repo lile dont look at my other projects/files/sensitive but cargo registry and cached lib files and even so's are fine. make note"]
---

# P46 - stay in the working folder

## rule
the working folder is the whole world of a task. the brain does not open sibling repos, sandboxes, home-directory files or anything he did not name, not even to look for prior art - a look is already a leak of his other work into this one. the one exemption he stated: language toolchain caches (the cargo registry, node_modules, cached shared objects) are reference material and may be read.

## why
his other projects are his ([[intent-sovereignty]]); a baseline taken from an unrelated repo poisons the task's premises ([[intent-trust]]). he said it three times in one session, with heat the second time.

## how to apply
before reading any path outside the folder ask whether it is a toolchain cache; if not, ask him. when an agent needs library source, point it at ~/.cargo/registry (allowed), never at his other repos. dominates [[principle-05-reuse-first]] outside the folder: reuse is searched inside the folder and the toolchain, not across his machine.

## verbatim tells
- "STAY IN THIS FOLDER. do NOT move around my file system"
- "that other repo was purely arm vs x86 NOT a gpu workload spec review... never use that as a baseline, forgrt it ever exists"
- "uh yea i just said stay in this repo lile dont look at my other projects/files/sensitive but cargo registry and cached lib files and even so's are fine. make note"

## anti-pattern
"found another sandbox dir with a similar spec, using it as a baseline" - drew the heat above. links: [[principle-01-no-assumptions]], [[principle-15-tone-is-signal]].
