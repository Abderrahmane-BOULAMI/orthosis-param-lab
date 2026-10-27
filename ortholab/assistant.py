"""Measurement assistant: can quick measurements (foot length, height, weight, sex) stand in for the tape?

If a model predicts a dimension within tolerance for most people, the clinic can skip measuring it.
If not, that dimension must be measured or scanned. Models are trained on 75 % of people and
judged on the 25 % they never saw.
"""
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .sizing import TOL

INPUTS = ["foot_length", "stature", "weight_kg", "is_male"]
TARGETS = ["foot_breadth", "heel_breadth", "ball_length", "ankle_circ", "calf_circ",
           "malleolus_height", "bimalleolar_breadth", "tibial_height"]
TOL_ALL = {**TOL, "ball_length": 10, "bimalleolar_breadth": 6}


def features(df):
    X = df[["foot_length", "stature", "weight_kg"]].copy()
    X["is_male"] = (df["sex"] == "M").astype(float)
    return X


def models():
    return {
        "median by sex": None,
        "linear regression": lambda: LinearRegression(),
        "neural network (MLP)": lambda: make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=3000,
                                                                                      early_stopping=True, random_state=0)),
        "gradient boosting (LightGBM)": lambda: LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=15,
                                                               min_child_samples=30, verbose=-1, random_state=0),
    }


def evaluate(df, seed=0):
    tr, te = train_test_split(df, test_size=0.25, random_state=seed, stratify=df["sex"])
    Xtr, Xte = features(tr), features(te)
    rows, preds = [], {}
    for name, make in models().items():
        for tgt in TARGETS:
            if make is None:
                med = tr.groupby("sex")[tgt].median()
                p = te["sex"].map(med).to_numpy()
            else:
                p = make().fit(Xtr, tr[tgt]).predict(Xte)
            err = np.abs(p - te[tgt].to_numpy())
            rows.append({"model": name, "target": tgt, "mae_mm": err.mean(),
                         "p90_mm": np.percentile(err, 90), "within_tol": (err <= TOL_ALL[tgt]).mean()})
            preds[(name, tgt)] = p
    return pd.DataFrame(rows), te.reset_index(drop=True), preds


def protocol(df, seed=0):
    """Share of unseen people for whom every predicted dimension lands within tolerance.

    A: quick inputs only. B: quick inputs plus the two girths taken with a tape.
    """
    tr, te = train_test_split(df, test_size=0.25, random_state=seed, stratify=df["sex"])
    out = {}
    for name, extra in (("A_quick_only", []), ("B_quick_plus_two_girths", ["ankle_circ", "calf_circ"])):
        Xtr = features(tr).assign(**{c: tr[c].to_numpy() for c in extra})
        Xte = features(te).assign(**{c: te[c].to_numpy() for c in extra})
        ok = np.ones(len(te), bool)
        for tgt in [t for t in TARGETS if t not in extra]:
            p = LinearRegression().fit(Xtr, tr[tgt]).predict(Xte)
            ok &= np.abs(p - te[tgt].to_numpy()) <= TOL_ALL[tgt]
        out[name] = float(ok.mean())
    return out
