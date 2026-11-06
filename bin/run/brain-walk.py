#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-walk: step the deterministic execution flow, one state at a time.

    b-walk -s PLANGATE -m build                   describe a state + its exits
    b-walk -s PLANGATE -o threshold_met -m build  the next state for that outcome
    b-walk -s PLANGATE -m build -d                print the doc even if shown earlier
    b-walk -l                                     print the legend: every command's flags

this is the b-recall of execution. the step is a pure function of the
authored flow.toml, read directly and validated on load through brainlib.Flow
(the same parse and checks b-flow renders from): the same (state, event,
mode) always yields the same next step - the brain follows the flowchart
because, to take a step, it must query this file. only how much prints depends
on the session (below). `-m` is required and must be one an `[[entries]]`
table declares; it decides between guarded sibling edges. the owner of a state
returns the outcome event, this walker only says where each event leads. that
keeps sequence (the flow) and knowledge (the graph) separate

a state prints after the legend - on a session's first walk every command's
row under one header line, on a later walk one line naming the call that
reprints it (below) - as its header (state, kind, owner), its doc, its
directives, then its exits when described. a later walk:

    legend: b-walk -l
    RECON work owner=brain-recall+brain-plan
    read fs; seed the relevant-file set from the task
    RECALL first, its principles are the method:
    b-recall <<'EOF'
    <task>
    EOF
    exits: seeded->EXPAND

reached by an outcome, the header opens `PLANGATE -threshold_met-> SANCTION`. a
RECALL directive is the state's `recall = true`; a boundary exit ends
`(boundary)`, a terminal state prints `terminal`

the legend and a state's doc each print in full once per session: a
SessionRecord over the session's walk log (brainlib.session) holds what was
shown, and a later walk prints the call that reprints it in its place. a
compaction empties the context, so what was shown before one prints again;
with no session id everything prints. the directives always print

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import (
    Args,
    DataLayout,
    Flag,
    Flow,
    Harnesses,
    Layout,
    NoVerdict,
    SessionRecord,
    State,
    Tool,
    Transition,
    UsageError,
)

# --------------------------------------------------
# external
# --------------------------------------------------
from collections.abc import Sequence
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages and the call it prints
TOOL = Layout.command(Path(__file__))
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()

# owners that must NOT produce a load directive
#   `-`                  a state with no owner
#   the recall script    a SCRIPT interface by design: `recall = true` runs
#                        it rather than loading a skill. an owner names the
#                        script's file, so it is matched by stem
# an ENTRY skill (flow.toml `[[entries]]`) is skipped too: it is already in
# context whenever its own region is walked - it is the caller - so directing
# it to load itself is noise at best and re-entry at worst
NOT_LOADABLE = {"-", LAYOUT.recall_script.stem}
# the session-log item that stands for the legend; `Flow.validate` keeps every state id upper case
LEGEND = "legend"


@dataclass(frozen=True)
class Walk:
    """one step of a walk: the flow, the mode it walks in, and what this session holds."""

    # the loaded, validated flow
    flow: Flow
    # the walk's declared mode, which decides between guarded siblings
    mode: str
    # the legend and the state docs this session has been shown in full
    record: SessionRecord
    # `-d`: print the doc even when this session was shown it
    full_doc: bool = False

    def describe(self, state: State) -> list[str]:
        """print a state, its directives, and every event it accepts in this mode.

        # Arguments
        * `state` - the state to describe; guarded exits the mode cannot take are not listed

        # Returns
        what printed in full, as `announce` gives it
        """
        shown = self.announce(state)
        exits = [f"{transition.on}->{transition.dst}{' (boundary)' if transition.boundary else ''}"
                 for transition in self.flow.exits(state.id, self.mode)]
        if exits:
            print(f"exits: {', '.join(exits)}")
        if state.terminal:
            print("terminal")
        return shown

    def advance(self, state: State, event: str) -> list[str]:
        """resolve one outcome event to the next state and print it.

        # Arguments
        * `state` - the current state
        * `event` - the outcome event the owner returned

        # Returns
        what printed in full, as `announce` gives it

        # Raises
        UsageError when no exit matches - naming the mode, because an edge that
        exists in the other one is the likeliest reason a walk stalls here
        """
        transition = self.flow.step(state.id, event, self.mode)
        if transition is None:
            raise UsageError(f"no exit from {state.id} on '{event}' in {self.mode} mode")
        return self.announce(self.flow.states[transition.dst], transition)

    def opening(self) -> str:
        """the legend, the first walk of a session; afterwards the call that prints it.

        # Returns

        the legend, or one line naming the `-l` call

        # Example

            >>> Walk(Flow.load(LAYOUT.flow_toml), "build", SessionRecord(TOOL)).opening().partition(",")[0]
            'legend: short=long'
        """
        if self.record.seen(LEGEND):
            return f"legend: {TOOL} {Flag.LEGEND.short}"
        return Tool.legend()

    def announce(self, state: State, via: Transition | None = None) -> list[str]:
        """print the legend or its pointer, a state's header, its doc once per session, and its directives.

        # Arguments
        * `state` - the state to announce
        * `via` - the transition that reached it, None when described in place

        # Returns
        what printed in full - the legend, the state's doc - for the session's walk log
        """
        shown = [item for item, full in ((LEGEND, not self.record.seen(LEGEND)), (state.id, self.prints_doc(state)))
                 if full]
        step = f"{via.src} -{via.on}-> " if via else ""
        print(self.opening())
        print(f"{step}{state.id} {state.kind} owner={state.owner}")
        print(self.doc_line(state))
        for line in (*self.recall_directive(state.binds, recall=state.recall), *self.owner_directive(state.owners)):
            print(line)
        return shown

    def prints_doc(self, state: State) -> bool:
        """whether a state's doc prints in full: asked for with `-d`, or not yet shown this session.

        # Arguments
        * `state` - the state whose doc is due

        # Returns
        True when the doc prints in full
        """
        return self.full_doc or not self.record.seen(state.id)

    def doc_line(self, state: State) -> str:
        """a state's doc, or the call that reprints it when this session was shown it already.

        # Arguments
        * `state` - the state whose doc line to print

        # Returns
        the doc, or `SessionRecord.earlier` with the `-d` call that reprints it

        # Example

            >>> from brainlib import Mark
            >>> import datetime as dt
            >>> flow = Flow.load(LAYOUT.flow_toml)
            >>> held = Mark(0, dt.datetime(2026, 11, 2, tzinfo=dt.UTC), frozenset({"IMPL"}))
            >>> walk = Walk(flow, "build", SessionRecord(TOOL, None, (held,)))
            >>> walk.doc_line(flow.states["IMPL"]).partition("context: ")[2]
            'b-walk -s IMPL -m build -d'
            >>> Walk(flow, "build", SessionRecord(TOOL)).doc_line(flow.states["IMPL"]) == flow.states["IMPL"].doc
            True
        """
        if self.prints_doc(state):
            return state.doc
        return SessionRecord.earlier(
            f"{TOOL} {Flag.STATE.short} {state.id} {Flag.MODE.short} {self.mode} {Flag.DOC.short}")

    @staticmethod
    def owner_call(base: str) -> str:
        """the literal call for one owner, resolved against the filesystem.

        an owner is an AGENT if an agent file defines it and a SKILL if a skill
        directory does; the name is not the discriminator. `brain-learner` is an
        agent, and a name-prefix rule would announce it as a skill, which loads
        the end-of-run learner into the very context it exists to be free of

        # Arguments

        * `base` - the bare owner name, lens suffix already stripped

        # Returns

        the directive line naming the tool call to make

        # Example

            >>> Walk.owner_call("aav-style-docs")
            "DISPATCH: Agent(subagent_type='aav-style-docs')"
        """
        agent = next(LAYOUT.agents.rglob(f"{base}.md"), None)
        if agent is not None:
            # agents under agents/brain/ are the brain's own, dispatched for a CLEARED
            # context (P03/P04); the rest carry a spec slice too large to inline
            cold = " COLD" if agent.parent.name == "brain" else ""
            return f"DISPATCH{cold}: Agent(subagent_type={base!r})"
        if (LAYOUT.skills / base / "SKILL.md").is_file():
            return f"LOAD FIRST: Skill({base})"
        return f"DISPATCH: Agent(subagent_type={base!r})"

    def owner_directive(self, owners: Sequence[str]) -> list[str]:
        """the literal call that must be made before a state's work begins.

        Naming an owner is not an instruction, and measurement says so: the one skill
        whose handoff carries a literal `Skill(...)` line loads reliably, while owners
        announced only as `owner=<name>` were loaded 4-24% of the time and their state's
        work got hand-rolled inline instead. So the directive is emitted, not implied

        # Arguments
        * `owners` - the state's bare owner names, composite split and lens dropped; an entry skill
          of the flow never gets a load directive

        # Returns
        the directive lines to print under the state, or an empty list when the state's
        owner is the entry itself or a script
        """
        entries = {entry.skill for entry in self.flow.entries}
        out = [self.owner_call(base) for base in owners
               if base and base not in NOT_LOADABLE and base not in entries]
        if out:
            out.append("^ make the call, not a Read; never this state's work inline")
        return out

    @staticmethod
    def recall_directive(binds: Sequence[str], *, recall: bool) -> list[str]:
        """the literal recall command for a state that declares `recall = true`.

        Emitted for the same reason `owner_directive` is: a bare `recall=True` is a
        FLAG, and a flag is not an instruction. Measured over one build session -
        `recall = true` states were entered eight times during execution and
        the recall script ran zero times, so principle-10 ("report only at gates")
        was never in context and the phase boundaries turned into status reports
        The owner line, which carries a literal call, is obeyed

        # Arguments
        * `binds` - the state's context tags, rendered as `-b` arguments so the
          principles a scored query ranks off the bottom still reach the owner
        * `recall` - the state's `recall` field, passed by keyword so the call site
          reads as a condition rather than a bare True (FBT001)

        # Returns
        the directive lines to print under the state, empty when recall is false.
        the task travels on stdin through a quoted heredoc, printed flush left so
        a copied `EOF` still ends it

        # Example

            >>> Walk.recall_directive(["code"], recall=True)[1]
            "b-recall -b code <<'EOF'"
        """
        if not recall:
            return []
        bound = "".join(f" {Flag.BINDS.short} {context}" for context in binds)
        return [
            "RECALL first, its principles are the method:",
            f"{Layout.command(LAYOUT.recall_script)}{bound} <<'EOF'",
            "<task>",
            "EOF",
        ]


def main(args: Args) -> None:
    """describe a state, or resolve its next step for an outcome event.

    the flow is validated first: a flow with warnings is never stepped

    # Arguments

    * `args` - the parsed command line; `-l` prints the legend alone; else `-s`
      and `-m` are required, `-o` names the outcome event to advance on
      (absent, the state is described), and `-d` prints the doc even when this
      session was shown it

    # Raises

    UsageError for a missing flag or an unknown mode or state; NoVerdict when the
    authored flow does not validate
    """
    # --------------------------------------------------
    # the legend alone, on request, marked shown like the one a first walk prints
    # --------------------------------------------------
    record = SessionRecord.load(TOOL, Harnesses.discover().running(), DataLayout.discover().local.writable())
    if args.has(Flag.LEGEND):
        print(Tool.legend())
        record.mark([LEGEND])
        return
    # --------------------------------------------------
    # parse
    # --------------------------------------------------
    state_id, event, mode = args.value(Flag.STATE), args.value(Flag.ON), args.value(Flag.MODE)
    if not state_id or not mode:
        raise UsageError(f"{Flag.STATE.spelling} and {Flag.MODE.spelling} are both required")
    # --------------------------------------------------
    # load and validate the authored flow; an unsound one is never stepped
    # --------------------------------------------------
    flow = Flow.load(LAYOUT.flow_toml)
    if warnings := flow.validate(LAYOUT):
        for warning in warnings:
            print(f"  warn: {warning}", file=sys.stderr)
        raise NoVerdict("INVALID flow.toml - refusing to step")
    if mode not in flow.modes():
        raise UsageError(f"unknown mode {mode}; flow.toml declares {', '.join(flow.modes())}")
    # --------------------------------------------------
    # resolve the state
    # --------------------------------------------------
    if state_id not in flow.states:
        raise UsageError(f"unknown state {state_id}")
    state = flow.states[state_id]
    # --------------------------------------------------
    # the legend or its pointer, then describe, or advance on the outcome event, against what this session was shown
    # --------------------------------------------------
    walk = Walk(flow, mode, record, full_doc=args.has(Flag.DOC))
    shown = walk.advance(state, event) if event else walk.describe(state)
    # --------------------------------------------------
    # what printed in full is marked, so a later walk this session prints its pointer instead
    # --------------------------------------------------
    if shown:
        record.mark(shown)


if __name__ == "__main__":
    Tool.of(TOOL, __doc__, modes=((Flag.LEGEND,), (Flag.STATE, Flag.MODE, Flag.ON, Flag.DOC))).run(main)
