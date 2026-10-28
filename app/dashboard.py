"""Orthosis Param Lab: design an AFO from nine measurements and see why made-to-measure matters."""
import io
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ortholab import articulated as ar, data, export, geometry, mechanics, printability as pr, segmented as sg  # noqa: E402
from ortholab.config import DENSITY, DESIGN, MEASURES  # noqa: E402

TEAL, INK, SOFT, RUST, GREY = "#00909C", "#14213D", "#E6F4F5", "#C2410C", "#8A96A3"
LABELS = {"foot_length": "Foot length", "foot_breadth": "Foot breadth", "heel_breadth": "Heel breadth",
          "ball_length": "Heel to ball of foot", "ankle_circ": "Ankle girth", "calf_circ": "Calf girth",
          "malleolus_height": "Malleolus height", "bimalleolar_breadth": "Ankle breadth (malleoli)",
          "tibial_height": "Tibial height"}

st.set_page_config(page_title="Orthosis Param Lab", page_icon="🦶", layout="wide")
st.markdown(f"""<style>
.block-container {{padding-top: 1.6rem; max-width: 1250px;}}
h1, h2, h3 {{color: {INK}; letter-spacing: -0.01em;}}
div[data-testid="stMetric"] {{background: {SOFT}; border-radius: 12px; padding: 10px 14px;}}
div[data-testid="stMetricValue"] {{color: {TEAL};}}
.kicker {{color: {TEAL}; font-weight: 700; letter-spacing: .08em; font-size: .78rem; text-transform: uppercase;}}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load_people():
    try:
        return data.load(), "6,068 people (ANSUR II)"
    except Exception:
        return data.load(sample=True), "300-person extract"


def results_dir():
    full = ROOT / "results"
    return full if (full / "summary.json").exists() else full / "sample"


@st.cache_data
def results():
    d = results_dir()
    read = lambda n: pd.read_csv(d / n) if (d / n).exists() else None  # noqa: E731
    summ = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else {}
    return summ, read("population.csv"), read("sizing_coverage.csv"), read("sizing_tolerance.csv"), \
        read("assistant_errors.csv"), read("stiffness_trimline.csv"), read("stress_test.csv")


@st.cache_resource
def build(meas, params):
    return geometry.build_afo(dict(meas), dict(params))


@st.cache_resource
def build_art(meas, params):
    P = ar.build_articulated(dict(meas), dict(params))
    return P, ar.range_of_motion_fast(P)


@st.cache_resource
def build_seg(meas, params):
    P = sg.build_segmented(dict(meas), dict(params))
    return P, ar.range_of_motion_fast(P), sg.joint_motion(P)


NAVY = "#335C9E"
SEG_HEX = {"hindfoot": TEAL, "midfoot": "#E3A33B", "forefoot": "#D9644A", "toes": "#7E6BB5"}


def mesh_figure(mesh, height=520, extra=()):
    traces = []
    for m_, col in [(mesh, TEAL), *extra]:
        v, f = m_.vertices, m_.faces
        traces.append(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                                color=col, opacity=1.0, flatshading=False,
                                lighting=dict(ambient=0.45, diffuse=0.8, specular=0.25, roughness=0.6),
                                lightposition=dict(x=200, y=-300, z=500)))
    fig = go.Figure(traces)
    fig.update_layout(scene=dict(aspectmode="data", xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
                                 camera=dict(eye=dict(x=2.1, y=-1.9, z=1.0))),
                      margin=dict(l=0, r=0, t=0, b=0), height=height, paper_bgcolor="white")
    return fig


people, source = load_people()
summ, pop, cov, tol, asst, trim, stress = results()

st.markdown('<div class="kicker">MedTech · Computational design · 3D printing</div>', unsafe_allow_html=True)
st.title("Orthosis Param Lab")
st.caption(f"An articulated ankle-foot orthosis generated from nine body measurements, one printed part per bone group, "
           f"checked before printing. "
           f"Body data: {source}. Every shape assumption is listed in the README.")

tab_design, tab_fit, tab_assist, tab_pop = st.tabs(
    ["Design an orthosis", "Why made-to-measure", "Measurement assistant", "Population checks"])

with tab_design:
    left, right = st.columns([1, 2.1], gap="large")
    with left:
        mode = st.radio("Measurements", ["Pick a person from the survey", "Type them in"], horizontal=True)
        if mode.startswith("Pick"):
            idx = st.number_input("Person index", 0, len(people) - 1, int(len(people) // 2))
            meas = {k: float(people.loc[idx, k]) for k in MEASURES}
            st.dataframe(pd.DataFrame({"mm": meas}).rename(index=LABELS), use_container_width=True)
        else:
            med = people[MEASURES].median()
            meas = {k: float(st.number_input(LABELS[k], value=float(med[k]), step=1.0)) for k in MEASURES}
        st.markdown("**Design parameters**")
        build_mode = st.radio("Build", ["Bone segments", "Two parts", "One piece"], horizontal=True,
                              help="Bone segments: hindfoot, midfoot, forefoot and toes, pinned at the Chopart, Lisfranc "
                                   "and MTP joints, plus the ankle hinge. Two parts: foot section and calf cuff hinged "
                                   "at the ankle. One piece: rigid AFO.")
        articulated = build_mode != "One piece"
        segmented = build_mode == "Bone segments"
        params = {
            "thickness": st.slider("Shell thickness (mm)", 2.0, 6.0, DESIGN["thickness"], 0.5),
            "clearance": st.slider("Liner clearance (mm)", 0.0, 6.0, DESIGN["clearance"], 0.5),
            "malleolus_relief": st.slider("Malleolus relief (mm)", 0.0, 6.0, DESIGN["malleolus_relief"], 0.5),
            "arch_height": st.slider("Arch support height (mm)", 0.0, 12.0, DESIGN["arch_height"], 1.0),
            "vent_rows": st.slider("Ventilation rows", 0, 5, 3),
            "side": st.radio("Leg", ["right", "left"], horizontal=True),
        }
        if articulated:
            use_stop = st.checkbox("Plantarflexion stop (drop-foot setting)", value=True)
            params["plantar_stop_deg"] = float(st.slider("Stop angle (deg)", 0, 20, 5)) if use_stop else None
            angle = st.slider("Move the ankle: plantarflexion < 0 < dorsiflexion (deg)", -30, 30, 0)
            if segmented:
                params["mtp_range"] = float(st.slider("Toe joint (MTP) range (deg)", 20, 60, int(DESIGN["mtp_range"]), 5))
                params["midfoot_range"] = float(st.slider("Chopart and Lisfranc range (deg)", 0, 20,
                                                          int(DESIGN["midfoot_range"]), 2))
                roll = st.slider("Roll over the toes (share of each foot joint's range)", 0.0, 1.0, 0.0, 0.1)
        else:
            params["ankle_wrap_deg"] = st.slider("Ankle trimline (deg, lower = more flexible)", 100, 240, 200, 10) * 1.0
    with right:
        if segmented:
            P, rom, motion = build_seg(tuple(meas.items()), tuple(params.items()))
            stop = rom["plantarflexion_deg"]
            shown = max(-stop, angle)
            Q = sg.pose(P, [roll * r["range_deg"] for r in motion], ankle_deg=shown)
            extra = [(Q[k], SEG_HEX[k]) for k in ("midfoot", "forefoot", "toes")]
            extra += [(P["upper"], NAVY), (P["pins"], "#9AA0A6"), (Q["foot_pins"], "#9AA0A6")]
            st.plotly_chart(mesh_figure(Q["hindfoot"], extra=extra), use_container_width=True)
            segs = P["segments"]
            c = st.columns(4)
            c[0].metric("Mass, PETG", f"{(sum(v.volume for v in segs.values()) + P['upper'].volume) / 1000 * DENSITY['PETG']:.0f} g")
            c[1].metric("Plantarflexion stop", f"{stop:.1f}°")
            mtp = [r for r in motion if r["joint"] == "mtp"][0]
            c[2].metric("Toe joint opens to", f"{mtp['dorsiflexion_deg']:.0f}°")
            fits = all(pr.best_orientation(v, (250.0, 210.0, 220.0)) is not None for v in segs.values())
            c[3].metric("Foot segments on a desktop printer", "all fit" if fits else "check")
            st.dataframe(pd.DataFrame([{"joint": {"chopart": "Chopart", "lisfranc": "Lisfranc", "mtp": "MTP"}[r["joint"]],
                                        "designed range (°)": r["range_deg"], "measured opening (°)": r["dorsiflexion_deg"],
                                        "locks under load at (°)": r["plantarflexion_deg"],
                                        "overlap at rest (mm³)": round(r["rest_overlap_mm3"], 2)} for r in motion]),
                         hide_index=True, use_container_width=True)
            st.caption("Segments: hindfoot (calcaneus, talus), midfoot (navicular, cuboid, cuneiforms), forefoot "
                       "(metatarsals), toes (phalanges). Every angle is measured by turning the parts about their axes "
                       "on the real meshes." + (f" Ankle shown at {shown:.0f}° (held by the stop)." if shown != angle else ""))
            cols = st.columns(3)
            with tempfile.TemporaryDirectory() as tmp:
                export.export_articulated(P, tmp, "afo", meas)
                import zipfile
                zbuf = io.BytesIO()
                with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
                    for f in sorted(Path(tmp).glob("afo_*.stl")):
                        z.write(f, f.name)
                cols[0].download_button("All parts, STL (zip)", zbuf.getvalue(), "afo_parts_stl.zip", use_container_width=True)
                cols[1].download_button("Assembly 3MF", (Path(tmp) / "afo_assembly.3mf").read_bytes(), "afo_assembly.3mf",
                                        use_container_width=True)
                cols[2].download_button("Assembly for Rhino", (Path(tmp) / "afo_assembly.3dm").read_bytes(),
                                        "afo_assembly.3dm", use_container_width=True)
        elif articulated:
            P, rom = build_art(tuple(meas.items()), tuple(params.items()))
            stop = rom["plantarflexion_deg"]
            shown = max(-stop, angle)                       # the stop holds the foot like the real part would
            lower = ar.rotate_about_axis(P["lower"], P["joint"], shown)
            st.plotly_chart(mesh_figure(lower, extra=[(P["upper"], NAVY), (P["pins"], "#9AA0A6")]),
                            use_container_width=True)
            c = st.columns(4)
            c[0].metric("Mass, PETG", f"{(P['lower'].volume + P['upper'].volume) / 1000 * DENSITY['PETG']:.0f} g")
            c[1].metric("Free dorsiflexion", f"{rom['dorsiflexion_deg']:.0f}°+" if rom["dorsiflexion_deg"] >= 50 else f"{rom['dorsiflexion_deg']:.0f}°")
            c[2].metric("Plantarflexion stop", f"{stop:.1f}°")
            fits = pr.best_orientation(P["lower"], (250.0, 210.0, 220.0)) is not None
            c[3].metric("Foot section on a desktop printer", "fits" if fits else "too big")
            st.caption(f"Both parts watertight: {'yes' if P['lower'].is_watertight and P['upper'].is_watertight else 'NO'}"
                       f" · overlap at rest {rom['rest_overlap_mm3']:.2f} mm³ · motion limits measured by turning the foot"
                       " section about the ankle axis on the real meshes."
                       + (f" Shown at {shown:.0f}° (held by the stop)." if shown != angle else ""))
            d1, d2, d3, d4 = st.columns(4)
            for col, key, label, fname in ((d1, "lower", "Foot section STL", "foot_section.stl"),
                                           (d2, "upper", "Calf cuff STL", "calf_cuff.stl")):
                buf = io.BytesIO()
                P[key].export(buf, file_type="stl")
                col.download_button(label, buf.getvalue(), fname, use_container_width=True)
            with tempfile.TemporaryDirectory() as tmp:
                export.export_articulated(P, tmp, "afo", meas)
                d3.download_button("Assembly 3MF", (Path(tmp) / "afo_assembly.3mf").read_bytes(), "afo_assembly.3mf",
                                   use_container_width=True)
                d4.download_button("Assembly for Rhino", (Path(tmp) / "afo_assembly.3dm").read_bytes(),
                                   "afo_assembly.3dm", use_container_width=True)
        else:
            afo = build(tuple(meas.items()), tuple(params.items()))
            st.plotly_chart(mesh_figure(afo), use_container_width=True)
            best = pr.best_orientation(afo, (400.0, 400.0, 400.0))
            I = mechanics.ankle_inertia(meas, params)
            c = st.columns(4)
            c[0].metric("Mass, PETG", f"{afo.volume / 1000 * DENSITY['PETG']:.0f} g")
            c[1].metric("Min. printer cube", f"{pr.min_cube_side(afo):.0f} mm")
            c[2].metric("Orientation (400 mm)", best["orientation"].replace("_", " ") if best else "does not fit")
            ref = pop["ankle_I_mm4"].median() if pop is not None else I
            c[3].metric("Ankle stiffness", f"{I / ref:.2f}×")
            st.caption("Stiffness is relative to the population median. Watertight: " + ("yes" if afo.is_watertight else "NO") +
                       f" · {len(afo.faces):,} triangles · stiffness is a beam-model ranking.")
            d1, d2, d3 = st.columns(3)
            buf = io.BytesIO()
            afo.export(buf, file_type="stl")
            d1.download_button("Download STL", buf.getvalue(), "afo.stl", use_container_width=True)
            buf3 = io.BytesIO()
            afo.export(buf3, file_type="3mf")
            d2.download_button("Download 3MF", buf3.getvalue(), "afo.3mf", use_container_width=True)
            with tempfile.TemporaryDirectory() as tmp:
                p_ = export.to_3dm(afo, Path(tmp) / "afo.3dm", meas, params)
                d3.download_button("Download for Rhino (.3dm)", p_.read_bytes(), "afo.3dm", use_container_width=True)

with tab_fit:
    st.subheader("Standard sizes leave most people outside tolerance")
    st.write("Sizes are designed on half of the survey and tested on the other half. A person fits a size only if "
             "foot length, foot and heel breadth, ankle and calf girth, malleolus and tibial height are all within tolerance.")
    if cov is not None:
        a, b = st.columns([1.4, 1])
        fig = go.Figure()
        fig.add_scatter(x=cov["sizes"], y=cov["foot_length_sizing"] * 100, mode="lines+markers", name="Sizes cut on foot length",
                        line=dict(color=GREY, width=2))
        fig.add_scatter(x=cov["sizes"], y=cov["multi_dim_sizing"] * 100, mode="lines+markers", name="Best-case sizes (k-means, all dimensions)",
                        line=dict(color=TEAL, width=2))
        fig.add_hline(y=100, line_dash="dot", line_color=INK, annotation_text="Made-to-measure: every person by construction")
        fig.update_layout(xaxis_title="Number of standard sizes", yaxis_title="People who fit (%)", yaxis_range=[0, 105],
                          height=420, margin=dict(t=20), legend=dict(orientation="h", y=-0.25), plot_bgcolor="white")
        a.plotly_chart(fig, use_container_width=True)
        b.markdown("**Sensitivity to the tolerance**")
        b.dataframe((tol.set_index("tolerance_x") * 100).round(1).rename(columns=lambda c: c.replace("_", " ") + " (%)"),
                    use_container_width=True)
        if summ.get("sizing_miss_by_dim_4_sizes"):
            miss = pd.Series(summ["sizing_miss_by_dim_4_sizes"]).rename(index=LABELS) * 100
            b.markdown("**With 4 shoe-size based sizes, share of people missed on each dimension**")
            b.bar_chart(miss.sort_values(), color=TEAL, horizontal=True)

with tab_assist:
    st.subheader("Which measurements can a model fill in, and which need the tape?")
    st.write("Inputs: foot length, height, weight and sex. Models are trained on 75 % of people and judged on the 25 % they never saw.")
    if asst is not None:
        piv = asst.pivot(index="target", columns="model", values="within_tol").rename(index=LABELS) * 100
        st.dataframe(piv.style.format("{:.0f} %").background_gradient(cmap="BuGn", axis=None), use_container_width=True)
        mae = asst.pivot(index="target", columns="model", values="mae_mm").rename(index=LABELS)
        st.caption("Share of unseen people predicted within tolerance (%). Mean absolute error (mm) below.")
        st.dataframe(mae.round(1), use_container_width=True)
    if summ.get("protocol_all_within_tol"):
        p = summ["protocol_all_within_tol"]
        c = st.columns(2)
        c[0].metric("Every predicted dimension in tolerance, quick inputs only", f"{p['A_quick_only'] * 100:.0f} %")
        c[1].metric("Same, after taping ankle and calf girth", f"{p['B_quick_plus_two_girths'] * 100:.0f} %")

with tab_pop:
    st.subheader("Every person in the survey, generated and checked")
    if pop is not None:
        c = st.columns(4)
        c[0].metric("Orthoses generated", f"{len(pop):,}")
        c[1].metric("Watertight", f"{pop['watertight'].mean() * 100:.1f} %")
        c[2].metric("Median generation time", f"{pop['gen_s'].median() * 1000:.0f} ms")
        c[3].metric("Fit a 400 mm printer", f"{pop['fits_large'].mean() * 100:.0f} %")
        if "art_watertight" in pop:
            st.markdown("**Articulated version, every person**")
            c = st.columns(4)
            c[0].metric("Both parts closed and separate", f"{(pop['art_watertight'] & (pop['art_rest_overlap_mm3'] < 1)).mean() * 100:.1f} %")
            c[1].metric("Free plantarflexion, median", f"{pop['art_plantar_free_deg'].median():.0f}°")
            c[2].metric("Free dorsiflexion, minimum", f"{pop['art_dorsi_free_deg'].min():.0f}°")
            c[3].metric("Foot section fits a desktop printer", f"{pop['art_lower_fits_desktop'].mean() * 100:.0f} %")
        if summ.get("seg_people"):
            st.markdown(f"**Bone segments, {summ['seg_people']} people drawn at random**")
            c = st.columns(4)
            c[0].metric("Every segment one closed part", f"{summ['seg_closed_share'] * 100:.0f} %")
            c[1].metric("Joint range reached, worst error", f"{summ['seg_range_abs_err_max_deg']:.1f}°")
            c[2].metric("Joints lock under load within", f"{summ['seg_locked_max_deg']:.1f}°")
            c[3].metric("Every segment fits a desktop printer", f"{summ['seg_fit_desktop_share'] * 100:.0f} %")
        a, b = st.columns(2)
        h1 = go.Figure(go.Histogram(x=pop["min_cube_mm"], marker_color=TEAL, nbinsx=40))
        h1.add_vline(x=250, line_dash="dot", annotation_text="250 mm desktop")
        h1.add_vline(x=400, line_dash="dot", annotation_text="400 mm large format")
        h1.update_layout(title="Smallest cubic build volume needed", xaxis_title="mm", height=340, plot_bgcolor="white")
        a.plotly_chart(h1, use_container_width=True)
        h2 = go.Figure(go.Histogram(x=pop["thickness_equal_stiffness"], marker_color=RUST, nbinsx=40))
        h2.update_layout(title="Thickness giving everyone the median ankle stiffness", xaxis_title="mm", height=340,
                         plot_bgcolor="white")
        b.plotly_chart(h2, use_container_width=True)
    if trim is not None:
        f = go.Figure(go.Scatter(x=trim["ankle_wrap_deg"], y=trim["relative_stiffness"], mode="lines+markers",
                                 line=dict(color=TEAL, width=2)))
        f.update_layout(title="Ankle trimline vs stiffness (median person, 200° = 1)", xaxis_title="wrap at the ankle (deg)",
                        yaxis_title="relative stiffness", height=330, plot_bgcolor="white")
        st.plotly_chart(f, use_container_width=True)
    if stress is not None:
        st.markdown("**Stress test**: people at the minimum and maximum of each measurement, five design variants each")
        st.dataframe(stress.groupby("variant").agg(cases=("watertight", "size"), watertight=("watertight", "mean"),
                                                   wall_p05_mm=("wall_p05", "min"), target_mm=("target_t", "first")).round(2),
                     use_container_width=True)
