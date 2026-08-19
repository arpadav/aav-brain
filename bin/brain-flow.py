#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-flow: build the deterministic execution flow from flow.toml.

    python3 brain-flow.py            build brain/flow/flow.json
    python3 brain-flow.py --check    build to memory, fail if it drifts from disk
    python3 brain-flow.py --mermaid  print the mermaid view (for docs)

the flow is AUTHORED as data in brain/flow/flow.toml (states + transitions),
exactly the way the knowledge graph is authored as data in the markdown cards
this script READS that data, validates it, and writes the canonical flow.json -
it does not hardcode the states. brain-walk.py then steps flow.json

the flow is the EXECUTION SEQUENCE, kept strictly separate from the knowledge
GRAPH (brain-graph.py): the flow has states/transitions, the graph has
nodes/edges, and the coupling is one-directional (a state may CALL recall via
its `recall` flag; the graph never calls the flow). see P30

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Artifact, Exit, Flag, Layout, State, Transition, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()

# the four entry skills, each of which must hand its walk to brain-meta-drive
# the handoff below is generated INTO all four from this one definition, so the
# four copies cannot drift apart
ENTRY_SKILLS = ("brain-plan", "brain-execute", "brain-review", "brain-self-refine")

# mermaid keywords that cannot be used as a node name; `style` is the one this
# flow actually collides with, and the collision renders as a parse error
MERMAID_KEYWORDS = frozenset({"style", "class", "state", "note", "direction", "end", "click", "link"})

HANDOFF_BEGIN = "<!-- GENERATED: handoff (brain-flow.py) - do not hand-edit -->"
HANDOFF_END = "<!-- END GENERATED: handoff -->"
# how the hand-pasted copy is recognised, so the first build migrates it in place
HANDOFF_ANCHOR = "this hands off to `brain-meta-drive`."
HANDOFF_TAIL = "you do not re-implement that loop here."

ENTRY_HANDOFF = """
this hands off to `brain-meta-drive`. the handoff has TWO steps and both are
mandatory - a summary of what the engine does is NOT a substitute for running it:

```bash
python3 $AAV_BRAIN/bin/brain-walk.py --state "$STATE"   # paste the output
```

**you may not proceed until that output is in the transcript.** it names the
state's owner and its transitions; if it is absent, the walk did not happen.
then, and only then:

```
Skill(brain-meta-drive)          # the literal tool call, not a Read
```

the engine steps `flow.json`, recalls per state, dispatches each owner, and
loops the gates to a terminal. you do not re-implement that loop here.

every state the engine reaches prints its own directive the same way - a
`Skill(...)` or `Agent(...)` line under the state. make that call before doing
the state's work; the owner skill IS the method, and hand-rolling it inline
looks identical in the transcript while discarding it.
"""

# the static prose framing the generated diagram + table; the mermaid, the owner
# table, and this doc as a whole are GENERATED so the file can never drift
DOC_HEADER = """# my end-to-end dev flowchart (the execution flow)

this is the EXECUTION FLOW - the sequence of how the brain runs a task. it is SEPARATE from the
knowledge GRAPH (brain/graph/graph.json), which is the context fetcher ("which principles apply").
the flow answers "what step is next"; the graph answers "which cards apply". they never conflate, and
the flow uses STATES + TRANSITIONS while the graph uses nodes + edges, so the vocabulary never
overlaps (P30).

the source of truth is `brain/flow/flow.toml` (authored DATA, like the cards are the graph's data).
`bin/brain-flow.py` reads + validates it and builds `brain/flow/flow.json`; `bin/brain-walk.py` steps
flow.json deterministically. this whole file is GENERATED from flow.json by `brain-flow.py` - do NOT
hand-edit it; re-run the builder after editing flow.toml so it can never drift. it is
drift-gated: `brain-flow.py --check` fails if this file is stale. a state may
CALL the graph (its `recall: true` flag fires brain-recall); the graph never calls the flow - one
direction.

## 1. the machine (generated)

"""

DOC_TABLE_INTRO = """## 2. state -> owner (generated from flow.json)

each state is owned by a brain skill or one of the two cold agents. the boundary state (SANCTION)
flips ask-first -> execute-through; BLOCKED is the only post-sanction stop (ask arpad, resume on
/continue).

"""

DOC_STEPPING = """## 3. how brain-meta-drive steps it

brain-meta-drive does not invent the sequence - it queries brain-walk:
1. `brain-walk --state <id>` returns the state's owner + recall flag.
2. if recall: run brain-recall to load the relevant cards (the one call into the graph).
3. run the owner; it yields an outcome event (threshold_met / below_threshold / set_grew / ...).
4. `brain-walk --state <id> --on <event>` returns the single next state - from the data, not judgement.

cyclic refinement is REQUIRED, not optional (P03). three regions LOOP until a metric threshold holds,
then advance exactly one phase:
- RECON..REORG: the per-file scrutiny + bidirectional reorg loop (P29, P27). the relevant-file set
  expands to a fixpoint (EXPAND self-loop) and re-expands after every move/reshape.
- PLAN -> PLANPROBE -> PLANGATE: the plan is traced THROUGH its own worked example; a gap routes back
  to PLAN. PLANGATE emits threshold_met (-> SANCTION) only when the plan is open-question-free and the
  example traces end-to-end, else below_threshold loops back to PLAN.
- IMPL -> PHASEGATE -> VERIFY: PHASEGATE loops below_threshold -> REMEDIATE -> PHASEGATE until the
  review converges (nits zero, consistent with the repo); VERIFY loops unsound -> REMEDIATE (which
  re-enters PHASEGATE) until the build/test/bench is sound. only then does it advance.

the gates never advance dirty: a threshold that is not met routes BACK, never forward.
"""

def node_id(state_id: str) -> str:
    """the mermaid node name for a state id, dodging the language's keywords.

    # Arguments

    * `state_id` - the flow state id

    # Returns

    the id, suffixed when it collides with a mermaid keyword

    # Example

        >>> node_id("STYLE"), node_id("IMPL")
        ('STYLE_GATE', 'IMPL')
    """
    return f"{state_id}_GATE" if state_id.lower() in MERMAID_KEYWORDS else state_id


def mermaid_label(doc: str) -> str:
    """a state doc, safe to sit inside a quoted mermaid label.

    # Arguments

    * `doc` - the state's doc string

    # Returns

    the doc with the quote character replaced, since it would close the label

    # Example

        >>> mermaid_label('emits "sound" only when green')
        "emits 'sound' only when green"
    """
    return doc.replace('"', "'")


@dataclass
class FlowBuilder(Artifact):
    """reads flow.toml, validates it, and builds flow.json."""

    states: list[State] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    # the validation result, computed once: the flow does not change after read
    _warnings: list[str] | None = field(default=None, repr=False, compare=False)

    @classmethod
    def read(cls, toml_path: Path, out_dir: Path) -> "FlowBuilder":
        """load the authored flow data from toml into typed states/transitions.

        # Arguments
        * `toml_path` - the flow.toml source path
        * `out_dir` - the directory flow.json is written to

        # Returns
        a FlowBuilder holding the parsed States and Transitions
        """
        data = tomllib.loads(read_text(toml_path))
        states = [State.from_dict(s) for s in data.get("states", [])]
        transitions = [Transition.from_dict(t) for t in data.get("transitions", [])]
        return cls(out_dir=out_dir, states=states, transitions=transitions)

    def dangling_warnings(self) -> list[str]:
        """one warning per transition endpoint that names no state.

        # Returns
        the warnings, one per unknown src or dst
        """
        ids = {s.id for s in self.states}
        out: list[str] = []
        for t in self.transitions:
            if t.src not in ids:
                out.append(f"transition from unknown state {t.src}")
            if t.dst not in ids:
                out.append(f"transition to unknown state {t.dst}")
        return out

    def boundary_warnings(self) -> list[str]:
        """the flow must carry exactly one sanction boundary.

        # Returns
        a single warning when the count is wrong, else nothing
        """
        boundaries = [t for t in self.transitions if t.boundary]
        if len(boundaries) == 1:
            return []
        return [f"expected exactly 1 boundary transition, found {len(boundaries)}"]

    def determinism_warnings(self) -> list[str]:
        """(src, on) must be unique, or step() is not a function.

        # Returns
        one warning per duplicated (src, on) pair
        """
        out: list[str] = []
        seen: set[tuple[str, str]] = set()
        for t in self.transitions:
            key = (t.src, t.on)
            if key in seen:
                out.append(f"duplicate transition ({t.src}, {t.on}) - step is ambiguous")
            seen.add(key)
        return out

    def exit_warnings(self) -> list[str]:
        """every non-terminal state needs a way out.

        # Returns
        one warning per non-terminal state with no outgoing transition
        """
        outgoing = {t.src for t in self.transitions}
        return [f"non-terminal state {s.id} has no outgoing transition"
                for s in self.states if not s.terminal and s.id not in outgoing]

    def connectivity_warnings(self) -> list[str]:
        """every state must be reachable from an entry AND able to reach a terminal.

        forward reachability is the union over all `entry` states, falling back
        to IDEATION when none is marked; the reverse walk proves no sink-trap

        # Returns
        one warning per unreachable state and one per sink-trapped state
        """
        entries = [s.id for s in self.states if s.entry] or ["IDEATION"]
        forward: set[str] = set()
        for entry in entries:
            forward |= self.reachable(entry)
        out = [f"state {s.id} is unreachable from any entry" for s in self.states if s.id not in forward]
        back: dict[str, list[str]] = {}
        for t in self.transitions:
            back.setdefault(t.dst, []).append(t.src)
        co_reach: set[str] = set()
        frontier = [s.id for s in self.states if s.terminal]
        while frontier:
            node = frontier.pop()
            if node in co_reach:
                continue
            co_reach.add(node)
            frontier.extend(back.get(node, []))
        out.extend(f"state {s.id} cannot reach any terminal (sink-trap)"
                   for s in self.states if s.id not in co_reach)
        return out

    def owner_warnings(self) -> list[str]:
        """every owner must resolve to a loadable skill, an agent, a script, or a whitelist entry.

        compound owners split on `+` and a `:lens` suffix is dropped
        (brain-meta-style:plan -> brain-meta-style). a SCRIPT is a legitimate
        owner: `brain-recall` is the retrieval interface and no skill wraps it,
        so resolving against bin/ as well as skills/ is what keeps this honest
        rather than forcing a stub skill to exist for the check (P18, P19). an
        AGENT is legitimate for the same reason - the cold reviewers and the
        aav-style lenses are dispatched, not loaded - so agents/ resolves too,
        by directory scan rather than by a hardcoded list that has to be edited
        every time a lens is added. a flow that dispatches a non-existent owner
        is unsound, and this is what catches a mid-rename drift

        # Returns
        one warning per owner that resolves to nothing
        """
        # --------------------------------------------------
        # gather: every name an owner may legally resolve to
        # --------------------------------------------------
        known: set[str] = {p.name for p in LAYOUT.skills.iterdir() if p.is_dir()} if LAYOUT.skills.is_dir() else set()
        if LAYOUT.bin.is_dir():
            known |= {p.stem for p in LAYOUT.bin.iterdir() if p.is_file()}
        if LAYOUT.agents.is_dir():
            known |= {p.stem for p in LAYOUT.agents.rglob("*.md")}
        # --------------------------------------------------
        # scan: every state owner against that set
        # --------------------------------------------------
        whitelist = {"worker", "-"}
        out: list[str] = []
        for s in self.states:
            for part in s.owner.split("+"):
                skill = part.split(":")[0].strip()
                if skill and skill not in whitelist and skill not in known:
                    out.append(f"state {s.id} owner '{skill}' is not a known skill")
        return out

    def validate(self) -> list[str]:
        """check the flow is a sound, deterministic state machine.

        the result is cached - the flow does not change after read, and
        to_json / summary / main each ask for it

        # Returns
        a sorted list of warnings (empty means valid)
        """
        if self._warnings is not None:
            return self._warnings
        warnings: list[str] = []
        for check in (self.dangling_warnings, self.boundary_warnings, self.determinism_warnings,
                      self.exit_warnings, self.connectivity_warnings, self.owner_warnings,
                      self.mermaid_warnings):
            warnings.extend(check())
        self._warnings = sorted(set(warnings))
        return self._warnings

    def mermaid_warnings(self) -> list[str]:
        """check the rendered flowchart can actually PARSE, not merely match the data.

        the drift gate only ever proved the doc equalled a fresh build, so the
        committed chart sat unparseable for its whole life - every label was bare
        and carried the `(`, `:` and `->` that end one, and `STYLE` named a node
        after a mermaid keyword. a gate that measures the wrong property passes
        forever

        # Returns
        one warning per state whose rendering mermaid would reject
        """
        out: list[str] = []
        for s in self.states:
            if '"' in s.doc:
                out.append(f"state {s.id} doc contains a quote, which closes its mermaid label")
            if s.id.lower() in MERMAID_KEYWORDS and node_id(s.id) == s.id:
                out.append(f"state {s.id} is a mermaid keyword and has no alias")
        return out

    def adjacency(self) -> dict[str, list[str]]:
        """outgoing adjacency map for the transitions.

        # Returns
        a dict of state id -> list of destination ids
        """
        adj: dict[str, list[str]] = {}
        for t in self.transitions:
            adj.setdefault(t.src, []).append(t.dst)
        return adj

    def reachable(self, start: str) -> set[str]:
        """forward reachability set from a start state.

        # Arguments
        * `start` - the entry state id

        # Returns
        the set of reachable state ids
        """
        adj = self.adjacency()
        seen: set[str] = set()
        frontier = [start]
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            frontier.extend(adj.get(node, []))
        return seen

    def to_json(self) -> str:
        """render the flow as deterministic json text.

        # Returns
        a json string with states in source order, transitions sorted by
        (src, on, dst), and a trailing newline
        """
        ordered = sorted(self.transitions, key=lambda t: (t.src, t.on, t.dst))
        flow = {"states": [s.to_dict() for s in self.states],
                    "transitions": [t.to_dict() for t in ordered],
                    "boundary": next((t.dst for t in self.transitions if t.boundary), None),
                    "warnings": self.validate()}
        return json.dumps(flow, indent=2, ensure_ascii=False) + "\n"

    def to_mermaid(self) -> str:
        """render the flow as a mermaid stateDiagram, for the human-facing doc.

        # Returns
        a mermaid code block as a string, generated from the same data so the
        doc cannot drift from flow.json
        """
        entries = [s.id for s in self.states if s.entry] or ["IDEATION"]
        lines = ["```mermaid", "stateDiagram-v2"]
        lines.extend(f"    [*] --> {node_id(entry)}" for entry in entries)
        lines.append("")
        # --------------------------------------------------
        # declare each state as `state "<label>" as <id>`. the label is QUOTED
        # because the docs carry (), :, ?, -> and / , every one of which ends a
        # bare mermaid label; and the id is aliased because `style` is a mermaid
        # keyword that cannot name a node
        # --------------------------------------------------
        lines.extend(f'    state "{s.id} [{s.kind}] {mermaid_label(s.doc)}" as {node_id(s.id)}'
                     for s in self.states)
        lines.append("")
        for t in sorted(self.transitions, key=lambda t: (t.src, t.on, t.dst)):
            mark = " *boundary*" if t.boundary else ""
            lines.append(f"    {node_id(t.src)} --> {node_id(t.dst)}: {t.on}{mark}")
        lines.extend(f"    {node_id(s.id)} --> [*]" for s in self.states if s.terminal)
        lines.append("```")
        return "\n".join(lines) + "\n"

    def to_table(self) -> str:
        """render the state -> owner table, generated from the states.

        # Returns
        a markdown table (header + one row per state) with a trailing newline
        """
        lines = ["| state | kind | entry | regime | owner | recall |", "|---|---|---|---|---|---|"]
        for s in self.states:
            entry = str(s.entry).lower() if s.entry else ""
            lines.append(f"| {s.id} | {s.kind} | {entry} | {s.regime} | {s.owner} | {str(s.recall).lower()} |")
        return "\n".join(lines) + "\n"

    def to_doc(self) -> str:
        """render the entire DEV_FLOWCHART.md from the flow data.

        the whole doc - intro, diagram, table, stepping prose - is generated so
        it is drift-gated and can never diverge from flow.toml

        # Returns
        the full markdown contents of docs/DEV_FLOWCHART.md
        """
        return (DOC_HEADER + self.to_mermaid() + "\n"
                + DOC_TABLE_INTRO + self.to_table() + "\n"
                + DOC_STEPPING)

    def handoffs(self) -> list[tuple[Path, str]]:
        """the handoff block, rendered into every entry skill from one source.

        the block is what makes an entry actually reach the engine. rendering
        all four from one source is what keeps them from drifting apart (P28)

        # Returns
        the (path, content) pairs for each entry SKILL.md whose handoff block
        changed, or an empty list when every entry is already current
        """
        out: list[tuple[Path, str]] = []
        for name in ENTRY_SKILLS:
            path = LAYOUT.skills / name / "SKILL.md"
            if not path.is_file():
                continue
            body = read_text(path)
            block = f"{HANDOFF_BEGIN}\n{ENTRY_HANDOFF}{HANDOFF_END}\n"
            if HANDOFF_BEGIN in body and HANDOFF_END in body:
                head, rest = body.split(HANDOFF_BEGIN, 1)
                tail = rest.split(HANDOFF_END, 1)[1].lstrip("\n")
                rendered = f"{head}{block}\n{tail}"
            elif HANDOFF_ANCHOR in body:
                # migrate the hand-pasted copy: replace it in place, with markers
                head, rest = body.split(HANDOFF_ANCHOR, 1)
                tail = rest.split(HANDOFF_TAIL, 1)[1].lstrip("\n") if HANDOFF_TAIL in rest else ""
                rendered = f"{head.rstrip()}\n\n{block}\n{tail}"
            else:
                continue
            if rendered != body:
                out.append((path, rendered))
        return out

    def targets(self) -> list[tuple[Path, str]]:
        """the committed artifacts: flow.json, the flowchart doc, the handoffs.

        # Returns
        the (path, content) pairs for flow.json, docs/DEV_FLOWCHART.md, and every
        entry skill whose generated handoff block is out of date
        """
        return [(LAYOUT.flow_json, self.to_json()),
                (LAYOUT.docs / "DEV_FLOWCHART.md", self.to_doc()),
                *self.handoffs()]

    def summary(self) -> str:
        """a one-line build summary.

        # Returns
        the state/transition/warning counts
        """
        return (f"brain-flow done -> {self.out_dir}\n"
                f"  states: {len(self.states)} | transitions: {len(self.transitions)} | "
                f"warnings: {len(self.validate())}")


def main() -> None:
    """build the flow from flow.toml, or check/emit it.

    a broken flow (validation warnings) fails the build - a stale or unsound
    flow.json must never be committed
    """
    args = Args.from_argv()
    if unknown := args.unknown(Flag.CHECK, Flag.MERMAID):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    builder = FlowBuilder.read(LAYOUT.flow_toml, LAYOUT.flow_dir)
    # --------------------------------------------------
    # mermaid mode: emit the doc view from the same data
    # --------------------------------------------------
    if args.has(Flag.MERMAID):
        print(builder.to_mermaid(), end="")
        return
    # --------------------------------------------------
    # refuse to build an unsound flow
    # --------------------------------------------------
    warnings = builder.validate()
    if warnings and not args.has(Flag.CHECK):
        print(f"{TOOL}: INVALID flow.toml - not writing:")
        for warning in warnings:
            print(f"  warn: {warning}")
        sys.exit(Exit.DRIFT)
    builder.run(args, "brain-flow")


if __name__ == "__main__":
    main()
