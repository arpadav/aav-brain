---
name: principle-47-copy-raw-fetches-into-the-repo
kind: principle
tier: narrow
rule: every page, api response or search result an agent fetches for data is copied into the repo's source corpus as it is fetched, and the row that cites it names that copy; a fetch that was not copied does not exist.
interest: [intent-trust, intent-comprehension]
confidence: high
evidence_count: 1
tells: ["and for all these subagent tasks which fetch data, where is that stored? ... were they ephemeral/in RAM or were they written to disk", "if that agent saved the raw info, then during the analysis it could be queried too", "no need to complicate with code, i was asking because next time i do fetches, the llm should know to copy stuff to snapshot, thats all"]
---

# P47 - copy raw fetches into the repo

## rule
a number in a curated table is only as good as the page it was read from, and the page is only usable later if it is on disk. every fetch lands as a file under research/sources/<date>/ (html, markdown, pdf, json) before the number is written; the source row carries the path; a validate rule fails on a cited snapshot that is not on disk. this is an instruction to every fetching agent, not a tool.

## why
he wants to query the raw material during analysis and to re-verify any printed number against the page it came from ([[intent-trust]]); he learns by the concrete instance, which the copy is ([[intent-comprehension]]).

## how to apply
put the rule in every dispatch that fetches; when a lane ran without it, salvage the pages from the fetch tool's store and stamp the rows before merging. a websearch answer is not a page - snapshot the publisher's page or say the row has none. links: [[principle-04-anti-fabrication]], [[principle-08-read-source-and-error]].

## verbatim tells
- "and for all these subagent tasks which fetch data, where is that stored? ... were they ephemeral/in RAM or were they written to disk"
- "if that agent saved the raw info, then during the analysis it could be queried too"
- "no need to complicate with code, i was asking because next time i do fetches, the llm should know to copy stuff to snapshot, thats all"

## anti-pattern
agents that fetched fifteen pages in memory and cited none; source rows whose snapshot is a model-written summary of the page.
