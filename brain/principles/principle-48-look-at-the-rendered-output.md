---
name: principle-48-look-at-the-rendered-output
kind: principle
rule: a pdf, chart, page or app is not done until its rendered output has been looked at - rasterise / screenshot and read it - and a programmatic audit of the things an eye misses (chart kind vs caption, embed width, label density, overfull lines, table overflow) sits in the build gate.
interest: [intent-craft, intent-trust]
confidence: very-high
evidence_count: 1
binds: [code]
tells: ["ok, and for the paper + charts, some stuff is very wrong. you should read the python chart outputs and even take screenshots to see what is wrong", "so please be hyper aware of these issues going forward, and talk to appropriate agents if they are working on them to bring these up", "but even a programmatic one, like looking through the tex and how the charts are embedded... some charts which are clearly not meant to be line graphs (like the intention was some surface?)... so look at chart types too and confirm", "this is visually so confusing. middle is a blank screen, no styling"]
---

# P48 - look at the rendered output

## rule
green checks are not a pass. a build that compiles, a test suite that is green and a chart that is written to disk can still be visibly wrong: an empty panel, a hairball, hundreds of labels, a surface drawn as lines, a table off the page, a blank page for one sentence. before an artifact is called done, its rendered form is rasterised or screenshotted and READ, page by page, shot by shot - by the worker that made it and by the coordinator that accepts it - and the classes an eye misses are audited by script in the gate.

## why
he judges the artifact, not the log ([[intent-craft]]); a visibly broken deliverable behind a green gate is the fabrication he warns about ([[intent-trust]]).

## how to apply
every worker that produces a visual pastes a one-line reading per page/shot; the coordinator reads a sample itself; the gate scripts fail closed on: chart kind against the plan's, embed width floors, legend and text-object caps, minimum type size at the embedded scale, overfull boxes, hand-typed digits. for an app: screenshots at the real viewports, and the ink box of the stage measured. links: [[principle-04-anti-fabrication]], [[principle-03-review-gate]].

## verbatim tells
- "ok, and for the paper + charts, some stuff is very wrong. you should read the python chart outputs and even take screenshots to see what is wrong"
- "so please be hyper aware of these issues going forward, and talk to appropriate agents if they are working on them to bring these up"
- "but even a programmatic one, like looking through the tex and how the charts are embedded... some charts which are clearly not meant to be line graphs (like the intention was some surface?)... so look at chart types too and confirm"
- "this is visually so confusing. middle is a blank screen, no styling"

## anti-pattern
"the build is green" offered as done while the pdf carries an empty 3d scatter and a 254 pt overfull; a first paint reported as fine that he called "visually so confusing".
