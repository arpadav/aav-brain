#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["matplotlib"]
# ///
"""plot expected vs actual recall score, one chart per labelled prompt.

expected is the rubric relevance a Sonnet rater assigned each card for that
prompt (ten weighted binary criteria, raw sum out of 10, rescaled to 0-1).
actual is what brain-recall.py scores the same card - its SHARE of the task,
already 0-1. both axes therefore mean "how much does this card bear on this
prompt", one judged and one computed, which is the comparison worth looking at.

a card joins on EITHER route - it explains at least its tier's absolute share
of the task, or it explains at least BEST_SHARE of what the best candidate
explains - so the bar that decides is the LOWER of the two, drawn as a solid
black tick per card (a narrow card's tier floor is lower), and at most MAX_N of
the cards above it are taken. three lines give the bars it is the lower of,
plus the lower one a card cited by an admitted card clears. green bands are
constitution cards, which load whatever they score; orange bands are the cards
the score admits for this prompt.

    uv run .charts/plot.py EVAL_DIR [OUT_DIR]

EVAL_DIR holds the labelled set: `prompts2.json` (a list of {n, bucket, prompt})
and `relevance3.json` (card id to {prompt n: {raw}}). OUT_DIR defaults to this
script's own folder

Author: aav
"""
# brainlib lives in bin/, a sibling of this folder
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import (
    BEST_SHARE,
    EXPLAIN_FLOOR,
    MAX_N,
    MAX_REFERENCES,
    REFERENCE_FLOOR,
    Args,
    Layout,
    NoVerdict,
    RecallIndex,
    Tier,
    Tool,
    read_text,
)

# --------------------------------------------------
# external
# --------------------------------------------------
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# where the charts land when no OUT_DIR is given
HERE = Path(__file__).resolve().parent
# the rubric's raw weighted sum tops out here, so dividing puts it on the
# same 0-1 axis as a share of the task
RUBRIC_MAX = 10.0
# the expected-minus-actual gap past which the summary counts a disagreement
DISAGREE = 0.30


@dataclass
class Charts:
    """the recall index and the one card order every chart is drawn over.

    the order is fixed so the x axis means the same thing on every chart and
    the distributions can be read against each other
    """

    index: RecallIndex
    out: Path
    # card id to {prompt n: {"raw": weighted rubric sum}}
    judged: dict[str, dict[int, dict[str, float]]]
    cards: list[str] = field(init=False)
    const: set[str] = field(init=False)

    def __post_init__(self) -> None:
        """fix the card order and the constitution every chart marks."""
        self.cards = sorted(self.index.nodes)
        self.const = set(self.index.constitution())

    def axes(self) -> tuple[Figure, Axes]:
        """a blank chart with one tick per card, labelled by its short id.

        # Returns

        the figure and its axes
        """
        # --------------------------------------------------
        # one wide card axis, shared by every chart
        # --------------------------------------------------
        fig, ax = plt.subplots(figsize=(15, 5.2))
        ax.set_xticks(range(len(self.cards)))
        # --------------------------------------------------
        # label each card by its short id, rotated to fit
        # --------------------------------------------------
        ax.set_xticklabels([self.index.nodes[c].short_id or c for c in self.cards], rotation=90, fontsize=5.4)
        return fig, ax

    def save(self, fig: Figure, name: str) -> None:
        """write one chart into the output directory and release it.

        # Arguments

        * `fig` - the finished figure
        * `name` - its file name
        """
        # --------------------------------------------------
        # fit, write, and release the figure
        # --------------------------------------------------
        fig.tight_layout()
        fig.savefig(self.out / name, dpi=115)
        plt.close(fig)

    def draw(self, prompt: dict[str, Any]) -> list[tuple[float, str]]:
        """draw one prompt's expected-vs-actual chart.

        # Arguments

        * `prompt` - one labelled prompt, {n, bucket, prompt}

        # Returns

        the expected-minus-actual gap per card, for the summary
        """
        # --------------------------------------------------
        # what recall scores for this prompt, against what the rubric judged
        # --------------------------------------------------
        n = prompt["n"]
        found = self.index.recall(prompt["prompt"])
        actual = [found.scores.explains(c) for c in self.cards]
        expect = [max(0.0, self.judged.get(c, {}).get(n, {}).get("raw", 0.0)) / RUBRIC_MAX for c in self.cards]
        fig, ax = self.axes()
        xs = range(len(self.cards))
        # --------------------------------------------------
        # the two curves: judged relevance and recall's share of the task
        # --------------------------------------------------
        ax.plot(xs, expect, color="#c44", lw=1.4, marker="o", ms=3.2, label="expected (rubric, judged by Sonnet)")
        ax.plot(xs, actual, color="#268", lw=1.4, marker="s", ms=3.2, label="actual (brain-recall share of task)")
        # --------------------------------------------------
        # the admission bars, each on the same 0-1 axis
        # --------------------------------------------------
        # a card joins on EITHER route, so the bar that decides is the lower of
        # its tier floor and the relative bar the recall used
        ax.axhline(EXPLAIN_FLOOR, color="#999", ls="--", lw=1.0,
                   label=f"absolute floor {EXPLAIN_FLOOR} (share of the task)")
        ax.axhline(found.bar, color="#e80", ls="-.", lw=1.1,
                   label=f"relative floor {BEST_SHARE}x best candidate = {found.bar:.2f}")
        ax.axhline(REFERENCE_FLOOR, color="#999", ls=":", lw=1.0,
                   label=f"reference floor {REFERENCE_FLOOR} - a card an admitted one cites, {MAX_REFERENCES} at most")
        # --------------------------------------------------
        # the bar each card must clear, which differs by tier
        # --------------------------------------------------
        ax.hlines([self.index.bar_for(c, found.bar) for c in self.cards], [x - 0.4 for x in xs],
                  [x + 0.4 for x in xs], color="#111", lw=1.6,
                  label=f"EFFECTIVE admission per card - the best {MAX_N} above it are read")
        # --------------------------------------------------
        # shade the constitution cards green and the score-admitted ones orange
        # --------------------------------------------------
        admitted = set(found.scored)
        for i, c in enumerate(self.cards):
            if c in self.const:
                ax.axvspan(i - 0.4, i + 0.4, color="#2a8", alpha=0.13, lw=0)
            elif c in admitted:
                ax.axvspan(i - 0.4, i + 0.4, color="#e80", alpha=0.13, lw=0)
        # --------------------------------------------------
        # axes, title and legend
        # --------------------------------------------------
        ax.set_ylim(-0.03, 1.05)
        ax.set_ylabel("relevance  (0-1)")
        ax.set_xlabel("card   (green = constitution, always loaded | orange = admitted by score for this prompt)")
        title = prompt["prompt"].replace("\n", " ")[:118]
        ax.set_title(f'{n:02d}. [{prompt["bucket"]}]  "{title}"', fontsize=9, loc="left")
        ax.legend(fontsize=7, loc="upper right", framealpha=0.9)
        ax.grid(alpha=0.16, lw=0.5)
        # --------------------------------------------------
        # write the chart, and hand back each card's expected-minus-actual gap
        # --------------------------------------------------
        self.save(fig, f"prompt-{n:02d}.png")
        return [(e - a, c) for e, a, c in zip(expect, actual, self.cards, strict=True)]

    def summary(self, gaps: list[tuple[float, str]], prompts: int) -> tuple[Counter[str], Counter[str]]:
        """draw where expected and actual disagree, over every prompt.

        # Arguments

        * `gaps` - every prompt's per-card gaps
        * `prompts` - how many prompts they span

        # Returns

        the (under-scored, over-scored) count per card
        """
        # --------------------------------------------------
        # count the prompts where a card was judged relevant but scored too low, and the reverse
        # --------------------------------------------------
        missed = Counter(c for gap, c in gaps if gap >= DISAGREE)
        spurious = Counter(c for gap, c in gaps if gap <= -DISAGREE)
        fig, ax = self.axes()
        xs = range(len(self.cards))
        # --------------------------------------------------
        # missed cards above the axis, spurious ones below
        # --------------------------------------------------
        ax.bar([x - 0.2 for x in xs], [missed[c] for c in self.cards], width=0.4,
               color="#c44", label="judged relevant, scored too low to be read")
        ax.bar([x + 0.2 for x in xs], [-spurious[c] for c in self.cards], width=0.4,
               color="#268", label="scored high, judged irrelevant")
        # --------------------------------------------------
        # axis, title and legend
        # --------------------------------------------------
        ax.axhline(0, color="#333", lw=0.8)
        ax.set_ylabel(f"prompts (of {prompts})")
        ax.set_title(f"where expected and actual disagree by more than {DISAGREE:.2f}, across all {prompts} prompts",
                     fontsize=10, loc="left")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.16, axis="y", lw=0.5)
        self.save(fig, "summary-disagreement.png")
        return missed, spurious


def main(args: Args) -> None:
    """render one chart per prompt plus a summary, into OUT_DIR.

    prints how many charts were written and the cards the score most under- and
    over-rates against the rubric

    # Arguments

    * `args` - the parsed command line; the first positional is the labelled-set
      directory, the optional second is the output directory (this script's own
      folder by default)

    # Raises

    NoVerdict when the labelled set's two files cannot be read or parsed
    """
    # --------------------------------------------------
    # the labelled set, and where the charts go
    # --------------------------------------------------
    paths = [Path(path) for path in args.positional()]
    labelled, out = paths[0], paths[1] if len(paths) > 1 else HERE
    try:
        # --------------------------------------------------
        # both judged files must read and parse
        # --------------------------------------------------
        relevance = json.loads(read_text(labelled / "relevance3.json"))
        prompts = json.loads(read_text(labelled / "prompts2.json"))
    except (OSError, ValueError) as broken:
        raise NoVerdict(f"cannot read the labelled set: {broken}") from broken
    # --------------------------------------------------
    # the output folder, then the recall index and the judged scores for the cards it knows
    # --------------------------------------------------
    out.mkdir(parents=True, exist_ok=True)
    index = RecallIndex.build(Layout.discover())
    judged = {c: {int(k): v for k, v in s.items()} for c, s in relevance.items() if c in index.nodes}
    # --------------------------------------------------
    # one chart per labelled prompt, then the summary across all of them
    # --------------------------------------------------
    charts = Charts(index, out, judged)
    gaps = [gap for prompt in prompts for gap in charts.draw(prompt)]
    missed, spurious = charts.summary(gaps, len(prompts))
    # --------------------------------------------------
    # report what was written and where recall and the rubric disagree most
    # --------------------------------------------------
    narrow = sum(1 for node in index.nodes.values() if node.tier == Tier.NARROW)
    print(f"wrote {len(prompts)} prompt charts + summary-disagreement.png -> {out}")
    print(f"cards: {len(charts.cards)} | constitution {len(charts.const)} | narrow {narrow}")
    print(f"biggest under-scored: {missed.most_common(5)}")
    print(f"biggest over-scored : {spurious.most_common(5)}")


if __name__ == "__main__":
    Tool(TOOL, __doc__, positionals=(1, 2)).run(main)
