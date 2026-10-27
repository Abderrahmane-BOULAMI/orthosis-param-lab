# r: numpy, scipy, trimesh, manifold3d, mapbox_earcut, shapely, rtree, rhino3dm
"""Grasshopper Python 3 component (Rhino 8 script editor) wrapping the same generator as the repository.

Inputs (set them on the component, type hints in brackets):
    repo        [str]    path to this repository on disk
    measures    [str]    nine measurements as "foot_length=264, foot_breadth=94, ..." (mm)
    thickness   [float]  shell thickness, mm (default 3)
    clearance   [float]  liner clearance, mm (default 3)
    ankle_wrap  [float]  wrap around the ankle, degrees (default 200; lower = more flexible)
    vent_rows   [int]    rows of ventilation openings (default 0)
Outputs:
    afo         Rhino mesh of the orthosis
    report      text: watertight, mass, smallest printer cube, ankle stiffness

The "# r:" line asks Rhino 8 to install the packages the first time the component runs.
This file is exercised outside Rhino by tests/test_grasshopper.py, which feeds it rhino3dm in place of Rhino.
"""
import sys


def parse_measures(text):
    out = {}
    for part in str(text).replace(";", ",").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = float(v)
    return out


def run(repo, measures, thickness=None, clearance=None, ankle_wrap=None, vent_rows=None, mesh_cls=None):
    if repo and repo not in sys.path:
        sys.path.insert(0, repo)
    from ortholab import export, geometry, mechanics, printability as pr
    from ortholab.config import DENSITY, MEASURES

    m = parse_measures(measures)
    missing = [k for k in MEASURES if k not in m]
    if missing:
        raise ValueError("missing measurements: " + ", ".join(missing))
    params = {k: v for k, v in {"thickness": thickness, "clearance": clearance,
                                "ankle_wrap_deg": ankle_wrap, "vent_rows": vent_rows}.items() if v is not None}
    afo = geometry.build_afo(m, params)
    report = (f"watertight: {afo.is_watertight}\n"
              f"mass PETG: {afo.volume / 1000 * DENSITY['PETG']:.0f} g\n"
              f"smallest printer cube: {pr.min_cube_side(afo):.0f} mm\n"
              f"ankle stiffness I: {mechanics.ankle_inertia(m, params):.0f} mm4")
    return export.to_rhino_mesh(afo, mesh_cls), report


try:                                    # inside Grasshopper the inputs exist as globals
    import Rhino.Geometry as rg
    afo, report = run(repo, measures, thickness, clearance, ankle_wrap, vent_rows, rg.Mesh)  # noqa: F821
except ImportError:                     # outside Rhino: nothing to do on import
    pass
