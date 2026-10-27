"""Write README.md from results/summary.json so every number in it comes from the last run."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())
stress = pd.read_csv(ROOT / "results" / "stress_test.csv")
pct = lambda v: f"{v * 100:.0f} %"  # noqa: E731
lo, hi = S["equal_stiffness_thickness_p05_p95"]
m05, m95 = S["mass_petg_g_p05_p95"]
c50, c95 = S["min_cube_mm_p50_p95"]
tol = S["assistant_lgbm_within_tol"]
mae = S["assistant_lgbm_mae_mm"]
proto = S["protocol_all_within_tol"]
miss = S["sizing_miss_by_dim_4_sizes"]

README = f"""<p align="center"><img src="docs/figures/banner.png" alt="Orthosis Param Lab" width="100%"></p>

<p align="center">
<a href="https://github.com/Abderrahmane-BOULAMI/orthosis-param-lab/actions"><img src="https://github.com/Abderrahmane-BOULAMI/orthosis-param-lab/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
<img src="https://img.shields.io/badge/python-3.12-00909C" alt="python">
<img src="https://img.shields.io/badge/data-ANSUR%20II%20·%206%2C068%20people-14213D" alt="data">
<img src="https://img.shields.io/badge/exports-STL%20·%203MF%20·%20Rhino%20.3dm-C2410C" alt="exports">
</p>

**A joint project by [Abderrahmane BOULAMI](https://github.com/Abderrahmane-BOULAMI) and [Kawtar BELLAMINE](https://github.com/kawtar-bellamine), engineering students at Arts et Métiers ParisTech.**

Custom orthoses are made one person at a time. This lab asks three practical questions a MedTech team meets every day,
and answers them with code that runs on real body measurements:

1. **Can a printable ankle-foot orthosis (AFO) be generated from a handful of tape measurements?** Yes: nine measurements in, a closed solid out, checked for wall thickness, orientation and build volume, exported as STL, 3MF and a Rhino `.3dm` file.
2. **Is made-to-measure worth it, compared with standard sizes?** On {S['people']:,} real people, four shoe-size based sizes fit only **{pct(S['sizing_4_foot_length_sizes'])}** of them within tolerance.
3. **What still needs the tape, and what can a model fill in?** Lengths can be predicted from foot length, height and weight; **ankle and calf girths cannot**, so they must be measured or scanned.

<p align="center"><img src="docs/figures/turntable.gif" alt="Generated orthosis, ventilated variant" width="360"></p>

## Results at a glance

| Question | Result on {S['people']:,} people (ANSUR II) |
|---|---|
| Orthoses generated, closed and printable | **{S['people']:,} / {S['people']:,}** watertight ({pct(S['watertight_share'])}), median **{S['gen_seconds_median'] * 1000:.0f} ms** each |
| Stress test: extreme bodies × 5 design variants | {S['stress_cases']} parts, {pct(S['stress_watertight_share'])} watertight, measured wall ≥ {S['stress_wall_p05_min_ratio'] * 100:.0f} % of target (5th percentile) |
| Mass in PETG, 100 % infill (5th to 95th percentile) | {m05:.0f} to {m95:.0f} g |
| Smallest cubic printer that holds the part | median {c50:.0f} mm, 95th percentile {c95:.0f} mm; **{pct(S['fits_desktop_share'])}** fit a 250 × 210 × 220 mm desktop printer, **{pct(S['fits_large_share'])}** fit a 400 mm cube |
| People within tolerance with 4 foot-length sizes | **{pct(S['sizing_4_foot_length_sizes'])}** (12 sizes: {pct(S['sizing_12_foot_length_sizes'])}; 40 best-case multi-dimension sizes: {pct(S['sizing_40_multi_dim_sizes'])}) |
| Main reasons a standard size misses (4 sizes) | calf girth {pct(miss['calf_circ'])}, ankle girth {pct(miss['ankle_circ'])}, tibial height {pct(miss['tibial_height'])} of people |
| Ankle stiffness spread at a constant 3 mm shell | 95th / 5th percentile = **{S['ankle_I_p95_over_p05']:.1f}×** |
| Thickness that gives everyone the median stiffness | **{lo:.1f} to {hi:.1f} mm** (5th to 95th percentile) |
| Ankle trimline 120° instead of 200° | **{S['trimline_120_vs_200']:.2f}×** the stiffness (beam model) |
| Unseen people predicted within tolerance (LightGBM) | malleolus height {pct(tol['malleolus_height'])}, heel breadth {pct(tol['heel_breadth'])}, **ankle girth {pct(tol['ankle_circ'])}, calf girth {pct(tol['calf_circ'])}** |
| Every predicted dimension in tolerance | quick inputs only {pct(proto['A_quick_only'])}; after taping ankle and calf {pct(proto['B_quick_plus_two_girths'])} |

<p align="center"><img src="docs/figures/hero.png" alt="Orthoses for a small, a median and a large person" width="80%"></p>
<p align="center"><sub>Same generator, three people from the survey (small, median, large), rendered at the same scale.</sub></p>

## How it works

```
9 measurements ──► limb profile ──► shell + footplate ──► Manifold union ──► checks ──► STL · 3MF · .3dm
 (tape or scan)    elliptical       exact normal           vents cut          watertight, wall,
                   sections, PCHIP  offset, wrap angle     (optional)         orientation, bed fit, mass
```

* **Geometry** (`ortholab/geometry.py`). The leg is a stack of ellipses set by measured girths and breadths
  (perimeter inverted with Ramanujan's formula). The shell is the exact normal offset of each ellipse from the
  liner clearance to clearance + thickness, so the wall is the thickness you ask for. A footplate built from heel
  breadth, ball-of-foot position and foot breadth is fused to it with Manifold booleans.
* **Parameters** (`ortholab/config.py`): thickness, clearance, wrap angle, ankle trimline, ventilation rows,
  plate length. Every height ANSUR does not measure is a named assumption (see [design notes](docs/design_notes.md)).
* **Printability** (`ortholab/printability.py`): watertight and positive volume, wall thickness by ray casting,
  three orientations with bed rotation, support area above 45°, smallest cubic build volume, mass.
* **Stiffness** (`ortholab/mechanics.py`): second moment of area of the exact ankle cross-section (Green's
  theorem), used to rank designs and to solve the thickness that equalises stiffness across people.
* **Rhino and Grasshopper**: `.3dm` files are written with `rhino3dm`, with every measurement and parameter stored
  as user text on the object, and read back in the tests. The core works on plain numbers, so it can move into a
  Grasshopper Python component; that step is not done yet.

## Why made-to-measure

<p align="center"><img src="docs/figures/sizing.png" alt="Coverage of standard sizes" width="85%"></p>

Sizes are designed on one half of the survey and judged on the other half ({S['sizing_test_people']:,} people).
A person fits only if foot length, foot and heel breadth, ankle and calf girth, malleolus and tibial height are all
within tolerance. Even 40 sizes clustered on all seven dimensions leave most people out. The tolerances are
assumptions, so `results/sizing_tolerance.csv` reports coverage from half to twice their values.

## What the tape is still for

<p align="center"><img src="docs/figures/assistant.png" alt="Measurement assistant" width="85%"></p>

Four models (median by sex, linear regression, a small neural network, LightGBM) predict eight measurements from
foot length, height, weight and sex, trained on 75 % of people and tested on the 25 % they never saw. The three learned
models agree within three points, so the limit is the information, not the algorithm: lengths are predictable (mean error {mae['malleolus_height']} mm for malleolus height), girths are not
({mae['ankle_circ']} mm ankle, {mae['calf_circ']} mm calf). A clinic can save time on lengths, not on girths.

## Stiffness and trimline

<p align="center"><img src="docs/figures/stiffness.png" alt="Stiffness study" width="95%"></p>

With the same 3 mm shell for everyone, ankle stiffness varies {S['ankle_I_p95_over_p05']:.1f}× between the 5th and 95th
percentile, because it follows the size of the ankle. The trimline matters even more: cutting the shell from 200° to 120° around the ankle
leaves about a tenth of the stiffness, which is how a rigid AFO becomes a flexible leaf spring.

## Printing

<p align="center"><img src="docs/figures/build_volume.png" alt="Build volume needed" width="85%"></p>

A full-height AFO does not fit a common desktop printer in any orientation. Lying it on its back trades height for
support material; the code reports both, so the choice is explicit.

## Dashboard

```bash
pip install -r requirements.txt
streamlit run app/dashboard.py
```

Design an orthosis from a survey person or your own measurements, move the sliders, see the checks update and download
STL, 3MF or `.3dm`. The other tabs show the sizing study, the measurement assistant and the population checks.

| Design | Sizing |
|---|---|
| ![design](docs/screenshots/design.png) | ![sizing](docs/screenshots/sizing.png) |

## Reproduce

```bash
python experiments/run_all.py --sample   # 300-person extract shipped in the repo, about a minute
python experiments/run_all.py            # all {S['people']:,} people: downloads ANSUR II once, checks SHA-256
pytest                                   # geometry, thickness, stiffness, export, sizing and model tests
python tools/figures.py && python tools/banner.py
```

Data: ANSUR II public working databases (US Army anthropometric survey, 2012; original at
[openlab.psu.edu/ansur2](https://www.openlab.psu.edu/ansur2/)), pulled from a GitHub mirror pinned to one commit and
verified by SHA-256 (`ortholab/config.py`). Lengths in mm.

## Limits

* **No physical prototype yet.** Every result here is computed. The [bench test protocol](docs/test_protocol.md) says
  what to print and measure first, and what result would prove the model wrong.
* **Shape from measurements, not scans.** Ellipses capture girths and breadths, not bony landmarks or the arch. Some
  heights (minimum ankle girth, calf girth, below-knee girth) are assumptions listed in the design notes. A scan-based
  shape would replace the limb profile and keep the rest of the pipeline.
* **Stiffness is a beam model.** It ranks designs and people; it is not FEA and gives no absolute stiffness.
* **Survey population.** ANSUR II measures US Army personnel aged about 17 to 58, healthy adults. Patients needing an AFO
  (children, elderly, swelling, deformity) will differ; the sizing gap is likely larger, not smaller.
* **Tolerances are assumptions** about what liners and straps absorb; the study shows results across a range.
* **Grasshopper**: the `.3dm` export is tested; running the generator inside Grasshopper is not.

## Résumé en français

Générateur paramétrique d'orthèse cheville-pied : à partir de neuf mesures, une coque fermée et imprimable, contrôlée
(épaisseur, orientation, volume d'impression) et exportée en STL, 3MF et pour Rhino. Testé sur les mesures réelles de
{S['people']:,} personnes : 4 tailles standard n'en ajustent que {pct(S['sizing_4_foot_length_sizes'])}, les longueurs se prédisent mais
les tours de cheville et de mollet doivent être mesurés, et l'épaisseur doit aller de {lo:.1f} à {hi:.1f} mm pour une même
rigidité. Aucun prototype physique n'est encore testé : le protocole d'essai est dans `docs/test_protocol.md`.

## Licence

Code under the MIT licence. ANSUR II data are published by the US Army for public use; see the original source above.
"""

(ROOT / "README.md").write_text(README)
print("README.md written")
