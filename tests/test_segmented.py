"""Foot split into bone segments: hindfoot, midfoot, forefoot and toes, hinged at the anatomical joints."""
import json

import numpy as np
import pytest

from ortholab import data, export, printability as pr, segmented as sg
from ortholab.config import DESIGN, MEASURES


@pytest.fixture(scope="module")
def person():
    s = data.load(sample=True)
    return {k: float(s.loc[10, k]) for k in MEASURES}


@pytest.fixture(scope="module")
def P(person):
    return sg.build_segmented(person, {"plantar_stop_deg": 5.0})


def test_joint_lines_follow_the_foot(person):
    chopart, lisfranc, mtp = sg.foot_joints(person, DESIGN)
    assert chopart.origin[1] < lisfranc.origin[1] < mtp.origin[1] < person["ball_length"]
    # MTP axis is oblique: the lateral end (+x on a right foot) lies further back than the medial end
    lateral = mtp.origin + 40 * mtp.axis
    medial = mtp.origin - 40 * mtp.axis
    assert lateral[1] < medial[1]
    assert abs(np.degrees(np.arctan2(medial[1] - lateral[1], lateral[0] - medial[0]))) == pytest.approx(DESIGN["mtp_obliquity"], abs=0.1)


def test_one_closed_part_per_segment(P):
    assert list(P["segments"]) == ["hindfoot", "midfoot", "forefoot", "toes"]
    for mesh in P["segments"].values():
        assert mesh.is_watertight and mesh.is_volume
        assert len(mesh.split(only_watertight=False)) == 1


def test_segments_keep_the_foot_volume(P):
    total = sum(m.volume for m in P["segments"].values())
    # gaps and V notches remove a little, knuckles, arms and bridges add about a tenth
    assert P["foot_section"].volume < total < 1.2 * P["foot_section"].volume


def test_joints_bend_up_as_designed_and_lock_under_load(P):
    for row in sg.joint_motion(P, tol_deg=0.25):
        assert row["rest_overlap_mm3"] == pytest.approx(0.0, abs=1e-6)
        assert row["dorsiflexion_deg"] == pytest.approx(row["range_deg"], abs=1.0)
        assert row["plantarflexion_deg"] <= 3.0


def test_every_segment_prints_on_a_desktop_printer(P):
    for mesh in P["segments"].values():
        assert pr.best_orientation(mesh, (250.0, 210.0, 220.0)) is not None


def test_ankle_still_works(P):
    from ortholab import articulated as ar
    rom = ar.range_of_motion_fast(P, tol_deg=0.25)
    assert abs(rom["plantarflexion_deg"] - 5.0) <= 1.0 and rom["rest_overlap_mm3"] == pytest.approx(0.0, abs=1e-6)


def test_segmented_export(P, person, tmp_path):
    export.export_articulated(P, tmp_path, "afo", person)
    for name in ("hindfoot", "midfoot", "forefoot", "toes"):
        assert (tmp_path / f"afo_foot_{name}.stl").exists()
    info = json.loads((tmp_path / "afo_assembly.json").read_text())
    assert [j["name"] for j in info["foot_joints"]] == ["chopart", "lisfranc", "mtp"]
    import rhino3dm
    assert len(rhino3dm.File3dm.Read(str(tmp_path / "afo_assembly.3dm")).Objects) == 6
