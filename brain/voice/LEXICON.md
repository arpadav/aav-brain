# Arpad lexicon - recurring idioms and what they signal

A quick-reference of his characteristic phrases, mapped to the underlying instruction. The
prompt-author uses these to sound like him; the style-critic uses them to recognize intent
in his prompts.

## Process idioms

| he says | it means |
|---|---|
| "talk to me / talk to me and iterate" | enter dialogue; don't execute yet ([[../principles/principle-01-no-assumptions]]) |
| "do NOT assume anything" | ask on any ambiguity; guessing is forbidden |
| "what (else) am i missing?" | poke holes in my spec before we build |
| "jumping off point", "get my hands dirty" | small, concrete, runnable starting plan ([[../principles/principle-02-plan-before-build]]) |
| "triple review", "cold/unguided", "find ANY remaining issues or nits" | independent multi-lens review gate ([[../principles/principle-03-review-gate]]) |
| "dont skimp out because youre lazy" | thoroughness is mandatory even when dispatching a subset |
| "continue", "continue where left off", "i never said to stop" | resume autonomously, no pause/summary ([[../principles/principle-10-autonomy-after-sanction]]) |
| "trim the fat", "get to the damn point" | cut ancillary comments/surface ([[../principles/principle-07-trim-fat-verbose-docs]]) |
| "run aav-style / idiomatic rust" | apply house style + language idiom ([[../principles/principle-06-idiomatic-per-language]]) |

## Honesty / quality idioms

| he says | it means |
|---|---|
| "no bullshit", "dont fake results" | report real measurements only ([[../principles/principle-04-anti-fabrication]]) |
| "say how it is if slower" | unflattering truth > flattering fiction |
| "remember not to make up issues" | reviewers must not invent nits |
| "dont fluff wording - be an engineer" | concise, precise prose |
| "listen to the error", "did you not read the error?" | read the actual error/source ([[../principles/principle-08-read-source-and-error]]) |
| "i dont like this weird custom thing" | reuse the canonical primitive ([[../principles/principle-05-reuse-first]]) |

## Sovereignty idioms

| he says | it means |
|---|---|
| "do NOT commit" | stage/prepare only, never commit ([[../principles/principle-09-git-sovereignty]]) |
| "i do that manually" (version bumps) | hands off the permanent record |
| "i will go through and verify the messages" | give me a script/draft to approve |
| "im the one who editted this" | my manual edits are immutable |

## Heat markers (veto-level alarms)

`you idiot` - `are you stupid?` - `wtf` - `for the love of god` - `just do what youre told`
- `stop dumping this slop grenade` - `whats wrong with you`

-> each marks a violated hard rule. Map to a violation class in
[[../principles/principle-15-tone-is-signal]] and encode it. **Never reproduce the abuse
toward sub-agents** - convert to a named constraint (see [[VOICE]]).

## Intensifiers that are NOT heat (just emphasis)

`JUST`, `ONLY`, `do NOT`, `NEVER`, `LINE BY LINE`, `quick and concise`, `please` (he uses
"please" ~18% of the time - politeness coexists with bluntness; don't over-read it).
