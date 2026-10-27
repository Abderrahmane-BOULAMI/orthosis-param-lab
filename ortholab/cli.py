"""Command line: turn a table of patients into printable orthoses and a check report.

    python -m ortholab.cli template patients.csv          # writes a 3-person example table
    python -m ortholab.cli batch patients.csv --out outputs/batch --vent-rows 4

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

from . import data, export, geometry, mechanics, printability as pr
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
    params = {"thickness": a.thickness, "clearance": a.clearance, "ankle_wrap_deg": a.ankle_wrap, "vent_rows": a.vent_rows}
    out = Path(a.out)
    rows = [check(r, params, out, min_wall=a.min_wall) for _, r in df.iterrows()]
    rep = pd.DataFrame(rows)[["id", "ok", "watertight", "wall_p05_mm", "volume_cm3", "mass_petg_g", "height_mm",
                              "min_cube_mm", "best_orientation", "support_cm2", "ankle_stiffness_mm4", "seconds"]]
    rep.to_csv(out / "report.csv", index=False)
    print(rep.to_string(index=False))
    print(f"{int(rep['ok'].sum())}/{len(rep)} parts pass; files in {out}")
    return 0 if rep["ok"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
