#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""brain-flow: build the deterministic execution flow from flow.toml.

    python3 brain-flow.py            build brain/flow/flow.json
    python3 brain-flow.py --check    build to memory, fail if it drifts from disk
    python3 brain-flow.py --mermaid  print the mermaid view (for docs)

the flow is AUTHORED as data in brain/flow/flow.toml (states + transitions),
exactly the way the knowledge graph is authored as data in the markdown cards.
this script READS that data, validates it, and writes the canonical flow.json -
it does not hardcode the states. brain-walk.py then steps flow.json.

the flow is the EXECUTION SEQUENCE, kept strictly separate from the knowledge
GRAPH (brain-graph.py): the flow has states/transitions, the graph has
nodes/edges, and the coupling is one-directional (a state may CALL recall via
its `recall` flag; the graph never calls the flow). see P30.

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from brainlib import Artifact, State, Transition, find_brain

# --------------------------------------------------
# constants
# --------------------------------------------------
# the authored flow source and the directory the built flow lands in
FLOW_DIR = (Path(__file__).resolve().parent / "../brain/flow").resolve()
FLOW_TOML = FLOW_DIR / "flow.toml"
# the human-facing flowchart doc, generated from the same data (never hand-edited).
DOCS_DIR = (Path(__file__).resolve().parent / "../docs").resolve()

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
hand-edit it; re-run the builder after editing flow.toml so it can never drift (the drift this file
used to have). it is drift-gated: `brain-flow.py --check` fails if this file is stale. a state may
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

# --------------------------------------------------
# types
# --------------------------------------------------
@dataclass
class FlowBuilder(Artifact):
    """reads flow.toml, validates it, and builds flow.json."""

    states: list = None
    transitions: list = None

    @classmethod
    def read(cls, toml_path, out_dir):
        """load the authored flow data from toml into typed states/transitions.

        # Arguments
        * `toml_path` - the flow.toml source path.
        * `out_dir` - the directory flow.json is written to.

        # Returns
        a FlowBuilder holding the parsed States and Transitions.
        """
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        states = [State.from_dict(s) for s in data.get("states", [])]
        transitions = [Transition.from_dict(t) for t in data.get("transitions", [])]
        return cls(out_dir=out_dir, states=states, transitions=transitions)

    def validate(self):
        """check the flow is a sound, deterministic state machine.

        the result is cached - the flow does not change after read, and
        to_json / summary / main each ask for it.

        # Returns
        a sorted list of warnings (empty means valid).
        """
        if getattr(self, "_warnings", None) is not None:
            return self._warnings
        warnings = []
        ids = {s.id for s in self.states}
        terminals = {s.id for s in self.states if s.terminal}
        # --------------------------------------------------
        # no dangling transition endpoints
        # --------------------------------------------------
        for t in self.transitions:
            if t.src not in ids:
                warnings.append(f"transition from unknown state {t.src}")
            if t.dst not in ids:
                warnings.append(f"transition to unknown state {t.dst}")
        # --------------------------------------------------
        # exactly one sanction boundary
        # --------------------------------------------------
        boundaries = [t for t in self.transitions if t.boundary]
        if len(boundaries) != 1:
            warnings.append(f"expected exactly 1 boundary transition, found {len(boundaries)}")
        # --------------------------------------------------
        # no duplicate (src, on): step() must be unambiguous
        # --------------------------------------------------
        seen = set()
        for t in self.transitions:
            key = (t.src, t.on)
            if key in seen:
                warnings.append(f"duplicate transition ({t.src}, {t.on}) - step is ambiguous")
            seen.add(key)
        # --------------------------------------------------
        # every non-terminal state has an exit
        # --------------------------------------------------
        outgoing = {t.src for t in self.transitions}
        for s in self.states:
            if not s.terminal and s.id not in outgoing:
                warnings.append(f"non-terminal state {s.id} has no outgoing transition")
        # --------------------------------------------------
        # forward: every state reachable from SOME entry node (multi-entry: the
        # union over all `entry` states, falling back to IDEATION if none marked)
        # --------------------------------------------------
        entries = [s.id for s in self.states if s.entry] or ["IDEATION"]
        forward = set()
        for entry in entries:
            forward |= self.reachable(entry)
        for s in self.states:
            if s.id not in forward:
                warnings.append(f"state {s.id} is unreachable from any entry")
        # --------------------------------------------------
        # reverse: every state can reach a terminal (no sink-trap)
        # --------------------------------------------------
        back = {}
        for t in self.transitions:
            back.setdefault(t.dst, []).append(t.src)
        co_reach = set()
        frontier = list(terminals)
        while frontier:
            node = frontier.pop()
            if node in co_reach:
                continue
            co_reach.add(node)
            frontier.extend(back.get(node, []))
        for s in self.states:
            if s.id not in co_reach:
                warnings.append(f"state {s.id} cannot reach any terminal (sink-trap)")
        # --------------------------------------------------
        # every owner resolves to a real skill: split compound owners on `+`,
        # drop the `:lens` suffix (brain-meta-style:plan -> brain-meta-style), and whitelist
        # `worker`, `-`, and the two cold agents. a flow that dispatches a
        # non-existent owner is unsound - this is what catches a mid-rename drift.
        # --------------------------------------------------
        skills_dir = find_brain() / "agentic-files" / "skills"
        known = {p.name for p in skills_dir.iterdir() if p.is_dir()} if skills_dir.is_dir() else set()
        owner_whitelist = {"worker", "-", "brain-review-gate", "brain-verifier"}
        for s in self.states:
            for part in s.owner.split("+"):
                skill = part.split(":")[0].strip()
                if skill and skill not in owner_whitelist and skill not in known:
                    warnings.append(f"state {s.id} owner '{skill}' is not a known skill")
        self._warnings = sorted(set(warnings))
        return self._warnings

    def adjacency(self):
        """outgoing adjacency map for the transitions.

        # Returns
        a dict of state id -> list of destination ids.
        """
        adj = {}
        for t in self.transitions:
            adj.setdefault(t.src, []).append(t.dst)
        return adj

    def reachable(self, start):
        """forward reachability set from a start state.

        # Arguments
        * `start` - the entry state id.

        # Returns
        the set of reachable state ids.
        """
        adj = self.adjacency()
        seen, frontier = set(), [start]
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            frontier.extend(adj.get(node, []))
        return seen

    def to_json(self):
        """render the flow as deterministic json text.

        # Returns
        a json string with states in source order, transitions sorted by
        (src, on, dst), and a trailing newline.
        """
        ordered = sorted(self.transitions, key=lambda t: (t.src, t.on, t.dst))
        flow = dict(states=[s.to_dict() for s in self.states],
                    transitions=[t.to_dict() for t in ordered],
                    boundary=next((t.dst for t in self.transitions if t.boundary), None),
                    warnings=self.validate())
        return json.dumps(flow, indent=2, ensure_ascii=False) + "\n"

    def to_mermaid(self):
        """render the flow as a mermaid stateDiagram, for the human-facing doc.

        # Returns
        a mermaid code block as a string, generated from the same data so the
        doc cannot drift from flow.json.
        """
        entries = [s.id for s in self.states if s.entry] or ["IDEATION"]
        lines = ["```mermaid", "stateDiagram-v2"]
        for entry in entries:
            lines.append(f"    [*] --> {entry}")
        for s in self.states:
            lines.append(f"    {s.id}: {s.id} [{s.kind}] {s.doc}")
        for t in sorted(self.transitions, key=lambda t: (t.src, t.on, t.dst)):
            mark = " *boundary*" if t.boundary else ""
            lines.append(f"    {t.src} --> {t.dst}: {t.on}{mark}")
        for s in self.states:
            if s.terminal:
                lines.append(f"    {s.id} --> [*]")
        lines.append("```")
        return "\n".join(lines) + "\n"

    def to_table(self):
        """render the state -> owner table, generated from the states.

        # Returns
        a markdown table (header + one row per state) with a trailing newline.
        """
        lines = ["| state | kind | entry | regime | owner | recall |", "|---|---|---|---|---|---|"]
        for s in self.states:
            entry = str(s.entry).lower() if s.entry else ""
            lines.append(f"| {s.id} | {s.kind} | {entry} | {s.regime} | {s.owner} | {str(s.recall).lower()} |")
        return "\n".join(lines) + "\n"

    def to_doc(self):
        """render the entire DEV_FLOWCHART.md from the flow data.

        the whole doc - intro, diagram, table, stepping prose - is generated so
        it is drift-gated and can never diverge from flow.toml.

        # Returns
        the full markdown contents of docs/DEV_FLOWCHART.md.
        """
        return (DOC_HEADER + self.to_mermaid() + "\n"
                + DOC_TABLE_INTRO + self.to_table() + "\n"
                + DOC_STEPPING)

    def targets(self):
        """the committed artifacts: flow.json and the generated flowchart doc.

        # Returns
        the (path, content) pairs for flow.json and docs/DEV_FLOWCHART.md.
        """
        return [(self.out_dir / "flow.json", self.to_json()),
                (DOCS_DIR / "DEV_FLOWCHART.md", self.to_doc())]

    def summary(self):
        """a one-line build summary.

        # Returns
        the state/transition/warning counts.
        """
        return (f"brain-flow done -> {self.out_dir}\n"
                f"  states: {len(self.states)} | transitions: {len(self.transitions)} | "
                f"warnings: {len(self.validate())}")


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """build the flow from flow.toml, or check/emit it.

    a broken flow (validation warnings) fails the build - a stale or unsound
    flow.json must never be committed.
    """
    builder = FlowBuilder.read(FLOW_TOML, FLOW_DIR)
    # --------------------------------------------------
    # mermaid mode: emit the doc view from the same data
    # --------------------------------------------------
    if "--mermaid" in sys.argv:
        print(builder.to_mermaid(), end="")
        return
    # --------------------------------------------------
    # refuse to build an unsound flow
    # --------------------------------------------------
    warnings = builder.validate()
    if warnings and "--check" not in sys.argv:
        print("brain-flow: INVALID flow.toml - not writing:")
        for warning in warnings:
            print(f"  warn: {warning}")
        sys.exit(1)
    builder.run(sys.argv, "brain-flow")


if __name__ == "__main__":
    main()
