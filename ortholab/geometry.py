"""Parametric ankle-foot orthosis (AFO) built from nine body measurements.

Axes: x medio-lateral, y forward (towards the toes), z up. The back of the heel sits at y = 0.
The leg is described by elliptical cross-sections whose size follows the measured girths and breadths;
the shell wraps the back of the limb with an exact constant thickness, and a footplate is fused under it.
"""
from dataclasses import dataclass

import mapbox_earcut as earcut
import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Point
from shapely.affinity import scale, translate
from shapely.ops import unary_union

from .config import DESIGN


def ellipse_axes(perimeter, ratio):
    """Semi-axes (a, b) of an ellipse with a given perimeter and width/depth ratio a/b (Ramanujan II)."""
    def per(b):
        a = ratio * b
        h = ((a - b) / (a + b)) ** 2
        return np.pi * (a + b) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))
    lo, hi = 1.0, perimeter
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if per(mid) < perimeter else (lo, mid)
    b = 0.5 * (lo + hi)
    return ratio * b, b


def perimeter(a, b):
    h = ((a - b) / (a + b)) ** 2
    return np.pi * (a + b) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))


@dataclass
class LimbProfile:
    """Half-width a(z) and half-depth b(z) of the limb, z measured from the sole of the foot."""
    z: np.ndarray
    a: np.ndarray
    b: np.ndarray
    z_ankle: float
    z_top: float

    def at(self, zq):
        fa = PchipInterpolator(self.z, self.a)
        fb = PchipInterpolator(self.z, self.b)
        return fa(zq), fb(zq)


def limb_profile(m, p=DESIGN):
    """Control sections from the ANSUR measurements. Heights not measured in ANSUR are explicit assumptions."""
    z_m = m["malleolus_height"]
    z_a = z_m + 40.0                                  # minimum ankle girth: assumed 40 mm above the malleolus
    z_c = p["calf_level"] * m["tibial_height"]
    z_t = m["tibial_height"] - p["top_below_tibiale"]
    a_a, b_a = ellipse_axes(m["ankle_circ"], 1.05)
    a_c, b_c = ellipse_axes(m["calf_circ"], p["calf_ratio"])
    a_t, b_t = ellipse_axes(0.92 * m["calf_circ"], p["calf_ratio"])  # below-knee girth: 92 % of calf (assumption)
    hb = m["heel_breadth"] / 2
    z = np.array([0.0, z_m, z_a, z_c, z_t])
    a = np.array([hb, m["bimalleolar_breadth"] / 2, a_a, a_c, a_t])
    b = np.array([hb, b_a, b_a, b_c, b_t])
    return LimbProfile(z, a, b, z_a, z_t)


def _wrap(z, prof, p):
    """Wrap angle (deg) along the leg: full wrap everywhere, optionally narrowed around the ankle."""
    w = p.get("ankle_wrap_deg", p["wrap_deg"])
    if w == p["wrap_deg"]:
        return np.full_like(z, p["wrap_deg"])
    bump = np.exp(-0.5 * ((z - prof.z_ankle) / 25.0) ** 2)
    return p["wrap_deg"] + (w - p["wrap_deg"]) * bump


def _arc(a, b, offset, thetas):
    """Points at a normal offset from the ellipse x = a cos t, y = b + b sin t (back of the limb at y = 0)."""
    c, s = np.cos(thetas), np.sin(thetas)
    nx, ny = b * c, a * s
    n = np.hypot(nx, ny)
    x = a * c + offset * nx / n
    y = b + b * s + offset * ny / n
    return x, y


def _levels(prof, n):
    """More sections near the heel and ankle, where the shape changes fastest."""
    u = np.linspace(0, 1, n) ** 1.6
    return u * prof.z_top


def shell_mesh(m, p=DESIGN):
    prof = limb_profile(m, p)
    t, cl, M = p["thickness"], p["clearance"], p["arc_points"]
    zs = _levels(prof, p["levels"])
    a_z, b_z = prof.at(np.maximum(zs - t, 0.0))   # the foot rests on the plate, so the limb starts at z = t
    wraps = _wrap(zs, prof, p)
    rings = []
    for z, a, b, w in zip(zs, a_z, b_z, wraps):
        half = np.radians(w) / 2
        th = np.linspace(-np.pi / 2 - half, -np.pi / 2 + half, M)
        xo, yo = _arc(a, b, cl + t, th)
        xi, yi = _arc(a, b, cl, th[::-1])
        ring = np.column_stack([np.r_[xo, xi], np.r_[yo, yi], np.full(2 * M, z)])
        rings.append(ring)
    V = np.vstack(rings)
    K = 2 * M
    faces = []
    for k in range(len(rings) - 1):
        o0, o1 = k * K, (k + 1) * K
        for i in range(K):
            j = (i + 1) % K
            faces += [[o0 + i, o0 + j, o1 + j], [o0 + i, o1 + j, o1 + i]]
    for k, flip in ((0, True), (len(rings) - 1, False)):
        tri = earcut.triangulate_float64(rings[k][:, :2], np.array([K], dtype=np.uint32)).reshape(-1, 3)
        tri = tri + k * K
        faces += (tri[:, ::-1] if flip else tri).tolist()
    mesh = trimesh.Trimesh(V, np.array(faces), process=True)
    trimesh.repair.fix_normals(mesh)
    return mesh, prof


def foot_outline(m, p=DESIGN):
    """Convex foot outline: heel circle, ball of the foot at its measured position and breadth, tapered toe."""
    hb, fb = m["heel_breadth"], m["foot_breadth"]
    L = p["plate_length"] * m["foot_length"]
    heel = Point(0, hb / 2).buffer(hb / 2, 64)
    ball = translate(scale(Point(0, 0).buffer(1, 64), fb / 2, 18), 0, m["ball_length"])
    toe = translate(scale(Point(0, 0).buffer(1, 64), 0.36 * fb, 22), 0, L - 22)
    return unary_union([heel, ball, toe]).convex_hull


def plate_mesh(m, p=DESIGN):
    poly = foot_outline(m, p).buffer(p["clearance"] + p["thickness"], 32)
    plate = trimesh.creation.extrude_polygon(poly, p["thickness"])
    return plate


def vents(m, prof, p):
    """Staggered rows of oval ventilation openings cut through the calf shell."""
    rows = int(p.get("vent_rows", 0))
    if rows <= 0:
        return None
    t, cl = p["thickness"], p["clearance"]
    rx, rz = p.get("vent_width", 16.0) / 2, p.get("vent_height", 26.0) / 2
    z0, z1 = prof.z_ankle + 55.0 + rz, prof.z_top - 22.0 - rz
    if z1 <= z0:
        return None
    cuts = []
    span = min(p["wrap_deg"] - 70.0, 130.0)          # keep solid bands along both edges
    for i, z in enumerate(np.linspace(z0, z1, rows)):
        a, b = (float(v) for v in prof.at(z - t))
        n = 4 if i % 2 else 5
        for th in np.radians(-90.0 + np.linspace(-span / 2, span / 2, n) * (0.78 if i % 2 else 1.0)):
            x, y = _arc(a, b, cl + t / 2, np.array([th]))
            d = np.array([b * np.cos(th), a * np.sin(th), 0.0])
            d /= np.linalg.norm(d)
            cyl = trimesh.creation.cylinder(radius=1.0, height=6 * t + 10, sections=40)
            cyl.apply_scale([rx, rz, 1.0])                       # oval: narrow across, tall along the leg
            R = trimesh.geometry.align_vectors([0, 0, 1], d)     # cylinder axis -> radial direction
            up = R[:3, :3] @ np.array([0, 1, 0])
            spin = np.arctan2(np.cross(up, [0, 0, 1]) @ d, up @ np.array([0, 0, 1]))
            R = R @ trimesh.transformations.rotation_matrix(spin, [0, 0, 1])
            R[:3, 3] = [x[0], y[0], z]
            cyl.apply_transform(R)
            cuts.append(cyl)
    return trimesh.util.concatenate(cuts)


def build_afo(m, p=None):
    """Watertight AFO mesh for one person (dict-like of measurements in mm)."""
    p = {**DESIGN, **(p or {})}
    shell, prof = shell_mesh(m, p)
    plate = plate_mesh(m, p)
    afo = trimesh.boolean.union([shell, plate], engine="manifold")
    cut = vents(m, prof, p)
    if cut is not None:
        afo = trimesh.boolean.difference([afo, cut], engine="manifold")
    afo.metadata["profile"] = prof
    afo.metadata["params"] = p
    return afo
