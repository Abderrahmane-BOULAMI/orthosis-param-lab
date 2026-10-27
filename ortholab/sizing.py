"""How many people would a range of standard sizes fit, compared with a made-to-measure orthosis?

A person fits a size when every fit dimension of the size is within tolerance of their own.
Sizes are designed on one half of the population and judged on the other half.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

FIT_DIMS = ["foot_length", "foot_breadth", "heel_breadth", "ankle_circ", "calf_circ",
            "malleolus_height", "tibial_height"]
# Tolerance (mm) a liner, straps and heat-moulding could absorb. Assumptions, varied in the study.
TOL = {"foot_length": 10, "foot_breadth": 6, "heel_breadth": 6, "ankle_circ": 10, "calf_circ": 15,
       "malleolus_height": 10, "tibial_height": 20}


def split(df, seed=0):
    rng = np.random.default_rng(seed)
    mask = rng.random(len(df)) < 0.5
    return df[mask].reset_index(drop=True), df[~mask].reset_index(drop=True)


def fits(people, sizes, scale=1.0, dims=FIT_DIMS):
    """Boolean matrix person x size."""
    X = people[dims].to_numpy(float)[:, None, :]
    S = sizes[dims].to_numpy(float)[None, :, :]
    tol = np.array([TOL[d] for d in dims]) * scale
    return (np.abs(X - S) <= tol).all(axis=2)


def foot_length_sizes(design, k):
    """Classic sizing: k sizes cut on foot length (shoe size); each size takes its group's medians."""
    bins = pd.qcut(design["foot_length"], k, labels=False, duplicates="drop")
    return design.groupby(bins)[FIT_DIMS].median().reset_index(drop=True)


def multi_dim_sizes(design, k, seed=0):
    """Best-case sizing: k sizes found by k-means on all fit dimensions (scaled by tolerance)."""
    tol = np.array([TOL[d] for d in FIT_DIMS])
    X = design[FIT_DIMS].to_numpy(float) / tol
    km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(X)
    return pd.DataFrame(km.cluster_centers_ * tol, columns=FIT_DIMS)


def coverage(people, sizes, scale=1.0):
    return float(fits(people, sizes, scale).any(axis=1).mean())


def per_dim_failure(people, sizes):
    """Share of people for whom the nearest foot-length size misses each single dimension."""
    idx = np.abs(people["foot_length"].to_numpy()[:, None] - sizes["foot_length"].to_numpy()[None, :]).argmin(1)
    near = sizes.iloc[idx].reset_index(drop=True)
    return {d: float((np.abs(people[d].to_numpy() - near[d].to_numpy()) > TOL[d]).mean()) for d in FIT_DIMS}


def study(df, ks=(1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 40), seed=0):
    design, test = split(df, seed)
    rows = []
    for k in ks:
        fl = foot_length_sizes(design, k) if k <= 12 else None
        md = multi_dim_sizes(design, k, seed)
        rows.append({"sizes": k,
                     "foot_length_sizing": coverage(test, fl) if fl is not None else np.nan,
                     "multi_dim_sizing": coverage(test, md)})
    tol_rows = []
    md10 = multi_dim_sizes(design, 10, seed)
    fl4 = foot_length_sizes(design, 4)
    for s in (0.5, 0.75, 1.0, 1.5, 2.0):
        tol_rows.append({"tolerance_x": s, "foot_length_4_sizes": coverage(test, fl4, s),
                         "multi_dim_10_sizes": coverage(test, md10, s)})
    return pd.DataFrame(rows), pd.DataFrame(tol_rows), per_dim_failure(test, fl4), len(test)
