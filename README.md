<p align="center"><img src="docs/figures/banner.png" alt="Orthosis Param Lab" width="100%"></p>

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

The lab answers four questions a MedTech product team meets every day, on the real measurements of 6,068 people:

1. **Can a printable, articulated AFO be generated from a handful of measurements?** Yes: **6,068 / 6,068** assemblies built with closed parts, zero overlap at rest and a hinge that turns freely, in about 0.9 s each.
2. **Do the joints behave as prescribed?** The ankle's plantarflexion stop (for example 5° for drop foot) is reached within **0.6°** for every person tested; each foot joint opens to its designed range within **0.8°** and locks flat under load.
3. **Is made-to-measure worth it?** Four standard sizes fit **20 %** of people within tolerance; the generator fits everyone by construction.
4. **How fast can a clinic measure?** From foot length, height, weight and sex, a LightGBM model predicts **six of the eight** fit measurements; taping ankle and calf completes the set.

## Results at a glance

| Question | Result on 6,068 people (ANSUR II) |
|---|---|
| Bone-segment foot (150 people drawn at random) | **100 %** of segments one closed part, zero overlap at rest; Chopart and Lisfranc open 10°, MTP 40° (designed 10° and 40°), every joint locks under load within 2.6°; **100 %** of segments fit a desktop printer |
| Articulated orthoses generated | **6,068 / 6,068**, both parts closed solids (100 %), overlap at rest ≤ 0.0 mm³, median **0.9 s** each |
| Free ankle motion (hinge only, no stop) | dorsiflexion ≥ **50°** for everyone; plantarflexion median **34°**, 5th percentile 30° |
| Plantarflexion stop, set to 0°, 5° or 10° | 60 people × 3 settings: mean error **0.3°**, max 0.6°, 100 % closed parts |
| Printing the parts | foot section fits a 250 × 210 × 220 mm desktop printer for **94 %** of people; calf cuff fits a 400 mm printer for 100 % |
| Mass of the assembly in PETG, 100 % infill | median 407 g |
| One-piece rigid version, same generator | 100 % watertight, median **249 ms** each |
| Stress test: extreme bodies × design variants | 105 parts (75 one-piece, 30 articulated), 100 % watertight; one-piece shells measure ≥ 88 % of the target wall (5th percentile of ray samples) |
| People within tolerance with 4 foot-length sizes | **20 %** (12 sizes: 31 %; 40 best-case multi-dimension sizes: 56 %) |
| Thickness that gives everyone the median stiffness | **2.3 to 3.9 mm** (5th to 95th percentile) |
| Ankle trimline 120° instead of 200° | **0.10×** the stiffness (beam model) |
| Measurements predicted for unseen people (LightGBM) | heel to ball 98 %, ankle breadth 95 %, malleolus height 96 %, heel breadth 84 % within tolerance |
| Fit from a leg scan | gap 2.96 to 3.07 mm for a 3 mm liner target, no contact point |

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
| midfoot | navicular, cuboid, cuneiforms | Chopart (midtarsal) | 34 % of foot length | 10° |
| forefoot | metatarsals | Lisfranc (tarsometatarsal) | ball length − 24 % of foot length | 10° |
| toes | phalanges | metatarsophalangeal, oblique line (20°) | measured ball of the foot | 40° |

* **Locks under load, rolls at push-off.** Each axis sits just above the footplate. The plate below the axis opens
  when the distal segment turns up, so the foot rolls over the toes; it closes at once when the segment turns down,
  so the plate stays rigid under body weight (measured lock within 2.6°, the print gap).
* **Range set by a V notch.** The side walls above the axis get a V notch whose angle is the allowed dorsiflexion;
  the range measured on the meshes matches the design within 0.8°.
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

Sizes are designed on one half of the survey and judged on the other half (3,029 people).
A person fits only if foot length, foot and heel breadth, ankle and calf girth, malleolus and tibial height are all
within tolerance. Even 40 sizes clustered on all seven dimensions leave most people out, which is exactly where a
parametric generator pays off. `results/sizing_tolerance.csv` reports coverage from half to twice the tolerances.

## Faster measuring

<p align="center"><img src="docs/figures/assistant.png" alt="Measurement assistant" width="85%"></p>

Four models (median by sex, linear regression, a small neural network, LightGBM) predict eight measurements from
foot length, height, weight and sex, trained on 75 % of people and tested on the 25 % they never saw. Lengths and
breadths come out within a few millimetres (mean error 3.9 mm for malleolus height,
2.4 mm for ankle breadth), so the clinic protocol is short: four quick inputs, two tape
girths, and the generator does the rest.

## Stiffness and trimline

<p align="center"><img src="docs/figures/stiffness.png" alt="Stiffness study" width="95%"></p>

With the same 3 mm shell for everyone, ankle stiffness varies 1.8× between the 5th and 95th
percentile, because it follows the size of the ankle; solving the thickness per person gives everyone the same
stiffness. The trimline is the main design knob: cutting the shell from 200° to 120° around the ankle leaves about a
tenth of the stiffness, which is how a rigid AFO becomes a flexible leaf spring.

## Printing

<p align="center"><img src="docs/figures/build_volume.png" alt="Build volume needed" width="85%"></p>

Splitting at the ankle is what makes desktop printing possible: the one-piece AFO needs a 382 mm cube for the
median person, while the articulated foot section fits a 250 × 210 × 220 mm desktop printer (such as a Bambu Lab)
for 94 % of people. The code reports orientation and support area for each part.

## Scan-ready

<p align="center"><img src="docs/figures/scan_fit.png" alt="Scan versus tape fit" width="85%"></p>

When a scan is available, the leg sections and the posterior line come from the scan itself. On a test leg whose calf
is lower and flatter than average, the scan-based shell keeps the 3 mm liner clearance everywhere it was measured
(gap 2.96 to 3.07 mm), while the heel and malleoli stay on the tape measurements.

```python
from ortholab import articulated, scan
prof = scan.profile_from_scan(leg_scan_mesh, measures)          # scan in mm, z up from the sole
parts = articulated.build_articulated(measures, {"plantar_stop_deg": 5}, profile=prof)
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
python experiments/run_all.py            # all 6,068 people: downloads ANSUR II once, checks SHA-256
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
exportée en STL, 3MF et Rhino. Sur 6,068 personnes réelles : 6,068 assemblages fermés et mobiles,
butée atteinte à 0.6° près ; chaque articulation du pied s'ouvre à l'amplitude prévue
à 0.8° près et se verrouille sous charge, et chaque segment s'imprime sur une imprimante de bureau. Le projet
montre aussi l'apport du sur-mesure (4 tailles standard n'ajustent que 20 % des
personnes), prédit 6 des 8 mesures par IA, produit des lots de patients en ligne de commande et s'utilise depuis
Grasshopper et un tableau de bord Streamlit.

## Licence

Code under the MIT licence. ANSUR II data are published by the US Army for public use; see the original source above.
