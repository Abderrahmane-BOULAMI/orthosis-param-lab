"""Run every study and write the results used in the README and the dashboard.

    python experiments/run_all.py            # 6,068 people (downloads ANSUR II once, checksum verified)
    python experiments/run_all.py --sample   # 300-person extract shipped in the repo, writes to results/sample/
"""
import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ortholab import assistant, data, export, geometry, mechanics, printability as pr, scan, sizing  # noqa: E402
from ortholab.config import DESIGN, MEASURES, OUTPUTS, RESULTS  # noqa: E402

BEDS = {"desktop": (250.0, 210.0, 220.0), "large": (400.0, 400.0, 400.0)}


def one_person(row):
    m = {k: float(row[k]) for k in MEASURES}
    t0 = time.perf_counter()
    afo = geometry.build_afo(m)
    gen_s = time.perf_counter() - t0
    out = {"subjectid": row["subjectid"], "sex": row["sex"], "gen_s": gen_s,
           "watertight": bool(afo.is_watertight), "volume_cm3": afo.volume / 1000,
           "height_mm": float(afo.extents[2])}
    for bed, dims in BEDS.items():
        ok = [r for r in pr.orientation_table(afo, dims) if r["fits_bed"]]
        best = min(ok, key=lambda r: r["support_cm2"]) if ok else None
        out[f"fits_{bed}"] = best is not None
        out[f"orient_{bed}"] = best["orientation"] if best else None
        out[f"support_{bed}_cm2"] = best["support_cm2"] if best else np.nan
    out["min_cube_mm"] = pr.min_cube_side(afo)
    out["ankle_I_mm4"] = mechanics.ankle_inertia(m)
    return out


def population(df, workers=2):
    with Pool(workers) as pool:
        rows = pool.map(one_person, [r for _, r in df.iterrows()], chunksize=20)
    pop = pd.DataFrame(rows)
    target = pop["ankle_I_mm4"].median()
    pop["thickness_equal_stiffness"] = [mechanics.thickness_for({k: float(r[k]) for k in MEASURES}, target)
                                        for _, r in df.iterrows()]
    return df.merge(pop, on=["subjectid", "sex"]), target


def stress_test(df):
    """People at the extremes of every measurement, built with several design variants."""
    picks = set()
    for c in MEASURES:
        picks.add(int(df[c].idxmin()))
        picks.add(int(df[c].idxmax()))
    variants = {"default": {}, "thin_2mm": {"thickness": 2.0}, "thick_5mm": {"thickness": 5.0},
                "leaf_spring_120deg": {"ankle_wrap_deg": 120.0}, "vented_4_rows": {"vent_rows": 4}}
    rows = []
    for i in sorted(picks):
        m = {k: float(df.loc[i, k]) for k in MEASURES}
        for name, p in variants.items():
            afo = geometry.build_afo(m, p)
            w = pr.wall_thickness(afo, n=300)
            t = {**DESIGN, **p}["thickness"]
            rows.append({"subjectid": df.loc[i, "subjectid"], "variant": name, "watertight": bool(afo.is_watertight),
                         "is_volume": bool(afo.is_volume), "wall_p05": float(np.percentile(w, 5)),
                         "wall_median": float(np.median(w)), "target_t": t})
    return pd.DataFrame(rows)


def trimline_curve(m):
    base = mechanics.ankle_inertia(m, {"ankle_wrap_deg": 200.0})
    return pd.DataFrame([{"ankle_wrap_deg": w, "relative_stiffness": mechanics.ankle_inertia(m, {"ankle_wrap_deg": w}) / base}
                         for w in range(100, 221, 10)])


def scan_study(m):
    """A synthetic scan whose calf sits lower and is flatter than the generator assumes (64 % instead of 72 % of
    tibial height, width/depth 1.25 instead of 1.15). Compare the tape-based and scan-based shells on that leg."""
    truth = geometry.limb_profile(m, {**DESIGN, "calf_level": 0.64, "calf_ratio": 1.25})
    leg = scan.limb_surface(truth, m["malleolus_height"] + 10, truth.z_top + 30)
    prof = scan.profile_from_scan(leg, m)
    zs = np.arange(m["malleolus_height"] + 40, prof.z_top - 10, 10)
    dirs = (-160, -135, -110, -90, -70, -45, -20)
    rows = []
    for name, afo in (("tape", geometry.build_afo(m)), ("scan", geometry.build_afo(m, profile=prof))):
        g = scan.fit_gaps(afo, leg, zs, DESIGN["thickness"], dirs)
        rows += [{"source": name, "height_mm": z, "direction_deg": a, "gap_mm": v} for z, a, v in g]
    return pd.DataFrame(rows)


def main(sample):
    out = RESULTS / "sample" if sample else RESULTS
    out.mkdir(parents=True, exist_ok=True)
    df = data.load(sample=sample)
    t0 = time.time()

    pop, target_I = population(df)
    pop.to_csv(out / "population.csv", index=False)
    stress = stress_test(df)
    stress.to_csv(out / "stress_test.csv", index=False)

    cov, tol, per_dim, n_test = sizing.study(df)
    cov.to_csv(out / "sizing_coverage.csv", index=False)
    tol.to_csv(out / "sizing_tolerance.csv", index=False)

    maes, _, _ = assistant.evaluate(df)
    maes.to_csv(out / "assistant_errors.csv", index=False)
    proto = assistant.protocol(df)

    med_idx = int((df[MEASURES] - df[MEASURES].median()).abs().div(df[MEASURES].std()).sum(axis=1).idxmin())
    median_person = {k: float(df.loc[med_idx, k]) for k in MEASURES}
    trim = trimline_curve(median_person)
    trim.to_csv(out / "stiffness_trimline.csv", index=False)

    gaps = scan_study(median_person)
    gaps.to_csv(out / "scan_fit.csv", index=False)
    g = gaps.groupby("source")["gap_mm"]

    if not sample:
        afo = geometry.build_afo(median_person, {"vent_rows": 4})
        export.export_all(afo, OUTPUTS, "afo_median_person", median_person, afo.metadata["params"])

    I = pop["ankle_I_mm4"]
    lgbm = maes[maes.model == "gradient boosting (LightGBM)"].set_index("target")
    summary = {
        "people": int(len(pop)),
        "watertight_share": float(pop["watertight"].mean()),
        "gen_seconds_median": float(pop["gen_s"].median()),
        "volume_cm3_median": float(pop["volume_cm3"].median()),
        "mass_petg_g_p05_p95": [float(np.percentile(pop["volume_cm3"] * 1.27, q)) for q in (5, 95)],
        "height_mm_p05_p95": [float(np.percentile(pop["height_mm"], q)) for q in (5, 95)],
        "fits_desktop_share": float(pop["fits_desktop"].mean()),
        "fits_large_share": float(pop["fits_large"].mean()),
        "min_cube_mm_p50_p95": [float(np.percentile(pop["min_cube_mm"], q)) for q in (50, 95)],
        "large_bed_orientation_counts": pop["orient_large"].value_counts(dropna=False).to_dict(),
        "stress_cases": int(len(stress)),
        "stress_watertight_share": float(stress["watertight"].mean()),
        "stress_wall_p05_min_ratio": float((stress["wall_p05"] / stress["target_t"]).min()),
        "ankle_I_p95_over_p05": float(np.percentile(I, 95) / np.percentile(I, 5)),
        "ankle_I_max_over_min": float(I.max() / I.min()),
        "equal_stiffness_thickness_p05_p95": [float(np.percentile(pop["thickness_equal_stiffness"], q)) for q in (5, 95)],
        "trimline_120_vs_200": float(trim.set_index("ankle_wrap_deg").loc[120, "relative_stiffness"]),
        "sizing_test_people": n_test,
        "sizing_4_foot_length_sizes": float(cov.set_index("sizes").loc[4, "foot_length_sizing"]),
        "sizing_12_foot_length_sizes": float(cov.set_index("sizes").loc[12, "foot_length_sizing"]),
        "sizing_40_multi_dim_sizes": float(cov.set_index("sizes").loc[40, "multi_dim_sizing"]),
        "sizing_miss_by_dim_4_sizes": per_dim,
        "assistant_lgbm_mae_mm": lgbm["mae_mm"].round(1).to_dict(),
        "assistant_lgbm_within_tol": lgbm["within_tol"].round(3).to_dict(),
        "protocol_all_within_tol": proto,
        "scan_fit_gap_min_mm": g.min().round(2).to_dict(),
        "scan_fit_gap_median_mm": g.median().round(2).to_dict(),
        "scan_fit_pressing_share": gaps.assign(p=gaps.gap_mm < 0).groupby("source")["p"].mean().round(3).to_dict(),
        "median_person": median_person,
        "runtime_s": round(time.time() - t0, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    main(ap.parse_args().sample)
