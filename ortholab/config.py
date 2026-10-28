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
    "levels": 56,              # cross-sections along the leg
    "arc_points": 64,          # points per cross-section arc
    # anatomy (assumptions where ANSUR has no measurement; a scan replaces the leg part)
    "side": "right",           # which leg: the lateral malleolus is on +x for a right leg
    "heel_radius": 12.0,       # rounding of the heel pad where it meets the sole
    "heel_bulge": 3.0,         # how far the heel sits behind the Achilles line at its fullest
    "achilles_inset": 9.0,     # how far the Achilles tendon sits in front of the heel line
    "medial_offset": 10.0,     # medial malleolus centre above the lateral one
    "malleolus_relief": 3.0,   # extra clearance (dome) over each malleolus
    # footplate
    "arch_height": 6.0,        # medial longitudinal arch support
    "wall_height": 14.0,       # low medial and lateral walls along the heel and midfoot
    # articulated version
    "hinge_radius": 16.0,      # radius of the flat hinge discs
    "pin_diameter": 5.3,       # hole for an M5 pin or screw
    "print_gap": 0.4,          # clearance between moving parts printed apart
    # segmented foot: one printed part per functional bone group, hinged at the anatomical joint lines
    "chopart_at": 0.34,        # midtarsal (Chopart) joint, share of foot length from the heel
    "metatarsal_length": 0.24, # first metatarsal, share of foot length: Lisfranc joint = ball_length - this
    "mtp_obliquity": 20.0,     # metatarsophalangeal line, degrees from medio-lateral (lateral side further back)
    "midfoot_range": 10.0,     # dorsiflexion allowed at Chopart and Lisfranc, degrees
    "mtp_range": 40.0,         # toe dorsiflexion allowed at the MTP joint (toe-off), degrees
    "foot_knuckle_radius": 6.0,
    "foot_pin_diameter": 3.2,  # hole for an M3 pin or screw
    "strap_slots": True,       # strap slots in the calf cuff
}

# Printing assumptions
BED_MM = (250.0, 210.0, 220.0)     # build volume x, y, z of a common desktop FDM printer (configurable)
DENSITY = {"PETG": 1.27, "PA12": 1.01}  # g/cm3, typical datasheet values
OVERHANG_DEG = 45.0
