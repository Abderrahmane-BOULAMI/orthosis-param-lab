"""Shaded renders of generated orthoses (matplotlib only, no GPU needed)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = np.array([0.0, 0.565, 0.612])     # teal #00909C
WARM = np.array([0.95, 0.56, 0.23])


def shade(mesh, view_dir, base=BASE, light=(0.35, -0.55, 0.75)):
    n = mesh.face_normals
    L = np.asarray(light, float)
    L /= np.linalg.norm(L)
    V = np.asarray(view_dir, float)
    V /= np.linalg.norm(V)
    diff = 0.55 * np.clip(n @ L, 0, 1) + 0.45 * np.abs(n @ V)   # key light + camera fill
    back = (n @ V) < 0                      # inner faces seen through the opening
    H = (L + V) / np.linalg.norm(L + V)
    spec = np.clip(n @ H, 0, 1) ** 30
    col = base[None, :] * (0.38 + 0.62 * diff[:, None]) + 0.35 * spec[:, None]
    col[back] = base * 0.45 + 0.42 * (0.6 + 0.4 * diff[back, None])
    return np.clip(col, 0, 1)


def draw(ax, mesh, elev=14, azim=-58, base=BASE, offset=(0, 0, 0)):
    v = mesh.vertices + np.asarray(offset)
    tri = v[mesh.faces]
    az, el = np.radians(azim), np.radians(elev)
    view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    col = shade(mesh, view, base)
    pc = Poly3DCollection(tri, facecolors=col, edgecolors=col, linewidths=0.25, antialiased=True)
    ax.add_collection3d(pc)
    ax.view_init(elev, azim)
    ax.set_axis_off()


def frame(ax, lo, hi, pad=10):
    c = (lo + hi) / 2
    r = (hi - lo).max() / 2 + pad
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))


def single(mesh, path, elev=14, azim=-58, size=6, dpi=150, base=BASE):
    fig = plt.figure(figsize=(size, size))
    ax = fig.add_axes([0, 0, 1, 1], projection="3d")
    draw(ax, mesh, elev, azim, base)
    frame(ax, mesh.bounds[0], mesh.bounds[1])
    fig.savefig(path, dpi=dpi, transparent=True)
    plt.close(fig)


NAVY = np.array([0.20, 0.36, 0.62])     # #335C9E, calf cuff
STEEL = np.array([0.62, 0.65, 0.69])     # pins


def draw_parts(ax, parts, elev=14, azim=-58, max_edge=8.0):
    """Several meshes, each with its own colour, drawn as one collection so they hide each other correctly."""
    az, el = np.radians(azim), np.radians(elev)
    view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    tris, cols = [], []
    for mesh, base in parts:
        if mesh.edges_unique_length.max() > max_edge:          # big flat faces sort badly in depth: split them
            v, f = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, max_edge=max_edge)
            mesh = trimesh.Trimesh(v, f, process=False)
        tris.append(mesh.vertices[mesh.faces])
        cols.append(shade(mesh, view, np.asarray(base, float)))
    tri, col = np.concatenate(tris), np.concatenate(cols)
    pc = Poly3DCollection(tri, facecolors=col, edgecolors=col, linewidths=0.25, antialiased=True)
    ax.add_collection3d(pc)
    ax.view_init(elev, azim)
    ax.set_axis_off()


SEG_COLORS = {"hindfoot": BASE, "midfoot": np.array([0.89, 0.64, 0.23]),     # teal, amber
              "forefoot": np.array([0.85, 0.39, 0.29]), "toes": np.array([0.49, 0.42, 0.71])}   # coral, violet


def assembly(parts, pins=True):
    """(mesh, colour) list for an articulated orthosis: foot section teal, calf cuff navy, pins steel."""
    if "segments" in parts:
        out = [(m, SEG_COLORS[k]) for k, m in parts["segments"].items()] + [(parts["upper"], NAVY)]
        if pins:
            out += [(parts["pins"], STEEL), (parts["foot_pins"], STEEL)]
        return out
    out = [(parts["lower"], BASE), (parts["upper"], NAVY)]
    if pins and "pins" in parts:
        out.append((parts["pins"], STEEL))
    return out
