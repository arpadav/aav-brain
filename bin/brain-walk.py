#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-walk: step the deterministic execution flow, one state at a time.

    python3 brain-walk.py --state PLANGATE                  describe a state + its exits
    python3 brain-walk.py --state PLANGATE --on approved    the next state for that outcome

this is the brain-recall of execution: a pure function over the committed
flow.json (built by brain-flow.py from flow.toml). same (state, event) always
yields the same next step - the brain follows the flowchart because, to take a
step, it must query this file. it shares the State/Transition datatypes with
brain-flow via brainlib (one definition, written by flow, read by walk). it
reads only flow.json; the owner of a state returns the outcome event, this
walker only says where each event leads. that keeps sequence (the flow) and
knowledge (the graph) separate.

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import sys
from dataclasses import dataclass, field
from pathlib import Path

from brainlib import State, Transition, load_json

# --------------------------------------------------
# constants
# --------------------------------------------------
# the built flow this walker reads; never re-derives it from flow.toml
FLOW = (Path(__file__).resolve().parent / "../brain/flow/flow.json").resolve()

# --------------------------------------------------
# types
# --------------------------------------------------
@dataclass
class Flow:
    """the built execution flow, indexed for deterministic stepping."""

    states: dict = field(default_factory=dict)
    transitions: list = field(default_factory=list)

    @classmethod
    def load(cls, path):
        """load flow.json into typed states (by id) and transitions.

        # Arguments
        * `path` - the flow.json path.

        # Returns
        a Flow holding shared State / Transition objects.
        """
        data = load_json(path, "brain-flow")
        states = {s["id"]: State.from_dict(s) for s in data["states"]}
        transitions = [Transition.from_dict(t) for t in data["transitions"]]
        return cls(states=states, transitions=transitions)

    def exits(self, state_id):
        """the transitions leaving a state, in stable order.

        # Arguments
        * `state_id` - the source state.

        # Returns
        the list of outgoing Transitions.
        """
        return [t for t in self.transitions if t.src == state_id]

    def step(self, state_id, event):
        """resolve the single next transition for a state and outcome event.

        # Arguments
        * `state_id` - the current state.
        * `event` - the outcome event the owner returned.

        # Returns
        the matching Transition, or None if no exit matches (e.g. a terminal).
        """
        for t in self.exits(state_id):
            if t.on == event:
                return t
        return None


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """describe a state, or resolve its next step for an outcome event."""
    args = sys.argv[1:]
    state_id = args[args.index("--state") + 1] if "--state" in args else ""
    event = args[args.index("--on") + 1] if "--on" in args else ""
    if not state_id:
        sys.exit("usage: brain-walk.py --state <ID> [--on <event>]")
    flow = Flow.load(FLOW)
    if state_id not in flow.states:
        sys.exit(f"brain-walk: unknown state {state_id}")
    state = flow.states[state_id]
    # --------------------------------------------------
    # no event: describe the state and the events it accepts
    # --------------------------------------------------
    if not event:
        print(f"{state.id} [{state.kind}] owner={state.owner} recall={state.recall}")
        print(f"  {state.doc}")
        for t in flow.exits(state_id):
            mark = " *BOUNDARY*" if t.boundary else ""
            print(f"  on {t.on:<14} -> {t.dst}{mark}")
        if state.terminal:
            print("  (terminal)")
        return
    # --------------------------------------------------
    # event given: resolve the next state deterministically
    # --------------------------------------------------
    transition = flow.step(state_id, event)
    if transition is None:
        sys.exit(f"brain-walk: no transition from {state_id} on '{event}'")
    nxt = flow.states[transition.dst]
    print(f"{state.id} --{event}--> {nxt.id} [{nxt.kind}] owner={nxt.owner} recall={nxt.recall}")
    print(f"  {nxt.doc}")


if __name__ == "__main__":
    main()
