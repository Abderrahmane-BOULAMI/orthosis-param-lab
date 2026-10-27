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
The back of every section is aligned on one vertical line (y = 0); a real Achilles region is slightly forward of the
heel, which a scan would capture.

The shell is the exact normal offset of each ellipse, from `clearance` to `clearance + thickness`, over the posterior
`wrap_deg`. The footplate is the convex hull of the heel circle, the ball of the foot (measured position and breadth)
and a tapered toe, offset by clearance + thickness so its back edge meets the heel cup. Shell and plate are fused with
Manifold booleans, so every output is a closed, consistently oriented solid.

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
* Three orientations (standing, on its back, on its side); for each, the part is rotated about the vertical axis in
  5° steps to find a placement on the bed. Support area counts downward faces steeper than 45°.
* Mass from volume at 100 % density (PETG 1.27 g/cm3, PA12 1.01 g/cm3).

## Sizing study

Tolerances (mm): foot length 10, foot and heel breadth 6, ankle girth 10, calf girth 15, malleolus height 10,
tibial height 20. They are assumptions about what a liner, straps and heat moulding can absorb; the study reports
coverage from half to twice these values.
