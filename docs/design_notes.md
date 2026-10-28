# Design notes and assumptions

## Geometry

The limb is a stack of ellipses. At each height the ellipse is set by a measured girth (perimeter, Ramanujan's second
approximation inverted by bisection) or a measured breadth, and a width/depth ratio.

| Height (from the sole) | Width | Depth | Source |
|---|---|---|---|
| 0 (heel) | heel breadth | heel breadth | measured |
| malleolus height | bimalleolar breadth | as at the ankle | measured |
| malleolus + 40 mm | ankle girth, ratio 1.05 | | girth measured, height **assumed** |
| 72 % of tibial height | calf girth, ratio 1.15 | | girth measured, height and ratio **assumed** |
| tibial height − 40 mm | 92 % of calf girth, ratio 1.15 | | **assumed** |

Between sections the half-axes follow a monotone cubic (PCHIP), so the leg never bulges between control points.

## Anatomy

* **Posterior line.** The back of each section sits on a line y0(z): the heel bulges 3 mm behind the reference at
  45 % of malleolus height, the Achilles tendon runs 9 mm in front of it from just above the malleoli to mid-calf,
  and the calf comes back to the reference. A scan replaces this line with the measured one.
* **Heel.** The bottom 12 mm of the heel cup is rounded with a quarter circle, so the shell follows the heel pad
  instead of ending in a sharp corner.
* **Malleoli.** The lateral malleolus sits at the measured malleolus height, the medial one 10 mm higher, as on most
  ankles. Each gets a Gaussian relief dome of 3 mm in the shell, so the bone never touches the plastic.
* **Footplate.** Outline from heel breadth, ball-of-foot position and foot breadth; a medial arch (ellipsoid, 6 mm)
  and side walls (14 mm, tapering forward) hold the foot in the plate.
* **Strap slots** near the top of the cuff take a standard 25 mm strap.

## Articulated version

The rigid shell is built first, then split into parts that are modelled and checked on their own:

| Part | Content | Printer |
|---|---|---|
| Foot section | footplate, heel cup, side uprights, inner hinge discs (r = 16 mm) | desktop (250 × 210 × 220 mm) |
| Calf cuff | leg shell above the ankle, strap slots, vents, side straps, outer discs (r = 17.5 mm), plantar stop | 400 mm format |
| Pins | one M5 screw and nut per side through a 5.3 mm hole (printed stand-in exported for previews) | bought |

* **Axis.** Medio-lateral, at the mean of the lateral and medial malleolus heights, centred on the ankle section.
  Discs are flat and coaxial, so they rotate on each other; every moving pair has a 0.4 mm print gap.
* **Clearances.** The lower part stops 4 mm below the axis except at the side uprights, the upper part starts
  R + 4 mm above it; the hinge window between them is what gives the free range of motion.
* **Range of motion.** The foot section is rotated about the axis and the intersection volume with the cuff is
  computed with Manifold; the first angle with more than 1 mm³ of overlap is the collision angle. Bisection finds it
  to 1° (0.25° in tests) and is checked against a one-degree sweep.
* **Plantarflexion stop.** A posterior block of the rigid shell grows down from the cuff. Its lower edge is found by
  bisection (12 steps) so the foot section stops at the target angle: 0° for a rigid-like ankle, 5° for drop foot,
  10° for a softer limit. Dorsiflexion stays free.

The shell is the exact normal offset of each ellipse, from `clearance` to `clearance + thickness`, over the posterior
`wrap_deg`. The footplate is the convex hull of the heel circle, the ball of the foot (measured position and breadth)
and a tapered toe, offset by clearance + thickness so its back edge meets the heel cup. Shell and plate are fused with
Manifold booleans, so every output is a closed, consistently oriented solid.

## Bone segments

The foot section can be split further, one printed part per functional bone group, following the Oxford and Rizzoli
multi-segment foot models used in gait analysis (26 separate bones would give parts too small to print or wear):

| Segment | Bones | Joint line | Position |
|---|---|---|---|
| hindfoot | calcaneus, talus | ankle (talocrural) | mean malleolus height |
| midfoot | navicular, cuboid, cuneiforms | Chopart (midtarsal) | `chopart_at` = 34 % of foot length from the heel |
| forefoot | metatarsals | Lisfranc (tarsometatarsal) | ball length − `metatarsal_length` (24 % of foot length) |
| toes | phalanges | metatarsophalangeal | through the first metatarsal head at the measured ball length, oblique by `mtp_obliquity` (20°, lateral side further back) |

The joint positions are **assumptions** scaled on foot length and ball length; a scan or an X-ray would place them
per patient.

* **Axis height.** Each axis is horizontal, `foot_knuckle_radius` (6 mm) above the plate top. Material below the axis
  separates when the distal segment turns up and closes at once when it turns down: the foot rolls over the toes at
  push-off and stays rigid under body weight. The lock angle is set by the 0.4 mm print gap (about 2.5°).
* **V notch.** Walls and arms above the axis lose a V of half-angle range/2 around the joint plane, so dorsiflexion
  stops at the designed range (`midfoot_range` 10° at Chopart and Lisfranc, `mtp_range` 40° at the toes, enough for
  toe-off).
* **Knuckles.** On each side, an inner knuckle (proximal segment) and an outer knuckle (distal segment) share the axis,
  each 3 mm thick with a 0.4 mm gap; an M3 screw (3.2 mm hole) joins them. The outer knuckle reaches its segment
  through a bridge that starts beyond the inner knuckle's radius plus the gap, so it never sweeps into it. Knuckles
  are placed beyond the widest point of both segments over the swept band, and zero-volume slivers left by coplanar
  booleans are removed.
* **Checks.** Each segment must be one closed solid. `joint_motion` turns the distal segment about its axis on the
  meshes and finds by bisection where it first overlaps the proximal one, in both directions.

## Why these choices

* **Measurements, not scans.** A clinic can take nine tape measurements in a few minutes; a scan gives a better
  shape. The generator takes a dictionary of numbers, so a scan-derived set can replace them without code changes.
* **Ellipses.** Few parameters, exact offsets, cheap to evaluate: 6,068 orthoses in minutes on a laptop.
* **Explicit assumptions.** Every height ANSUR does not measure is a named parameter in `config.DESIGN`.

## Stiffness model

The section at the minimum-girth ankle level is a thin open profile. Its second moment of area about the
medio-lateral axis is computed exactly from the polygon (Green's theorem). Multiplied by Young's modulus it gives the
flexural rigidity of a beam; the code reports it relative to a reference, because the absolute value depends on the
material and print settings. This ranks designs; it is not a substitute for FEA or a bench test
(see `test_protocol.md`).

## Printability

* Closed solid (watertight, positive volume), checked on every generated part.
* Wall thickness sampled by casting rays inwards from 300 to 400 random points on the side walls.
* Three orientations per part (standing, on its back, on its side); for each, the part is rotated about the vertical axis in
  5° steps to find a placement on the bed. Support area counts downward faces steeper than 45°.
* Mass from volume at 100 % density (PETG 1.27 g/cm3, PA12 1.01 g/cm3).

## Sizing study

Tolerances (mm): foot length 10, foot and heel breadth 6, ankle girth 10, calf girth 15, malleolus height 10,
tibial height 20. They are assumptions about what a liner, straps and heat moulding can absorb; the study reports
coverage from half to twice these values.
