import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import time

# ─────────────────────────────────────────────
# Configuration / Constants
# ─────────────────────────────────────────────
NOMINAL_DIAMETER_MM = 50.0   # mm — reference diameter
NOISE_STD_MM        = 0.002  # mm — simulated sensor noise
ANGLE_STEP_DEG      = 10     # degrees between measurement points

st.set_page_config(page_title="Laser Bore Gauge", layout="wide")

# ─────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────
if "scan_data"    not in st.session_state: st.session_state["scan_data"]    = None
if "scan_history" not in st.session_state: st.session_state["scan_history"] = []
if "scan_count"   not in st.session_state: st.session_state["scan_count"]   = 0

# ─────────────────────────────────────────────
# Sidebar — Configuration
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    nominal_dia   = st.number_input("Nominal Diameter (mm)", value=NOMINAL_DIAMETER_MM, step=0.1, format="%.3f")
    tol_ovality   = st.number_input("Ovality Tolerance (mm)", value=0.003, step=0.001, format="%.4f")
    tol_taper     = st.number_input("Taper Tolerance (mm)",   value=0.005, step=0.001, format="%.4f")
    tol_diameter  = st.number_input("Diameter Tolerance ± (mm)", value=0.010, step=0.001, format="%.4f")

    st.divider()
    st.caption("Simulation Settings")
    noise_std = st.slider("Simulated Noise Std Dev (mm)", 0.001, 0.010, NOISE_STD_MM, step=0.001)

    if st.button("🗑️ Clear History"):
        st.session_state["scan_history"] = []
        st.session_state["scan_data"]    = None
        st.session_state["scan_count"]   = 0
        st.rerun()

# ─────────────────────────────────────────────
# Core Scan Function
# ─────────────────────────────────────────────
def run_scan(nominal: float, noise: float) -> dict:
    """Simulate a bore scan and return structured results."""
    angles   = np.arange(0, 360, ANGLE_STEP_DEG)
    diameter = nominal + np.random.normal(0, noise, len(angles))

    mean_dia = float(np.mean(diameter))
    ovality  = float((np.max(diameter) - np.min(diameter)) / 2)   # industry standard
    taper    = float(np.max(diameter) - np.min(diameter))
    deviation = mean_dia - nominal

    return {
        "angles":    angles.tolist(),
        "diameter":  diameter.tolist(),
        "mean_dia":  mean_dia,
        "ovality":   ovality,
        "taper":     taper,
        "deviation": deviation,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

# ─────────────────────────────────────────────
# Polar Chart
# ─────────────────────────────────────────────
def polar_chart(scan: dict) -> go.Figure:
    angles   = scan["angles"] + [scan["angles"][0]]   # close the loop
    diameter = scan["diameter"] + [scan["diameter"][0]]

    fig = go.Figure()

    # Nominal reference ring
    ref_angles = list(range(0, 361))
    ref_r      = [scan["mean_dia"]] * len(ref_angles)   # center on actual mean
    fig.add_trace(go.Scatterpolar(
        r=ref_r, theta=ref_angles,
        mode="lines",
        line=dict(color="#94a3b8", dash="dash", width=1),
        name="Mean Ø Reference",
        hoverinfo="skip"
    ))

    # Measured profile
    fig.add_trace(go.Scatterpolar(
        r=diameter, theta=angles,
        mode="lines+markers",
        fill="toself",
        fillcolor="rgba(56, 189, 248, 0.15)",
        line=dict(color="#38bdf8", width=2),
        marker=dict(size=6, color="#0ea5e9"),
        name="Bore Profile",
        hovertemplate="<b>%{theta}°</b><br>Ø %{r:.4f} mm<extra></extra>"
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                tickformat=".3f",
                title=dict(text="Diameter (mm)", font=dict(size=11)),
            ),
            angularaxis=dict(direction="clockwise", rotation=90)
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
        margin=dict(t=20, b=60, l=40, r=40),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
    )
    return fig

# ─────────────────────────────────────────────
# History Trend Chart
# ─────────────────────────────────────────────
def history_chart(history: list) -> go.Figure:
    df = pd.DataFrame(history)
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["mean_dia"],
        mode="lines+markers", name="Mean Diameter",
        line=dict(color="#38bdf8"), marker=dict(size=5)
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["ovality"],
        mode="lines+markers", name="Ovality",
        line=dict(color="#f59e0b"), marker=dict(size=5), yaxis="y2"
    ))

    fig.update_layout(
        xaxis=dict(title="Scan Time", tickangle=-30),
        yaxis=dict(title="Mean Diameter (mm)", titlefont=dict(color="#38bdf8")),
        yaxis2=dict(title="Ovality (mm)", titlefont=dict(color="#f59e0b"),
                    overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35),
        height=280,
        margin=dict(t=10, b=80, l=60, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
    )
    return fig

# ─────────────────────────────────────────────
# Page Header
# ─────────────────────────────────────────────
st.title("🔬 Laser Bore Gauge Dashboard")
st.caption("Precision bore measurement — simulated sensor data")
st.divider()

# ─────────────────────────────────────────────
# Scan Control
# ─────────────────────────────────────────────
col_btn, col_info = st.columns([1, 3])

with col_btn:
    scan_clicked = st.button("▶ Start Scan", use_container_width=True, type="primary")

with col_info:
    st.caption(f"Nominal Ø {nominal_dia:.3f} mm  ·  "
               f"Ovality limit {tol_ovality:.4f} mm  ·  "
               f"Taper limit {tol_taper:.4f} mm  ·  "
               f"Diameter ± {tol_diameter:.4f} mm")

# ─────────────────────────────────────────────
# Run Scan
# ─────────────────────────────────────────────
if scan_clicked:
    try:
        with st.spinner("Scanning bore... please wait"):
            time.sleep(1)
            result = run_scan(nominal_dia, noise_std)

        st.session_state["scan_data"]  = result
        st.session_state["scan_count"] += 1
        st.session_state["scan_history"].append({
            "scan_no":   st.session_state["scan_count"],
            "timestamp": result["timestamp"],
            "mean_dia":  result["mean_dia"],
            "deviation": result["deviation"],
            "ovality":   result["ovality"],
            "taper":     result["taper"],
        })
        st.success("Scan complete ✅")

    except Exception as e:
        st.error(f"Scan failed: {e}")

# ─────────────────────────────────────────────
# Results Panel
# ─────────────────────────────────────────────
scan = st.session_state["scan_data"]

if scan:
    # ── Status Banner ──────────────────────────
    dia_ok      = abs(scan["deviation"]) <= tol_diameter
    ovality_ok  = scan["ovality"]        <= tol_ovality
    taper_ok    = scan["taper"]          <= tol_taper
    all_ok      = dia_ok and ovality_ok and taper_ok

    if all_ok:
        st.success("**STATUS: MEASURE OK** 🟢  — All parameters within tolerance")
    else:
        flags = []
        if not dia_ok:     flags.append("Diameter out of tolerance")
        if not ovality_ok: flags.append("Ovality exceeds limit")
        if not taper_ok:   flags.append("Taper exceeds limit")
        st.error(f"**STATUS: OUT OF LIMIT** 🔴  — {' · '.join(flags)}")

    st.caption(f"Scan #{st.session_state['scan_count']}  ·  {scan['timestamp']}")

    # ── Metrics ───────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Mean Diameter",
        f"{scan['mean_dia']:.4f} mm",
        delta=f"{scan['deviation']:+.4f} mm",
        delta_color="inverse" if not dia_ok else "normal"
    )
    m2.metric(
        "Ovality",
        f"{scan['ovality']:.4f} mm",
        delta="PASS" if ovality_ok else "FAIL",
        delta_color="normal" if ovality_ok else "inverse"
    )
    m3.metric(
        "Taper",
        f"{scan['taper']:.4f} mm",
        delta="PASS" if taper_ok else "FAIL",
        delta_color="normal" if taper_ok else "inverse"
    )
    m4.metric(
        "Deviation from Nominal",
        f"{scan['deviation']:+.4f} mm",
    )

    st.divider()

    # ── Polar Chart + Raw Table ────────────────
    chart_col, table_col = st.columns([3, 2])

    with chart_col:
        st.subheader("Bore Profile (Polar)")
        st.plotly_chart(polar_chart(scan), use_container_width=True)

    with table_col:
        st.subheader("Raw Measurements")
        df_raw = pd.DataFrame({
            "Angle (°)":    scan["angles"],
            "Diameter (mm)": [f"{d:.4f}" for d in scan["diameter"]],
        })
        st.dataframe(df_raw, use_container_width=True, height=380)

    # ── Export ────────────────────────────────
    df_export = pd.DataFrame({
        "Angle_deg":    scan["angles"],
        "Diameter_mm":  scan["diameter"],
    })
    df_export["Nominal_mm"]  = nominal_dia
    df_export["Deviation_mm"] = df_export["Diameter_mm"] - nominal_dia

    st.download_button(
        label="⬇ Export Scan as CSV",
        data=df_export.to_csv(index=False),
        file_name=f"bore_scan_{st.session_state['scan_count']}_{scan['timestamp'].replace(' ','_').replace(':','-')}.csv",
        mime="text/csv"
    )

else:
    st.info("Press **▶ Start Scan** to begin measurement.")

# ─────────────────────────────────────────────
# Scan History
# ─────────────────────────────────────────────
history = st.session_state["scan_history"]

if len(history) > 1:
    st.divider()
    st.subheader("📈 Scan History")

    st.plotly_chart(history_chart(history), use_container_width=True)

    df_hist = pd.DataFrame(history)
    df_hist.columns = ["Scan #", "Timestamp", "Mean Ø (mm)", "Deviation (mm)", "Ovality (mm)", "Taper (mm)"]
    st.dataframe(df_hist, use_container_width=True, hide_index=True)

    st.download_button(
        label="⬇ Export Full History as CSV",
        data=df_hist.to_csv(index=False),
        file_name="bore_gauge_history.csv",
        mime="text/csv"
    )
