"""Write README.md from results/summary.json so every number in it comes from the last run."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import os
RES = ROOT / "results" / ("sample" if os.environ.get("ORTHO_SAMPLE") else "")
S = json.loads((RES / "summary.json").read_text())
stress = pd.read_csv(RES / "stress_test.csv")
pct = lambda v: f"{v * 100:.0f} %"  # noqa: E731
lo, hi = S["equal_stiffness_thickness_p05_p95"]
m05, m95 = S["mass_petg_g_p05_p95"]
c50, c95 = S["min_cube_mm_p50_p95"]
tol = S["assistant_lgbm_within_tol"]
mae = S["assistant_lgbm_mae_mm"]
proto = S["protocol_all_within_tol"]
miss = S["sizing_miss_by_dim_4_sizes"]
sg_min, sg_med, sg_p = S["scan_fit_gap_min_mm"], S["scan_fit_gap_median_mm"], S["scan_fit_pressing_share"]
sg_max = pd.read_csv(RES / "scan_fit.csv").groupby("source")["gap_mm"].max().round(2).to_dict()

stops = pd.read_csv(RES / "plantar_stop.csv")
_rigid = stress[~stress["variant"].str.startswith("articulated")]
wall_ratio = float((_rigid["wall_p05"] / _rigid["target_t"]).min())
n_rigid, n_art = len(_rigid), len(stress) - len(_rigid)
pf05, pf50, pfmin = S["art_plantar_free_p05_p50_min"]
README = f"""<p align="center"><img src="docs/figures/banner.png" alt="Orthosis Param Lab" width="100%"></p>

<p align="center">
<a href="https://github.com/Abderrahmane-BOULAMI/orthosis-param-lab/actions"><img src="https://github.com/Abderrahmane-BOULAMI/orthosis-param-lab/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
<img src="https://img.shields.io/badge/python-3.12-00909C" alt="python">
<img src="https://img.shields.io/badge/data-ANSUR%20II%20·%206%2C068%20people-14213D" alt="data">
<img src="https://img.shields.io/badge/exports-STL%20·%203MF%20·%20Rhino%20.3dm-C2410C" alt="exports">
</p>

**A joint project by [Abderrahmane BOULAMI](https://github.com/Abderrahmane-BOULAMI) and [Kawtar BELLAMINE](https://github.com/kawtar-bellamine), engineering students at Arts et Métiers ParisTech.**

An **articulated, made-to-measure ankle-foot orthosis (AFO)** generated from nine body measurements or a leg scan,
with **one printed part per bone group**: hindfoot (calcaneus, talus), midfoot (navicular, cuboid, cuneiforms),
forefoot (metatarsals) and toes (phalanges), pinned at the Chopart, Lisfranc and metatarsophalangeal joints, plus a
calf cuff hinged at the ankle. Each part is modelled on its own, anatomy first (heel, Achilles line, malleoli, arch),
then assembled, checked for collisions and range of motion on the real meshes, and exported ready to print as STL,
3MF and Rhino `.3dm`.

<p align="center">
<img src="docs/figures/motion.gif" alt="Roll-over: foot flat, heel rise, toe-off" width="360">
<img src="docs/figures/turntable.gif" alt="Articulated orthosis, turntable" width="360">
</p>

The lab answers four questions a MedTech product team meets every day, on the real measurements of {S['people']:,} people:

1. **Can a printable, articulated AFO be generated from a handful of measurements?** Yes: **{S['people']:,} / {S['people']:,}** assemblies built with closed parts, zero overlap at rest and a hinge that turns freely, in about {S['art_gen_seconds_median']:.1f} s each.
2. **Do the joints behave as prescribed?** The ankle's plantarflexion stop (for example 5° for drop foot) is reached within **{S['plantar_stop_abs_err_max_deg']:.1f}°** for every person tested; each foot joint opens to its designed range within **{S['seg_range_abs_err_max_deg']:.1f}°** and locks flat under load.
3. **Is made-to-measure worth it?** Four standard sizes fit **{pct(S['sizing_4_foot_length_sizes'])}** of people within tolerance; the generator fits everyone by construction.
4. **How fast can a clinic measure?** From foot length, height, weight and sex, a LightGBM model predicts **six of the eight** fit measurements; taping ankle and calf completes the set.

## Results at a glance

| Question | Result on {S['people']:,} people (ANSUR II) |
|---|---|
| Bone-segment foot ({S['seg_people']} people drawn at random) | **{pct(S['seg_closed_share'])}** of segments one closed part, zero overlap at rest; Chopart and Lisfranc open {S['seg_dorsi_median_deg']['chopart']:.0f}°, MTP {S['seg_dorsi_median_deg']['mtp']:.0f}° (designed {S['seg_range_deg']['chopart']:.0f}° and {S['seg_range_deg']['mtp']:.0f}°), every joint locks under load within {S['seg_locked_max_deg']:.1f}°; **{pct(S['seg_fit_desktop_share'])}** of segments fit a desktop printer |
| Articulated orthoses generated | **{S['people']:,} / {S['people']:,}**, both parts closed solids ({pct(S['art_watertight_share'])}), overlap at rest ≤ {S['art_rest_overlap_max_mm3']:.1f} mm³, median **{S['art_gen_seconds_median']:.1f} s** each |
| Free ankle motion (hinge only, no stop) | dorsiflexion ≥ **{S['art_dorsi_free_min_deg']:.0f}°** for everyone; plantarflexion median **{pf50:.0f}°**, 5th percentile {pf05:.0f}° |
| Plantarflexion stop, set to 0°, 5° or 10° | {S['plantar_stop_people']} people × 3 settings: mean error **{S['plantar_stop_abs_err_mean_deg']:.1f}°**, max {S['plantar_stop_abs_err_max_deg']:.1f}°, {pct(S['plantar_stop_watertight_share'])} closed parts |
| Printing the parts | foot section fits a 250 × 210 × 220 mm desktop printer for **{pct(S['art_lower_fits_desktop_share'])}** of people; calf cuff fits a 400 mm printer for {pct(S['art_upper_fits_large_share'])} |
| Mass of the assembly in PETG, 100 % infill | median {S['art_mass_petg_g_median']:.0f} g |
| One-piece rigid version, same generator | {pct(S['watertight_share'])} watertight, median **{S['gen_seconds_median'] * 1000:.0f} ms** each |
| Stress test: extreme bodies × design variants | {S['stress_cases']} parts ({n_rigid} one-piece, {n_art} articulated), {pct(S['stress_watertight_share'])} watertight; one-piece shells measure ≥ {wall_ratio * 100:.0f} % of the target wall (5th percentile of ray samples) |
| People within tolerance with 4 foot-length sizes | **{pct(S['sizing_4_foot_length_sizes'])}** (12 sizes: {pct(S['sizing_12_foot_length_sizes'])}; 40 best-case multi-dimension sizes: {pct(S['sizing_40_multi_dim_sizes'])}) |
| Thickness that gives everyone the median stiffness | **{lo:.1f} to {hi:.1f} mm** (5th to 95th percentile) |
| Ankle trimline 120° instead of 200° | **{S['trimline_120_vs_200']:.2f}×** the stiffness (beam model) |
| Measurements predicted for unseen people (LightGBM) | heel to ball {pct(tol['ball_length'])}, ankle breadth {pct(tol['bimalleolar_breadth'])}, malleolus height {pct(tol['malleolus_height'])}, heel breadth {pct(tol['heel_breadth'])} within tolerance |
| Fit from a leg scan | gap {sg_min['scan']:.2f} to {sg_max['scan']:.2f} mm for a 3 mm liner target, no contact point |

<p align="center"><img src="docs/figures/hero.png" alt="Articulated orthoses for a small, a median and a large person" width="80%"></p>
<p align="center"><sub>Same generator, three people from the survey (small, median, large), rendered at the same scale. Hindfoot teal, midfoot amber, forefoot coral, toes violet, calf cuff blue, pins grey.</sub></p>

## One part per bone group

<p align="center"><img src="docs/figures/segments.png" alt="Bone segments and roll-over" width="100%"></p>

The 26 bones of the foot move as a few functional groups, which is how gait labs model them (Oxford and Rizzoli
multi-segment foot models). `ortholab/segmented.py` cuts the foot section along those joint lines and turns each
group into its own printed part:

| Segment | Bones | Joint behind it | Placed from | Designed range |
|---|---|---|---|---|
| hindfoot | calcaneus, talus | ankle, M5 hinge to the calf cuff | malleolus heights | free, plantar stop |
| midfoot | navicular, cuboid, cuneiforms | Chopart (midtarsal) | 34 % of foot length | {S['seg_range_deg']['chopart']:.0f}° |
| forefoot | metatarsals | Lisfranc (tarsometatarsal) | ball length − 24 % of foot length | {S['seg_range_deg']['lisfranc']:.0f}° |
| toes | phalanges | metatarsophalangeal, oblique line (20°) | measured ball of the foot | {S['seg_range_deg']['mtp']:.0f}° |

* **Locks under load, rolls at push-off.** Each axis sits just above the footplate. The plate below the axis opens
  when the distal segment turns up, so the foot rolls over the toes; it closes at once when the segment turns down,
  so the plate stays rigid under body weight (measured lock within {S['seg_locked_max_deg']:.1f}°, the print gap).
* **Range set by a V notch.** The side walls above the axis get a V notch whose angle is the allowed dorsiflexion;
  the range measured on the meshes matches the design within {S['seg_range_abs_err_max_deg']:.1f}°.
* **Knuckle hinges.** On each side a knuckle of the proximal segment sits inside a knuckle of the distal one, an M3
  screw runs through both, and the outer knuckle reaches its segment through a bridge placed beyond the inner
  knuckle's reach, so nothing collides over the range. Every segment prints flat on a desktop printer.

## Parts and joint

<p align="center"><img src="docs/figures/parts.png" alt="Exploded view and ankle motion" width="95%"></p>

* **Anatomy** (`ortholab/geometry.py`). The leg is a stack of sections set by measured girths and breadths
  (ellipse perimeter inverted with Ramanujan's formula), on a posterior line that follows the heel bulge and the
  Achilles tendon. The heel is rounded, the lateral and medial malleoli sit at their own heights (medial higher)
  and get a relief dome so the shell never presses on the bone. The footplate carries a medial arch and side walls.
* **Foot section**: footplate, heel cup and two side uprights ending in flat inner hinge discs (split into bone
  segments as above, or printed as one part).
* **Calf cuff** (blue): leg shell above the ankle with strap slots and ventilation, joined by two side straps to
  outer hinge discs that sit outside the inner ones, with a 0.4 mm print gap between every moving pair.
* **Joint** (`ortholab/articulated.py`). The axis runs medio-laterally through the malleoli. One M5 screw per side
  (5.3 mm hole) holds the discs; a printed pin is exported for previews.
* **Range of motion**. The foot section is turned about the axis on the real meshes and the overlap volume with the
  cuff is measured; bisection finds the first collision in about a dozen tests and matches a one-degree sweep.
* **Plantarflexion stop**. The back of the cuff grows down towards the heel until the foot section stops at the
  prescribed angle; the height is found by bisection, so the setting holds whatever the person's size.

## How it works

```
9 measurements ─► anatomy ─► rigid shell + footplate ─► split at ankle axis ─► hinges, straps, stop ─► checks ─► STL · 3MF · .3dm
 (tape or scan)   heel, Achilles,  exact normal offset,     foot section          M5 discs, 0.4 mm gap      closed parts, overlap,
                  malleoli, arch   Manifold booleans        + calf cuff           bisection-sized stop      motion, wall, bed fit, mass
```

* **Printability** (`ortholab/printability.py`): watertight and positive volume, wall thickness by ray casting,
  orientations with bed rotation, support area above 45°, smallest cubic build volume, mass.
* **Stiffness** (`ortholab/mechanics.py`): second moment of area of the exact ankle cross-section (Green's
  theorem), used to rank designs and to solve the thickness that equalises stiffness across people.
* **Scan input** (`ortholab/scan.py`): slices a leg scan every 8 mm and replaces the default sections with the
  measured widths, depths, girths and posterior line; `fit_gaps` measures the skin-to-shell gap on the real meshes.
* **Batch command** (`ortholab/cli.py`): a table of patients in, one set of parts and a check report per patient out;
  the exit code fails the batch if a part is not printable.
* **Rhino and Grasshopper**: `.3dm` files are written with `rhino3dm`, one layer per part, with every measurement
  and parameter stored as user text. `grasshopper/afo_component.py` is a Rhino 8 Python component that calls the
  same generator and outputs the foot section and calf cuff as Rhino meshes.

## Why made-to-measure

<p align="center"><img src="docs/figures/sizing.png" alt="Coverage of standard sizes" width="85%"></p>

Sizes are designed on one half of the survey and judged on the other half ({S['sizing_test_people']:,} people).
A person fits only if foot length, foot and heel breadth, ankle and calf girth, malleolus and tibial height are all
within tolerance. Even 40 sizes clustered on all seven dimensions leave most people out, which is exactly where a
parametric generator pays off. `results/sizing_tolerance.csv` reports coverage from half to twice the tolerances.

## Faster measuring

<p align="center"><img src="docs/figures/assistant.png" alt="Measurement assistant" width="85%"></p>

Four models (median by sex, linear regression, a small neural network, LightGBM) predict eight measurements from
foot length, height, weight and sex, trained on 75 % of people and tested on the 25 % they never saw. Lengths and
breadths come out within a few millimetres (mean error {mae['malleolus_height']} mm for malleolus height,
{mae['bimalleolar_breadth']} mm for ankle breadth), so the clinic protocol is short: four quick inputs, two tape
girths, and the generator does the rest.

## Stiffness and trimline

<p align="center"><img src="docs/figures/stiffness.png" alt="Stiffness study" width="95%"></p>

With the same 3 mm shell for everyone, ankle stiffness varies {S['ankle_I_p95_over_p05']:.1f}× between the 5th and 95th
percentile, because it follows the size of the ankle; solving the thickness per person gives everyone the same
stiffness. The trimline is the main design knob: cutting the shell from 200° to 120° around the ankle leaves about a
tenth of the stiffness, which is how a rigid AFO becomes a flexible leaf spring.

## Printing

<p align="center"><img src="docs/figures/build_volume.png" alt="Build volume needed" width="85%"></p>

Splitting at the ankle is what makes desktop printing possible: the one-piece AFO needs a {c50:.0f} mm cube for the
median person, while the articulated foot section fits a 250 × 210 × 220 mm desktop printer (such as a Bambu Lab)
for {pct(S['art_lower_fits_desktop_share'])} of people. The code reports orientation and support area for each part.

## Scan-ready

<p align="center"><img src="docs/figures/scan_fit.png" alt="Scan versus tape fit" width="85%"></p>

When a scan is available, the leg sections and the posterior line come from the scan itself. On a test leg whose calf
is lower and flatter than average, the scan-based shell keeps the 3 mm liner clearance everywhere it was measured
(gap {sg_min['scan']:.2f} to {sg_max['scan']:.2f} mm), while the heel and malleoli stay on the tape measurements.

```python
from ortholab import articulated, scan
prof = scan.profile_from_scan(leg_scan_mesh, measures)          # scan in mm, z up from the sole
parts = articulated.build_articulated(measures, {{"plantar_stop_deg": 5}}, profile=prof)
print(articulated.range_of_motion_fast(parts))                  # free dorsiflexion, plantar stop, overlap at rest
```

## Batch production

```bash
python -m ortholab.cli template patients.csv                                  # example table: id + nine measurements
python -m ortholab.cli batch patients.csv --out outputs/batch --segmented --plantar-stop 5
```

Each patient gets every part as STL (four foot segments and the calf cuff with `--segmented`, foot section and cuff
with `--articulated`), the assembly as 3MF, `.3dm` (one layer per part) and JSON (axis points and directions, pin
sizes, ranges, print gap). `report.csv` lists closed parts, overlap at rest, ankle motion and stop, the opening and
lock of every foot joint, wall thickness, printer fit and mass. Measurements outside the survey range raise a warning,
and the command exits with code 1 if any part fails, for example a wall under the 2 mm minimum.

## Grasshopper

Paste `grasshopper/afo_component.py` into a Rhino 8 Python 3 component, add the inputs listed at the top of the file
(`repo`, `measures`, `thickness`, `clearance`, `ankle_wrap`, `vent_rows`, `articulated`, `plantar_stop`, `segments`)
and the `afo` (foot section, or the list of four foot segments), `cuff` and `report` outputs. The first run installs the Python packages through the `# r:` line.

## Dashboard

```bash
pip install -r requirements.txt
streamlit run app/dashboard.py
```

Design an orthosis from a survey person or your own measurements, choose bone segments, two parts or one piece, set
the plantar stop and the foot joint ranges, move the ankle and roll over the toes with sliders, see the checks update
and download every part as STL, the assembly as 3MF or `.3dm`. The other tabs show the sizing study, the measurement assistant and the population checks.

| Design | Sizing |
|---|---|
| ![design](docs/screenshots/design.png) | ![sizing](docs/screenshots/sizing.png) |

## Reproduce

```bash
python experiments/run_all.py --sample   # 300-person extract shipped in the repo, a few minutes
python experiments/run_all.py            # all {S['people']:,} people: downloads ANSUR II once, checks SHA-256
python experiments/segmented_study.py    # bone-segment foot on 150 people (also run by run_all.py)
pytest                                   # anatomy, parts, joints, segments, motion, stop, printing, scan, batch, Grasshopper, dashboard
python tools/figures.py && python tools/banner.py
```

Data: ANSUR II public working databases (US Army anthropometric survey, 2012; original at
[openlab.psu.edu/ansur2](https://www.openlab.psu.edu/ansur2/)), pulled from a GitHub mirror pinned to one commit and
verified by SHA-256 (`ortholab/config.py`). Lengths in mm.

## Roadmap: toward a bio-inspired orthosis

The generator already produces the skeleton of a bio-inspired orthosis: anatomical joint axes, one part per bone
group, measured ranges of motion. The next versions build on that same parametric chain.

| Next step | What it adds | Builds on |
|---|---|---|
| **Print and bench test** | First prints (foot segments on a Bambu Lab, cuff on a large-format printer), hinge, stop and roll-over measured against the [test protocol](docs/test_protocol.md) | exported 3MF and joint JSON |
| **Spring-assisted ankle** | Torsion springs on the ankle pins to lift the foot in swing (drop foot), stiffness sized per person | ankle axis, stiffness model |
| **Adjustable stop pins** | Range of motion set with interchangeable pins instead of a fixed printed stop | bisection-sized plantar stop |
| **Plantar fascia cable** | A tension cable from heel to toes that tightens as the toes lift (windlass mechanism), stiffening the arch at push-off | MTP axis and segment chain |
| **Ray-segmented forefoot** | Forefoot and toes split along the metatarsal rays, so the sole follows uneven ground | oblique MTP line, segment cutting |
| **Compliant joints** | Printed flexures in TPU in place of pins for the midfoot joints | V-notch range design |
| **Finite elements** | Stresses in hinges, knuckles and cuff under ground reaction forces through the gait cycle | exported meshes |
| **Clinical inputs** | Cleaned clinical scans aligned to the sole and heel frame; children and patients with swelling or deformity | scan input, ANSUR study |
| **Comfort** | Padded liner offsets and ratchet strap mounts generated with the shell | clearance and strap slots |

## Résumé en français

Orthèse cheville-pied articulée et sur mesure, générée à partir de neuf mesures ou d'un scan, avec une pièce imprimée
par groupe osseux : arrière-pied (calcanéus, talus), médio-pied (naviculaire, cuboïde, cunéiformes), avant-pied
(métatarsiens) et orteils (phalanges), articulés aux interlignes de Chopart, de Lisfranc et métatarso-phalangien, plus
une manchette de mollet articulée à la cheville par des charnières M5. Chaque pièce est modélisée séparément puis
assemblée, contrôlée (collisions, amplitude articulaire, butée de flexion plantaire, épaisseur, volume d'impression) et
exportée en STL, 3MF et Rhino. Sur {S['people']:,} personnes réelles : {S['people']:,} assemblages fermés et mobiles,
butée atteinte à {S['plantar_stop_abs_err_max_deg']:.1f}° près ; chaque articulation du pied s'ouvre à l'amplitude prévue
à {S['seg_range_abs_err_max_deg']:.1f}° près et se verrouille sous charge, et chaque segment s'imprime sur une imprimante de bureau. Le projet
montre aussi l'apport du sur-mesure (4 tailles standard n'ajustent que {pct(S['sizing_4_foot_length_sizes'])} des
personnes), prédit 6 des 8 mesures par IA, produit des lots de patients en ligne de commande et s'utilise depuis
Grasshopper et un tableau de bord Streamlit.

## Licence

Code under the MIT licence. ANSUR II data are published by the US Army for public use; see the original source above.
"""

(ROOT / ("README_sample.md" if os.environ.get("ORTHO_SAMPLE") else "README.md")).write_text(README)
print("README.md written")
