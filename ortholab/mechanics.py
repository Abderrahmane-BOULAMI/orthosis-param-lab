"""Bending stiffness of the shell at the ankle, from the exact cross-section polygon.

The ankle section is where an AFO flexes when the foot pushes into dorsiflexion. For a thin shell the
flexural rigidity there is E * I, with I the second moment of area of the section about the
medio-lateral axis. This is a beam model: it ranks designs and people, it does not replace FEA or a bench test.
"""
import numpy as np

from .config import DESIGN
from .geometry import _arc, _wrap, limb_profile


def section_polygon(m, z, p=DESIGN):
    p = {**DESIGN, **p}
    prof = limb_profile(m, p)
    a, b = prof.at(max(z - p["thickness"], 0.0))
    w = float(_wrap(np.array([z]), prof, p)[0])
    half = np.radians(w) / 2
    th = np.linspace(-np.pi / 2 - half, -np.pi / 2 + half, 400)
    xo, yo = _arc(float(a), float(b), p["clearance"] + p["thickness"], th)
    xi, yi = _arc(float(a), float(b), p["clearance"], th[::-1])
    return np.r_[xo, xi], np.r_[yo, yi]


def polygon_moments(x, y):
    """Area, centroid and centroidal second moments (Ixx about the x axis) of a simple polygon."""
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cr = x * y1 - x1 * y
    A = cr.sum() / 2
    cx = ((x + x1) * cr).sum() / (6 * A)
    cy = ((y + y1) * cr).sum() / (6 * A)
    Ixx = ((y ** 2 + y * y1 + y1 ** 2) * cr).sum() / 12
    Iyy = ((x ** 2 + x * x1 + x1 ** 2) * cr).sum() / 12
    s = np.sign(A)
    A, Ixx, Iyy = abs(A), s * Ixx, s * Iyy
    return A, cx, cy, Ixx - A * cy ** 2, Iyy - A * cx ** 2


def ankle_inertia(m, p=DESIGN):
    """Second moment (mm^4) of the shell section at the minimum-girth ankle level."""
    p = {**DESIGN, **p}
    z = limb_profile(m, p).z_ankle
    x, y = section_polygon(m, z, p)
    return polygon_moments(x, y)[3]


def thickness_for(m, target_I, p=DESIGN, lo=1.0, hi=8.0):
    """Shell thickness that gives this person the target ankle stiffness (bisection)."""
    p = {**DESIGN, **p}
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if ankle_inertia(m, {**p, "thickness": mid}) < target_I:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
