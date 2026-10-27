"""README figures, banner, LinkedIn visual and turntable GIF, all built from results/ and the generator."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from ortholab import data, geometry  # noqa: E402
from ortholab.config import FIGURES, MEASURES, RESULTS  # noqa: E402
from render import draw, frame  # noqa: E402

TEAL, RUST, GREY, INK, MUTED = "#00909C", "#C2410C", "#8A96A3", "#14213D", "#5B6675"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": "#C9D1D9",
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#EEF1F4", "grid.linewidth": 0.8, "axes.axisbelow": True})

import os
R = RESULTS / "sample" if os.environ.get("ORTHO_SAMPLE") else RESULTS
S = json.loads((R / "summary.json").read_text())
FIGURES = FIGURES / "sample" if os.environ.get("ORTHO_SAMPLE") else FIGURES
FIGURES.mkdir(parents=True, exist_ok=True)


def title(ax, t, sub=None):
    ax.set_title(t, loc="left", fontsize=13, fontweight="bold", color=INK, pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=10, color=MUTED)


def three_people():
    df = data.load()
    size = (df[MEASURES] - df[MEASURES].mean()) / df[MEASURES].std()
    score = size.mean(axis=1)
    picks = [score.sub(score.quantile(q)).abs().idxmin() for q in (0.03, 0.5, 0.97)]
    return [{k: float(df.loc[i, k]) for k in MEASURES} for i in picks]


def hero(path=None):
    """Three people (small, median, large) rendered at the same scale, side by side."""
    path = path or FIGURES / "hero.png"
    people = three_people()
    meshes = [geometry.build_afo(m, {"vent_rows": 4}) for m in people]
    r = max(float(np.max(a.extents)) for a in meshes) / 2 + 5
    tiles = []
    for a in meshes:
        fig = plt.figure(figsize=(4.4, 5.6), dpi=320)
        fig.patch.set_alpha(0)
        ax = fig.add_axes([0, 0, 1, 1], projection="3d")
        ax.patch.set_alpha(0)
        draw(ax, a, elev=12, azim=-62)
        c = (a.bounds[0] + a.bounds[1]) / 2
        c[2] = a.bounds[0][2] + r                       # common floor so heights compare
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
        ax.set_box_aspect((1, 1, 1))
        fig.canvas.draw()
        tiles.append(Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).copy())
        plt.close(fig)
    boxes = [t.getbbox() for t in tiles]
    top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
    crops = [t.crop((b[0], top, b[2], bottom)) for t, b in zip(tiles, boxes)]
    gap = 40
    W = sum(c.width for c in crops) + gap * (len(crops) - 1)
    out = Image.new("RGBA", (W, bottom - top), (0, 0, 0, 0))
    x = 0
    for c in crops:
        out.paste(c, (x, 0), c)
        x += c.width + gap
    out.save(path)
    return people


def sizing():
    cov = pd.read_csv(R / "sizing_coverage.csv")
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    fl = cov.dropna(subset=["foot_length_sizing"])
    ax.plot(fl["sizes"], fl["foot_length_sizing"] * 100, color=GREY, lw=2, marker="o", ms=5)
    ax.plot(cov["sizes"], cov["multi_dim_sizing"] * 100, color=TEAL, lw=2, marker="o", ms=5)
    ax.axhline(100, color=INK, lw=1, ls=":")
    ax.text(40, 97, "made-to-measure: everyone, by construction", ha="right", va="top", color=INK, fontsize=10)
    ax.text(fl["sizes"].iloc[-1] - 0.3, fl["foot_length_sizing"].iloc[-1] * 100 + 3, "sizes cut on foot length", color=MUTED, ha="right", va="bottom", fontsize=10)
    ax.text(cov["sizes"].iloc[-1] - 0.5, cov["multi_dim_sizing"].iloc[-1] * 100 - 9, "best case: sizes clustered\non all seven dimensions",
            color=INK, ha="right", va="top", fontsize=10)
    k4 = S["sizing_4_foot_length_sizes"] * 100
    ax.annotate(f"{k4:.0f} % with 4 sizes", (4, k4), (12, 8), color=INK, fontsize=10,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlabel("number of standard sizes")
    ax.set_ylabel("people within tolerance (%)")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 42)
    title(ax, "Standard sizes leave most people outside tolerance",
          f"{S['sizing_test_people']:,} people the sizes were not designed on; all seven fit dimensions must be in tolerance")
    fig.tight_layout()
    fig.savefig(FIGURES / "sizing.png", dpi=160)
    plt.close(fig)


LAB = {"foot_breadth": "Foot breadth", "heel_breadth": "Heel breadth", "ball_length": "Heel to ball",
       "ankle_circ": "Ankle girth", "calf_circ": "Calf girth", "malleolus_height": "Malleolus height",
       "bimalleolar_breadth": "Ankle breadth", "tibial_height": "Tibial height"}


def assistant():
    a = pd.read_csv(R / "assistant_errors.csv")
    g = a[a.model == "gradient boosting (LightGBM)"].set_index("target")
    g = g.sort_values("within_tol")
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    cols = [RUST if t in ("ankle_circ", "calf_circ") else TEAL for t in g.index]
    ax.barh([LAB[t] for t in g.index], g["within_tol"] * 100, color=cols, height=0.62)
    for i, (v, mae) in enumerate(zip(g["within_tol"] * 100, g["mae_mm"])):
        ax.text(v + 1, i, f"{v:.0f} %   (mean error {mae:.1f} mm)", va="center", fontsize=9.5, color=INK)
    ax.set_xlim(0, 125)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("unseen people predicted within tolerance (%)")
    ax.grid(axis="y", visible=False)
    title(ax, "Lengths can be predicted, girths need the tape",
          "LightGBM from foot length, height, weight and sex; 25 % of people held out")
    fig.tight_layout()
    fig.savefig(FIGURES / "assistant.png", dpi=160)
    plt.close(fig)


def stiffness():
    pop = pd.read_csv(R / "population.csv")
    trim = pd.read_csv(R / "stiffness_trimline.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    ax.hist(pop["thickness_equal_stiffness"], bins=45, color=TEAL, edgecolor="white", linewidth=0.6)
    lo, hi = S["equal_stiffness_thickness_p05_p95"]
    for v in (lo, hi):
        ax.axvline(v, color=INK, lw=1, ls=":")
    ax.text(0.98, 0.95, f"90 % of people:\n{lo:.1f} to {hi:.1f} mm", transform=ax.transAxes, ha="right", va="top",
            fontsize=10, color=INK, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none"))
    ax.set_xlabel("shell thickness (mm)")
    ax.set_ylabel("people")
    title(ax, "Same stiffness for everyone", "thickness that gives each person the median stiffness")
    ax = axes[1]
    ax.plot(trim["ankle_wrap_deg"], trim["relative_stiffness"], color=RUST, lw=2, marker="o", ms=5)
    r120 = trim.set_index("ankle_wrap_deg").loc[120, "relative_stiffness"]
    ax.annotate(f"120°: {r120:.2f}×", (120, r120), (135, 0.55), fontsize=10, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlabel("wrap around the ankle (degrees)")
    ax.set_ylabel("stiffness relative to 200°")
    title(ax, "The trimline is the main stiffness knob", "median person, 3 mm shell, beam model")
    fig.tight_layout()
    fig.savefig(FIGURES / "stiffness.png", dpi=160)
    plt.close(fig)


def build_volume():
    pop = pd.read_csv(R / "population.csv")
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.hist(pop["min_cube_mm"], bins=50, color=TEAL, edgecolor="white", linewidth=0.6)
    for v, lab in ((250, "250 mm\ndesktop"), (400, "400 mm\nlarge format")):
        ax.axvline(v, color=INK, lw=1, ls=":")
        ax.text(v + 4, ax.get_ylim()[1] * 0.82, lab, fontsize=9.5, color=INK)
    ax.set_xlabel("side of the smallest cubic build volume that holds the orthosis (mm)")
    ax.set_ylabel("people")
    title(ax, "Desktop printers are too small for a full AFO",
          f"{len(pop):,} generated orthoses, best of three orientations and bed rotations")
    fig.tight_layout()
    fig.savefig(FIGURES / "build_volume.png", dpi=160)
    plt.close(fig)


def scan_fit():
    g = pd.read_csv(R / "scan_fit.csv")
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for src, col, lab in (("tape", RUST, "shell from the tape (default shape assumptions)"),
                          ("scan", TEAL, "shell from the scan")):
        d = g[g.source == src].groupby("height_mm")["gap_mm"].min()
        ax.plot(d.index, d.values, color=col, lw=2)
        ax.text(d.index[-1] + 4, d.values[-1] + (0.45 if src == "scan" else 0), lab.split(" (")[0], color=col,
                va="center", fontsize=10)
    ax.axhline(0, color=INK, lw=1)
    ax.hlines(3, g.height_mm.min(), g.height_mm.max(), color=MUTED, lw=1, ls=":")
    ax.text(g.height_mm.min(), 3.3, "target: 3 mm liner clearance (the scan-based shell sits on it)", color=MUTED, fontsize=9.5)
    ax.fill_between([g.height_mm.min(), g.height_mm.max()], -3, 0, color=RUST, alpha=0.06, lw=0)
    ax.text(g.height_mm.min(), -2.6, "below 0: the shell presses on the leg", color=RUST, fontsize=9.5)
    ax.set_xlim(g.height_mm.min(), g.height_mm.max() + 70)
    ax.set_ylim(-3, 4.5)
    ax.set_xlabel("height above the sole (mm)")
    ax.set_ylabel("smallest gap skin to shell (mm)")
    title(ax, "A scan removes the shape guesswork",
          "synthetic scan with a lower, flatter calf than the generator assumes; median person")
    fig.tight_layout()
    fig.savefig(FIGURES / "scan_fit.png", dpi=160)
    plt.close(fig)


def turntable(m, path=None, n=36):
    path = path or FIGURES / "turntable.gif"
    afo = geometry.build_afo(m, {"vent_rows": 4})
    frames = []
    for k in range(n):
        fig = plt.figure(figsize=(4.2, 4.2), facecolor="white")
        ax = fig.add_axes([-0.15, -0.15, 1.3, 1.3], projection="3d")
        draw(ax, afo, elev=16, azim=-60 + k * 360 / n)
        frame(ax, afo.bounds[0], afo.bounds[1], pad=0)
        fig.canvas.draw()
        im = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
        frames.append(im.quantize(colors=96, method=Image.Quantize.MEDIANCUT))
        plt.close(fig)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)


if __name__ == "__main__":
    people = hero()
    sizing()
    assistant()
    stiffness()
    build_volume()
    scan_fit()
    turntable(S["median_person"])
    print("figures written to", FIGURES)
