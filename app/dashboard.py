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
from ortholab import data, export, geometry, mechanics, printability as pr  # noqa: E402
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


def mesh_figure(mesh, height=520):
    v, f = mesh.vertices, mesh.faces
    fig = go.Figure(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
                              color=TEAL, opacity=1.0, flatshading=False,
                              lighting=dict(ambient=0.45, diffuse=0.8, specular=0.25, roughness=0.6),
                              lightposition=dict(x=200, y=-300, z=500)))
    fig.update_layout(scene=dict(aspectmode="data", xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
                                 camera=dict(eye=dict(x=2.1, y=-1.9, z=1.0))),
                      margin=dict(l=0, r=0, t=0, b=0), height=height, paper_bgcolor="white")
    return fig


people, source = load_people()
summ, pop, cov, tol, asst, trim, stress = results()

st.markdown('<div class="kicker">MedTech · Computational design · 3D printing</div>', unsafe_allow_html=True)
st.title("Orthosis Param Lab")
st.caption(f"A printable ankle-foot orthosis generated from nine body measurements, checked before printing. "
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
        params = {
            "thickness": st.slider("Shell thickness (mm)", 2.0, 6.0, DESIGN["thickness"], 0.5),
            "clearance": st.slider("Liner clearance (mm)", 0.0, 6.0, DESIGN["clearance"], 0.5),
            "wrap_deg": st.slider("Leg wrap (deg)", 150, 240, int(DESIGN["wrap_deg"]), 10) * 1.0,
            "ankle_wrap_deg": st.slider("Ankle trimline (deg, lower = more flexible)", 100, 240, 200, 10) * 1.0,
            "vent_rows": st.slider("Ventilation rows", 0, 6, 4),
        }
    afo = build(tuple(meas.items()), tuple(params.items()))
    with right:
        st.plotly_chart(mesh_figure(afo), use_container_width=True)
        best = pr.best_orientation(afo, (400.0, 400.0, 400.0))
        I = mechanics.ankle_inertia(meas, params)
        c = st.columns(4)
        c[0].metric("Mass, PETG", f"{afo.volume / 1000 * DENSITY['PETG']:.0f} g")
        c[1].metric("Min. printer cube", f"{pr.min_cube_side(afo):.0f} mm")
        c[2].metric("Orientation (400 mm)", best["orientation"].replace("_", " ") if best else "does not fit")
        ref = summ.get("ankle_I_median", pop["ankle_I_mm4"].median() if pop is not None else I)
        c[3].metric("Ankle stiffness", f"{I / ref:.2f}×")
        st.caption("Stiffness is relative to the population median. Watertight: " + ("yes" if afo.is_watertight else "NO") +
                   f" · {len(afo.faces):,} triangles · stiffness is a beam-model ranking, not a bench result.")
        d1, d2, d3 = st.columns(3)
        buf = io.BytesIO()
        afo.export(buf, file_type="stl")
        d1.download_button("Download STL", buf.getvalue(), "afo.stl", use_container_width=True)
        buf3 = io.BytesIO()
        afo.export(buf3, file_type="3mf")
        d2.download_button("Download 3MF", buf3.getvalue(), "afo.3mf", use_container_width=True)
        with tempfile.TemporaryDirectory() as tmp:
            p = export.to_3dm(afo, Path(tmp) / "afo.3dm", meas, params)
            d3.download_button("Download for Rhino (.3dm)", p.read_bytes(), "afo.3dm", use_container_width=True)

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
