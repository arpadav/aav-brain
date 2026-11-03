# R01: 39 low and nit findings from the 2026-11-02 self-refine build, deferred

The third cold review of the 2026-11-02 self-refine build (plans/2026-11-02-self-refine.md) found 56 issues. The 17 serious ones are fixed in that build. These 39 low/nit ones were deferred by your call ("redesign tool entry, fix 17"). Each is one site, one fix. Some may close when the shared tool entry lands; re-check before working one.

## Low
- brain-private `lan`: a LAN ip on `br0`, a bond or a VLAN is dropped without marking the source unavailable. Exclude `lo`/`docker*`/`veth*`/`tailscale*`/`virbr*` by name instead of requiring a `device` link.
- brain-private ignores positional args (`brain-private ../x` scans the cwd); brain-recall and brain-misses each carry their own rejection stanza.
- brain-private `probe`: `UnicodeDecodeError` uncaught; probes run before a malformed private.toml is rejected.
- `Graph.build` / `Node.from_principle`: one non-UTF-8 principle crashes recall, brain-graph and brain-principles. Catch and report the principle.
- tiers.toml: line 12 says all 68 values reproduce but 50 are measured; line 6 says 51; line 64 "these three"; the P24 row is unmeasured since the merge.
- vocab `Kind.INTEREST` has no producer but is still used at recall/model/text. Drop it or say why it stays.
- Stale doc referents: paths.py "the graph ... walk principle_dirs"; ARCHITECTURE intents/voice "via the graph", brain-sync omitted, tier diagram omits aav-brain-served and the archive; text.py "or the built graph"; model.py "committed" for gitignored output; bin/store/brain-flow.py:19; README:29.
- brain-self-refine SKILL runs `brain-graph --check` against a gitignored export; fails on a fresh clone. Run `brain-graph` for its warnings.
- P24 "resume only if i say so" vs P01, P11, brain-meta-intent and intent-comprehension. P24 owns it; others point to it.
- schema/principle.md "a link to a not-yet-written principle is fine" vs Graph.build's unknown-principle warning.
- brain-verifier agent omits the always-on private scan.
- P61 rule lists usernames and device ids as enforced; LIMITS says unchecked; the --help pointer appears twice.
- README "each script answers --help" but brain-sync --help exits 1.
- session.py: `Mark.parse` accepts a negative `at`; `# utc` vs any offset accepted; O_APPEND atomicity fails past the stdio buffer; `held` is O(n*m).
- brain-misses: row stamps lack `Z`; repeated `--since` keeps the first; usage silent on whole-corpus window; control characters pass through to the terminal.
- brain-recall flag edges: `--neighbors` with no value matches 68 principles; `--all --tells` silently runs `--all`; a `--tells` with no match exits 0 printing nothing.
- `Args.stdin_text` blocks forever on an inherited pipe that never closes.
- brain-register: `read_text` without encoding; missing file or dir gives a traceback; outside a repo reports 0 findings and exits 0.
- brain-compile: unlinks any `*.toml` no source builds (incl. hand-placed); `--check` does not name the orphan; `targets()` rebuilt 2-3 times.
- brain-graph `--check` does not print the warnings its docstring says the CLI exists for.
- brain-extract: usage omits `--archive-dir`; the only argparse script left.
- brain-eval: `run_recall` ignores the returncode; usage omits `clean`; `--check` does nothing; `report`/`clean nosuch` exit 0; `clean` on a file tracebacks; `clean` follows a symlink's target.
- .charts/plot.py: outside brain-lint's paths; mypy fails without matplotlib; creates the output dir before validating; USAGE for missing input.
- brain-private matching: no IPv6 globals while LIMITS calls them "lan"; lookbehind misses an ip after a `.`; declared prefixes never match; an over-cap tracked file fails forever with no listed skip; scope lines unflushed; `+ scan` line lacks the TOOL prefix.
- Real session id prefix in tracked doctests: bin/brainlib/paths.py, bin/check/brain-misses.py. Use a placeholder uuid.
- Harness knowledge outside transcript.py: brain-eval strips only the claude session env; brain-misses tests `SESSION_ENV is None`; brain-extract depends on `reversed(harnesses.all)`.
- Structure: `Json` stuck in brain-private; `PrivateScan` holds four jobs; `MissReport` holds trace query, served state and render.
- Duplicated parsers: repo discovery (`paths.find_repo_root` vs `RepoTree`); frontmatter (brain-compile vs text); principle-link regex (brain-principles vs model); brain-sync submodules via `split()[1]` while `RepoTree._gitlinks` exists.
- brain-recall `-n ²` passes `isdigit()` then tracebacks; use `isdecimal()`.

## Nit
- transcript.py `Harness.discover` has no callers.
- recall.py: a zero-padded token never resolves an unpadded short id; compare as ints.
- INDEX.md "## tier 2.5: the graph" flagged by the register lint.
- transcript.py prose restates `SHORT_ID`/`PROJECT_LABEL` numbers.
- Prose: P24:5, P24:76 overlong, P40:60 comment column, mypy.ini overlong lines, brain-review-gate.md:50-54 dangling quote.
- bin/run/brain-verify.py docstring lines 19, 21, 169.
- transcript.py:553 calls `DENIAL` claude's refusal text; it matches more.
- Idiom: `Recall` 10 positional fields (`kw_only`); `sorted(nodes.items())` compares Nodes on ties; frozen dataclasses with mutable fields; `Harnesses.all` shadows a builtin; `__init__` missing `Codex`/`Compacted`/`Place`; inconsistent `@override`; quoted annotations in brain-extract; hard-coded "brain-extract"; `binds`/`bound` naming; `REFERENCE_EDGES` filter is a no-op.
- Fragile matching: `Codex.NEEDLES` assumes compact json; `Place.every` calls `str.format` on the pattern; `Transcript.stem` splits on `.jsonl`; compaction detected by its opening phrase.
- Near-twin names: `Scope.around` vs `RepoTree.around`.

## Pre-existing, found on the way (not caused by the build)
- brain-gate untracked list without `-z`, scoped to cwd.
- brain-extract Archiver: stat outside the try; `gzip.open(target, "wb")` truncates a good copy and the mtime check then skips it forever; archives 0664.
- transcript.py DENIAL regex: 24 of 171 denials.jsonl rows are file-read output.
- `Claude.project` hardcodes `{home}-repos-personal-` with an unanchored replace.
- recall tokenizer turns "don't" into "don".
- brain-extract RE_MACHINE is `^`-anchored; 2 rows carry a mid-text system-reminder.
- brain-compile `agent.name` can escape the output dir.
- brain-sync: timeout uncaught, commit/add return values ignored, identity hardcoded.
- brain-gate ShapePolicy loaded at import.
- `brain-trace --prune nosuch` exits 0.
- schema/principle.md says brain-extract refreshes evidence_count.
- brain-self-refine SKILL glob `bin/*.py` misses the subfolders.
- schema/flow.md:30 "fires".
- eval scores an ungraded sheet as 0.000.

## Your call

<!-- sha256: 940522cfe8f5ca942634977dc361b176969d01e6a14be005a2f8e794df89251b -->
