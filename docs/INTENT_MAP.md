# intent map: my positions -> my interests

> take prompts not literally. if i say "dispatch X reviewer for the code", that action isnt
> necessarily whats needed. its the intention behind it. the founding instruction of this brain.

## the frame (the name i was reaching for)
principled negotiation, from fisher & ury, "getting to yes" (harvard negotiation project, 1981). the
move: focus on interests, not positions.
- position: the concrete thing a party says they want ("dispatch the idiomatic-rust reviewer", "do
  NOT commit", "trim the fat").
- interest: the underlying need the position serves (security, control, leverage, trust, money,
  comprehension). people fight over positions but reconcile at the level of interests, because one
  interest can be met by many positions.
- BATNA: best alternative to a negotiated agreement, the walk-away power. my BATNA when an agent
  wont serve the interest is to interrupt and do it myself (49 recorded interruptions). serve the
  interest before i reach for the BATNA and the brain wins.

why this matters: obey positions literally and the brain is a brittle command-follower that breaks
the moment a position is slightly wrong for the situation. serve the interest and it can pick the
best position for the moment, even one i didnt name. the brain serves interests, not commands.

## the six interests (cards in brain/intents/)
| interest | one-line | card |
|---|---|---|
| CONTROL | stay the architect-in-the-loop; no surprises; power balance | [[../brain/intents/intent-control]] |
| TRUST | act only on whats real; no fabrication | [[../brain/intents/intent-trust]] |
| EFFICIENCY | leverage on my scarce attention; multiply, dont babysit | [[../brain/intents/intent-efficiency]] |
| CRAFT | uniform, idiomatic, minimal, durable code; low cognitive load | [[../brain/intents/intent-craft]] |
| COMPREHENSION | own the mental model; learn by concrete instance | [[../brain/intents/intent-comprehension]] |
| SOVEREIGNTY | control of the permanent, public, irreversible record | [[../brain/intents/intent-sovereignty]] |

## the mapping table (position -> atomic identity -> interest)
each row breaks a recurring position into its atomic identity (the literal action) and the interest
it serves. this is the "break it into atomic components, then assign an INTENT" decomposition.

| # | position (what i say) | atomic identity | interest | brains correct response |
|---|---|---|---|---|
| 1 | "dispatch the idiomatic-rust / semantic-architecture / code reviewer" | run a specific reviewer | TRUST + CRAFT | independent adversarial verification of correctness & architecture. the agent is a means; pick the right lenses, run them cold, converge |
| 2 | "do NOT assume, talk to me, ask under any ambiguity" | pause and ask | CONTROL + COMPREHENSION | keep the binding decisions mine; ask the smallest unblocking question; no fait accompli |
| 3 | "continue, dont pause, no summary, back to back" | execute without stopping | EFFICIENCY | once sanctioned, drive to completion; report only at gates and only what i cant see |
| 4 | "no bullshit, dont fake results, say how it is if slower" | report honestly | TRUST | ground every claim in real measurement; "unverified" is allowed, fabrication is not |
| 5 | "trim the fat, YAGNI out, net reduction of lines" but "verbose doc comments" | cut inline noise, keep docs rich | CRAFT | maximize signal/noise; docs are the durable interface, inline chatter is debt |
| 6 | "use rust style in rust, ts in ts; run aav-style" | apply house/idiom style | CRAFT | uniformity to cut review cost & cognitive load; style pass after correctness |
| 7 | "do NOT commit / i bump versions manually / i verify the messages" | hands off the record | SOVEREIGNTY | prepare the commit (stage, draft semantic messages, write the script); stop at the line |
| 8 | "reuse my existing types / why custom funcs not the suite / use criterion" | reuse the primitive | CRAFT (DRY) | grep for prior art first; extend, dont duplicate; distrust bespoke one-offs |
| 9 | "read ~/.cargo source / listen to the error / did you not read the error" | ground in primary source | TRUST | read the real error and real dependency source before proposing a fix |
| 10 | "show me an example struct / small verbose plan / i want to save the code" | give a concrete instance | COMPREHENSION | lead with a worked example; let me validate the abstraction against something real |
| 11 | "use context-mode / think in code / exclusively when searching" | keep context clean | EFFICIENCY | derive answers in the sandbox; never dump raw bytes into the window |
| 12 | "worlds simplest docker / no clap / just what is critical" | minimal surface | CRAFT | smallest correct thing; no speculative deps/abstractions |
| 13 | "make it faster / best/fastest api / raw % comparison" | optimize honestly | CRAFT + TRUST | fastest correct path, measured honestly; zero-cost abstractions |
| 14 | (heat) "you idiot / are you stupid? / just do what youre told" | express frustration | CONTROL + TRUST (a violated rule) | treat as a veto-level alarm: a hard rule broke; identify which, fix, encode it |
| 15 | (this review) "scripts i would write / not node / my voice" | tooling in my stack/voice | CRAFT + COMPREHENSION | rust/bash not node/mjs; my register in tooling/docs (P16). general agent brain, not claude-coupled (P17) |

## the apparent contradiction, resolved
rows 2 (ask first) and 3 (dont pause) look opposed. theyre the same interests (CONTROL of decisions,
EFFICIENCY of attention) in two phases:
- before the plan is sanctioned: ask. a cheap question prevents expensive rework and keeps the
  decision mine. CONTROL dominates.
- after the plan is sanctioned: execute through. pausing to narrate is pure tax. EFFICIENCY dominates.

the brains prime skill is detecting which side of the sanction boundary its on. that boundary is the
central transition in DEV_FLOWCHART.

## how the brain uses this map
1. a request arrives as a position.
2. the brain-meta-intent skill decomposes it into atomic identity + interest(s) using this table, and
   surfaces any ambiguity (CONTROL) before acting.
3. the brain-meta-author-prompt skill writes worker prompts that serve the interest, choosing the best
   positions for the moment, which may differ from the literal ask.
4. the brain-meta-style skill judges results against the interest, with the row-14 violation classes as
   hard vetoes.

sources: fisher & ury, "getting to yes". see PRIOR_ART for citations.
