import numpy as np
import pytest

from ortholab import assistant, data, export, geometry, mechanics, printability as pr, sizing
from ortholab.config import MEASURES


@pytest.fixture(scope="module")
def sample():
    return data.load(sample=True)


@pytest.fixture(scope="module")
def person(sample):
    return {k: float(sample.loc[0, k]) for k in MEASURES}


def test_sample_has_all_measures(sample):
    assert len(sample) == 300
    assert set(MEASURES) <= set(sample.columns)
    assert sample[MEASURES].notna().all().all()
    assert sample["foot_length"].between(180, 340).all()


def test_ellipse_axes_round_trip():
    for per, ratio in [(220, 1.05), (390, 1.15), (300, 1.0)]:
        a, b = geometry.ellipse_axes(per, ratio)
        assert a / b == pytest.approx(ratio, rel=1e-6)
        assert geometry.perimeter(a, b) == pytest.approx(per, rel=1e-6)


def test_afo_is_a_printable_solid(person):
    afo = geometry.build_afo(person)
    assert afo.is_watertight and afo.is_volume
    assert afo.bounds[0][2] == pytest.approx(0.0, abs=1e-6)
    top = person["tibial_height"] - 40.0
    assert afo.extents[2] == pytest.approx(top, abs=0.5)


@pytest.mark.parametrize("params", [{"thickness": 2.0}, {"thickness": 5.0},
                                    {"ankle_wrap_deg": 120.0}, {"vent_rows": 4}])
def test_variants_stay_watertight(person, params):
    afo = geometry.build_afo(person, params)
    assert afo.is_watertight and afo.is_volume


def test_wall_thickness_matches_parameter(person):
    for t in (2.0, 3.0, 4.5):
        w = pr.wall_thickness(geometry.build_afo(person, {"thickness": t}), n=300)
        assert np.median(w) == pytest.approx(t, rel=0.03)


def test_volume_grows_with_thickness(person):
    v = [geometry.build_afo(person, {"thickness": t}).volume for t in (2.0, 3.0, 4.0)]
    assert v[0] < v[1] < v[2]


def test_vents_remove_material(person):
    assert geometry.build_afo(person, {"vent_rows": 4}).volume < geometry.build_afo(person).volume


def test_polygon_moments_match_a_disk():
    th = np.linspace(0, 2 * np.pi, 4000, endpoint=False)
    A, cx, cy, Ixx, Iyy = mechanics.polygon_moments(50 * np.cos(th), 50 * np.sin(th))
    assert A == pytest.approx(np.pi * 50 ** 2, rel=1e-4)
    assert Ixx == pytest.approx(np.pi / 4 * 50 ** 4, rel=1e-4)
    assert cx == pytest.approx(0, abs=1e-6)


def test_stiffness_rises_with_thickness_and_wrap(person):
    assert mechanics.ankle_inertia(person, {"thickness": 4}) > mechanics.ankle_inertia(person, {"thickness": 3})
    assert mechanics.ankle_inertia(person, {"ankle_wrap_deg": 120}) < mechanics.ankle_inertia(person)


def test_thickness_for_hits_target(person):
    target = mechanics.ankle_inertia(person, {"thickness": 3.7})
    assert mechanics.thickness_for(person, target) == pytest.approx(3.7, abs=0.01)


def test_bed_fit_uses_rotation():
    import trimesh
    bar = trimesh.creation.box((300, 20, 10))
    bar.apply_translation(-bar.bounds[0])
    assert not pr.fits_bed(bar, (250, 250, 100), step_deg=90)
    assert pr.fits_bed(bar, (250, 250, 100), step_deg=5)


def test_support_area_zero_for_box_on_bed():
    import trimesh
    box = trimesh.creation.box((50, 50, 50))
    box.apply_translation(-box.bounds[0])
    assert pr.support_area(box) == pytest.approx(0.0)


def test_3dm_round_trip(person, tmp_path):
    afo = geometry.build_afo(person)
    path = export.to_3dm(afo, tmp_path / "afo.3dm", person, {"thickness": 3.0})
    back = export.read_3dm(path)
    assert back["vertices"] == len(afo.vertices) and back["faces"] == len(afo.faces)
    assert back["user_text"]["measure.foot_length"] == str(person["foot_length"])


def test_sizing_coverage_bounds(sample):
    design, test = sizing.split(sample)
    one = sizing.foot_length_sizes(design, 1)
    many = sizing.multi_dim_sizes(design, 20)
    assert 0 <= sizing.coverage(test, one) <= sizing.coverage(test, many) <= 1
    assert sizing.coverage(test, many, scale=2) >= sizing.coverage(test, many)


def test_assistant_beats_median_baseline(sample):
    res, _, _ = assistant.evaluate(sample)
    mae = res.pivot(index="target", columns="model", values="mae_mm")
    assert (mae["linear regression"] <= mae["median by sex"] + 0.5).all()
