---
name: principle-40-idiom-needs-exemplars
kind: principle
rule: an abstract style instruction does not change what gets written. every idiom rule the brain enforces carries a concrete before/after pair, and the writer is shown the pairs - never the adjective alone. "be idiomatic" is not an instruction; a worked example is.
interest: [intent-craft, intent-comprehension]
confidence: very-high
evidence_count: 4
binds: [code]
tells: ["simply passing be idiomatic concretely to an agent wont do much, unless you explicitly list examples", "put simple/dummy examples before/after into cards, which the agent can then see", "THIS is exactly what i mean by idiomatic, and something i would write", "it should have caught these mistakes FROM inception, not a huge refactor after the fact"]
---

# P40 - an idiom rule binds only when it carries an example

## rule
naming a quality does not produce it. a writer told "be idiomatic" writes what it already would
have; a writer shown `args[args.index("--state") + 1]` beside `args.value(Flag.STATE)` writes the
second. so every idiom rule the brain holds is stored WITH a minimal before/after pair, and the
doctrine handed to a writer is the pairs, not the adjective.

this is measured, not asserted: the brain's own python scripts carried 48 hand-built paths, 45 bare
flag strings, zero enums and 24 free functions while [[principle-06-idiomatic-per-language]],
[[principle-26-struct-based]] and [[principle-28-dry-merge-blast-radius]] all already said not to.
the rules were present and abstract. what finally moved the code was a prompt that named two
instances - "args not being strenum, and paths being manually constructed in multiple places" - and
demanded the rest be found. "this prompt fixed 90%+ of what ive been looking for, by simply ASKING
FOR IT."

## why
he learns and instructs by concrete instance ([[intent-comprehension]]), and a writer resolves an
adjective against its own priors rather than his. the pair removes the interpretation step: there is
nothing to infer about what "idiomatic" meant, because the wrong form and the right form are both on
the page. uniformity is what keeps the code cheap to re-read ([[intent-craft]]).

## the exemplar catalogue (python)
each row is a rule the brain broke in its own `bin/`, with the shape that replaced it. treat the
right column as the target, not the only permitted spelling.

**1. a path is spelled once, on a layout type - never rebuilt at a call site**
```python
brain = find_brain(); skills = brain / "agentic-files" / "skills"   # before
layout.skills                                                      # after
```

**2. a fixed set of strings is an enum, not a literal compared by hand**
```python
if "--check" in sys.argv: ...          # before
if args.has(Flag.CHECK): ...           # after
```

**3. an environment variable is named once, never at the read site**
```python
os.environ.get("XDG_DATA_HOME", "")    # before
Env.XDG_DATA_HOME.read()               # after
```

**4. a status code carries its meaning**
```python
sys.exit(1)                            # before
sys.exit(Exit.DRIFT)                   # after
```

**5. a constant argument repeated at every call belongs to the module**
```python
path.read_text(encoding="utf-8")       # before, x21
read_text(path)                        # after
```

**6. logic lives on a type, not loose in a module ([[principle-26-struct-based]])**
```python
def card_dirs(store): return [store / "principles", store / "intents"]   # before
layout.card_dirs                                                        # after
```

**7. modern generics, no deprecated typing aliases**
```python
def f(x: Optional[List[str]]) -> Union[str, int]:   # before
def f(x: list[str] | None) -> str | int:            # after
```

**8. a repeated shape is a named type, not an anonymous tuple**
```python
def load() -> tuple[dict, str, Path]:  # before
def load() -> Aperture:                # after
```

**9. an unrecognised flag is rejected, not ignored**
```python
# before: a typo in --check silently ran the default path
if unknown := args.unknown(Flag.CHECK):
    sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
```

**10. a value declared in N places is declared once**
```python
# before: the interpreter floor appeared in 16 files
PYTHON_VERSION = "3.12"   # after: named once, referenced
```

## how to apply
- writing code -> the doctrine loaded before the first line is this catalogue, filtered to the
  language, at the rigor [[principle-41-rigor-scales-with-purpose]] sets.
- reviewing code -> seed with two named instances, then demand the rest be found exhaustively, and
  forbid padding the list ([[principle-04-anti-fabrication]]). "dont make anything up if you cant
  find any more" is part of the ask, not a caveat on it.
- learning a new rule from him -> capture the pair, not just the sentence. a rule that arrives
  without an example is not yet finished.
- the catalogue GROWS. every correction he gives adds a row; that is what keeps this card from
  going abstract again.

## orthogonality
[[principle-11-comprehension-ownership]] is the same mechanism pointed at HIM - a concrete example so
he owns the mental model. P40 points it at the WRITER, so the rule binds machine-side. P06 owns which
idiom applies per language; P40 owns the form that idiom must be stored in.
[[principle-39-style-contract]] is the surface layer (separators, doc form, imports) and is already
exemplar-carrying in its lens specs - P40 is that same discipline extended to structure and typing,
which no gate can measure.

## anti-pattern
handing a writer "follow my style" / "be idiomatic" / "make it clean" and expecting different output.
a rule stated only as an adjective, with no wrong-form beside the right-form. a review that stops at
the first two findings when the ask was exhaustiveness - and, its mirror, inventing findings to look
thorough.
