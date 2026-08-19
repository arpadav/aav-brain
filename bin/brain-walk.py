#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
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
knowledge (the graph) separate

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Flag, Layout, Mode, State, Transition, load_json

# --------------------------------------------------
# external
# --------------------------------------------------
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()

@dataclass
class Flow:
    """the built execution flow, indexed for deterministic stepping."""

    states: dict[str, State] = field(default_factory=dict)
    transitions: list[Transition] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "Flow":
        """load flow.json into typed states (by id) and transitions.

        # Arguments
        * `path` - the flow.json path

        # Returns
        a Flow holding shared State / Transition objects
        """
        data = load_json(path, "brain-flow")
        states = {s["id"]: State.from_dict(s) for s in data["states"]}
        transitions = [Transition.from_dict(t) for t in data["transitions"]]
        return cls(states=states, transitions=transitions)

    def exits(self, state_id: str, mode: Mode = Mode.BUILD) -> list[Transition]:
        """the transitions leaving a state in a given mode, in stable order.

        # Arguments
        * `state_id` - the source state
        * `mode` - the walk's declared mode; a guarded edge this mode does not
          satisfy is not an exit at all, and is omitted rather than listed

        # Returns
        the list of outgoing Transitions available in this mode
        """
        return [t for t in self.transitions if t.src == state_id and mode.satisfies(t.guard)]

    def step(self, state_id: str, event: str, mode: Mode = Mode.BUILD) -> Transition | None:
        """resolve the single next transition for a state, event and mode.

        # Arguments
        * `state_id` - the current state
        * `event` - the outcome event the owner returned
        * `mode` - the walk's declared mode, which decides between guarded siblings

        # Returns
        the matching Transition, or None if no exit matches (e.g. a terminal)
        """
        for t in self.exits(state_id, mode):
            if t.on == event:
                return t
        return None


# owners that must NOT produce a load directive
#   `-`                  a state with no owner
#   brain-recall         a SCRIPT interface by design: `recall = true` runs
#                        bin/brain-recall.py rather than loading a skill
#   the four ENTRY skills is already in context whenever its own region is being
#                        walked - it is the caller - so directing it to load
#                        itself is noise at best and re-entry at worst
NOT_LOADABLE = {
    "-",
    "brain-recall",
    "brain-meta-recall",
    "brain-plan",
    "brain-execute",
    "brain-review",
    "brain-self-refine",
}


def owner_call(base: str) -> str:
    """the literal call for one owner, resolved against the filesystem.

    an owner is an AGENT if an agent file defines it and a SKILL if a skill
    directory does; the name is not the discriminator. a hardcoded whitelist got
    this wrong the moment a new brain agent was added - `brain-learner` is an
    agent, and a name-prefix rule announced it as a skill, which would have
    loaded the end-of-run learner into the very context it exists to be free of

    # Arguments

    * `base` - the bare owner name, lens suffix already stripped

    # Returns

    the directive line naming the tool call to make

    # Example

        >>> owner_call("aav-style-docs")
        "  DISPATCH ITS OWNER:  Agent(subagent_type='aav-style-docs')"
    """
    agent = next(LAYOUT.agents.rglob(f"{base}.md"), None)
    if agent is not None:
        # agents under agents/brain/ are the brain's own, dispatched for a CLEARED
        # context (P03/P04); the rest carry a spec slice too large to inline
        cold = " COLD" if agent.parent.name == "brain" else ""
        return f"  DISPATCH ITS OWNER{cold}:  Agent(subagent_type={base!r})"
    if (LAYOUT.skills / base / "SKILL.md").is_file():
        return f"  LOAD ITS OWNER FIRST:  Skill({base})"
    return f"  DISPATCH ITS OWNER:  Agent(subagent_type={base!r})"


def owner_directive(owner: str) -> list[str]:
    """the literal call that must be made before a state's work begins.

    Naming an owner is not an instruction, and measurement says so: the one skill
    whose handoff carries a literal `Skill(...)` line loads reliably, while owners
    announced only as `owner=<name>` were loaded 4-24% of the time and their state's
    work got hand-rolled inline instead. So the directive is emitted, not implied

    # Arguments
    * `owner` - the state's `owner` field, which may carry a `:lens` suffix or be a
      `a+b` composite of several owners

    # Returns
    the directive lines to print under the state, or an empty list when the state's
    owner is the entry itself or a script
    """
    out: list[str] = []
    for part in owner.split("+"):
        base = part.split(":")[0].strip()
        if not base or base in NOT_LOADABLE:
            continue
        out.append(owner_call(base))
    if out:
        out.append("  ^ the literal tool call, not a Read. do NOT do this state's work inline.")
    return out


def recall_directive(binds: Sequence[str], *, recall: bool) -> list[str]:
    """the literal recall command for a state that declares `recall = true`.

    Emitted for the same reason `owner_directive` is: a bare `recall=True` is a
    FLAG, and a flag is not an instruction. Measured over one build session -
    `recall = true` states were entered eight times during execution and
    `brain-recall.py` ran zero times, so principle-10 ("report only at gates")
    was never in context and the phase boundaries turned into status reports
    The owner line, which carries a literal call, is obeyed

    # Arguments
    * `binds` - the state's context tags, rendered as `--binds` arguments so the
      cards a scored query ranks off the bottom still reach the owner
    * `recall` - the state's `recall` field, passed by keyword so the call site
      reads as a condition rather than a bare True (FBT001)

    # Returns
    the directive lines to print under the state, empty when recall is false
    """
    if not recall:
        return []
    bound = "".join(f" --binds {context}" for context in binds)
    return [
        f'  RECALL FIRST:  python3 $AAV_BRAIN/bin/brain-recall.py "<active task>"{bound}',
        "  ^ run it before this state's work; the cards it returns ARE the method.",
    ]


def main() -> None:
    """describe a state, or resolve its next step for an outcome event."""
    # --------------------------------------------------
    # parse
    # --------------------------------------------------
    args = Args.from_argv()
    if unknown := args.unknown(Flag.STATE, Flag.ON, Flag.SELF_REFINE):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    state_id, event = args.value(Flag.STATE), args.value(Flag.ON)
    mode = Mode.of(self_refine=args.has(Flag.SELF_REFINE))
    if not state_id:
        sys.exit("usage: brain-walk.py --state <ID> [--on <event>] [--self-refine]")
    # --------------------------------------------------
    # resolve the state against the built flow
    # --------------------------------------------------
    flow = Flow.load(LAYOUT.flow_json)
    if state_id not in flow.states:
        sys.exit(f"{TOOL}: unknown state {state_id}")
    state = flow.states[state_id]
    # --------------------------------------------------
    # describe, or advance on the outcome event
    # --------------------------------------------------
    if not event:
        describe(flow, state, mode)
        return
    advance(flow, state, event, mode)


def describe(flow: Flow, state: State, mode: Mode = Mode.BUILD) -> None:
    """print a state, its directives, and every event it accepts in this mode.

    # Arguments
    * `flow` - the loaded flow
    * `state` - the state to describe
    * `mode` - the walk's declared mode; guarded exits it cannot take are not listed
    """
    print(f"{state.id} [{state.kind}] owner={state.owner} recall={state.recall}")
    print(f"  {state.doc}")
    for line in recall_directive(state.binds, recall=state.recall):
        print(line)
    for line in owner_directive(state.owner):
        print(line)
    for transition in flow.exits(state.id, mode):
        mark = " *BOUNDARY*" if transition.boundary else ""
        print(f"  on {transition.on:<14} -> {transition.dst}{mark}")
    if state.terminal:
        print("  (terminal)")


def advance(flow: Flow, state: State, event: str, mode: Mode = Mode.BUILD) -> None:
    """resolve one outcome event to the next state and print it.

    # Arguments
    * `flow` - the loaded flow
    * `state` - the current state
    * `event` - the outcome event the owner returned
    * `mode` - the walk's declared mode, which decides between guarded siblings

    # Raises
    `SystemExit` when no exit matches - naming the mode, because an edge that
    exists in the other one is the likeliest reason a walk stalls here
    """
    transition = flow.step(state.id, event, mode)
    if transition is None:
        sys.exit(f"{TOOL}: no exit from {state.id} on '{event}' in {mode.value} mode")
    nxt = flow.states[transition.dst]
    print(f"{state.id} --{event}--> {nxt.id} [{nxt.kind}] owner={nxt.owner} recall={nxt.recall}")
    print(f"  {nxt.doc}")
    for line in recall_directive(nxt.binds, recall=nxt.recall):
        print(line)
    for line in owner_directive(nxt.owner):
        print(line)


if __name__ == "__main__":
    main()
