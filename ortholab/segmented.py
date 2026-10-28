"""Segmented foot: the foot section of the articulated AFO split into one printed part per functional bone group.

Splitting the foot into its 26 bones would give parts too small to print or wear, so the segments follow the
multi-segment foot models used in gait analysis (Oxford and Rizzoli foot models):

====================  =====================================  ====================================================
Segment               Bones                                  Joint with the segment behind it
====================  =====================================  ====================================================
hindfoot              calcaneus, talus                       ankle (talocrural), M5 hinge to the calf cuff
midfoot               navicular, cuboid, cuneiforms          Chopart (midtarsal) joint
forefoot              metatarsals                            Lisfranc (tarsometatarsal) joint
toes                  phalanges                              metatarsophalangeal (MTP) joint, oblique line
====================  =====================================  ====================================================

Every foot joint is a pin hinge with its axis just above the footplate. Material below the axis (the plate) opens
when the distal segment turns up, so the foot rolls over the toes at push-off, and closes at once when it turns down,
so the plate locks flat under body weight. Material above the axis (the side walls) gets a V notch whose angle is the
allowed dorsiflexion. On each side, a knuckle of the proximal segment sits inside a knuckle of the distal segment, an
M3 pin runs through both, and a bridge outside the inner knuckle's reach joins the outer knuckle to its segment.
"""
from dataclasses import dataclass

import numpy as np
import trimesh

from .articulated import build_articulated, overlap_volume
from .config import DESIGN

SEGMENTS = [
    ("hindfoot", "calcaneus, talus"),
    ("midfoot", "navicular, cuboid, cuneiforms"),
    ("forefoot", "metatarsals"),
    ("toes", "phalanges"),
]


@dataclass
class FootJoint:
    name: str
    origin: np.ndarray      # point on the axis, at the foot centre line, axis height
    axis: np.ndarray        # unit, horizontal; rotation by +deg about it lifts the distal segment
    normal: np.ndarray      # unit, horizontal, pointing to the distal segment
    range_deg: float        # designed dorsiflexion
    radius: float
    pin_radius: float
    gap: float


def foot_joints(m, p):
    """Chopart, Lisfranc and MTP joint axes from the foot measurements."""
    L, B, fb = m["foot_length"], m["ball_length"], m["foot_breadth"]
    medial = -1.0 if p.get("side", "right") == "right" else 1.0
    z = p["thickness"] + p["foot_knuckle_radius"]
    r, pr, g = p["foot_knuckle_radius"], p["foot_pin_diameter"] / 2, p["print_gap"]
    out = []
    for name, y, rng in (("chopart", p["chopart_at"] * L, p["midfoot_range"]),
                         ("lisfranc", B - p["metatarsal_length"] * L, p["midfoot_range"])):
        out.append(FootJoint(name, np.array([0.0, y, z]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), rng, r, pr, g))
    b = np.radians(p["mtp_obliquity"])
    d = np.array([np.cos(b), medial * np.sin(b), 0.0])       # lateral end further back
    x_med = medial * 0.25 * fb                                # first metatarsal head, at the measured ball length
    y0 = B + (0.0 - x_med) / d[0] * d[1]
    n = np.cross([0, 0, 1.0], d)
    out.append(FootJoint("mtp", np.array([0.0, y0, z]), d, n, p["mtp_range"], r, pr, g))
    return out


def _frame(j):
    """Matrix from the joint frame (s along the axis, u towards the toes, w up) to the model."""
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = j.axis, j.normal, [0, 0, 1.0], j.origin
    return M


def _lbox(j, s0, s1, u0, u1, w0, w1):
    b = trimesh.creation.box([s1 - s0, u1 - u0, w1 - w0])
    b.apply_translation([0.5 * (s0 + s1), 0.5 * (u0 + u1), 0.5 * (w0 + w1)])
    b.apply_transform(_frame(j))
    return b


def _ldisc(j, s0, s1, radius):
    d = trimesh.creation.cylinder(radius=radius, height=s1 - s0, sections=64)
    d.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0]))
    d.apply_translation([0.5 * (s0 + s1), 0, 0])
    d.apply_transform(_frame(j))
    return d


def _wedge(j, half_deg, height=80.0):
    """V notch above the axis: |u| < w tan(half angle), w > 0, across the whole foot."""
    k = np.tan(np.radians(half_deg)) * height
    tri = np.array([[0.0, 0.0], [-k, height], [k, height]])
    from shapely.geometry import Polygon
    pr = trimesh.creation.extrude_polygon(Polygon(tri), 400.0)       # (u, w) polygon extruded along s
    pr.apply_translation([0, 0, -200.0])
    R = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])   # (u, w, s) -> (s, u, w)
    pr.apply_transform(R)
    pr.apply_transform(_frame(j))
    return pr


def _edges(mesh, j, u0, u1):
    """Furthest extent of the part along the axis, on each side, over the band u0 < u < u1."""
    pts = []
    for u in np.arange(u0, u1 + 1e-6, 1.0):
        sec = mesh.section(plane_origin=j.origin + u * j.normal, plane_normal=j.normal)
        if sec is not None:
            pts.append(sec.vertices)
    s = (np.concatenate(pts) - j.origin) @ j.axis
    return float(s.max()), float(-s.min())


def _clean(mesh, min_mm3=1.0):
    """Drop zero-volume slivers that coplanar booleans can leave behind."""
    parts = mesh.split(only_watertight=False)
    keep = [q for q in parts if abs(q.volume) > min_mm3]
    if len(keep) == len(parts):
        return mesh
    return keep[0] if len(keep) == 1 else trimesh.util.concatenate(keep)


def split_at(part, j, p):
    """Cut `part` at joint j into (proximal, distal, pins), with knuckles, bridges and the V notch."""
    g, r, t = j.gap, j.radius, p["thickness"]
    e_pos, e_neg = _edges(part, j, -(r + g + 7.0), r + g + 7.0)        # knuckles clear everything they sweep
    w_lo = -j.origin[2]                                        # sole level in the joint frame
    prox = trimesh.boolean.intersection([part, _lbox(j, -500, 500, -900, -g / 2, -200, 400)], engine="manifold")
    dist = trimesh.boolean.intersection([part, _lbox(j, -500, 500, g / 2, 900, -200, 400)], engine="manifold")
    p_pos, p_neg = _edges(prox, j, -(r + 5.0), -g / 2 - 0.5)            # where the arms meet each segment
    d_pos, d_neg = _edges(dist, j, r + g + 0.5, r + g + 6.0)
    notch = _wedge(j, j.range_deg / 2)
    knuck_p, knuck_d, arms_p, arms_d, holes, pins = [], [], [], [], [], []
    for sgn, e, ep, ed in ((1.0, e_pos, p_pos, d_pos), (-1.0, e_neg, p_neg, d_neg)):
        def S(a, b):
            return tuple(sorted((sgn * a, sgn * b)))
        knuck_p.append(_ldisc(j, *S(e + g, e + g + t), r))                                  # inner knuckle
        knuck_d.append(_ldisc(j, *S(e + 2 * g + t, e + 2 * g + 2 * t), r))                  # outer knuckle
        arms_p.append(_lbox(j, *S(min(e, ep) - 3.0, e + g + t), -(r + 5.0), -g / 2, w_lo, r))
        arms_d += [_lbox(j, *S(e + 2 * g + t, e + 2 * g + 2 * t), 0.0, r + g + 6.0, w_lo, r),
                   _lbox(j, *S(min(e, ed) - 3.0, e + 2 * g + 2 * t), r + g, r + g + 6.0, w_lo, r)]  # bridge out of reach
        holes.append(_ldisc(j, *S(e - 4.0, e + 2 * g + 2 * t + 1.0), j.pin_radius))
        shaft = _ldisc(j, *S(e - 1.0, e + 2 * g + 2 * t + 1.0), j.pin_radius - 0.1)
        head = _ldisc(j, *S(e + 2 * g + 2 * t + 0.2, e + 2 * g + 2 * t + 2.2), 2.8)
        pins.append(trimesh.boolean.union([shaft, head], engine="manifold"))
    hole = trimesh.util.concatenate(holes)
    # the V notch clears walls and arms above the axis; knuckles turn on the axis and keep their full disc
    prox = trimesh.boolean.difference([trimesh.boolean.union([prox] + arms_p, engine="manifold"), notch], engine="manifold")
    dist = trimesh.boolean.difference([trimesh.boolean.union([dist] + arms_d, engine="manifold"), notch], engine="manifold")
    prox = trimesh.boolean.difference([trimesh.boolean.union([prox] + knuck_p, engine="manifold"), hole], engine="manifold")
    dist = trimesh.boolean.difference([trimesh.boolean.union([dist] + knuck_d, engine="manifold"), hole], engine="manifold")
    return _clean(prox), _clean(dist), trimesh.util.concatenate(pins)


def build_segmented(m, p=None, profile=None):
    """Articulated AFO whose foot section is split into hindfoot, midfoot, forefoot and toes.

    Returns the articulated dict ('upper', 'pins', 'joint', ...) plus 'segments' (name -> mesh, heel to toes),
    'foot_joints' and 'foot_pins'; 'lower' stays the hindfoot so ankle checks keep working.
    """
    p = {**DESIGN, **(p or {})}
    P = build_articulated(m, p, profile)
    joints = foot_joints(m, p)
    segs, pins, rest = [], [], P["lower"]
    for j in joints:
        prox, rest, pin = split_at(rest, j, p)
        segs.append(prox)
        pins.append(pin)
    segs.append(rest)
    P["segments"] = {name: mesh for (name, _), mesh in zip(SEGMENTS, segs)}
    for name, mesh in P["segments"].items():
        mesh.metadata.update({"part": name, "params": p})
    P["foot_section"] = P["lower"]          # uncut foot section: same walls, used for thickness checks
    P["lower"] = P["segments"]["hindfoot"]
    P["foot_joints"] = joints
    P["foot_pins"] = trimesh.util.concatenate(pins)
    return P


def rotate_distal(mesh, j, deg):
    out = mesh.copy()
    out.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), j.axis, j.origin))
    return out


def joint_motion(P, limit=60.0, tol_deg=0.5, tol_mm3=1.0):
    """For each foot joint: free dorsiflexion and plantarflexion of the distal segment, measured on the meshes."""
    names = [n for n, _ in SEGMENTS]
    out = []
    for k, j in enumerate(P["foot_joints"]):
        prox, dist = P["segments"][names[k]], P["segments"][names[k + 1]]
        row = {"joint": j.name, "range_deg": j.range_deg, "rest_overlap_mm3": overlap_volume(prox, dist)}
        for key, sgn in (("dorsiflexion_deg", 1.0), ("plantarflexion_deg", -1.0)):
            def hits(a):
                return overlap_volume(rotate_distal(dist, j, sgn * a), prox) > tol_mm3
            if not hits(limit):
                row[key] = float(limit)
                continue
            lo, hi = 0.0, float(limit)
            while hi - lo > tol_deg:
                mid = 0.5 * (lo + hi)
                lo, hi = (lo, mid) if hits(mid) else (mid, hi)
            row[key] = round(lo, 1)
        out.append(row)
    return out


def pose(P, foot_deg=(0.0, 0.0, 0.0), ankle_deg=0.0):
    """Segments (and foot pins) turned at each joint, heel to toes, then the whole foot turned at the ankle.

    foot_deg: dorsiflexion at the Chopart, Lisfranc and MTP joints (positive = toes up).
    Returns {segment name: mesh, 'foot_pins': mesh}, all in the model frame.
    """
    names = [n for n, _ in SEGMENTS]
    joints = P["foot_joints"]
    out = {}
    for k, name in enumerate(names):
        mesh = P["segments"][name].copy()
        for i in reversed(range(k)):                      # innermost joint first, in the rest frame
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(foot_deg[i]), joints[i].axis,
                                                                         joints[i].origin))
        out[name] = mesh
    pins = []
    for piece in P["foot_pins"].split(only_watertight=False):
        piece = piece.copy()
        # a pin belongs to the joint whose axis it lies on
        d = [np.linalg.norm(np.cross(piece.centroid - j.origin, j.axis)) for j in joints]
        k = int(np.argmin(d))
        for i in reversed(range(k + 1)):
            if i < k:
                piece.apply_transform(trimesh.transformations.rotation_matrix(np.radians(foot_deg[i]), joints[i].axis,
                                                                              joints[i].origin))
        pins.append(piece)
    out["foot_pins"] = trimesh.util.concatenate(pins)
    if ankle_deg:
        R = trimesh.transformations.rotation_matrix(np.radians(ankle_deg), [1, 0, 0], P["joint"].origin)
        for v in out.values():
            v.apply_transform(R)
    return out
