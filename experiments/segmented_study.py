"""Segmented foot study: build the bone-segment orthosis for a random set of people and measure every joint.

    python experiments/segmented_study.py            # 150 people from the full survey
    python experiments/segmented_study.py --sample   # 20 people from the committed sample

Writes results[/sample]/segmented.csv and adds the seg_* keys to summary.json (run_all.py calls it too).
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ortholab import data, printability as pr, segmented as sg  # noqa: E402
from ortholab.config import MEASURES, RESULTS  # noqa: E402

DESK = (250.0, 210.0, 220.0)


def one(row):
    m = {k: float(row[k]) for k in MEASURES}
    t0 = time.perf_counter()
    P = sg.build_segmented(m, {"plantar_stop_deg": 5.0})
    gen = time.perf_counter() - t0
    segs = P["segments"]
    out = {"subjectid": row["subjectid"], "sex": row["sex"], "gen_s": gen,
           "closed": bool(all(v.is_watertight and v.is_volume and len(v.split(only_watertight=False)) == 1
                              for v in segs.values())),
           "fit_desktop": bool(all(pr.best_orientation(v, DESK) is not None for v in segs.values())),
           "mass_petg_g": (sum(v.volume for v in segs.values()) + P["upper"].volume) / 1000 * 1.27}
    for r in sg.joint_motion(P, tol_deg=0.25):
        out[f"{r['joint']}_range_deg"] = r["range_deg"]
        out[f"{r['joint']}_dorsi_deg"] = r["dorsiflexion_deg"]
        out[f"{r['joint']}_plantar_deg"] = r["plantarflexion_deg"]
        out[f"{r['joint']}_rest_overlap_mm3"] = r["rest_overlap_mm3"]
    return out


def study(df, n, seed=5, workers=2):
    s = df.sample(n, random_state=seed) if len(df) > n else df
    with Pool(workers) as pool:
        return pd.DataFrame(pool.map(one, [r for _, r in s.iterrows()], chunksize=4))


def summarise(seg):
    joints = ("chopart", "lisfranc", "mtp")
    return {
        "seg_people": int(len(seg)),
        "seg_closed_share": float(seg["closed"].mean()),
        "seg_fit_desktop_share": float(seg["fit_desktop"].mean()),
        "seg_rest_overlap_max_mm3": float(seg[[f"{j}_rest_overlap_mm3" for j in joints]].max().max()),
        "seg_range_abs_err_max_deg": float(max((seg[f"{j}_dorsi_deg"] - seg[f"{j}_range_deg"]).abs().max() for j in joints)),
        "seg_dorsi_median_deg": {j: float(seg[f"{j}_dorsi_deg"].median()) for j in joints},
        "seg_range_deg": {j: float(seg[f"{j}_range_deg"].iloc[0]) for j in joints},
        "seg_locked_max_deg": float(max(seg[f"{j}_plantar_deg"].max() for j in joints)),
        "seg_gen_seconds_median": float(seg["gen_s"].median()),
        "seg_mass_petg_g_median": float(seg["mass_petg_g"].median()),
    }


def main(sample):
    out = RESULTS / "sample" if sample else RESULTS
    seg = study(data.load(sample=sample), n=20 if sample else 150)
    seg.to_csv(out / "segmented.csv", index=False)
    path = out / "summary.json"
    S = json.loads(path.read_text()) if path.exists() else {}
    S.update(summarise(seg))
    path.write_text(json.dumps(S, indent=2, default=str))
    print(json.dumps(summarise(seg), indent=2))


if __name__ == "__main__":
    main("--sample" in sys.argv)
