"""Articulated AFO: the rigid orthosis split at the ankle axis into two printable parts joined by hinges.

Parts, each built on its own and then assembled:

* lower part (foot section): footplate, heel cup and two side uprights ending in flat inner hinge discs;
* upper part (calf cuff): leg shell above the ankle with strap slots, and two side straps ending in flat outer
  hinge discs that sit outside the inner ones;
* pins: one M5 pin per side through both discs (a standard screw and nut; a printed pin is exported for previews).

The ankle axis runs medio-laterally through the malleoli (mean of the lateral and medial heights). Discs are flat
and centred on that axis, so they turn on each other without touching; a print gap separates every moving pair.
`range_of_motion` turns the foot section about the axis and measures, on the real meshes, the angles at which the
two parts first collide.
"""
from dataclasses import dataclass

import numpy as np
import trimesh

from .config import DESIGN
from .geometry import build_afo, limb_profile, malleoli, plate_mesh, relief, section, shell_layer, strap_slots, vents


@dataclass
class Joint:
    origin: np.ndarray       # a point on the ankle axis (x = 0)
    x_inner: float           # |x| where the inner (lower) disc starts
    radius: float
    pin_radius: float
    gap: float
    thickness: float


def ankle_joint(m, p, prof):
    t, cl = p["thickness"], p["clearance"]
    (_, z_lat), (_, z_med) = malleoli(m, p)
    z_ax = 0.5 * (z_lat + z_med)
    a, b, y0 = (float(v) for v in section(prof, z_ax, p))
    x_in = a + cl + p["malleolus_relief"]
    return Joint(np.array([0.0, y0 + b, z_ax]), x_in, p["hinge_radius"], p["pin_diameter"] / 2, p["print_gap"], t)


def _disc(j, x0, x1, radius):
    """Flat disc between x0 and x1 (x0 < x1), centred on the ankle axis."""
    d = trimesh.creation.cylinder(radius=radius, height=x1 - x0, sections=96)
    d.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0]))
    d.apply_translation([0.5 * (x0 + x1), j.origin[1], j.origin[2]])
    return d


def _both_sides(fn):
    parts = [fn(1.0), fn(-1.0)]
    return trimesh.boolean.union(parts, engine="manifold")


def _box(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box([x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)])
    return b


def _side_box(j, s, x0, x1, y0, y1, z0, z1):
    a, b = sorted((s * x0, s * x1))
    return _box(a, b, y0, y1, z0, z1)


def build_articulated(m, p=None, profile=None):
    """Return dict with 'lower', 'upper', 'pins' meshes and the joint, all in the assembled position."""
    p = {**DESIGN, **(p or {})}
    prof = profile or limb_profile(m, p)
    j = ankle_joint(m, p, prof)
    t, g, R = j.thickness, j.gap, j.radius
    oy, oz = j.origin[1], j.origin[2]
    xi = j.x_inner

    rigid = build_afo(m, {**p, "strap_slots": False, "vent_rows": 0}, prof)

    # ---- lower part: everything below the ankle window, plus the side uprights up to the inner discs
    below = _box(-500, 500, -500, 900, -50, oz - 4.0)
    upright_zone = _both_sides(lambda s: _side_box(j, s, 0.55 * xi, 500, oy - 0.75 * R, oy + 0.75 * R, -50, oz))
    lower = trimesh.boolean.intersection([rigid, trimesh.boolean.union([below, upright_zone], engine="manifold")],
                                         engine="manifold")
    inner_discs = _both_sides(lambda s: _disc(j, *sorted((s * (xi - 0.6), s * (xi + t))), R))
    lower = trimesh.boolean.union([lower, inner_discs], engine="manifold")

    # ---- upper part: shell above the window, outer discs outside the inner ones, side straps joining them
    z_cut = oz + R + 4.0
    above = _box(-500, 500, -500, 900, z_cut, 2000)
    upper = trimesh.boolean.intersection([rigid, above], engine="manifold")
    xo0, xo1 = xi + t + g, xi + 2 * t + g
    outer_discs = _both_sides(lambda s: _disc(j, *sorted((s * xo0, s * xo1)), R + 1.5))
    straps = _both_sides(lambda s: _side_box(j, s, xo0, xo1, oy - 0.7 * R, oy + 0.7 * R, oz, z_cut + 22))
    # bridge from the strap inwards into the cuff wall, above the reach of the lower part
    a_b, b_b, y_b = (float(v) for v in section(prof, z_cut + 10, p))
    x_wall = a_b + p["clearance"] + 0.5
    bridges = _both_sides(lambda s: _side_box(j, s, x_wall, xo1, oy - 0.7 * R, oy + 0.7 * R, z_cut + 2, z_cut + 22))
    upper = trimesh.boolean.union([upper, outer_discs, straps, bridges], engine="manifold")
    rigid_back = rigid

    # ---- slots, vents and pin holes
    cuts = [c for c in (strap_slots(m, prof, p, [prof.z_top - 28.0]), vents(m, prof, p)) if c is not None]
    hole = trimesh.creation.cylinder(radius=j.pin_radius, height=2 * (xo1 + 10), sections=48)
    hole.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0]))
    hole.apply_translation([0, oy, oz])
    upper = trimesh.boolean.difference([upper, trimesh.util.concatenate(cuts + [hole])], engine="manifold")
    lower = trimesh.boolean.difference([lower, hole], engine="manifold")

    # ---- pins (M5 screw stand-ins) for previews
    def pin(s):
        shaft = _disc(j, *sorted((s * (xi - 1.0), s * (xo1 + 1.5))), j.pin_radius - 0.15)
        head = _disc(j, *sorted((s * (xo1 + 0.2), s * (xo1 + 3.2))), 4.2)
        return trimesh.boolean.union([shaft, head], engine="manifold")
    pins = trimesh.util.concatenate([pin(1.0), pin(-1.0)])

    parts = {"lower": lower, "upper": upper, "pins": pins, "joint": j, "profile": prof, "params": p}
    if p.get("plantar_stop_deg") is not None:
        parts["upper"] = _add_plantar_stop(parts, rigid_back, z_cut, float(p["plantar_stop_deg"]))
    for name in ("lower", "upper"):
        parts[name].metadata.update({"profile": prof, "params": p, "part": name})
    return parts


def _stop_block(rigid, j, z_bottom, z_top):
    """Posterior part of the shell between two heights: grows down from the cuff to meet the heel cup."""
    zone = _box(-0.45 * j.x_inner, 0.45 * j.x_inner, -500, j.origin[1] - 0.5 * j.radius, z_bottom, z_top + 1.0)
    return trimesh.boolean.intersection([rigid, zone], engine="manifold")


def _add_plantar_stop(parts, rigid, z_cut, target_deg, iters=12):
    """Extend the back of the calf cuff downwards until the foot section stops at target_deg of plantarflexion.

    The height of the stop is found by bisection on the real meshes, so the clinical setting (for example
    5 degrees for a drop-foot orthosis) is met whatever the person's size.
    """
    lower, upper, j = parts["lower"], parts["upper"], parts["joint"]
    lo, hi = j.origin[2] - 4.0 + j.gap, z_cut               # lowest possible stop (touches at rest) .. no stop
    best = upper
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        cand = trimesh.boolean.union([upper, _stop_block(rigid, j, mid, z_cut)], engine="manifold")
        trial = {**parts, "upper": cand}
        stop = range_of_motion_fast(trial, limit=50.0, tol_deg=0.5)["plantarflexion_deg"]
        if stop > target_deg:
            hi, best = mid, cand            # stop too late: bring the block lower
        else:
            lo = mid
    return trimesh.boolean.union([upper, _stop_block(rigid, j, hi, z_cut)], engine="manifold")


def rotate_about_axis(mesh, j, deg):
    """Copy of mesh turned about the ankle axis; positive = dorsiflexion (toes up)."""
    out = mesh.copy()
    out.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0], j.origin))
    return out


def overlap_volume(a, b):
    inter = trimesh.boolean.intersection([a, b], engine="manifold")
    return float(inter.volume) if len(inter.faces) else 0.0


def range_of_motion(parts, limit=40, step=1.0, tol_mm3=1.0):
    """First angles (deg) at which the foot section collides with the calf cuff, dorsiflexion and plantarflexion."""
    lower, upper, j = parts["lower"], parts["upper"], parts["joint"]
    out = {}
    for name, sgn in (("dorsiflexion_deg", 1), ("plantarflexion_deg", -1)):
        free = 0.0
        a = step
        while a <= limit:
            if overlap_volume(rotate_about_axis(lower, j, sgn * a), upper) > tol_mm3:
                break
            free = a
            a += step
        out[name] = free
    out["rest_overlap_mm3"] = overlap_volume(lower, upper)
    return out


def range_of_motion_fast(parts, limit=50.0, tol_deg=1.0, tol_mm3=1.0):
    """Same as range_of_motion, by bisection: about a dozen collision tests instead of one per degree."""
    lower, upper, j = parts["lower"], parts["upper"], parts["joint"]
    out = {}
    for name, sgn in (("dorsiflexion_deg", 1), ("plantarflexion_deg", -1)):
        hits = lambda a: overlap_volume(rotate_about_axis(lower, j, sgn * a), upper) > tol_mm3  # noqa: E731
        if not hits(limit):
            out[name] = float(limit)
            continue
        lo, hi = 0.0, float(limit)
        while hi - lo > tol_deg:
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if hits(mid) else (mid, hi)
        out[name] = round(lo, 1)
    out["rest_overlap_mm3"] = overlap_volume(lower, upper)
    return out


def exploded(parts, gap=40.0):
    """Parts pulled apart along their natural directions, for an exploded-view render.

    The calf cuff lifts by `gap`, the pins slide out sideways along the hinge axis.
    """
    lower = parts["lower"].copy()
    upper = parts["upper"].copy()
    upper.apply_translation([0, 0, gap])
    pins = []
    for piece in parts["pins"].split(only_watertight=False):
        s = 1.0 if piece.centroid[0] > 0 else -1.0
        piece = piece.copy()
        piece.apply_translation([s * 0.9 * gap, 0, 0.5 * gap])   # out of the discs, level with the lifted cuff
        pins.append(piece)
    return {"lower": lower, "upper": upper, "pins": trimesh.util.concatenate(pins)}
