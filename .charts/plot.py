#!/usr/bin/env python3
"""plot expected vs actual recall score, one chart per labelled prompt.

expected is the rubric relevance a Sonnet rater assigned each card for that
prompt (ten weighted binary criteria, raw sum out of 10, rescaled to 0-1).
actual is what brain-recall.py scores the same card - its SHARE of the task,
already 0-1. both axes therefore mean "how much does this card bear on this
prompt", one judged and one computed, which is the comparison worth looking at.

three horizontal lines. a card joins on EITHER route - it explains at least its
tier's absolute share of the task, or it explains at least BEST_SHARE of what
the best available card explains - so the line that actually decides is the
LOWER of the two, drawn solid black. green bands are constitution cards, which
load whatever they score; orange bands are the conditional cards this prompt
actually admits.

    .charts-venv/bin/python .charts/plot.py
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import collections
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --------------------------------------------------
# constants
# --------------------------------------------------
BRAIN = Path(__file__).resolve().parent.parent
OUT = BRAIN / ".charts"
EVAL = Path("/tmp/claude-1000/-home-arpad-repos--sandbox-budget/"
            "534596cc-9045-47f5-a3ab-e1b4d11c089e/scratchpad/eval")
# the rubric's raw weighted sum tops out here, so dividing puts it on the
# same 0-1 axis as a share of the task
RUBRIC_MAX = 10.0

sys.path.insert(0, str(BRAIN / "bin"))
spec = importlib.util.spec_from_file_location("recall", BRAIN / "bin" / "brain-recall.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def main() -> None:
    """render one chart per prompt plus a summary, into .charts/."""
    index = R.RecallIndex.load(R.LAYOUT.graph_json)
    judged = {c: {int(k): v for k, v in s.items()}
              for c, s in json.loads((EVAL / "relevance3.json").read_text()).items()
              if c in index.nodes}
    prompts = json.loads((EVAL / "prompts2.json").read_text())
    # one fixed card order for every chart, so the x axis means the same thing
    # on all 50 and the distributions can be read against each other
    cards = sorted(index.nodes)
    const = set(index.constitution())
    narrow = {c for c in cards if index.nodes[c].tier == R.Tier.NARROW}
    xs = list(range(len(cards)))

    gaps: list[tuple[float, int, str]] = []
    for prompt in prompts:
        n = prompt["n"]
        seeds = index.seed(R.tokenize(prompt["prompt"]))
        final, _why = index.traverse(seeds) if seeds else ({}, {})
        actual = [index.explains(final, c) if seeds else 0.0 for c in cards]
        expect = [max(0.0, judged.get(c, {}).get(n, {}).get("raw", 0.0)) / RUBRIC_MAX for c in cards]
        for i, c in enumerate(cards):
            gaps.append((expect[i] - actual[i], n, c))

        fig, ax = plt.subplots(figsize=(15, 5.2))
        ax.plot(xs, expect, color="#c44", lw=1.4, marker="o", ms=3.2,
                label="expected (rubric, judged by Sonnet)")
        ax.plot(xs, actual, color="#268", lw=1.4, marker="s", ms=3.2,
                label="actual (brain-recall share of task)")
        # a card joins on EITHER route, so the line that actually decides is the
        # lower of its tier floor and BEST_SHARE of the best card available.
        # drawing only the absolute floor made admitted cards look rejected
        best = max((v for c, v in zip(cards, actual) if c not in const), default=0.0)
        relative = R.BEST_SHARE * best
        effective = min(R.EXPLAIN_FLOOR, relative)
        ax.axhline(R.EXPLAIN_FLOOR, color="#999", ls="--", lw=1.0,
                   label=f"absolute floor {R.EXPLAIN_FLOOR} (share of the task)")
        ax.axhline(relative, color="#e80", ls="-.", lw=1.1,
                   label=f"relative floor {R.BEST_SHARE}x best available = {relative:.2f}")
        ax.axhline(effective, color="#111", ls="-", lw=1.6,
                   label=f"EFFECTIVE admission = {effective:.2f} - above this the agent reads it")
        for i, c in enumerate(cards):
            if c in const:
                ax.axvspan(i - 0.4, i + 0.4, color="#2a8", alpha=0.13, lw=0)
            elif actual[i] >= (R.NARROW_FLOOR if c in narrow else R.EXPLAIN_FLOOR) or actual[i] >= relative:
                ax.axvspan(i - 0.4, i + 0.4, color="#e80", alpha=0.13, lw=0)
        ax.set_xticks(xs)
        ax.set_xticklabels([c.replace("principle-", "P").replace("intent-", "i:")[:26]
                            for c in cards], rotation=90, fontsize=5.4)
        ax.set_ylim(-0.03, 1.05)
        ax.set_ylabel("relevance  (0-1)")
        ax.set_xlabel("card   (green = constitution, always loaded | orange = admitted for this prompt)")
        title = prompt["prompt"].replace("\n", " ")[:118]
        ax.set_title(f'{n:02d}. [{prompt["bucket"]}]  "{title}"', fontsize=9, loc="left")
        ax.legend(fontsize=7, loc="upper right", framealpha=0.9)
        ax.grid(alpha=0.16, lw=0.5)
        fig.tight_layout()
        fig.savefig(OUT / f"prompt-{n:02d}.png", dpi=115)
        plt.close(fig)

    # --------------------------------------------------
    # the summary: where the two disagree, over all 50
    # --------------------------------------------------
    missed = collections.Counter()
    spurious = collections.Counter()
    for gap, _n, c in gaps:
        if gap >= 0.30:
            missed[c] += 1
        elif gap <= -0.30:
            spurious[c] += 1
    fig, ax = plt.subplots(figsize=(15, 5.2))
    ax.bar([x - 0.2 for x in xs], [missed[c] for c in cards], width=0.4,
           color="#c44", label="judged relevant, scored too low to be read")
    ax.bar([x + 0.2 for x in xs], [-spurious[c] for c in cards], width=0.4,
           color="#268", label="scored high, judged irrelevant")
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([c.replace("principle-", "P").replace("intent-", "i:")[:26]
                        for c in cards], rotation=90, fontsize=5.4)
    ax.set_ylabel("prompts (of 50)")
    ax.set_title("where expected and actual disagree by more than 0.30, across all 50 prompts",
                 fontsize=10, loc="left")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.16, axis="y", lw=0.5)
    fig.tight_layout()
    fig.savefig(OUT / "summary-disagreement.png", dpi=115)
    plt.close(fig)

    print(f"wrote {len(prompts)} prompt charts + summary-disagreement.png -> {OUT}")
    print(f"cards: {len(cards)} | constitution {len(const)} | narrow {len(narrow)}")
    print(f"biggest under-scored: {missed.most_common(5)}")
    print(f"biggest over-scored : {spurious.most_common(5)}")


if __name__ == "__main__":
    main()
