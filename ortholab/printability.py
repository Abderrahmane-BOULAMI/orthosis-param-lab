"""Checks run on every generated orthosis before it goes to a printer."""
import numpy as np
import trimesh

from .config import BED_MM, DENSITY, OVERHANG_DEG

ORIENTATIONS = {
    # name: direction of the part that faces the bed
    "standing": [0, 0, -1],     # footplate on the bed, leg upright
    "on_back": [0, -1, 0],      # posterior shell on the bed
    "on_side": [1, 0, 0],       # lateral side on the bed
}


def orient(mesh, down):
    m = mesh.copy()
    R = trimesh.geometry.align_vectors(down, [0, 0, -1])
    m.apply_transform(R)
    m.apply_translation(-m.bounds[0])
    return m


def fits_bed(m, bed=BED_MM, step_deg=5):
    """True if the oriented part fits the build volume, trying rotations about the vertical axis."""
    X, Y, Z = bed
    if m.extents[2] > Z:
        return False
    hull = m.convex_hull.vertices[:, :2]
    for a in np.radians(np.arange(0, 90, step_deg)):
        c, s = np.cos(a), np.sin(a)
        r = hull @ np.array([[c, -s], [s, c]])
        w, d = np.ptp(r[:, 0]), np.ptp(r[:, 1])
        if (w <= X and d <= Y) or (w <= Y and d <= X):
            return True
    return False


def support_area(m, angle=OVERHANG_DEG):
    """Area (mm2, projected on the bed) of downward faces steeper than the overhang limit, bed contact excluded."""
    n = m.face_normals
    on_bed = m.vertices[m.faces][:, :, 2].max(axis=1) < 0.2
    need = (n[:, 2] < -np.cos(np.radians(angle))) & ~on_bed
    return float((m.area_faces[need] * -n[need, 2]).sum())


def orientation_table(mesh, bed=BED_MM):
    rows = []
    for name, down in ORIENTATIONS.items():
        m = orient(mesh, down)
        rows.append({"orientation": name, "height_mm": float(m.extents[2]),
                     "fits_bed": fits_bed(m, bed), "support_cm2": support_area(m) / 100.0})
    return rows


def best_orientation(mesh, bed=BED_MM):
    rows = orientation_table(mesh, bed)
    ok = [r for r in rows if r["fits_bed"]]
    return min(ok, key=lambda r: r["support_cm2"]) if ok else None


def wall_thickness(mesh, n=400, seed=0):
    """Thickness sampled by casting rays inwards from random surface points (ignores the open top/bottom caps)."""
    pts, fid = trimesh.sample.sample_surface(mesh, n, seed=seed)
    normals = mesh.face_normals[fid]
    keep = np.abs(normals[:, 2]) < 0.7          # side walls only
    pts, normals = pts[keep], normals[keep]
    origins = pts - normals * 1e-3
    locs, idx, _ = mesh.ray.intersects_location(origins, -normals, multiple_hits=False)
    d = np.full(len(pts), np.nan)
    d[idx] = np.linalg.norm(locs - origins[idx], axis=1)
    return d[np.isfinite(d)]


def report(mesh, bed=BED_MM):
    best = best_orientation(mesh, bed)
    vol_cm3 = mesh.volume / 1000.0
    return {
        "watertight": bool(mesh.is_watertight),
        "is_volume": bool(mesh.is_volume),
        "volume_cm3": round(vol_cm3, 1),
        "mass_petg_g": round(vol_cm3 * DENSITY["PETG"], 1),
        "mass_pa12_g": round(vol_cm3 * DENSITY["PA12"], 1),
        "height_mm": round(float(mesh.extents[2]), 1),
        "best_orientation": best["orientation"] if best else None,
        "support_cm2": round(best["support_cm2"], 1) if best else None,
        "fits_bed": best is not None,
    }


def min_cube_side(mesh, step_deg=5):
    """Side (mm) of the smallest cubic build volume that holds the part, over orientations and bed rotations."""
    best = np.inf
    for down in ORIENTATIONS.values():
        m = orient(mesh, down)
        hull = m.convex_hull.vertices[:, :2]
        side_xy = np.inf
        for a in np.radians(np.arange(0, 90, step_deg)):
            c, s = np.cos(a), np.sin(a)
            r = hull @ np.array([[c, -s], [s, c]])
            side_xy = min(side_xy, max(np.ptp(r[:, 0]), np.ptp(r[:, 1])))
        best = min(best, max(side_xy, m.extents[2]))
    return float(best)
