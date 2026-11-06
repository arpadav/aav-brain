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
    COMMAND_PREFIX,
    ISOLATED,
    DataLayout,
    EditCopyMissing,
    EvidenceLayout,
    Layout,
    LocalLayout,
    XdgLayout,
    find_brain,
    find_repo,
    find_repo_root,
    plain_name,
)
from brainlib.recall import (
    BEST_SHARE,
    EXPLAIN_FLOOR,
    INLINE_BYTES,
    INLINE_PRINCIPLES,
    MAX_N,
    MAX_REFERENCES,
    REFERENCE_FLOOR,
    Recall,
    RecallError,
    RecallIndex,
    Scores,
)
from brainlib.repo.diff import Patch
from brainlib.repo.private import PrivateScan, ScanScope
from brainlib.repo.push import NO_REPLACE, Excerpt, Origin, Outgoing
from brainlib.repo.tree import PLANS, UNTRACKED, Change, Ending, GitRun, RepoError, RepoTree, git
from brainlib.session import Mark, SessionLog, SessionRecord
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
from brainlib.tool import Args, Tool
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
    LONG_GIT_TIMEOUT,
    PYTHON_VERSION,
    Confidence,
    Env,
    Exit,
    Flag,
    Frontmatter,
    Kind,
    NoVerdict,
    Rel,
    Tier,
    UsageError,
)

# --------------------------------------------------
# re-exports
# --------------------------------------------------
# the public surface, named once so a reader sees it without chasing modules
__all__ = [
    "BEST_SHARE", "COMMAND_PREFIX", "ENCODING", "EXPLAIN_FLOOR", "GIT_TIMEOUT", "INLINE_BYTES",
    "INLINE_PRINCIPLES", "ISOLATED", "LONG_GIT_TIMEOUT", "MAX_N", "MAX_REFERENCES", "NO_REPLACE", "PLANS",
    "PYTHON_VERSION", "REFERENCE_FLOOR", "UNTRACKED",
    "Args", "Artifact", "Change", "Claude", "Confidence", "DataLayout", "Decision", "Denied", "Driven", "Edge",
    "EditCopyMissing", "Ending", "Entry", "Env", "Event", "EvidenceLayout", "Excerpt", "Exit", "Flag", "Flow",
    "Frontmatter", "GitRun", "Graph", "Harness", "Harnesses", "Interrupted", "Json", "Kind", "Layout", "Ledger",
    "LocalLayout", "Mark", "MergeCount", "NoVerdict", "Node", "Origin", "Outgoing", "Patch", "PrivateScan",
    "PrunePolicy", "Recall", "RecallError", "RecallIndex", "Record", "Rel", "Replied", "RepoError", "RepoTree",
    "ScanScope", "Scores", "SessionLog", "SessionRecord", "ShapePolicy", "Spoke", "State", "Tier", "Tool",
    "Transcript", "TranscriptError", "Transition", "UsageError", "XdgLayout",
    "clip", "find_brain", "find_repo", "find_repo_root",
    "git", "iso_now", "kind_rank", "parse_frontmatter", "parse_iso", "plain_name",
    "read_text", "split_frontmatter", "write_text",
]
