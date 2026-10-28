"""README figures, banner, LinkedIn visual and turntable GIF, all built from results/ and the generator."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from ortholab import articulated as ar, data, geometry, segmented as sg  # noqa: E402
from ortholab.config import FIGURES, MEASURES, RESULTS  # noqa: E402
from render import BASE, NAVY, SEG_COLORS, STEEL, assembly, draw, draw_parts, frame  # noqa: E402

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


def _tile(parts, elev, azim, r=None, floor=None, size=(4.4, 5.6), dpi=320):
    """Transparent render of (mesh, colour) pairs; common radius r and floor so several tiles share a scale."""
    fig = plt.figure(figsize=size, dpi=dpi)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1], projection="3d")
    ax.patch.set_alpha(0)
    draw_parts(ax, parts, elev=elev, azim=azim)
    lo = np.min([m.bounds[0] for m, _ in parts], 0)
    hi = np.max([m.bounds[1] for m, _ in parts], 0)
    r = r or float(np.max(hi - lo)) / 2 + 5
    c = (lo + hi) / 2
    c[2] = (lo[2] if floor is None else floor) + r
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    fig.canvas.draw()
    im = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).copy()
    plt.close(fig)
    return im


def _row(tiles, gap=40):
    boxes = [t.getbbox() for t in tiles]
    top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
    crops = [t.crop((b[0], top, b[2], bottom)) for t, b in zip(tiles, boxes)]
    out = Image.new("RGBA", (sum(c.width for c in crops) + gap * (len(crops) - 1), bottom - top), (0, 0, 0, 0))
    x = 0
    for c in crops:
        out.paste(c, (x, 0), c)
        x += c.width + gap
    return out


def hero(path=None):
    """Three people (small, median, large), segmented articulated orthoses at the same scale, side by side."""
    path = path or FIGURES / "hero.png"
    people = three_people()
    builds = [sg.build_segmented(m, {"vent_rows": 3, "plantar_stop_deg": 5.0}) for m in people]
    r = max(float(np.max(np.max([P["upper"].bounds[1], P["lower"].bounds[1]], 0)
                         - np.min([P["upper"].bounds[0], P["lower"].bounds[0]], 0))) for P in builds) / 2 + 5
    _row([_tile(assembly(P), 12, -40, r=r) for P in builds]).save(path)
    return people


def parts_figure(m, path=None):
    """Median person: exploded view of the parts, then the foot section at plantar stop, neutral and dorsiflexion."""
    path = path or FIGURES / "parts.png"
    P = ar.build_articulated(m, {"vent_rows": 3, "plantar_stop_deg": 5.0})
    E = ar.exploded(P, gap=55.0)
    j = P["joint"]
    ex = _tile([(E["lower"], BASE), (E["upper"], NAVY), (E["pins"], STEEL)], 14, -35, size=(5, 6.2), dpi=260)
    ex = ex.crop(ex.getbbox())
    cut = j.origin[2] + 90
    upper = P["upper"].slice_plane([0, 0, cut], [0, 0, -1], cap=True)
    poses = [_tile([(ar.rotate_about_axis(P["lower"], j, d), BASE), (upper, NAVY), (P["pins"], STEEL)],
                   6, 0, r=125, floor=-30, size=(4, 4), dpi=240) for d in (-5.0, 0.0, 15.0)]
    boxes = [t.getbbox() for t in poses]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    poses = [t.crop(box) for t in poses]

    fig = plt.figure(figsize=(13, 5.6), dpi=160)
    fig.text(0.02, 0.93, "Separate printable parts", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.02, 0.885, "exploded view, median person", fontsize=10, color=MUTED)
    ax = fig.add_axes([0.03, 0.03, 0.22, 0.82]); ax.imshow(ex); ax.set_axis_off()
    zlo = E["lower"].bounds[0][2]; zhi = E["upper"].bounds[1][2]
    def yfrac(z):
        return (z - zlo) / (zhi - zlo)
    for t, c, z in (("calf cuff", NAVY, 0.5 * (cut + 55 + zhi)),
                    ("M5 pins", STEEL, j.origin[2] + 55 * 0.5 + 6),
                    ("foot section", BASE, zlo + 25)):
        ax.text(1.04, yfrac(z), t, transform=ax.transAxes, color=tuple(c * 0.85), fontsize=11,
                fontweight="bold", va="center")
    fig.text(0.40, 0.93, "Hinged at the ankle, stopped where the setting says", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.40, 0.885, "foot section turned about the malleolar axis; the cuff stops it at the 5° plantarflexion setting",
             fontsize=10, color=MUTED)
    names = {-5: "plantar stop", 0: "neutral", 15: "dorsiflexion"}
    for k, (deg, im) in enumerate(zip((-5, 0, 15), poses)):
        ax = fig.add_axes([0.40 + k * 0.2, 0.16, 0.19, 0.62]); ax.imshow(im); ax.set_axis_off()
        ax.text(0.5, -0.12, f"{deg:+d}°  {names[deg]}", transform=ax.transAxes, ha="center", color=INK, fontsize=11)
    fig.savefig(path, facecolor="white")
    plt.close(fig)


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
    title(ax, "Six of eight measurements predicted from four inputs",
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


def _frame_rgb(parts, elev, azim, lo, hi, pad=0, size=4.2):
    fig = plt.figure(figsize=(size, size), facecolor="white")
    ax = fig.add_axes([-0.15, -0.15, 1.3, 1.3], projection="3d")
    draw_parts(ax, parts, elev=elev, azim=azim)
    frame(ax, lo, hi, pad=pad)
    fig.canvas.draw()
    im = Image.frombuffer("RGBA", fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert("RGB")
    plt.close(fig)
    return im.quantize(colors=96, method=Image.Quantize.MEDIANCUT)


def turntable(m, path=None, n=36):
    path = path or FIGURES / "turntable.gif"
    P = sg.build_segmented(m, {"vent_rows": 3, "plantar_stop_deg": 5.0})
    parts = assembly(P)
    lo = np.min([x.bounds[0] for x, _ in parts], 0); hi = np.max([x.bounds[1] for x, _ in parts], 0)
    frames = [_frame_rgb(parts, 16, -60 + k * 360 / n, lo, hi) for k in range(n)]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)


GAIT = [("foot flat", 0.0, (0.0, 0.0, 0.0)),
        ("heel rise", 10.0, (2.0, 2.0, 15.0)),
        ("toe-off", -5.0, (4.0, 4.0, 30.0))]


def _posed(P, ankle, foot, upper):
    """Assembly posed at the ankle and foot joints, shown in the ground frame: toes flat, heel and leg lifted."""
    Q = sg.pose(P, foot, ankle_deg=ankle)
    parts = [(Q[k], SEG_COLORS[k]) for k in SEG_COLORS] + [(Q["foot_pins"], STEEL)]
    j = P["joint"]
    ank = [upper.copy(), P["pins"].copy()]
    parts += [(ank[0], NAVY), (ank[1], STEEL)]
    tip = Q["toes"].vertices[np.argmax(Q["toes"].vertices[:, 1])]
    R = trimesh.transformations.rotation_matrix(np.radians(-(ankle + sum(foot))), [1, 0, 0], [0, tip[1], 0.0])
    meshes = []
    for m_, c in parts:
        m_ = m_.copy(); m_.apply_transform(R); meshes.append((m_, c))
    zmin = min(m_.bounds[0][2] for m_, _ in meshes[:4])
    for m_, _ in meshes:
        m_.apply_translation([0, 0, -zmin])
    return meshes


def _gait_frames(P, n):
    """Ankle and foot angles from foot flat through heel rise to toe-off."""
    keys = np.array([[g[1], *g[2]] for g in GAIT])
    ts = np.linspace(0, len(GAIT) - 1, n)
    return [(float(np.interp(t, range(len(GAIT)), keys[:, 0])),
             tuple(float(np.interp(t, range(len(GAIT)), keys[:, i])) for i in (1, 2, 3))) for t in ts]


def motion(m, path=None, n=28):
    """Roll-over: foot flat, heel rise, toe-off and back, in the ground frame."""
    path = path or FIGURES / "motion.gif"
    P = sg.build_segmented(m, {"vent_rows": 3, "plantar_stop_deg": 5.0})
    j = P["joint"]
    upper = P["upper"].slice_plane([0, 0, j.origin[2] + 90], [0, 0, -1], cap=True)
    seq = _gait_frames(P, n // 2)
    posed = [_posed(P, a, f, upper) for a, f in seq + seq[::-1]]
    lo = np.min([x.bounds[0] for fr in posed for x, _ in fr], 0)
    hi = np.max([x.bounds[1] for fr in posed for x, _ in fr], 0)
    frames = [_frame_rgb(fr, 8, -20, lo, hi, pad=-25) for fr in posed]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)


def segments_figure(m, path=None):
    """Median person: the foot as bone segments (exploded, labelled) and three stages of push-off."""
    path = path or FIGURES / "segments.png"
    P = sg.build_segmented(m, {"vent_rows": 3, "plantar_stop_deg": 5.0})
    j = P["joint"]
    upper = P["upper"].slice_plane([0, 0, j.origin[2] + 90], [0, 0, -1], cap=True)
    gap = 26.0
    ex, labels = [], []
    for k, (name, bones) in enumerate(sg.SEGMENTS):
        mesh = P["segments"][name].copy()
        mesh.apply_translation([0, k * gap, 0])
        ex.append((mesh, SEG_COLORS[name]))
        labels.append((name, bones, mesh.bounds))
    big = _tile(ex, 40, -35, size=(6, 6), dpi=260)
    big = big.crop(big.getbbox())
    stages = [(g, f"{g[0]}: ankle {g[1]:+.0f}°, MTP {g[2][2]:.0f}°") for g in GAIT]
    poses = [_tile(_posed(P, g[1], g[2], upper), 6, 0, r=150, floor=0, size=(4, 4), dpi=230) for g, _ in stages]
    boxes = [t.getbbox() for t in poses]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    poses = [t.crop(box) for t in poses]

    fig = plt.figure(figsize=(14, 6.4), dpi=160)
    fig.text(0.02, 0.93, "One printed part per bone group", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.02, 0.885, "segments of the Oxford and Rizzoli foot models, pin hinges at the anatomical joints",
             fontsize=10, color=MUTED)
    ax = fig.add_axes([0.02, 0.04, 0.30, 0.80]); ax.imshow(big); ax.set_axis_off()
    ax2 = fig.add_axes([0.33, 0.10, 0.12, 0.72]); ax2.set_axis_off()
    joints = ["ankle (M5)", "Chopart (M3)", "Lisfranc (M3)", "MTP, oblique (M3)"]
    for k, (name, bones, _) in enumerate(labels[::-1]):
        y = 0.86 - k * 0.24
        c = tuple(SEG_COLORS[name] * 0.9)
        ax2.text(0, y, name, color=c, fontsize=11.5, fontweight="bold", transform=ax2.transAxes)
        ax2.text(0, y - 0.055, bones, color=INK, fontsize=9.5, transform=ax2.transAxes)
        ax2.text(0, y - 0.105, "joint: " + joints[3 - k], color=MUTED, fontsize=9, transform=ax2.transAxes)
    fig.text(0.49, 0.93, "Rolls over the toes, stays rigid under load", fontsize=13, fontweight="bold", color=INK)
    rng = [int(round(jj.range_deg)) for jj in P["foot_joints"]]
    fig.text(0.49, 0.9, f"axes above the plate: joints open upwards (up to Chopart {rng[0]}°, Lisfranc {rng[1]}°, MTP {rng[2]}°)\n"
             "and lock flat against each other when loaded; shown in the ground frame", fontsize=10, color=MUTED, va="top")
    for k, ((t, lab), im) in enumerate(zip(stages, poses)):
        ax = fig.add_axes([0.49 + k * 0.17, 0.16, 0.16, 0.62]); ax.imshow(im); ax.set_axis_off()
        ax.text(0.5, -0.1, lab, transform=ax.transAxes, ha="center", color=INK, fontsize=10)
    fig.savefig(path, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    people = hero()
    sizing()
    assistant()
    stiffness()
    build_volume()
    scan_fit()
    parts_figure(S["median_person"])
    segments_figure(S["median_person"])
    turntable(S["median_person"])
    motion(S["median_person"])
    print("figures written to", FIGURES)
