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

## 2. Parts to print

* Median person, default parameters (3 mm, 200°), PETG, 100 % infill, printed on its back.
* Same person at 2 mm and 4 mm.
* Same person with a 120° ankle trimline.
* Same person with four rows of ventilation openings.

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

## 5. What would change the design

* Pressure at the malleoli: increase local clearance there (a parameter to add).
* Gaps at the calf: the calf height assumption (72 % of tibial height) is wrong for this person; measure it.
* Cracks at the heel corner: add a fillet between the plate and the heel cup.
