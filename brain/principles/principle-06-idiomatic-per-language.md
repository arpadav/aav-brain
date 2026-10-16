---
name: principle-06-idiomatic-per-language
kind: principle
tier: conditional
rule: Write each language in its own idiom and the house conventions, and run that language's REGISTERED toolchain. Rust style in Rust, TS style in TS. A language with no registered toolchain is a question for him, never a guess.
interest: [intent-craft]
confidence: very-high
evidence_count: 16
binds: [code]
tells: ["use rust style in rust, ts style in ts. thats it", "idiomatic rust said NEVER do unwrap_or", "doc-comment first then attributes", "did you use uv ruff and ty to check the python? minimize standalone functions?", "when using X language, use Y tools"]
---

# P06 - Idiomatic per language + house conventions

**Rule.** Match the idiom of the language you're in and the established house
conventions. "use rust style in rust, ts style in ts. thats it." This is non-negotiable
and is the reason his `aav-idiomatic-rust` suite exists. The `aav-style-*` suite is the
other half and is deliberately NOT per-language: one spec, applied through whatever
comment marker, import stanza and doc convention the file's language uses.

**Why.** Uniformity is what keeps the codebase cheap to read and review ([[intent-craft]]).
Inconsistency is friction every time he returns to the code.

**House conventions observed (Rust-leaning):**
- Idiomatic error handling - **never** `unwrap_or` where it hides a real case ("idiomatic
  rust said NEVER do unwrap_or you idiot, why did you do that?"). Typed errors with
  `thiserror`, not `Box<dyn Error>`.
- Enum dispatch over `Box<dyn>` / `Arc<dyn>` / `&dyn`.
- No magic strings/numbers - `const`/`static`, reused.
- **Doc-comment first, then attributes** (verified as the house convention: "62
  occurrences crate-wide, 0 the other way").
- Tightest visibility that compiles (`pub(super)` > `pub(crate)` > `pub`).
- No standalone free functions for logic - methods on named types.
- Comment **separators** between logical sections; `cargo fmt` always last.
- Clippy denies in `Cargo.toml` / `clippy.toml`.

**Language-independent, and they bind while the code is being written:** a comment
describes the code as it now stands ([[principle-37-comment-the-artifact-not-the-edit]]),
at the volume [[principle-07-trim-fat-verbose-docs]] sets. Every row of the registry
below inherits both; no toolchain checks either one.

## The per-language toolchain registry

Each language has a REGISTERED toolchain + workflow. Run it; don't improvise one.
The registry grows as he defines each language - it is deliberately incomplete.

| language | toolchain + workflow |
|---|---|
| **rust** | `cargo fmt` last, clippy denies in `Cargo.toml`/`clippy.toml`; enum dispatch over `dyn`; typed errors (`thiserror`); no free functions for logic - methods on named types; tightest visibility that compiles. |
| **python** | `uv venv` for envs, `uv pip install`, run via `.venv/bin/python` - never bare `pip`, never `python3 -m venv`. Checking is **every checker that is installed, each against its own pinned config** - `ruff.toml`, `ty.toml`, `mypy.ini`, `pyrightconfig.json` - run by `bin/check/brain-lint.py`, which skips an absent tool out loud rather than silently. They do not overlap: ruff is a linter and cannot see types at all, so a bare `dict` is invisible to all 956 of its rules. Annotate everything; every generic carries its arguments (`dict[str, Node]`, never `dict`), builtin generics not `typing.List` (deprecated by PEP 585, and ruff's UP006 rewrites it). Minimize standalone functions - keep it class-based, methods on types, decorators where they fit. **Structure, which no checker sees:** paths spelled once on a layout type, never rebuilt at a call site; a fixed set of strings is a `StrEnum`, never a literal compared by hand; env var names and status codes named, not inlined; a constant argument repeated at every call belongs to the module; PEP 604 unions and builtin generics. the before/after pairs live on [[principle-40-idiom-needs-exemplars]] and are what gets handed to a writer - this cell names the rules, that card shows them. |
| **wgsl** | no standard formatter exists, so none runs. Comments follow the C/CUDA form: `//` line comments, the 50-hyphen separators, and `///` doc comments above the `@` attributes on every struct, binding and entry point. There are no imports; the `@group`/`@binding` block comes first. Validation is the consumer's: wgpu/naga parse the shader at pipeline creation, so a native test that builds every pipeline is the check. Any struct shared with a host language is mirrored field for field and pinned by a layout test against the host type (`size_of`, the naga span). Defined by him (email, 2026-09-13: "do B"). |
| **html/css** | no formatter and no checker run - the browser is the consumer, so the check is loading the page in a real browser and looking at it ([[principle-48-look-at-the-rendered-output]]). html5, 2-space indent, lowercase tags and attributes, double-quoted attribute values. css lives in ONE `<style>` block inside the page: no separate css file, no framework, no preprocessor, no npm. Separators take each language's own marker around the 50-hyphen rule - `<!-- -------------------------------------------------- -->` then a `<!-- label -->` line then the rule again in html, and `/* -------------------------------------------------- */`, `/* label */`, the rule in css. No js files where rust over web-sys drives the page. Defined by him (email, 2026-09-14, wave-rgpu: "A or B i am indifferent" - A, the recommended option, taken). |
| **cuda/c++** | build with `nvcc -arch=sm_120 -lineinfo -O3` (pinned per-repo in each `tests/cases.json`, not typed at a call site). Format against the repo's checked-in `.clang-format` - LLVM base, `IndentWidth: 4`, `ColumnLimit: 100`, `BreakBeforeBraces: Attach`, `PointerAlignment: Right`, `SortIncludes: false`. Doxygen `/** @param */` on every kernel and its host wrapper, naming what each argument actually receives at the call site, not just its type. **The `.clang-format` file is an editor config, not an enforced gate** - the nvidia-prep repo measures 15+ clang-format violations per 100 lines in labs this row's toolchain never touched, so `--check`-style enforcement there would fail on pre-existing content that is out of scope for any one change ([[principle-03-review-gate]]). Comment-separator width is measured per-repo, never assumed - this repo's house form is 78 hyphens, not [[principle-39-style-contract]]'s 50-hyphen default; a formatter that rewrites to 50 here corrupts the convention instead of enforcing it. Row resolved from in-tree evidence (the repo's own `.clang-format`, `verify.sh`, `tests/cases.json`), not yet confirmed with him directly - next invocation still gets the one-time confirm below. |

**A checker list is not an idiom.** Every checker in the python row ran CLEAN on code carrying 48
hand-built paths, 45 bare flag strings and zero enums: ruff cannot see structure, and a type checker
cannot see that a correctly-typed string should have been an enum. The tools bound the row's floor;
[[principle-40-idiom-needs-exemplars]] binds its substance, at the rigor
[[principle-41-rigor-scales-with-purpose]] sets. Rust's row is carried by an agent that writes to it;
a row backed only by prose is a row that binds only when someone remembers to read it.

**A row is a floor, not a ceiling.** Every rule a checker enforces is pinned in a config
file, and every rule turned OFF carries its reason on the line above it - an unexplained
exception is indistinguishable from an unexamined default, which is the state a pinned
config exists to leave.

**The ask rule.** Before writing a language whose row is missing, ASK him to define it,
offering a recommendation to react to. Never invent a toolchain silently.
- Row exists + he says "use existing tooling/workflow" -> proceed, no confirmation needed.
- Row exists but he hasn't invoked it -> confirm once: "toolchain for X is A, B, C - good?"
- Row missing, or the project mixes languages with any row missing -> **ASK**, per language.
  A mixed repo needs every language defined, not just the dominant one ([[principle-01-no-assumptions]]).

**How to apply.** When in Rust, run it through the idiomatic-rust lens; when in TS, the
TS idiom. Don't cross-contaminate. Style pass comes **after** correctness
([[principle-03-review-gate]]) and **before** `cargo fmt`.

**Anti-pattern.** Applying one language's idioms to another; introducing `unwrap_or`,
`Box<dyn>`, magic numbers, or attribute-before-doc ordering.
