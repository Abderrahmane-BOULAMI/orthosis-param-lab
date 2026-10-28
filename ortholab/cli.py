"""Command line: turn a table of patients into printable orthoses and a check report.

    python -m ortholab.cli template patients.csv          # writes a 3-person example table
    python -m ortholab.cli batch patients.csv --out outputs/batch --vent-rows 4
    python -m ortholab.cli batch patients.csv --articulated --plantar-stop 5 --segmented

One row per patient: an `id` column and the nine measurements in mm (see ortholab.config.MEASURES).
Each patient gets STL, 3MF, .3dm and JSON files; report.csv lists the checks. The exit code is 1 if any
part fails a check, so the command can gate a production queue.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import articulated as ar, data, export, geometry, mechanics, printability as pr, segmented as sg
from .config import DESIGN, MEASURES

LARGE_BED = (400.0, 400.0, 400.0)


def check(row, params, out, bed=LARGE_BED, min_wall=2.0):
    m = {k: float(row[k]) for k in MEASURES}
    t0 = time.perf_counter()
    afo = geometry.build_afo(m, params)
    rep = pr.report(afo, bed)
    wall = pr.wall_thickness(afo, n=200)
    stem = f"afo_{row['id']}"
    export.export_all(afo, out, stem, m, afo.metadata["params"])
    t = afo.metadata["params"]["thickness"]
    rep.update({
        "id": row["id"],
        "wall_p05_mm": round(float(np.percentile(wall, 5)), 2) if len(wall) else None,  # rays grazing an edge read thin
        "min_cube_mm": round(pr.min_cube_side(afo), 1),
        "ankle_stiffness_mm4": round(mechanics.ankle_inertia(m, params), 0),
        "seconds": round(time.perf_counter() - t0, 2),
    })
    rep["ok"] = bool(rep["watertight"] and rep["is_volume"] and rep["fits_bed"]
                     and rep["wall_p05_mm"] is not None and rep["wall_p05_mm"] >= max(0.9 * t, min_wall))
    return rep


def check_articulated(row, params, out, desk=(250.0, 210.0, 220.0), min_wall=2.0):
    m = {k: float(row[k]) for k in MEASURES}
    t0 = time.perf_counter()
    seg = bool(params.get("foot_segments"))
    P = sg.build_segmented(m, params) if seg else ar.build_articulated(m, params)
    rom = ar.range_of_motion_fast(P)
    export.export_articulated(P, out, f"afo_{row['id']}", m)
    walls = [float(np.percentile(pr.wall_thickness(P[k], n=200), 5)) for k in ("foot_section" if seg else "lower", "upper")]
    rep = {
        "id": row["id"],
        "watertight": bool(all(P[k].is_watertight and P[k].is_volume for k in ("lower", "upper"))),
        "rest_overlap_mm3": round(rom["rest_overlap_mm3"], 3),
        "dorsiflexion_free_deg": rom["dorsiflexion_deg"],
        "plantarflexion_stop_deg": rom["plantarflexion_deg"],
        "wall_p05_mm": round(min(walls), 2),
        "foot_section_fits_desktop": pr.best_orientation(P["lower"], desk) is not None,
        "calf_cuff_fits_400mm": pr.best_orientation(P["upper"], LARGE_BED) is not None,
        "mass_petg_g": round((P["lower"].volume + P["upper"].volume) / 1000 * 1.27, 1),
        "seconds": round(time.perf_counter() - t0, 2),
    }
    t = P["params"]["thickness"]
    ok_seg = True
    if seg:
        motion = sg.joint_motion(P)
        segs = P["segments"]
        rep.update({
            "segments_closed": bool(all(v.is_watertight and v.is_volume and len(v.split(only_watertight=False)) == 1
                                        for v in segs.values())),
            "segments_fit_desktop": bool(all(pr.best_orientation(v, desk) is not None for v in segs.values())),
            **{f"{r['joint']}_dorsiflexion_deg": r["dorsiflexion_deg"] for r in motion},
            "foot_joints_locked_under_load_deg": max(r["plantarflexion_deg"] for r in motion),
            "foot_joints_rest_overlap_mm3": round(max(r["rest_overlap_mm3"] for r in motion), 3),
        })
        rep["mass_petg_g"] = round((sum(v.volume for v in segs.values()) + P["upper"].volume) / 1000 * 1.27, 1)
        ok_seg = (rep["segments_closed"] and rep["foot_joints_rest_overlap_mm3"] < 1.0
                  and all(r["dorsiflexion_deg"] >= r["range_deg"] - 1.0 for r in motion)
                  and rep["foot_joints_locked_under_load_deg"] <= 3.0)
    rep["seconds"] = round(time.perf_counter() - t0, 2)
    rep["ok"] = bool(rep["watertight"] and rep["rest_overlap_mm3"] < 1.0 and rep["calf_cuff_fits_400mm"]
                     and rep["wall_p05_mm"] >= max(0.8 * t, min_wall) and ok_seg)
    return rep


def validate(df):
    missing = [c for c in ["id", *MEASURES] if c not in df.columns]
    if missing:
        raise SystemExit(f"missing columns: {', '.join(missing)}")
    bad = df[MEASURES].apply(pd.to_numeric, errors="coerce").isna().any(axis=1)
    if bad.any():
        raise SystemExit(f"non-numeric or empty measurements on rows: {list(df.index[bad])}")
    ref = data.load(sample=True)[MEASURES]
    lo, hi = ref.min() * 0.85, ref.max() * 1.15
    out = ((df[MEASURES] < lo) | (df[MEASURES] > hi)).any(axis=1)
    return list(df.loc[out, "id"])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ortholab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("template", help="write an example patients table")
    t.add_argument("path")
    b = sub.add_parser("batch", help="generate and check one orthosis per row")
    b.add_argument("csv")
    b.add_argument("--out", default="outputs/batch")
    b.add_argument("--thickness", type=float, default=DESIGN["thickness"])
    b.add_argument("--clearance", type=float, default=DESIGN["clearance"])
    b.add_argument("--ankle-wrap", type=float, default=DESIGN["wrap_deg"])
    b.add_argument("--vent-rows", type=int, default=0)
    b.add_argument("--min-wall", type=float, default=2.0, help="thinnest wall accepted for printing (mm)")
    b.add_argument("--articulated", action="store_true", help="two parts with M5-pin hinges on the ankle axis")
    b.add_argument("--plantar-stop", type=float, default=None, help="plantarflexion stop in degrees (articulated only)")
    b.add_argument("--segmented", action="store_true",
                   help="articulated, with the foot split into hindfoot, midfoot, forefoot and toes (pin hinges at "
                        "the Chopart, Lisfranc and MTP joints)")
    b.add_argument("--side", choices=["right", "left"], default="right")
    a = ap.parse_args(argv)

    if a.cmd == "template":
        s = data.load(sample=True).iloc[[0, 1, 2]].copy()
        s.insert(0, "id", ["P001", "P002", "P003"])
        s[["id", *MEASURES]].to_csv(a.path, index=False)
        print(f"wrote {a.path}")
        return 0

    df = pd.read_csv(a.csv)
    unusual = validate(df)
    if unusual:
        print(f"warning: measurements outside the survey range for {unusual}; check them before printing")
    params = {"thickness": a.thickness, "clearance": a.clearance, "ankle_wrap_deg": a.ankle_wrap, "vent_rows": a.vent_rows,
              "side": a.side}
    out = Path(a.out)
    if a.articulated or a.segmented:
        params["plantar_stop_deg"] = a.plantar_stop
        params["foot_segments"] = a.segmented
        rows = [check_articulated(r, params, out, min_wall=a.min_wall) for _, r in df.iterrows()]
        rep = pd.DataFrame(rows)
        rep = rep[["id", "ok", *[c for c in rep.columns if c not in ("id", "ok")]]]
    else:
        rows = [check(r, params, out, min_wall=a.min_wall) for _, r in df.iterrows()]
        rep = pd.DataFrame(rows)[["id", "ok", "watertight", "wall_p05_mm", "volume_cm3", "mass_petg_g", "height_mm",
                                  "min_cube_mm", "best_orientation", "support_cm2", "ankle_stiffness_mm4", "seconds"]]
    rep.to_csv(out / "report.csv", index=False)
    print(rep.to_string(index=False))
    print(f"{int(rep['ok'].sum())}/{len(rep)} parts pass; files in {out}")
    return 0 if rep["ok"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
