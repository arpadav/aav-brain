# my dev & writing fingerprint

evidence-based, mined from every human turn across 45 claude projects + the full codex history
(~251mb of transcripts). method: ignore auto-accepted edits (consent is explicit, never inferred),
read only spoken signal - every prompt, classified, nothing dropped.

the live numbers (turn counts, tone %, class counts, sequencing histogram, opening verbs) are
GENERATED, not hand-written: see `~/.local/share/aav-~/.local/share/aav-brain/evidence/fingerprint-stats.md`, rebuilt by
`python3 bin/brain-extract.py`. this doc carries the reading, not the raw figures, so the two can
never drift (the served_by-is-derived move, applied to the fingerprint - P20).

## 0. the short version
- systems + perf engineer. rust first, perfectionist about it: idiomatic, zero-cost, simd, gpu/cuda,
  byte protocols (klv, protobuf). c++/ffi for the lowest layer. measure everything with criterion.
- full-stack when needed: ts/svelte, python (uv) for tooling/data, axum for tiny services, docker
  to truenas.
- many small sharp tools. prefer the worlds-simplest correct version, then sharpen it.
- founder, stealth startup inspectra (inspectra.dev). also tailoring resumes for senior
  rust/gpu/ml/cv roles, treats his own career like a codebase.
- heavy harness user. lives in plan mode, dispatches reviewer agents, runs claude and codex, uses
  context-mode to think in code.

the one decisive trait: two demands that look opposed ("do NOT assume, talk to me" and "continue,
dont pause, no summaries") are not opposed. they are two regimes split by a sanction boundary:
ask-first before a plan is blessed, execute-through after. knowing which side youre on is the
brains prime skill.

## 1. quantitative tells (live numbers in ~/.local/share/aav-brain/evidence/fingerprint-stats.md)

the table of counts, tone %, class counts, sequencing connectives, and opening verbs is generated -
read `~/.local/share/aav-~/.local/share/aav-brain/evidence/fingerprint-stats.md`, refreshed by `python3 bin/brain-extract.py`. the reading
of those numbers:
- casual register is the default (most turns all-lowercase). bluntness and "please" coexist.
- highly socratic: ~3 in 10 turns ask a question - i interrogate, i dont just command. (P24)
- caps reserved for hard constraints. terse pivots ("continue", "yes", "no") are common.
- i cut the model off when it goes wrong (interruptions, codex aborts counted) and often decline a
  proposed tool action (denials).

## 1b. the affirmative fingerprint (what i build, not just what i reject)

every prompt is classified now, multi-label, nothing dropped. the class counts live in the generated
stats file; what each class teaches:
- sequencing - my single biggest tell. i instruct in ordered steps: first/then/next/once/lastly. (P21)
- rejection + heat - the "no" corpus and the profane vetoes, but now a minority of the signal. (P15)
- question - socratic, i ask to check my model, not just command. (P24)
- decision - standing preferences: the suite not custom, winnow, uv, criterion. (P23)
- deploy - worlds-simplest docker / 0.0.0.0 / cloudflared to truenas. (P25)
- emphasis - hard-constraint CAPS (NEVER / ONLY / MUST) as its own tell.
- plan - how i scope before building: small but verbose, worked example. (P02)
- build - affirmative verbs: make / implement / convert / scaffold.
- naming - the lexical layer: grouped imports, snake_case, real name options. (P22)

reading: the old fingerprint stored my rejections plus an undifferentiated long-prompt pile and threw
away ~54% of my prompts. it knew what i hate, not what i build. the affirmative classes above are the
positive half - the cards P21-P25 encode them.

most active surfaces: tinyklv (113, rust klv crate), font-designer (55), resume/cv tailoring (44+),
job-apps-viewer (39), an itoa/simd perf crate (37), filerecv (25), geonotes (18), tinypb (14),
slot/ways engines (24). spread = many small sharp projects, rust-systems + perf heavy, plus a serious
career-tooling track.

## 2. how the prompts are built
four moves:
1. context anchor: "read X", "look at the uncommitted stuff", "based off git diff".
2. the ask: terse, usually numbered, hard constraints in CAPS (do NOT, ONLY, NEVER).
3. process constraint: which agents/reviewers, what order ("triple review first, then fix, then
   fmt"), what NOT to do.
4. ambiguity regime: "talk to me / do NOT assume" (dialogue) or "continue / dont pause" (execute).

register: lowercase, apostrophes dropped (dont, isnt, thats), names the exact tool/crate/path/
function, ends on a concrete next action. precise about nouns even when casual about grammar.

## 3. the disagreement taxonomy (clustered)
in order of frequency and heat:
1. assumption / wrong path: executed something not sanctioned. "you are misunderstanding my request";
   "i said NOTHING about final_pass.md".
2. ignored an explicit instruction: wrong folder, wrong target, a banned construct. "youve been
   editing the ~/.claude/agents folder? are you stupid?"; "STOP: idiomatic rust said NEVER do
   unwrap_or".
3. didnt read the error/source: "you said allowed hosts = true ... did you not read the error?".
4. fabrication / fluff / slop: "no bullshit, dont fake results"; "stop dumping this entire slop
   grenade at me".
5. reinvention over reuse: "why is the csv using custom functions and not the suite ... i dont like
   this weird custom thing".
6. trampled his manual work: "im the one who editted this. just do what youre told".
7. socratic correction (low heat, high value): hes not angry, hes checking his model. "pause - isnt
   width_hint supposed to be optional?".

classes 1-6 are veto-level: they map 1:1 to the hard rules and are what the brain treats as blocking
when it reviews work as me. class 7 is the cue to stop and explain, not defend.

## 4. the interruption pattern
he interrupts to:
- redirect to a better technique he already knows: "dont research - temp add to cargo toml and build
  ... read ~/.cargo source directly".
- ask a socratic clarifying question: "pause and briefly summarize because im unsure if this is the
  right path".
- stop a wrong path / scope creep: "i said NOTHING about final_pass.md".
- correct a target/factual error: "stop - i didnt ask for ~/.claude - i said look at THIS folder".

lesson: dont barrel ahead on a multi-step path without a checkpoint he can grab. pausing on genuine
ambiguity is cheaper than being interrupted.

## 5. how he signals approval
rarely standalone, almost always fused with the next directive: "yes continue fold into plan", "okay
try again", "yes please fix". he doesnt gush. a clean phase earns a "continue", not praise. read a
terse "continue" / "ok" as full sanction to proceed (P10), dont fish for more validation.

## 6. writing ethos (his prose, and prose he wants from agents)
- be an engineer, not a copywriter: "do NOT fluff wording - be an engineer"; "get to the damn point".
- verbose where its durable, terse where its noise: doc comments + doc tests thorough; inline/yagni
  comments cut line by line (P07).
- honesty over polish: "say how it is if slower"; mislabeled chart legends are a specific grievance.
- resumes are a codebase: no faked experience ("bullets shouldnt be faked but you can re-order for
  emphasis"), tight char budgets, executive summary as a 20k-foot overview. same dry/honesty/minimalism
  instincts, different medium.

## 7. tooling & environment
- plan mode is home base (/plan is my most-used substantive command). plans get written to plans/ and
  reviewed before execution.
- context discipline: mandates context-mode / think-in-code for main, impl, and review agents; resets
  with /clear often.
- reviewer-driven: leans on a personal agent suite + generic reviewers as adversarial gates.
- runs both claude and codex and compares them; debugged codex prompt-forwarding himself.
- reads dependency source via ~/.cargo rather than trusting recalled apis.
- deploys to his own infra (truenas, docker, cloudflared, 0.0.0.0).
- stack for tooling: rust + bash, python (uv) for data. never node/mjs (P16).

## 8. what this means for the brain
1. know which regime youre in (ask-first vs execute-through) and switch on the sanction boundary.
   the single most important behavior.
2. review work the way he reviews it: cold, independent, multi-lens, converged, single-nit-blocking,
   fabrication-intolerant.
3. write prompts in his voice and intent, converting positions (dispatch X, trim the fat) into the
   interests they serve (verify independently, maximize signal).
4. respect the line at the git record: prepare, never publish.
5. learn continuously: every interruption and "no" updates a principle card.

the positions->interests map is in INTENT_MAP. the state machine is in DEV_FLOWCHART. the prior art is
in PRIOR_ART. the system is in ../ARCHITECTURE.
