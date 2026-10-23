#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-flow: populate docs/DEV_FLOWCHART.md from its template and flow.toml.

    python3 brain-flow.py            write docs/DEV_FLOWCHART.md
    python3 brain-flow.py --check    fail if the doc drifts from a fresh render
    python3 brain-flow.py --mermaid  print the mermaid view alone

the flow is AUTHORED as data in brain/flow/flow.toml and stepped directly by
brain-walk.py; both load and validate it through brainlib.Flow. this script
only renders the human-facing view: the prose lives in the tracked template
docs/templates/DEV_FLOWCHART.md, and each fill-in marker there is replaced by
the diagram or table generated from flow.toml. an unsound flow is refused

the flow is the EXECUTION SEQUENCE, kept strictly separate from the knowledge
GRAPH (brain-graph.py): the flow has states/transitions, the graph has
nodes/edges, and the coupling is one-directional (a state may CALL recall via
its `recall` flag; the graph never calls the flow). see P30

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Artifact, Exit, Flag, Flow, Layout, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()

# mermaid keywords that cannot be used as a node name; `style` is the one this
# flow actually collides with, and the collision renders as a parse error
MERMAID_KEYWORDS = frozenset({"style", "class", "state", "note", "direction", "end", "click", "link"})

# the template's fill-in markers, each replaced by the section generated from flow.toml
FILL_MERMAID = "<!-- fill: mermaid -->"
FILL_TABLE = "<!-- fill: owner table -->"

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
class FlowDoc(Artifact):
    """renders DEV_FLOWCHART.md from the template and the loaded flow."""

    flow: Flow
    template: str

    def mermaid_warnings(self) -> list[str]:
        """check the rendered flowchart can actually PARSE, not merely match the data.

        a drift gate only proves the doc equals a fresh render, so a chart whose
        labels carried a quote, or whose node was a mermaid keyword, sat
        unparseable and still passed. a gate that measures the wrong property
        passes forever

        # Returns
        one warning per state whose rendering mermaid would reject
        """
        out: list[str] = []
        for s in self.flow.states.values():
            if '"' in s.doc:
                out.append(f"state {s.id} doc contains a quote, which closes its mermaid label")
            if s.id.lower() in MERMAID_KEYWORDS and node_id(s.id) == s.id:
                out.append(f"state {s.id} is a mermaid keyword and has no alias")
        return out

    def template_warnings(self) -> list[str]:
        """every fill-in marker must appear in the template exactly once.

        # Returns
        one warning per marker that is missing or repeated
        """
        return [f"template must carry {marker} exactly once"
                for marker in (FILL_MERMAID, FILL_TABLE) if self.template.count(marker) != 1]

    def to_mermaid(self) -> str:
        """render the flow as a mermaid stateDiagram.

        # Returns
        a mermaid code block, generated from the same data the walk steps
        """
        lines = ["```mermaid", "stateDiagram-v2"]
        lines.extend(f"    [*] --> {node_id(e.state)}" for e in self.flow.entries)
        lines.append("")
        # --------------------------------------------------
        # declare each state as `state "<label>" as <id>`. the label is QUOTED
        # because the docs carry (), :, ?, -> and / , every one of which ends a
        # bare mermaid label; and the id is aliased because `style` is a mermaid
        # keyword that cannot name a node
        # --------------------------------------------------
        lines.extend(f'    state "{s.id} [{s.kind}] {mermaid_label(s.doc)}" as {node_id(s.id)}'
                     for s in self.flow.states.values())
        lines.append("")
        for t in sorted(self.flow.transitions, key=lambda t: (t.src, t.on, t.dst)):
            mark = " *boundary*" if t.boundary else ""
            # the guard rides the edge label, so which mode may take it is legible
            gate = f" [{t.guard}]" if t.guard else ""
            lines.append(f"    {node_id(t.src)} --> {node_id(t.dst)}: {t.on}{gate}{mark}")
        lines.extend(f"    {node_id(s.id)} --> [*]" for s in self.flow.states.values() if s.terminal)
        lines.append("```")
        return "\n".join(lines)

    def to_table(self) -> str:
        """render the state -> owner table.

        # Returns
        a markdown table, one row per state
        """
        lines = ["| state | kind | entry | regime | owner | recall |", "|---|---|---|---|---|---|"]
        for s in self.flow.states.values():
            entry = self.flow.entry_of(s.id)
            seeded = f"{entry.skill} ({entry.mode})" if entry else ""
            lines.append(f"| {s.id} | {s.kind} | {seeded} | {s.regime} | {s.owner} | {str(s.recall).lower()} |")
        return "\n".join(lines)

    def targets(self) -> list[tuple[Path, str]]:
        """the populated flowchart doc.

        # Returns
        the single (path, content) pair for docs/DEV_FLOWCHART.md
        """
        doc = self.template.replace(FILL_MERMAID, self.to_mermaid()).replace(FILL_TABLE, self.to_table())
        return [(self.out_dir / "DEV_FLOWCHART.md", doc)]

    def summary(self) -> str:
        """a one-line build summary.

        # Returns
        the state/transition/entry counts
        """
        return (f"brain-flow done -> {self.out_dir / 'DEV_FLOWCHART.md'}\n"
                f"  states: {len(self.flow.states)} | transitions: {len(self.flow.transitions)} | "
                f"entries: {len(self.flow.entries)}")


def main() -> None:
    """render the flowchart doc, or check/emit it.

    an unsound flow or a broken template fails before anything is written
    """
    args = Args.from_argv()
    args.gate(TOOL, __doc__, Flag.CHECK, Flag.MERMAID)
    doc = FlowDoc(out_dir=LAYOUT.docs, flow=Flow.load(LAYOUT.flow_toml), template=read_text(LAYOUT.flow_template))
    # --------------------------------------------------
    # refuse an unsound flow or template
    # --------------------------------------------------
    warnings = [*doc.flow.validate(LAYOUT), *doc.mermaid_warnings(), *doc.template_warnings()]
    if warnings:
        print(f"{TOOL}: INVALID flow.toml or template - not writing:")
        for warning in warnings:
            print(f"  warn: {warning}")
        sys.exit(Exit.DRIFT)
    # --------------------------------------------------
    # mermaid mode: emit the diagram alone
    # --------------------------------------------------
    if args.has(Flag.MERMAID):
        print(doc.to_mermaid())
        return
    doc.run(args, TOOL)


if __name__ == "__main__":
    main()
