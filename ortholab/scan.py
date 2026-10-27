"""Use a 3D scan of the lower leg instead of the tape for the leg shape.

The scan is sliced horizontally; each slice gives a measured width, depth and girth, which replace the
assumed ellipses above the ankle. Below that height (heel and malleoli, where foot scans are noisy and the
section runs into the foot) the measurement-based profile is kept. The scan must be in mm, z up from the sole,
y forward, heel at the back; aligning a raw scan to that frame is a separate step.
"""
import numpy as np
import trimesh

from .config import DESIGN
from .geometry import LimbProfile, _arc, limb_profile, perimeter


def limb_surface(prof, z0, z1, levels=70, n=120, cap=True):
    """Closed tube following a limb profile: a stand-in for a scan, used for demos and tests."""
    zs = np.linspace(z0, z1, levels)
    a, b = prof.at(zs)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rings = [np.column_stack([ai * np.cos(th), bi + bi * np.sin(th), np.full(n, z)]) for z, ai, bi in zip(zs, a, b)]
    V = np.vstack(rings)
    F = []
    for k in range(levels - 1):
        o0, o1 = k * n, (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            F += [[o0 + i, o0 + j, o1 + j], [o0 + i, o1 + j, o1 + i]]
    if cap:
        for k, flip in ((0, True), (levels - 1, False)):
            c = len(V)
            V = np.vstack([V, rings[k].mean(axis=0)])
            for i in range(n):
                tri = [c, k * n + (i + 1) % n, k * n + i]
                F.append(tri if flip else tri[::-1])
    mesh = trimesh.Trimesh(V, np.array(F), process=True)
    trimesh.repair.fix_normals(mesh)
    return mesh


def slice_scan(scan, heights):
    """Width, depth and girth (mm) of the largest closed section at each height."""
    rows = []
    for z in heights:
        sec = scan.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            rows.append((z, np.nan, np.nan, np.nan))
            continue
        planar, T = sec.to_2D()
        polys = planar.polygons_full
        if not polys:
            rows.append((z, np.nan, np.nan, np.nan))
            continue
        poly = max(polys, key=lambda q: q.area)
        pts3 = trimesh.transform_points(np.column_stack([np.array(poly.exterior.coords), np.zeros(len(poly.exterior.coords))]), T)
        rows.append((z, np.ptp(pts3[:, 0]), np.ptp(pts3[:, 1]), poly.exterior.length))
    return np.array(rows)


def profile_from_scan(scan, m, p=None, start_above_malleolus=25.0, step=8.0, top_margin=5.0):
    """LimbProfile whose leg part comes from the scan and whose heel/ankle base comes from the measurements m."""
    p = {**DESIGN, **(p or {})}
    base = limb_profile(m, p)
    z_start = m["malleolus_height"] + start_above_malleolus
    z_end = min(scan.bounds[1][2] - top_margin, base.z_top)
    sl = slice_scan(scan, np.arange(z_start, z_end + 1e-9, step))
    sl = sl[np.isfinite(sl[:, 1])]
    if len(sl) < 4:
        raise ValueError("scan too short or not closed above the ankle")
    keep = base.z < z_start
    z = np.r_[base.z[keep], sl[:, 0]]
    a = np.r_[base.a[keep], sl[:, 1] / 2]
    b = np.r_[base.b[keep], sl[:, 2] / 2]
    girth = sl[:, 3]
    lower = sl[:, 0] < z_start + 120
    z_ankle = float(sl[lower, 0][np.argmin(girth[lower])]) if lower.any() else base.z_ankle
    prof = LimbProfile(z, a, b, z_ankle, float(sl[-1, 0]))
    prof.girths = dict(zip(sl[:, 0].round(1), girth))
    return prof


def girth_error(prof, scan_slices):
    """Relative difference between the ellipse perimeter of the profile and the scanned girth, per slice."""
    a, b = prof.at(scan_slices[:, 0])
    return perimeter(a, b) / scan_slices[:, 3] - 1


def fit_gaps(afo, scan, heights, thickness, directions_deg=(-150, -120, -90, -60, -30)):
    """Signed gap (mm) between the scanned skin and the inner surface of the orthosis, on the real meshes.

    The scan stands on the floor; in the orthosis the foot rests on the plate, so the scan is raised by the
    plate thickness. From the centre of each scan slice, a horizontal ray is cast in each direction
    (-90 = straight back): gap = distance to the orthosis inner surface - distance to the skin.
    A negative gap means the shell would press into the leg.
    """
    leg = scan.copy()
    leg.apply_translation([0, 0, thickness])
    out = []
    for z in heights:
        zz = z + thickness
        sl = slice_scan(leg, [zz])
        if not np.isfinite(sl[0, 1]):
            continue
        sec = leg.section(plane_origin=[0, 0, zz], plane_normal=[0, 0, 1])
        centre = np.r_[sec.vertices[:, :2].mean(axis=0), zz]
        for ang in np.radians(directions_deg):
            d = np.array([np.cos(ang), np.sin(ang), 0.0])
            h_skin, _, _ = leg.ray.intersects_location([centre], [d], multiple_hits=False)
            h_afo, _, _ = afo.ray.intersects_location([centre], [d], multiple_hits=False)
            if len(h_skin) and len(h_afo):
                gap = np.linalg.norm(h_afo[0] - centre) - np.linalg.norm(h_skin[0] - centre)
                out.append((z, float(np.degrees(ang)), float(gap)))
    return np.array(out)
