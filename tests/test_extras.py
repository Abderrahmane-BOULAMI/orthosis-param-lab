"""Scan input, batch command, Grasshopper component and dashboard."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ortholab import cli, data, geometry, scan
from ortholab.config import MEASURES

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def person():
    s = data.load(sample=True)
    return {k: float(s.loc[3, k]) for k in MEASURES}


def test_scan_profile_recovers_girths(person):
    m2 = dict(person, calf_circ=person["calf_circ"] + 25)
    truth = geometry.limb_profile(m2)
    leg = scan.limb_surface(truth, person["malleolus_height"] + 10, truth.z_top + 30)
    prof = scan.profile_from_scan(leg, person)
    sl = scan.slice_scan(leg, np.arange(120, truth.z_top, 20))
    assert np.abs(scan.girth_error(prof, sl)).max() < 0.005


def test_scan_based_shell_keeps_the_clearance(person):
    m2 = dict(person, calf_circ=person["calf_circ"] + 25)
    truth = geometry.limb_profile(m2)
    leg = scan.limb_surface(truth, person["malleolus_height"] + 10, truth.z_top + 30)
    prof = scan.profile_from_scan(leg, person)
    afo = geometry.build_afo(person, profile=prof)
    assert afo.is_watertight
    zs = np.arange(person["malleolus_height"] + 40, prof.z_top - 10, 25)
    back = scan.fit_gaps(afo, leg, zs, 3.0, directions_deg=(-90,))
    assert np.median(back[:, 2]) == pytest.approx(3.0, abs=0.1)     # straight back: gap equals the clearance
    sides = (-150, -30)                                              # the bigger calf shows on the sides
    gaps = scan.fit_gaps(afo, leg, zs, 3.0, directions_deg=sides)
    tape = scan.fit_gaps(geometry.build_afo(person), leg, zs, 3.0, directions_deg=sides)
    assert gaps[:, 2].min() > 2.5
    assert tape[:, 2].min() < gaps[:, 2].min() - 1.0                 # the tape-based shell presses on the calf


def test_batch_command(tmp_path):
    csv = tmp_path / "patients.csv"
    assert cli.main(["template", str(csv)]) == 0
    assert cli.main(["batch", str(csv), "--out", str(tmp_path / "out"), "--vent-rows", "2"]) == 0
    rep = pd.read_csv(tmp_path / "out" / "report.csv")
    assert len(rep) == 3 and rep["ok"].all()
    assert (tmp_path / "out" / "afo_P001.3dm").exists() and (tmp_path / "out" / "afo_P003.stl").exists()
    assert cli.main(["batch", str(csv), "--out", str(tmp_path / "thin"), "--thickness", "1.5"]) == 1


def test_batch_rejects_missing_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,foot_length\nX,250\n")
    with pytest.raises(SystemExit):
        cli.main(["batch", str(bad), "--out", str(tmp_path / "o")])


def test_grasshopper_component_outside_rhino(person):
    spec = importlib.util.spec_from_file_location("ghc", ROOT / "grasshopper" / "afo_component.py")
    ghc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ghc)
    text = ", ".join(f"{k}={v}" for k, v in person.items())
    mesh, report = ghc.run(str(ROOT), text, thickness=3.0, vent_rows=2)
    assert mesh.Faces.Count > 1000 and "watertight: True" in report


def test_dashboard_runs():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app" / "dashboard.py"), default_timeout=180).run()
    assert not at.exception
    assert len(at.tabs) == 4
