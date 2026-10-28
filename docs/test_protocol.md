# Bench test protocol for the first printed prototypes

This is the plan for turning the model's predictions into measurements. No physical results are reported in this
repository yet; the protocol says what to measure, how, and what would prove the model wrong.

## 1. What the model predicts and what a test must confirm

| Prediction from the code | Test that confirms or refutes it |
|---|---|
| Wall thickness equals the parameter (median within 3 %) | Caliper at 12 marked points per part, after printing |
| Ankle stiffness ranks designs (thicker, wider trimline = stiffer) | Three-point bending of the ankle section, see 3 |
| A 120° ankle trimline gives about a tenth of the stiffness of 200° | Same bench, two parts differing only by trimline |
| Fit error comes mostly from the ankle and calf girths | Fit check on volunteers, see 4 |
| The hinge turns freely with 0.4 mm gap after printing | Assemble with M5 screws, turn by hand, see 5 |
| The plantar stop holds at the set angle (5°) | Goniometer on the assembled orthosis, see 5 |
| Foot section prints on a desktop printer | Print on a Bambu Lab printer from the exported 3MF |
| Foot joints open to their range (10°, 10°, 40°) and lock flat under load | Goniometer and standing load, see 5 |

## 2. Parts to print

* Median person, default parameters (3 mm, 200°), PETG, 100 % infill, printed on its back.
* Same person at 2 mm and 4 mm.
* Same person with a 120° ankle trimline.
* Same person with four rows of ventilation openings.
* Articulated version, median person, plantar stop 5°: foot section on a Bambu Lab desktop printer (Bambu Studio,
  PETG, 0.2 mm layers, on its back), calf cuff on a 400 mm printer, two M5 × 12 shoulder or button-head screws with nylon lock nuts.
* Bone-segment version, same person: four foot segments printed flat on the Bambu Lab, six M3 × 10 screws with
  nylon lock nuts for the Chopart, Lisfranc and MTP knuckles.

Record for each part: printer, nozzle, layer height, orientation, print time, mass on a scale. Compare mass with the
code's estimate (volume x 1.27 g/cm3); a gap above 10 % means infill or density assumptions are wrong.

## 3. Stiffness bench

Clamp the footplate, load the top of the shell backwards (dorsiflexion direction) with weights in 5 N steps up to 50 N,
measure the displacement of the top edge with a dial gauge. Stiffness = slope of force vs displacement in the linear part.

The beam model gives relative values only. The test passes if the measured ranking of the five parts matches the
predicted ranking and the 120° / 200° ratio is within a factor 2 of the prediction. Otherwise the beam model is not good
enough to choose thickness, and FEA (Abaqus shell model) becomes the next step.

## 4. Fit check

Take the nine measurements with a tape and an anthropometer on each volunteer, generate the orthosis, print it, and
record: gaps or pressure points (location, mm), donning time, comfort after 10 minutes of walking (0 to 10 scale).
Repeat the measurement twice by two people to know the measurement error before blaming the model.

## 5. Hinge and stop

Assemble the two parts with the screws finger-tight. Check that the discs turn without binding over the full range;
measure the play at the top of the cuff with a dial gauge. Fix the cuff, push the footplate into plantarflexion until
it stops and read the angle with a goniometer, three times. The test passes if the stop is within 2° of the setting
and the play under 1 mm at the top of the cuff. A stop that comes too late means the block needs to be stiffer
(thicker), not lower; a binding hinge means the 0.4 mm gap must grow for this printer.

For the bone-segment version, hold the hindfoot and lift each distal segment until it stops: Chopart and Lisfranc
should open 10° ± 2°, the toes 40° ± 3°. Then stand on the orthosis on a flat floor: the plate must stay flat
(no segment folding down by more than 3°), and a heel rise must roll over the MTP knuckles without binding.

## 6. What would change the design

* Pressure at the malleoli: increase `malleolus_relief`.
* Hinge axis felt off the ankle: adjust the medial malleolus offset (10 mm by default).
* Gaps at the calf: the calf height assumption (72 % of tibial height) is wrong for this person; measure it.
* Cracks at the heel corner: add a fillet between the plate and the heel cup.
