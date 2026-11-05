"""Draws docs/img/expected_charts.svg: what the app's three charts must show for
test_vectors/node_stream.txt (run reference/simulate_node.py first)."""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "..", "test_vectors", "expected_log.tsv")), delimiter="\t"))
t = [int(r["ms"]) / 1000 for r in rows]
num = lambda k: [float(r[k]) if r[k] else float("nan") for r in rows]
INK, GRID, RAW, AVG, LIM, ALM = "#2b2f33", "#d9dde1", "#b0b7bf", "#d1495b", "#3b4148", "#f6d5d9"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
                     "svg.fonttype": "none"})
fig, ax = plt.subplots(3, 1, figsize=(7.2, 5.6), sharex=True, gridspec_kw={"height_ratios": [1.5, 1, 1]})
high = [r["alarm"] == "HIGH" for r in rows]
ax[0].fill_between(t, 15, 35, where=high, color=ALM, step="mid", label="alarm HIGH")
ax[0].plot(t, num("temp_c"), color=RAW, lw=1, label="temperature")
ax[0].plot(t, num("temp_avg5"), color=AVG, lw=1.8, label="moving average (5)")
ax[0].axhline(28, color=LIM, lw=0.8, ls="--"); ax[0].axhline(27.5, color=LIM, lw=0.6, ls=":")
ax[0].text(0.5, 28.3, "high limit 28 °C", fontsize=8); ax[0].text(0.5, 26.6, "back to OK below 27.5 °C", fontsize=8)
ax[0].set_ylim(21, 33); ax[0].set_ylabel("°C"); ax[0].legend(loc="upper left", ncol=3, fontsize=8)
ax[1].plot(t, num("dist_cm"), color="#2e86ab", lw=1.2); ax[1].set_ylabel("distance (cm)")
ax[2].plot(t, num("light_pct"), color="#edae49", lw=1.2); ax[2].set_ylabel("light (%)")
ax[2].set_xlabel("time (s)")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "img", "expected_charts.svg"), facecolor="white")
if os.environ.get("CHECK_PNG"):
    fig.savefig(os.path.join(os.environ["CHECK_PNG"], "expected_charts.png"), dpi=90)
print("wrote docs/img/expected_charts.svg")
