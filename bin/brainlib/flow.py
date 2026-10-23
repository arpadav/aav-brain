"""brainlib.flow: the execution flow, read straight from flow.toml and validated.

brain-flow renders the human-facing flowchart from it and brain-walk steps it;
both load it through `Flow.load` and both refuse an unsound one through
`Flow.validate`, so there is one parse and one set of checks (P31). the walk
reads the authored toml directly - there is no built intermediate to go stale

entries and modes are DATA: each `[[entries]]` table names the skill that
starts a walk, the state it seeds, and the mode it walks in. a transition
`guard` names one of those modes (`!mode` negates), so adding an entry is a
flow.toml edit, never a code edit

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.model import State, Transition
from brainlib.paths import Layout
from brainlib.text import read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class Entry:
    """one way into the flow: the skill he types, where it starts, how it walks."""

    skill: str
    state: str
    mode: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entry":
        """reconstruct an Entry from a flow.toml `[[entries]]` table.

        # Arguments
        * `data` - the entry mapping

        # Returns
        an Entry
        """
        return cls(skill=data["skill"], state=data["state"], mode=data["mode"])


@dataclass
class Flow:
    """the authored execution flow: states by id, transitions, entries."""

    states: dict[str, State] = field(default_factory=dict)
    transitions: list[Transition] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "Flow":
        """parse flow.toml into typed states, transitions and entries.

        # Arguments
        * `path` - the flow.toml path

        # Returns
        a Flow; call `validate` before trusting it
        """
        data = tomllib.loads(read_text(path))
        return cls(states={s["id"]: State.from_dict(s) for s in data.get("states", [])},
                   transitions=[Transition.from_dict(t) for t in data.get("transitions", [])],
                   entries=[Entry.from_dict(e) for e in data.get("entries", [])])

    def modes(self) -> list[str]:
        """every mode a walk may declare, named by the entries.

        # Returns
        the distinct entry modes, sorted
        """
        return sorted({e.mode for e in self.entries})

    def entry_of(self, state_id: str) -> Entry | None:
        """the entry seeding a state, if any.

        # Arguments
        * `state_id` - the state id

        # Returns
        the first Entry whose state it is, or None
        """
        return next((e for e in self.entries if e.state == state_id), None)

    @staticmethod
    def satisfies(mode: str, guard: str) -> bool:
        """whether a transition's guard admits a mode.

        an empty guard admits every mode; `name` admits only that mode; `!name`
        admits every other

        # Arguments
        * `mode` - the walk's declared mode
        * `guard` - the transition's guard string

        # Returns
        true when the guarded edge is available in this mode

        # Example

            >>> Flow.satisfies("build", ""), Flow.satisfies("build", "!edit")
            (True, True)
            >>> Flow.satisfies("build", "edit")
            False
        """
        if not guard:
            return True
        return (guard.lstrip("!") == mode) != guard.startswith("!")

    def exits(self, state_id: str, mode: str) -> list[Transition]:
        """the transitions leaving a state in a given mode, in source order.

        # Arguments
        * `state_id` - the source state
        * `mode` - the walk's declared mode; a guarded edge it does not satisfy
          is not an exit at all

        # Returns
        the outgoing Transitions available in this mode
        """
        return [t for t in self.transitions if t.src == state_id and self.satisfies(mode, t.guard)]

    def step(self, state_id: str, event: str, mode: str) -> Transition | None:
        """resolve the single next transition for a state, event and mode.

        # Arguments
        * `state_id` - the current state
        * `event` - the outcome event the owner returned
        * `mode` - the walk's declared mode, which decides between guarded siblings

        # Returns
        the matching Transition, or None if no exit matches (e.g. a terminal)
        """
        return next((t for t in self.exits(state_id, mode) if t.on == event), None)

    # --------------------------------------------------
    # validation
    # --------------------------------------------------
    def dangling_warnings(self) -> list[str]:
        """one warning per transition or entry endpoint that names no state.

        # Returns
        the warnings, one per unknown src, dst or entry state
        """
        out: list[str] = []
        for t in self.transitions:
            if t.src not in self.states:
                out.append(f"transition from unknown state {t.src}")
            if t.dst not in self.states:
                out.append(f"transition to unknown state {t.dst}")
        out.extend(f"entry {e.skill} seeds unknown state {e.state}"
                   for e in self.entries if e.state not in self.states)
        return out

    def mode_warnings(self) -> list[str]:
        """every guard must name a mode some entry declares.

        a typo in a guard would otherwise make its edge silently unreachable

        # Returns
        one warning per guard naming an undeclared mode, plus one if no entry exists
        """
        modes = set(self.modes())
        out = [] if self.entries else ["flow declares no [[entries]]"]
        out.extend(f"transition ({t.src}, {t.on}) guard {t.guard!r} names no entry mode"
                   for t in self.transitions if t.guard and t.guard.lstrip("!") not in modes)
        return out

    def boundary_warnings(self) -> list[str]:
        """the flow must carry exactly one sanction boundary.

        # Returns
        a single warning when the count is wrong, else nothing
        """
        count = sum(1 for t in self.transitions if t.boundary)
        return [] if count == 1 else [f"expected exactly 1 boundary transition, found {count}"]

    def determinism_warnings(self) -> list[str]:
        """(src, on, mode) must resolve to exactly one edge, or step() is not a function.

        guarded siblings are legal only when their guards PARTITION the modes;
        keying on (src, on, guard) alone would pass `""` and `"edit"` together,
        which both admit an edit walk

        # Returns
        one warning per (src, on) pair that resolves to two edges in some mode
        """
        by_key: dict[tuple[str, str], list[Transition]] = {}
        for t in self.transitions:
            by_key.setdefault((t.src, t.on), []).append(t)
        out: list[str] = []
        for (src, on), edges in sorted(by_key.items()):
            for mode in self.modes():
                taken = [t for t in edges if self.satisfies(mode, t.guard)]
                if len(taken) > 1:
                    guards = ", ".join(repr(t.guard) for t in taken)
                    out.append(f"transition ({src}, {on}) resolves to {len(taken)} edges "
                               f"in mode {mode} (guards: {guards}) - step is ambiguous")
        return out

    def exit_warnings(self) -> list[str]:
        """every non-terminal state needs a way out.

        # Returns
        one warning per non-terminal state with no outgoing transition
        """
        outgoing = {t.src for t in self.transitions}
        return [f"non-terminal state {s.id} has no outgoing transition"
                for s in self.states.values() if not s.terminal and s.id not in outgoing]

    def connectivity_warnings(self) -> list[str]:
        """every state must be reachable from an entry AND able to reach a terminal.

        # Returns
        one warning per unreachable state and one per sink-trapped state
        """
        forward: dict[str, list[str]] = {}
        back: dict[str, list[str]] = {}
        for t in self.transitions:
            forward.setdefault(t.src, []).append(t.dst)
            back.setdefault(t.dst, []).append(t.src)
        reached = self.closure([e.state for e in self.entries], forward)
        co_reached = self.closure([s.id for s in self.states.values() if s.terminal], back)
        return ([f"state {s} is unreachable from any entry" for s in self.states if s not in reached]
                + [f"state {s} cannot reach any terminal (sink-trap)" for s in self.states if s not in co_reached])

    @staticmethod
    def closure(seeds: list[str], adjacency: dict[str, list[str]]) -> set[str]:
        """every node reachable from the seeds over an adjacency map.

        # Arguments
        * `seeds` - the start node ids
        * `adjacency` - node id -> neighbour ids

        # Returns
        the reachable set, seeds included
        """
        seen: set[str] = set()
        frontier = list(seeds)
        while frontier:
            node = frontier.pop()
            if node not in seen:
                seen.add(node)
                frontier.extend(adjacency.get(node, []))
        return seen

    def owner_warnings(self, layout: Layout) -> list[str]:
        """every owner must resolve to a skill, an agent, a script, or a whitelist entry.

        compound owners split on `+` and a `:lens` suffix is dropped. scripts and
        agents resolve by directory scan, not a hardcoded list, so a flow that
        dispatches a non-existent owner (a mid-rename drift) is caught (P18, P19)

        # Arguments
        * `layout` - the store layout the owners resolve against

        # Returns
        one warning per owner that resolves to nothing
        """
        known = {"worker", "-"}
        if layout.skills.is_dir():
            known |= {p.name for p in layout.skills.iterdir() if p.is_dir()}
        if layout.bin.is_dir():
            known |= {p.stem for p in layout.bin.rglob("*.py") if "brainlib" not in p.parts}
        if layout.agents.is_dir():
            known |= {p.stem for p in layout.agents.rglob("*.md")}
        return [f"state {s.id} owner '{name}' is not a known skill"
                for s in self.states.values()
                for name in (part.split(":")[0].strip() for part in s.owner.split("+"))
                if name and name not in known]

    def validate(self, layout: Layout) -> list[str]:
        """check the flow is a sound, deterministic state machine.

        # Arguments
        * `layout` - the store layout owners resolve against

        # Returns
        a sorted list of warnings (empty means valid)
        """
        warnings = [*self.dangling_warnings(), *self.mode_warnings(), *self.boundary_warnings(),
                    *self.determinism_warnings(), *self.exit_warnings(),
                    *self.connectivity_warnings(), *self.owner_warnings(layout)]
        return sorted(set(warnings))
