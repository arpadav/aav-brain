"""brainlib: shared datatypes and helpers for the brain tools.

every brain script imports its datatypes from here rather than redefining them,
so a datatype one tool writes is the same datatype another reads (P31). this
module re-exports the whole surface, so `from brainlib import X` reaches any of
it; each submodule's own docstring says what it owns

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.flow import Entry, Flow
from brainlib.graph import Graph
from brainlib.model import Artifact, Edge, Node, State, Transition
from brainlib.paths import (
    DataLayout,
    EvidenceLayout,
    Layout,
    find_archive,
    find_brain,
    find_config,
    find_data,
    find_gate_state,
    find_repo,
    find_repo_root,
    find_served,
    plain_name,
)
from brainlib.recall import (
    BEST_SHARE,
    EXPLAIN_FLOOR,
    INLINE_BYTES,
    INLINE_CARDS,
    MAX_N,
    MAX_REFERENCES,
    REFERENCE_FLOOR,
    Recall,
    RecallError,
    RecallIndex,
    Scores,
)
from brainlib.repos import UNTRACKED, Change, RepoError, RepoTree, git
from brainlib.served import Mark, ServedLog
from brainlib.store import Decision, Ledger, MergeCount, PrunePolicy, ShapePolicy
from brainlib.text import (
    Json,
    clip,
    iso_now,
    kind_rank,
    parse_frontmatter,
    parse_iso,
    read_text,
    split_frontmatter,
    write_text,
)
from brainlib.tool import Args, NoVerdict, Tool, UsageError
from brainlib.transcript import (
    Claude,
    Denied,
    Driven,
    Event,
    Harness,
    Harnesses,
    Interrupted,
    Record,
    Replied,
    Spoke,
    Transcript,
    TranscriptError,
)
from brainlib.vocab import (
    ENCODING,
    GIT_TIMEOUT,
    PYTHON_VERSION,
    Confidence,
    Env,
    Exit,
    Flag,
    Frontmatter,
    Kind,
    Rel,
    Tier,
)

# --------------------------------------------------
# re-exports
# --------------------------------------------------
# the public surface, named once so a reader sees it without chasing modules
__all__ = [
    "BEST_SHARE", "ENCODING", "EXPLAIN_FLOOR", "GIT_TIMEOUT", "INLINE_BYTES", "INLINE_CARDS", "MAX_N",
    "MAX_REFERENCES", "PYTHON_VERSION", "REFERENCE_FLOOR", "UNTRACKED",
    "Args", "Artifact", "Change", "Claude", "Confidence", "DataLayout", "Decision", "Denied", "Driven", "Edge", "Entry",
    "Env", "Event", "EvidenceLayout", "Exit", "Flag", "Flow", "Frontmatter", "Graph", "Harness", "Harnesses",
    "Interrupted", "Json", "Kind", "Layout", "Ledger", "Mark", "MergeCount", "NoVerdict", "Node", "PrunePolicy",
    "Recall", "RecallError", "RecallIndex", "Record", "Rel", "Replied", "RepoError", "RepoTree", "Scores", "ServedLog",
    "ShapePolicy", "Spoke", "State", "Tier", "Tool", "Transcript", "TranscriptError", "Transition", "UsageError",
    "clip", "find_archive", "find_brain", "find_config", "find_data", "find_gate_state", "find_repo", "find_repo_root",
    "find_served", "git", "iso_now", "kind_rank", "parse_frontmatter", "parse_iso", "plain_name", "read_text",
    "split_frontmatter", "write_text",
]
