"""README banner and LinkedIn visual, composed from the hero render and summary.json."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
S = json.loads((ROOT / "results" / "summary.json").read_text())

TEAL, INK, MUTED, BG, RUST = "#00909C", "#14213D", "#5B6675", "#F4F8F9", "#C2410C"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def stats():
    return [
        (f"{S['people']:,}", "orthoses generated from\nreal body measurements"),
        (f"{S['watertight_share'] * 100:.0f} %", "closed, printable solids\n(watertight, checked)"),
        (f"{S['sizing_4_foot_length_sizes'] * 100:.0f} %", "of people fit 4 standard\nsizes within tolerance"),
    ]


def compose(W, H, path, hero_h, title_size, pad, stack=False):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    hero = Image.open(FIG / "hero.png")
    s = hero_h / hero.height
    hero = hero.resize((int(hero.width * s), hero_h), Image.LANCZOS)
    if stack:   # square visual: hero bottom right, text top left
        img.paste(hero, ((W - hero.width) // 2, H - hero_h - int(pad * 1.6)), hero)
    else:
        img.paste(hero, (W - hero.width - pad, (H - hero_h) // 2), hero)
    x, y = pad, pad
    d.text((x, y), "MEDTECH · COMPUTATIONAL DESIGN · 3D PRINTING", font=font(int(title_size * 0.32), True), fill=TEAL)
    y += int(title_size * 0.7)
    d.text((x, y), "Orthosis Param Lab", font=font(title_size, True), fill=INK)
    y += int(title_size * 1.25)
    d.text((x, y), "A printable ankle-foot orthosis from nine body\nmeasurements, checked before it reaches the printer.",
           font=font(int(title_size * 0.42)), fill=MUTED, spacing=8)
    y += int(title_size * 1.45)
    for big, small in stats():
        d.text((x, y), big, font=font(int(title_size * 0.75), True), fill=TEAL)
        d.text((x + int(title_size * 2.6), y + 4), small, font=font(int(title_size * 0.32)), fill=INK, spacing=4)
        y += int(title_size * 1.05)
    d.text((x, H - pad - int(title_size * 0.35)), "Python · trimesh · Manifold · Rhino .3dm · scikit-learn · Streamlit",
           font=font(int(title_size * 0.3)), fill=MUTED)
    img.save(path)


if __name__ == "__main__":
    compose(1600, 640, FIG / "banner.png", hero_h=560, title_size=62, pad=56)
    compose(1200, 1200, FIG / "linkedin.png", hero_h=560, title_size=58, pad=60, stack=True)
    print("banner and LinkedIn visual written")
