# r: numpy, scipy, trimesh, manifold3d, mapbox_earcut, shapely, rtree, rhino3dm
"""Grasshopper Python 3 component (Rhino 8 script editor) wrapping the same generator as the repository.

Inputs (set them on the component, type hints in brackets):
    repo        [str]    path to this repository on disk
    measures    [str]    nine measurements as "foot_length=264, foot_breadth=94, ..." (mm)
    thickness   [float]  shell thickness, mm (default 3)
    clearance   [float]  liner clearance, mm (default 3)
    ankle_wrap  [float]  wrap around the ankle, degrees (default 200; lower = more flexible)
    vent_rows   [int]    rows of ventilation openings (default 0)
    articulated [bool]   two parts with M5-pin hinges on the ankle axis (default False)
    plantar_stop[float]  plantarflexion stop in degrees, articulated only (empty = free)
    segments    [bool]   split the foot into hindfoot, midfoot, forefoot and toes, pinned at the Chopart,
                         Lisfranc and MTP joints (implies articulated)
Outputs:
    afo         Rhino mesh of the rigid orthosis, the foot section when articulated, or a list of the four
                foot segments (heel to toes) when segments is on
    cuff        Rhino mesh of the calf cuff (articulated only)
    report      text: watertight, mass, smallest printer cube, ankle stiffness or range of motion

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


def run(repo, measures, thickness=None, clearance=None, ankle_wrap=None, vent_rows=None, mesh_cls=None,
        articulated=False, plantar_stop=None, segments=False):
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
    if segments:
        from ortholab import articulated as ar, segmented as sg
        P = sg.build_segmented(m, {**params, "plantar_stop_deg": plantar_stop})
        rom = ar.range_of_motion_fast(P)
        lines = [f"segments closed: {all(v.is_watertight for v in P['segments'].values())}",
                 f"plantarflexion stop: {rom['plantarflexion_deg']} deg"]
        lines += [f"{r['joint']}: opens {r['dorsiflexion_deg']} deg, locks under load at {r['plantarflexion_deg']} deg"
                  for r in sg.joint_motion(P)]
        mass = (sum(v.volume for v in P["segments"].values()) + P["upper"].volume) / 1000 * DENSITY["PETG"]
        lines.append(f"mass PETG: {mass:.0f} g")
        foot = [export.to_rhino_mesh(v, mesh_cls) for v in P["segments"].values()]
        return foot, export.to_rhino_mesh(P["upper"], mesh_cls), "\n".join(lines)
    if articulated:
        from ortholab import articulated as ar
        P = ar.build_articulated(m, {**params, "plantar_stop_deg": plantar_stop})
        rom = ar.range_of_motion_fast(P)
        report = (f"watertight: {P['lower'].is_watertight and P['upper'].is_watertight}\n"
                  f"free dorsiflexion: {rom['dorsiflexion_deg']} deg\n"
                  f"plantarflexion stop: {rom['plantarflexion_deg']} deg\n"
                  f"mass PETG: {(P['lower'].volume + P['upper'].volume) / 1000 * DENSITY['PETG']:.0f} g")
        return export.to_rhino_mesh(P["lower"], mesh_cls), export.to_rhino_mesh(P["upper"], mesh_cls), report
    afo = geometry.build_afo(m, params)
    report = (f"watertight: {afo.is_watertight}\n"
              f"mass PETG: {afo.volume / 1000 * DENSITY['PETG']:.0f} g\n"
              f"smallest printer cube: {pr.min_cube_side(afo):.0f} mm\n"
              f"ankle stiffness I: {mechanics.ankle_inertia(m, params):.0f} mm4")
    return export.to_rhino_mesh(afo, mesh_cls), None, report


try:                                    # inside Grasshopper the inputs exist as globals
    import Rhino.Geometry as rg
    afo, cuff, report = run(repo, measures, thickness, clearance, ankle_wrap, vent_rows, rg.Mesh,  # noqa: F821
                            articulated, plantar_stop, segments)  # noqa: F821
except ImportError:                     # outside Rhino: nothing to do on import
    pass
