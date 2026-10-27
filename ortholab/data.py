"""Download, verify and load the ANSUR II lower-limb measurements."""
import hashlib
import urllib.parse
import urllib.request

import pandas as pd

from .config import COLUMNS, FILES, MIRROR, RAW_DIR, SAMPLE_DIR


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(force=False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, digest in FILES.items():
        path = RAW_DIR / name
        if force or not path.exists():
            urllib.request.urlretrieve(MIRROR + urllib.parse.quote(name), path)
        got = sha256(path)
        if got != digest:
            raise ValueError(f"{name}: checksum {got} does not match {digest}")
    return RAW_DIR


def _tidy(df, sex):
    df = df.rename(columns={"SubjectId": "subjectid"})
    out = df[["subjectid", *COLUMNS]].rename(columns=COLUMNS)
    out["weight_kg"] = out["weight_kg"] / 10.0  # ANSUR stores weight in tenths of a kg
    out.insert(1, "sex", sex)
    return out


def load(sample=False):
    """One row per person, lengths in mm. sample=True uses the 300-person extract shipped in the repo."""
    if sample:
        return pd.read_csv(SAMPLE_DIR / "ansur_lower_limb_sample.csv")
    download()
    parts = [_tidy(pd.read_csv(RAW_DIR / "ANSUR II MALE Public.csv", encoding="latin-1"), "M"),
             _tidy(pd.read_csv(RAW_DIR / "ANSUR II FEMALE Public.csv", encoding="latin-1"), "F")]
    return pd.concat(parts, ignore_index=True)


def make_sample(n=300, seed=7):
    df = load()
    s = pd.concat([df[df.sex == k].sample(n // 2, random_state=seed) for k in ("F", "M")], ignore_index=True)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    s.to_csv(SAMPLE_DIR / "ansur_lower_limb_sample.csv", index=False)
    return s
