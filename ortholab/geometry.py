"""Parametric ankle-foot orthosis (AFO) built from nine body measurements.

Axes: x medio-lateral (lateral = +x for a right leg), y forward (towards the toes), z up from the sole.

The limb is a stack of elliptical sections set by measured girths and breadths, with the anatomy that a
tape does not give modelled explicitly: a rounded heel pad, the heel standing behind the Achilles tendon,
and the two malleoli (lateral lower than medial). The orthosis is assembled from parts built one by one:

* the leg shell: an exact normal offset of the limb, with a relief dome over each malleolus;
* the footplate: foot outline with a medial arch and low side walls that run into the heel cup;
* strap slots and optional ventilation openings, cut afterwards.

`build_afo` fuses them into the rigid orthosis; `ortholab.articulated` splits it at the ankle axis and adds
hinges.
"""
from dataclasses import dataclass, field

import mapbox_earcut as earcut
import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
from shapely.affinity import scale, translate
from shapely.geometry import Point, box as sbox
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


# --------------------------------------------------------------------------- anatomy

@dataclass
class LimbProfile:
    """Half-width a(z), half-depth b(z) and position of the back of the limb y0(z); z from the sole."""
    z: np.ndarray
    a: np.ndarray
    b: np.ndarray
    z_ankle: float
    z_top: float
    y0: np.ndarray = None
    zy: np.ndarray = None
    girths: dict = field(default_factory=dict)

    def at(self, zq):
        return PchipInterpolator(self.z, self.a)(zq), PchipInterpolator(self.z, self.b)(zq)

    def back(self, zq):
        if self.y0 is None:
            return np.zeros_like(np.asarray(zq, float))
        return PchipInterpolator(self.zy if self.zy is not None else self.z, self.y0)(zq)


def limb_profile(m, p=DESIGN):
    """Control sections from the ANSUR measurements. Heights not measured in ANSUR are explicit assumptions."""
    p = {**DESIGN, **p}
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
    # back of the limb: heel behind the Achilles line, tendon set forward, calf bulging back again
    zy = np.array([0.0, 0.45 * z_m, z_m + 15.0, z_a, z_c, z_t])
    y0 = np.array([0.0, -p["heel_bulge"], p["achilles_inset"], p["achilles_inset"], 0.0, 3.0])
    return LimbProfile(z, a, b, z_a, z_t, y0, zy)


def heel_rounding(zl, r):
    """Inset (mm) of the heel pad near the sole: a quarter circle of radius r."""
    zl = np.asarray(zl, float)
    d = np.zeros_like(zl)
    k = zl < r
    d[k] = r - np.sqrt(np.maximum(r ** 2 - (r - zl[k]) ** 2, 0.0))
    return d


def malleoli(m, p=DESIGN):
    """Centres of the lateral and medial malleoli: (angle on the section in rad, height above the sole)."""
    p = {**DESIGN, **p}
    t = p["thickness"]
    lat = 1.0 if p.get("side", "right") == "right" else -1.0
    z_lat = m["malleolus_height"] + t
    z_med = z_lat + p["medial_offset"]
    th_lat = np.radians(-8.0) if lat > 0 else np.radians(-172.0)    # lateral malleolus slightly posterior
    th_med = np.radians(-178.0) if lat > 0 else np.radians(-2.0)
    return [(th_lat, z_lat), (th_med, z_med)]


def relief(th, z, m, p=DESIGN, sz=10.0, sth=np.radians(16.0)):
    """Extra clearance (mm) forming a dome over each malleolus."""
    p = {**DESIGN, **p}
    out = np.zeros(np.broadcast(th, z).shape)
    for thc, zc in malleoli(m, p):
        dth = np.angle(np.exp(1j * (th - thc)))
        out = out + p["malleolus_relief"] * np.exp(-0.5 * (((z - zc) / sz) ** 2 + (dth / sth) ** 2))
    return out


def section(prof, z, p=DESIGN):
    """(a, b, y0) of the limb at plate-referenced height z, heel rounding included."""
    p = {**DESIGN, **p}
    zl = np.maximum(np.asarray(z, float) - p["thickness"], 0.0)
    a, b = prof.at(zl)
    y0 = prof.back(zl)
    d = heel_rounding(zl, p["heel_radius"])
    return a - d, b - d, y0 + d


def _wrap(z, prof, p):
    """Wrap angle (deg) along the leg: full wrap everywhere, optionally narrowed around the ankle."""
    w = p.get("ankle_wrap_deg", p["wrap_deg"])
    if w == p["wrap_deg"]:
        return np.full_like(np.asarray(z, float), p["wrap_deg"])
    bump = np.exp(-0.5 * ((np.asarray(z, float) - prof.z_ankle) / 25.0) ** 2)
    return p["wrap_deg"] + (w - p["wrap_deg"]) * bump


def _arc(a, b, offset, thetas, y0=0.0):
    """Points at a normal offset from the ellipse x = a cos t, y = y0 + b + b sin t (back of the limb at y0)."""
    c, s = np.cos(thetas), np.sin(thetas)
    nx, ny = b * c, a * s
    n = np.hypot(nx, ny)
    x = a * c + offset * nx / n
    y = y0 + b + b * s + offset * ny / n
    return x, y


def _levels(prof, n):
    """More sections near the heel and ankle, where the shape changes fastest."""
    u = np.linspace(0, 1, n) ** 1.6
    return u * prof.z_top


# --------------------------------------------------------------------------- parts

def _loft(rings):
    """Closed solid from a stack of rings with the same vertex count (side strips plus two capped ends)."""
    V = np.vstack(rings)
    K = len(rings[0])
    faces = []
    for k in range(len(rings) - 1):
        o0, o1 = k * K, (k + 1) * K
        i = np.arange(K)
        j = (i + 1) % K
        faces.append(np.column_stack([o0 + i, o0 + j, o1 + j]))
        faces.append(np.column_stack([o0 + i, o1 + j, o1 + i]))
    for k, flip in ((0, True), (len(rings) - 1, False)):
        tri = earcut.triangulate_float64(rings[k][:, :2], np.array([K], dtype=np.uint32)).reshape(-1, 3) + k * K
        faces.append(tri[:, ::-1] if flip else tri)
    mesh = trimesh.Trimesh(V, np.vstack(faces), process=True)
    trimesh.repair.fix_normals(mesh)
    return mesh


def shell_layer(m, p, prof, inner=0.0, outer=None, z0=0.0, z1=None, levels=None):
    """One shell layer between offsets clearance+inner and clearance+outer (default: thickness), with malleolus relief."""
    t, cl, M = p["thickness"], p["clearance"], p["arc_points"]
    outer = t if outer is None else outer
    z1 = prof.z_top if z1 is None else z1
    n = levels or p["levels"]
    zs = z0 + (z1 - z0) * np.linspace(0, 1, n) ** (1.6 if z0 == 0 else 1.0)
    wraps = _wrap(zs, prof, p)
    a_z, b_z, y_z = section(prof, zs, p)
    rings = []
    for z, a, b, y0, w in zip(zs, a_z, b_z, y_z, wraps):
        half = np.radians(w) / 2
        th = np.linspace(-np.pi / 2 - half, -np.pi / 2 + half, M)
        rel = relief(th, z, m, p)
        xo, yo = _arc(a, b, cl + rel + outer, th, y0)
        xi, yi = _arc(a, b, cl + rel + inner, th[::-1], y0)
        rings.append(np.column_stack([np.r_[xo, xi], np.r_[yo, yi], np.full(2 * M, z)]))
    return _loft(rings)


def shell_mesh(m, p=DESIGN, prof=None):
    p = {**DESIGN, **p}
    prof = prof or limb_profile(m, p)
    return shell_layer(m, p, prof), prof


def foot_outline(m, p=DESIGN):
    """Foot outline: heel pad (rounded inset), ball of the foot at its measured position and breadth, tapered toe."""
    p = {**DESIGN, **p}
    hb, fb = m["heel_breadth"], m["foot_breadth"]
    L = p["plate_length"] * m["foot_length"]
    r = p["heel_radius"]
    heel = Point(0, hb / 2).buffer(hb / 2 - r, 64)
    mid = translate(scale(Point(0, 0).buffer(1, 64), hb / 2 - r * 0.4, 22), 0, hb / 2 + 25)
    ball = translate(scale(Point(0, 0).buffer(1, 64), fb / 2, 18), 0, m["ball_length"])
    toe = translate(scale(Point(0, 0).buffer(1, 64), 0.36 * fb, 22), 0, L - 22)
    return unary_union([heel, mid, ball, toe]).convex_hull


def plate_mesh(m, p=DESIGN):
    """Footplate: outline offset to meet the heel cup, a medial arch support and low tapered side walls."""
    p = {**DESIGN, **p}
    t, cl = p["thickness"], p["clearance"]
    outline = foot_outline(m, p)
    plate = trimesh.creation.extrude_polygon(outline.buffer(cl + t, 32), t)
    parts = [plate]
    medial = -1.0 if p.get("side", "right") == "right" else 1.0
    fb, L = m["foot_breadth"], p["plate_length"] * m["foot_length"]
    if p["arch_height"] > 0:
        arch = trimesh.creation.icosphere(subdivisions=4)
        arch.apply_scale([0.22 * fb, 0.22 * L, p["arch_height"]])
        arch.apply_translation([medial * 0.24 * fb, 0.40 * L, t])
        prism = trimesh.creation.extrude_polygon(outline, 60.0)
        prism.apply_translation([0, 0, t - 0.01])
        parts.append(trimesh.boolean.intersection([arch, prism], engine="manifold"))
    if p["wall_height"] > 0:
        y0, y1 = m["heel_breadth"] * 0.45, m["ball_length"] - 10.0
        ring = outline.buffer(cl + t, 32).difference(outline.buffer(cl, 32)).intersection(sbox(-200, y0, 200, y1))
        if not ring.is_empty:
            wall = trimesh.creation.extrude_polygon(ring, t + p["wall_height"]) if ring.geom_type == "Polygon" else \
                trimesh.util.concatenate([trimesh.creation.extrude_polygon(g, t + p["wall_height"]) for g in ring.geoms])
            # taper the walls down towards the ball of the foot
            ymid = y0 + 0.45 * (y1 - y0)
            ang = np.arctan2(p["wall_height"], y1 - ymid)
            cutter = trimesh.creation.box([600, 600, 200])
            cutter.apply_translation([0, 300, 100])
            R = trimesh.transformations.rotation_matrix(ang, [1, 0, 0], [0, 0, 0])
            cutter.apply_transform(R)
            cutter.apply_translation([0, ymid, t + p["wall_height"]])
            parts.append(trimesh.boolean.difference([wall, cutter], engine="manifold"))
    return trimesh.boolean.union(parts, engine="manifold")


def _radial_cutter(prof, m, p, th, z, w, h, depth_extra=10.0):
    """Box through the shell at angle th and height z, w wide (tangential) and h tall."""
    t, cl = p["thickness"], p["clearance"]
    a, b, y0 = (float(v) for v in section(prof, z, p))
    x, y = _arc(a, b, cl + float(relief(th, z, m, p)) + t / 2, np.array([th]), y0)
    d = np.array([b * np.cos(th), a * np.sin(th), 0.0])
    d /= np.linalg.norm(d)
    cut = trimesh.creation.box([w, h, 4 * t + depth_extra])
    R = trimesh.geometry.align_vectors([0, 0, 1], d)
    up = R[:3, :3] @ np.array([0, 1, 0])
    spin = np.arctan2(np.cross(up, [0, 0, 1]) @ d, up @ np.array([0, 0, 1]))
    R = R @ trimesh.transformations.rotation_matrix(spin, [0, 0, 1])
    R[:3, 3] = [x[0], y[0], z]
    cut.apply_transform(R)
    return cut


def strap_slots(m, prof, p, levels=None):
    """Vertical slits near both trimline edges for hook-and-loop straps (calf strap, and one above the ankle)."""
    if not p.get("strap_slots", True):
        return None
    levels = levels or [prof.z_top - 28.0, prof.z_ankle + 30.0]
    cuts = []
    for z in levels:
        w = float(_wrap(np.array([z]), prof, p)[0])
        for sgn in (-1, 1):
            th = np.radians(-90.0 + sgn * (w / 2 - 13.0))
            cuts.append(_radial_cutter(prof, m, p, th, z, 5.0, 28.0))
    return trimesh.util.concatenate(cuts)


def vents(m, prof, p):
    """Staggered rows of oval ventilation openings cut through the calf shell."""
    rows = int(p.get("vent_rows", 0))
    if rows <= 0:
        return None
    rx, rz = p.get("vent_width", 16.0) / 2, p.get("vent_height", 26.0) / 2
    z0, z1 = prof.z_ankle + 70.0 + rz, prof.z_top - 50.0 - rz
    if z1 <= z0:
        return None
    t, cl = p["thickness"], p["clearance"]
    cuts = []
    span = min(p["wrap_deg"] - 90.0, 120.0)            # keep solid bands along both edges for the straps
    for i, z in enumerate(np.linspace(z0, z1, rows)):
        a, b, y0 = (float(v) for v in section(prof, z, p))
        n = 4 if i % 2 else 5
        for th in np.radians(-90.0 + np.linspace(-span / 2, span / 2, n) * (0.78 if i % 2 else 1.0)):
            x, y = _arc(a, b, cl + t / 2, np.array([th]), y0)
            d = np.array([b * np.cos(th), a * np.sin(th), 0.0])
            d /= np.linalg.norm(d)
            cyl = trimesh.creation.cylinder(radius=1.0, height=6 * t + 10, sections=40)
            cyl.apply_scale([rx, rz, 1.0])
            R = trimesh.geometry.align_vectors([0, 0, 1], d)
            up = R[:3, :3] @ np.array([0, 1, 0])
            spin = np.arctan2(np.cross(up, [0, 0, 1]) @ d, up @ np.array([0, 0, 1]))
            R = R @ trimesh.transformations.rotation_matrix(spin, [0, 0, 1])
            R[:3, 3] = [x[0], y[0], z]
            cyl.apply_transform(R)
            cuts.append(cyl)
    return trimesh.util.concatenate(cuts)


def build_afo(m, p=None, profile=None):
    """Watertight rigid AFO for one person (dict-like of measurements in mm).

    profile: optional LimbProfile, for instance from a 3D scan (see ortholab.scan); the footplate still uses m.
    """
    p = {**DESIGN, **(p or {})}
    prof = profile or limb_profile(m, p)
    shell = shell_layer(m, p, prof)
    plate = plate_mesh(m, p)
    afo = trimesh.boolean.union([shell, plate], engine="manifold")
    cuts = [c for c in (strap_slots(m, prof, p), vents(m, prof, p)) if c is not None]
    if cuts:
        afo = trimesh.boolean.difference([afo, trimesh.util.concatenate(cuts)], engine="manifold")
    afo.metadata["profile"] = prof
    afo.metadata["params"] = p
    return afo
