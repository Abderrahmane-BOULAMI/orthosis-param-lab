"""Paths, data source and default design parameters."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLE_DIR = DATA_DIR / "sample"
RESULTS = ROOT / "results"
FIGURES = ROOT / "docs" / "figures"
OUTPUTS = ROOT / "outputs"

# ANSUR II public working databases (US Army, 2012). Original: https://www.openlab.psu.edu/ansur2/
# Pulled from a GitHub mirror pinned to one commit; files are checked against their SHA-256.
MIRROR = "https://raw.githubusercontent.com/senihberkay/US-Army-ANSUR-II/da756f4cf2561eb049459232f5fe376f214f8c0a/"
FILES = {
    "ANSUR II MALE Public.csv": "0547aea0170e5293de519389981135e75803f02e6d40c77ace740decc0caac64",
    "ANSUR II FEMALE Public.csv": "ed7e800aa97a4d42f8286b988be2fe1883a2e789588169db959864b707d1757a",
}

# ANSUR column -> name used in this project (all lengths in mm)
COLUMNS = {
    "footlength": "foot_length",
    "footbreadthhorizontal": "foot_breadth",
    "heelbreadth": "heel_breadth",
    "balloffootlength": "ball_length",
    "anklecircumference": "ankle_circ",
    "calfcircumference": "calf_circ",
    "lateralmalleolusheight": "malleolus_height",
    "bimalleolarbreadth": "bimalleolar_breadth",
    "tibialheight": "tibial_height",
    "stature": "stature",
    "weightkg": "weight_kg",
}
MEASURES = ["foot_length", "foot_breadth", "heel_breadth", "ball_length", "ankle_circ",
            "calf_circ", "malleolus_height", "bimalleolar_breadth", "tibial_height"]

# Default design parameters (mm unless stated). Every value is an assumption you can change.
DESIGN = {
    "thickness": 3.0,          # shell and footplate thickness
    "clearance": 3.0,          # gap for a liner / sock, added to the limb surface
    "wrap_deg": 200.0,         # posterior wrap angle of the leg shell
    "top_below_tibiale": 40.0, # trimline below the tibial plateau (clears the fibular head)
    "calf_level": 0.72,        # calf girth assumed at 72 % of tibial height (not measured in ANSUR)
    "calf_ratio": 1.15,        # width / depth of the calf cross-section (assumption)
    "plate_length": 0.95,      # footplate length as a share of foot length
    "vent_rows": 0,            # ventilation holes in the calf shell (0 = solid)
    "levels": 36,              # cross-sections along the leg
    "arc_points": 48,          # points per cross-section arc
}

# Printing assumptions
BED_MM = (250.0, 210.0, 220.0)     # build volume x, y, z of a common desktop FDM printer (configurable)
DENSITY = {"PETG": 1.27, "PA12": 1.01}  # g/cm3, typical datasheet values
OVERHANG_DEG = 45.0
