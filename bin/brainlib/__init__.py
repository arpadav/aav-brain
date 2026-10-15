"""brainlib: shared datatypes and helpers for the brain tools.

every brain script that needs one - cards, compile, extract, find, flow, graph,
recall, shape, trace, walk - imports its datatypes and its drift-gate from here
rather than redefining them. a datatype written by one tool is the same datatype
read by another (graph writes Node.to_dict, recall reads Node.from_dict). that
is the library: scripts helping one another by sharing structs, not duplicating
them

it is a PACKAGE rather than one file because the working copy reached 2005
lines - past shape.toml's own `file_lines = 2000` - and P27 says a file that
grew too long splits into a tree. the last committed version was 1759; the
crossing was caused by the same session's additions, which is why splitting it
was that session's job and not a later one's.
this module re-exports the whole surface, so `from brainlib import X` reads the
same as it always did and no caller had to change:

- `vocab`  the closed vocabularies: Kind (rank + neo4j label), Rel (the closed
  edge vocabulary, with its neo4j label), Tier (how a card reaches an agent),
  Confidence, Env (every environment variable read), Flag (every command-line
  flag accepted), Exit (every status code), Mode (which region of the flow a
  walk traverses, and what a guard admits), Entry (every skill a walk starts
  from)
- `args`   Args, one argv parse, with the flag-versus-value rule applied once
- `text`   the pure helpers: clip, iso_now, kind_rank, read_text, write_text,
  parse_frontmatter
- `model`  the datatypes tools exchange: Node, Edge, State, Transition, and
  Artifact (build / --check / drift-gate), so the "committed artifact must equal
  a fresh build" invariant lives in exactly one place
- `paths`  Layout and DataLayout, the ONE place a path inside the brain is
  spelled, plus the discovery that finds the store without a hardcoded path
- `store`  the append-merge Ledger + MergeCount, the ONE reader and writer for
  every jsonl corpus, so "a log may only ever grow" lives in one place; Decision
  (one logged fork); PrunePolicy (how old an entry must be to be eligible to be
  judged stale, scaled by how fast the repo moves); ShapePolicy (the numbers
  behind P27 and P28 and the change budget that arms a phase gate); and git(),
  the ONE read-only shell-out, returning None (could not run) distinctly from ""
  (ran, said nothing)

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.args import Args
from brainlib.model import Artifact, Edge, Node, State, Transition, load_json
from brainlib.paths import (
    DataLayout,
    Layout,
    find_archive,
    find_brain,
    find_data,
    find_gate_state,
    find_repo,
)
from brainlib.store import Decision, Ledger, MergeCount, PrunePolicy, ShapePolicy, git
from brainlib.text import clip, iso_now, kind_rank, parse_frontmatter, read_text, write_text
from brainlib.vocab import (
    ENCODING,
    GIT_TIMEOUT,
    PYTHON_VERSION,
    Confidence,
    Entry,
    Env,
    Exit,
    Flag,
    Frontmatter,
    Kind,
    Mode,
    Rel,
    Tier,
)

# --------------------------------------------------
# the public surface, named once so a reader sees it without chasing modules
# --------------------------------------------------
__all__ = [
    "ENCODING", "GIT_TIMEOUT", "PYTHON_VERSION",
    "Args", "Artifact", "Confidence", "DataLayout", "Decision", "Edge", "Entry", "Env", "Exit",
    "Flag", "Frontmatter", "Kind", "Layout", "Ledger", "MergeCount", "Mode", "Node",
    "PrunePolicy", "Rel", "ShapePolicy", "State", "Tier", "Transition",
    "clip", "find_archive", "find_brain", "find_data", "find_gate_state", "find_repo", "git",
    "iso_now",
    "kind_rank", "load_json", "parse_frontmatter", "read_text", "write_text",
]
