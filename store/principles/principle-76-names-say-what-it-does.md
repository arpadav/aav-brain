---
name: principle-76-names-say-what-it-does
kind: principle
tier: conditional
rule: every file, module, folder, type, service, unit and command is named so that someone who never opened it knows what it does from the name alone. no metaphors, no vague nouns, no names that need the code to decode them. a name is checked before it is built, in the plan, and every name in a tree that fails is renamed with all its references.
interest: [interest-comprehension, interest-craft]
confidence: high
evidence_count: 3
tells: ["wtf is \"door.py\" please have an actual name like prompt_router", "from reading prompt_router I can immediately tell what it is, whereas door.py I can't", "can you describe what the \"fence\" is? i dont like that term. it means nothing.", "this could really help with code organization and semantics, across languages and all"]
---

# P76 - a name says what the thing does

## rule
the name is the first line of documentation, and the only line most readers see: in a file tree,
an import, a stack trace, a unit list. so the name alone must tell a newcomer what the thing does.
- **the test:** read only the name. say in one plain sentence what the thing does. if that sentence
  needs the code, the name fails. `prompt_router.py` passes (it routes prompts). `door.py` fails:
  a door to what, doing what? the code turned out to be a proxy that picks the version, so it is
  `version_proxy.py`.
- **no metaphors.** `door`, `gate`, `fence`, `bridge`, `brain`, `engine` and `hub` each need the
  code to decode. a metaphor survives only when it is the field's own term and the reader already
  knows it (`router`, `proxy`, `queue`, `cache`).
- **no vague nouns.** `model`, `tools`, `utils`, `helpers`, `common`, `misc`, `manager`, `data`,
  `stuff`, `core` and `debug` say nothing about what is inside. in a relay that runs claude,
  `model.py` reads as the LLM, so it became `messages.py`.
- **no ambiguous twins.** two names a reader can mix up fail together: `stream.py` beside
  `live_stream.py` became `stream_json.py` and `live_stream.py`.
- **the name follows the job.** when the job changes, the name changes. "debug view" became the
  main page, so its stream is `live_stream`, not `debug`.
- **every language, every layer:** files, modules, packages, folders, classes, systemd units, CLI
  subcommands, routes, config keys and branches.

## orthogonality
[[principle-22-lexical-conventions]] owns the lexical micro-layer: casing, imports, bare prepositions
like `of`/`on`, leading underscores and constructor names. this principle owns the semantic layer:
whether a thing's name tells you its job. [[principle-27-organization-reorg]] decides where a thing
lives. this one decides what it is called once it lives there. the "name test" in
aav-semantic-architecture-reviewer applies this principle.

## why
he reads the tree long before the code. a name that needs decoding costs him a lookup every time he
sees it, and it costs every agent a read of the file just to learn what it is
([[interest-comprehension]]). a self-describing name also keeps the structure honest: if no honest
name fits, the thing is doing two jobs, which is a design finding, not a naming one ([[interest-craft]]).

## how to apply
- **plan time:** every new file, module, folder, type, unit and command in a plan gets its name
  checked against the test above before the plan is shown. the would-arpad fidelity questions
  ([[principle-29-interrogate-the-work]]) include "would he know what this does from its name?"
- **review time:** aav-semantic-architecture-reviewer READS this file and runs the test on every
  name in scope, not only the new ones.
- **fixing:** the `naming-audit` skill lists every failing name with 2-3 alternatives and a pick,
  then renames the file and every reference (imports, tests, docs, units, scripts) in one pass.
  the test suite proves nothing broke.
- **when no honest name fits:** report it as a split. the thing does two jobs.
- **worker prompts:** spell new names out in the prompt instead of leaving them to the worker. a
  worker left to invent names reaches for metaphors.

## anti-pattern
`door.py`, `gate.py`, `debug.py` (once it was the main page), `model.py` in an LLM project,
`tools.py` holding one function, `utils/`, `helpers.py`, a `fence` that needs a paragraph to explain.
also a rename that misses a reference, so an import, unit or doc still says the old name.

## verbatim tells
- "You remember what I said about file names and semantic architecture ? Like wtf is \"door.py\" please have an actual name like prompt_router (I'm not saying that's what door py is, but I'm saying from reading prompt_router I can immediately tell what it is, whereas door.py I can't)" (2026-11-14, signal relay blue/green)
- "can you describe what the \"fence\" is? i dont like that term. it means nothing." (2026-11-03)
- "The renaming thing, I think this can be super helpful ... I think this could really help with code organization and semantics, across languages and all" (2026-11-14)
