---
name: principle-49-his-interactive-app-shape
kind: principle
rule: an interactive data app of his opens on the data (a 3d stage, the full universe drawn, click a point for its page), lets him weight importance himself with sliders, keeps detail as stackable pages not side drawers, offers settings as a questionnaire first with a raw tab behind it and keeps them across restarts, prints money like a receipt, wears his 90's academic page style with a harsh retro scene, works by finger on his surface pro and phone, and relays any settings/filter change to every surface at once - list, stage, graphs - never just the tab being edited.
interest: [intent-craft, intent-comprehension]
confidence: very-high
evidence_count: 3
tells: ["i want it ALL and then i can filter out, choose min/max. i should be able to filter and sort everything. there should be an interactive model", "this is supposed to be an analysis across a bunch of existing workloads with 3d data, then i click on datapoint and can view specs and all. then apply optional filters to remove datapoints", "any way to make the list format where i can weight importance? like i care about memory 50% and power 25% and flops 25% or something, 0% price", "thats an option, they should all be sliders", "id much rather have a dedicated page for each which i can view and return to. not necessarily URL, but like a stack, where i can press on it, it overlays, and i press back and it returns to layer underneath", "the default view is a questionnaire. the questionnare should page you through asking questions in an interactive sleek format, which then sets settings for you. the settings are applied and shouldnt be ephemeral", "make it look like a receipt or something", "harsh black white rgb colors, 24bit colors or whatever", "any way on browser-side to allow for touch options? i see point and click but on my MS surface pro or phone, no work", "very last, mobile view?", "not some naive line graph but something more scientific like optimization problem across cost power vram gflops and other metrics", "search the web, use browser skills, etc to fetch relevant images for each... not only of the products, but saying this is gpu, this is a case, and company logos too. feel free to use ffmpeg to style/alter logos... use dithered options for more of that retro look", "when i change settings/filters then i dont see that relayed on the list. it should be realyed everywhere, the list the 3d the graphs etc"]
---

# P49 - his interactive app shape

## rule
the shape he asks for, item by item, when the deliverable is an interactive analysis: it starts from
wanting something more scientific than a chart - "not some naive line graph but something more
scientific like optimization problem across cost power vram gflops and other metrics" - which is why
the stage comes first (a 3d view of every datapoint, coloured by a value, the frontier marked); click
a point and its page opens as a layer on a stack with a back button, recursing to the things it
names; the outer chrome is a collapsible left nav whose top-level tabs separate that live view from
settings/filters; filters are optional and secondary; the objective is his - one slider per metric
with the share shown; settings come as a questionnaire that pages through plain questions and writes
the settings, then shows the answered list with a re-ask button, with a raw tab for the direct
controls, as the settings tab's own pair; settings persist across server restarts in the browser with
export/import; totals read like a till receipt; the page is his 90's academic sheet and the scene is
the harsh eight-colour retro look with a scanline/dither filter layered on without costing it
performance or interactability; pictures of the products, kind illustrations and maker logos, fetched
from the web and dithered; it works by touch on his surface pro (type cover on) and phone, and has a
phone layout; every surface reads the same settings/filters - a change relays live to the list, the
stage and the graphs at once, not just the tab it was made on.

## why
he learns by the concrete instance and wants his own mental model in the loop ([[intent-comprehension]]); the look and the interaction are part of the craft he judges ([[intent-craft]]).

## how to apply
start from this shape and ask the experience questions that remain (P42) - palette, persistence, filter - each with a recommended default; touch is decided per pointer event (his surface reports a fine primary pointer with its cover on); the page style is asked before it is applied.
- the nav is two levels of tabs, not one flat set: outer tabs pick live-view vs settings/filters,
  and inside settings the questionnaire-result and raw-controls views are the tabs. treat this as the
  answer P42's experience-first question converges on for this shape, not a thing to re-derive.
- a retro filter (scanline/dither) sits on top of the render and must not cost it performance or
  interactability - it is decoration, never at the expense of the interaction it dresses up.
- settings/filters are one piece of shared state, not one copy per view: a change must relay to
  every surface at once (list, stage, graphs). build it as one derived set feeding all consumers,
  not a value each view reads independently - a view that shows the old set until revisited is broken.
links: [[principle-42-plain-english-questions]], [[principle-23-standing-decisions]], [[principle-48-look-at-the-rendered-output]].

## verbatim tells
- "i want it ALL and then i can filter out, choose min/max. i should be able to filter and sort everything. there should be an interactive model"
- "this is supposed to be an analysis across a bunch of existing workloads with 3d data, then i click on datapoint and can view specs and all. then apply optional filters to remove datapoints"
- "any way to make the list format where i can weight importance? like i care about memory 50% and power 25% and flops 25% or something, 0% price"
- "thats an option, they should all be sliders"
- "id much rather have a dedicated page for each which i can view and return to. not necessarily URL, but like a stack, where i can press on it, it overlays, and i press back and it returns to layer underneath"
- "the default view is a questionnaire. the questionnare should page you through asking questions in an interactive sleek format, which then sets settings for you. the settings are applied and shouldnt be ephemeral"
- "make it look like a receipt or something"
- "harsh black white rgb colors, 24bit colors or whatever"
- "any way on browser-side to allow for touch options? i see point and click but on my MS surface pro or phone, no work"
- "very last, mobile view?"
- "not some naive line graph but something more scientific like optimization problem across cost power vram gflops and other metrics"
- "a left bar that you can toggle out/in. multiple tabs. one tab is the current view, one tab is the settings/filters"
- "i would like you to search the web, use browser skills, etc to fetch relevant images for each... not only of the products, but saying 'this is gpu' 'this is a case' and company logos too. feel free to use ffmpeg to style/alter logos... use dithered options for more of that retro look"
- "it would be cool to have some filter overlay without compromising performance or interactability"
- "when i change settings/filters then i dont see that relayed on the list. it should be realyed everywhere, the list the 3d the graphs etc"

## anti-pattern
a left column of knobs, a blank middle and a grey right pane; a side drawer for detail; a streamlit page; a scene in a scientific colour ramp when he asked for harsh rgb; a retro filter overlay that costs the frame rate or breaks a click/hover; a settings/filter change that updates the tab you're on but leaves the list, 3d stage or graphs showing the stale set.
