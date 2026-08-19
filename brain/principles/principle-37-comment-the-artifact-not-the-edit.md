---
name: principle-37-comment-the-artifact-not-the-edit
kind: principle
rule: every comment describes the code as it now stands - never the edit that produced it. no comment may name an identifier, algorithm or structure absent from the post-edit file, narrate a change, or explain an instruction he gave.
interest: [intent-craft, intent-comprehension]
confidence: very-high
evidence_count: 5
tells: ["almost as if claude/brain is commenting the EDIT instead of the POST-EDIT CONTENT and its getting infuriating", "theres now artifacts of H and W in the comments and unnecessary comments about typing which i clearly dont care about", "why on earth do i need to have this ancillary information about timestamp when clearly the other 7 args dont go into such detail", "not every line has to be commented", "remove the comment there"]
---

# P37 - comment the artifact, not the edit

## rule
a comment is read by someone who never saw the diff. write for that reader.

- **no stale referent.** a comment may not name a variable, argument, function, type,
  file or algorithm that does not exist in the post-edit source. renaming `H, W` to `N`
  deletes `H` and `W` from the file - and from every comment in it.
- **no change narration.** no "instead of", "changed from", "previously", "now uses",
  "this was added so that". that is changelog; it belongs in the commit message, never
  in the source.
- **no narration of the request.** a comment does not explain that type hints were added
  because type hints were asked for - the signature already shows it. restating the
  instruction back to whoever gave it is noise.
- **no contentless filler.** a comment that paraphrases the line it sits above says
  nothing. `# red` beats `# red is the third channel of the pixel tuple`.
- **altitude is symmetric.** if seven fields get a phrase each, the eighth does not get a
  paragraph. an item documented far above its siblings is almost always the one that was
  just touched - that asymmetry is the tell that a comment drifted onto the edit.

this is about comment CONTENT and it binds while the comment is being typed, not at a
later cleanup pass.

## why
he reads the file, not the diff ([[intent-comprehension]]). a comment naming `H` in a
file with no `H` is unresolvable - the reader has to reconstruct a history they were
never shown, to understand code that is already in front of them. and the narration is
agent-speak leaking into his source ([[principle-16-my-stack-my-voice]],
[[intent-craft]]): it documents the assistant's turn, not the program.

## how to apply
- write the comment as if the previous version never existed. if a phrase only makes
  sense against the old code, delete the phrase.
- after any edit, re-read every comment in the touched hunk against the POST-edit text,
  not the diff. scripted: `brain-fmt.py --stale` reports comments naming tokens that
  survive only in the pre-image ([[principle-19-think-in-code-ops]]).
- this governs comment CONTENT. how verbose to be is the other knob
  ([[principle-07-trim-fat-verbose-docs]]); how to phrase it in this language is
  [[principle-06-idiomatic-per-language]].
- it binds at WRITE time, not just at the cleanup pass. the comment is wrong the moment
  it is typed.
- his own comments are his ([[principle-09-git-sovereignty]]). this applies to comments
  the agent wrote or touched in this session, never to pre-existing prose.

## anti-pattern
```python
# typing here is used so that args is defined as a list, and also giving a return type
# and N is used here instead of H and W since dimensionality doesnt matter
def function(N: int, args: list[Any]) -> int:
```
two sentences, both about the edit, one naming two identifiers that no longer exist. it
draws heat every time ([[principle-15-tone-is-signal]]) - twice inside 26 hours.
