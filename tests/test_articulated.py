"""Anatomy, separate parts and the articulated assembly."""
import numpy as np
import pytest

from ortholab import articulated as ar, data, export, geometry, printability as pr
from ortholab.config import DESIGN, MEASURES


@pytest.fixture(scope="module")
def person():
    s = data.load(sample=True)
    return {k: float(s.loc[10, k]) for k in MEASURES}


@pytest.fixture(scope="module")
def parts(person):
    return ar.build_articulated(person)


def test_heel_rounding_is_a_quarter_circle():
    d = geometry.heel_rounding(np.array([0.0, 6.0, 12.0, 30.0]), 12.0)
    assert d[0] == pytest.approx(12.0) and d[2] == pytest.approx(0.0) and d[3] == 0.0
    assert 0 < d[1] < 12


def test_malleolus_relief_peaks_on_the_malleoli(person):
    (th_l, z_l), (th_m, z_m) = geometry.malleoli(person)
    assert z_m > z_l                                        # medial malleolus sits higher
    peak = geometry.relief(np.array([th_l]), z_l, person)[0]
    far = geometry.relief(np.array([np.radians(-90.0)]), z_l + 60, person)[0]
    assert peak == pytest.approx(DESIGN["malleolus_relief"], rel=0.05) and far < 0.01


def test_back_line_has_heel_and_achilles(person):
    prof = geometry.limb_profile(person)
    heel = prof.back(0.45 * person["malleolus_height"])
    achilles = prof.back(person["malleolus_height"] + 20)
    assert heel < 0 < achilles                              # heel behind the line, tendon in front of it


def test_footplate_has_arch_and_walls(person):
    flat = geometry.plate_mesh(person, {"arch_height": 0.0, "wall_height": 0.0})
    full = geometry.plate_mesh(person)
    assert full.is_watertight and full.volume > flat.volume
    assert full.extents[2] > DESIGN["thickness"] + 5        # walls rise above the plate


def test_parts_are_closed_and_separate(parts):
    for name in ("lower", "upper"):
        assert parts[name].is_watertight and parts[name].is_volume
    assert ar.overlap_volume(parts["lower"], parts["upper"]) == pytest.approx(0.0, abs=1e-6)


def test_hinge_axis_through_the_malleoli(person, parts):
    j = parts["joint"]
    (_, z_l), (_, z_m) = geometry.malleoli(person)
    assert z_l <= j.origin[2] <= z_m
    assert j.x_inner > person["bimalleolar_breadth"] / 2      # discs sit outside the ankle


def test_free_motion_covers_walking(parts):
    rom = ar.range_of_motion_fast(parts)
    assert rom["dorsiflexion_deg"] >= 20 and rom["plantarflexion_deg"] >= 20
    assert rom["rest_overlap_mm3"] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("target", [0.0, 5.0])
def test_plantar_stop_meets_the_setting(person, target):
    P = ar.build_articulated(person, {"plantar_stop_deg": target})
    rom = ar.range_of_motion_fast(P, tol_deg=0.25)
    assert abs(rom["plantarflexion_deg"] - target) <= 1.0
    assert P["upper"].is_watertight and rom["rest_overlap_mm3"] == pytest.approx(0.0, abs=1e-6)


def test_bisection_matches_the_degree_sweep(parts):
    fast = ar.range_of_motion_fast(parts, limit=40, tol_deg=0.5)
    slow = ar.range_of_motion(parts, limit=40, step=1.0)
    assert abs(fast["plantarflexion_deg"] - slow["plantarflexion_deg"]) <= 1.5


def test_foot_section_fits_a_desktop_printer(parts):
    assert pr.best_orientation(parts["lower"], (250.0, 210.0, 220.0)) is not None


def test_articulated_export(parts, person, tmp_path):
    export.export_articulated(parts, tmp_path, "afo", person)
    for f in ("afo_foot_section.stl", "afo_calf_cuff.stl", "afo_assembly.3mf", "afo_assembly.3dm", "afo_assembly.json"):
        assert (tmp_path / f).exists()
    import rhino3dm
    model = rhino3dm.File3dm.Read(str(tmp_path / "afo_assembly.3dm"))
    assert len(model.Objects) == 3 and len(model.Layers) == 3


def test_exploded_view_pulls_parts_apart(parts):
    E = ar.exploded(parts, gap=40.0)
    assert E["upper"].bounds[0][2] == pytest.approx(parts["upper"].bounds[0][2] + 40.0)
    assert len(E["pins"].split(only_watertight=False)) == 2
    assert np.abs(E["pins"].vertices[:, 0]).min() > np.abs(parts["pins"].vertices[:, 0]).min() + 30
