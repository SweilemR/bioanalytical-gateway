import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
from io import StringIO

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="BioAnalytical Gateway Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CUSTOM STYLING
# =========================================================

st.markdown("""
<style>
.main {
    background-color: #0E1117;
    color: white;
}

.metric-card {
    background-color: #1E1E1E;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #333333;
}

.stDataFrame {
    border: 1px solid #444;
}

hr {
    margin-top: 1rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================

st.title("🧪 BioAnalytical Gateway Engine: Raw-to-Regulatory Pipeline")

st.markdown("""
Bridging the gap between raw chromatography sequence exports and  
**PK-ready DMPK / Clinical Pharmacology modeling datasets**.

This prototype automates the manual "Excel tax" commonly associated with:
- LC-MS/MS sequence parsing
- Empower chromatography exports
- Injection-level QC review
- PK-ready normalization workflows
""")

st.markdown("---")

# =========================================================
# SYNTHETIC DATA GENERATION
# =========================================================

def generate_synthetic_data(seed=42):
    """
    Generate realistic synthetic LC-MS/MS sequence data.
    """

    np.random.seed(seed)

    subjects = ["SUBJ01", "SUBJ02", "SUBJ03"]
    timepoints = ["BLANK", 0.25, 0.5, 1, 2, 4, 8, 12, 24]

    analyte = "AZD-991"
    project = "AZ99"
    species = "Rat"
    dose = "10mg"

    base_internal_std = 100000
    base_pressure = 2500

    dose_factor = 500000
    elimination_rate = 0.18

    rows = []
    injection_id = 1000

    for subj in subjects:

        for tp in timepoints:

            if tp == "BLANK":
                peak_area = np.random.normal(1000, 200)
                sample_name = f"{project}_{species}_{subj}_{dose}_BLANK"
                sample_type = "Unknown"
                time_numeric = 0

            else:
                time_numeric = float(tp)

                true_signal = (
                    dose_factor *
                    np.exp(-elimination_rate * time_numeric)
                )

                noise = np.random.normal(0, true_signal * 0.05)

                peak_area = max(true_signal + noise, 100)

                sample_name = (
                    f"{project}_{species}_{subj}_{dose}_{tp}hr"
                )

                sample_type = "Unknown"

            internal_std = np.random.normal(
                base_internal_std,
                5000
            )

            pressure = np.random.normal(
                base_pressure,
                50
            )

            # -------------------------------------------------
            # Inject realistic system anomaly
            # SUBJ02 @ 4 hr
            # -------------------------------------------------

            if subj == "SUBJ02" and tp == 4:
                internal_std = base_internal_std * 0.75
                pressure = base_pressure + 800

            rows.append({
                "Injection_ID": injection_id,
                "Sample_Name": sample_name,
                "Sample_Type": sample_type,
                "Analyte_Name": analyte,
                "Peak_Area": round(peak_area, 2),
                "Retention_Time": round(
                    np.random.normal(2.45, 0.03),
                    2
                ),
                "Internal_Standard_Area": round(internal_std, 2),
                "System_Pressure_Psi": round(pressure, 2)
            })

            injection_id += 1

    df = pd.DataFrame(rows)

    return df


# =========================================================
# PARSER
# =========================================================

def parse_sample_name(sample_name):
    """
    Parse encoded chromatography sample names.
    """

    pattern = (
        r'(?P<Project>[A-Za-z0-9]+)_'
        r'(?P<Species>[A-Za-z]+)_'
        r'(?P<Subject_ID>SUBJ\d+)_'
        r'(?P<Dose>\d+mg)_'
        r'(?P<Timepoint>(BLANK|[\d\.]+hr))'
    )

    match = re.match(pattern, sample_name)

    if match:

        parsed = match.groupdict()

        tp = parsed["Timepoint"]

        if tp == "BLANK":
            parsed["Timepoint_HR"] = 0.0
        else:
            parsed["Timepoint_HR"] = float(
                tp.replace("hr", "")
            )

        return parsed

    return {
        "Project": None,
        "Species": None,
        "Subject_ID": None,
        "Dose": None,
        "Timepoint": None,
        "Timepoint_HR": None
    }


# =========================================================
# ANOMALY DETECTION
# =========================================================

def run_anomaly_detection(df, threshold_pct):
    """
    Flag injections deviating from mean internal standard.
    """

    mean_is = df["Internal_Standard_Area"].mean()

    deviation_pct = (
        np.abs(
            df["Internal_Standard_Area"] - mean_is
        ) / mean_is
    ) * 100

    df["IS_Deviation_Pct"] = deviation_pct

    df["QC_Status"] = np.where(
        deviation_pct > threshold_pct,
        "⚠️ System Drift/OOS",
        "✅ Valid"
    )

    return df, mean_is


# =========================================================
# FILE UPLOAD
# =========================================================

st.header("Step 1: Upload Raw Sequence File")

uploaded_file = st.file_uploader(
    "Upload LC-MS/MS or Waters Empower CSV export",
    type=["csv"]
)

if uploaded_file is not None:

    df_raw = pd.read_csv(uploaded_file)

else:

    st.info(
        "No file uploaded. Loaded simulated non-proprietary "
        "chromatography sequence data."
    )

    df_raw = generate_synthetic_data()

st.markdown("---")

# =========================================================
# DATA PARSING
# =========================================================

st.header("Step 2: Automated Data Parsing & Anomaly Core")

parsed_df = df_raw.copy()

parsed_columns = parsed_df["Sample_Name"].apply(
    parse_sample_name
)

parsed_expanded = pd.DataFrame(parsed_columns.tolist())

parsed_df = pd.concat(
    [parsed_df, parsed_expanded],
    axis=1
)

# =========================================================
# THRESHOLD CONTROL
# =========================================================

threshold = st.slider(
    "Internal Standard Drift Threshold (%)",
    min_value=5,
    max_value=40,
    value=15
)

parsed_df, mean_is = run_anomaly_detection(
    parsed_df,
    threshold
)

# =========================================================
# METRICS
# =========================================================

total_injections = len(parsed_df)

flagged = (
    parsed_df["QC_Status"]
    .eq("⚠️ System Drift/OOS")
    .sum()
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total Injections",
        total_injections
    )

with col2:
    st.metric(
        "Flagged Anomalies",
        flagged
    )

with col3:
    st.metric(
        "Mean Internal Standard Area",
        f"{mean_is:,.0f}"
    )

# =========================================================
# DATAFRAME HIGHLIGHTING
# =========================================================

def highlight_rows(row):

    if row["QC_Status"] == "⚠️ System Drift/OOS":
        return ['background-color: #5C1E1E'] * len(row)

    return [''] * len(row)


st.subheader("Parsed & QC-Assessed Injection Table")

styled_df = parsed_df.style.apply(
    highlight_rows,
    axis=1
)

st.dataframe(
    styled_df,
    use_container_width=True,
    height=450
)

st.markdown("---")

# =========================================================
# PK VISUALIZATION
# =========================================================

st.header("Step 3: Pharmacokinetic Visualization")

plot_df = parsed_df[
    parsed_df["Timepoint_HR"].notna()
].copy()

fig = px.line(
    plot_df,
    x="Timepoint_HR",
    y="Peak_Area",
    color="Subject_ID",
    markers=True,
    hover_data=[
        "Injection_ID",
        "QC_Status",
        "Internal_Standard_Area",
        "System_Pressure_Psi"
    ],
    title="PK Exposure Curve: Peak Area vs Time"
)

# Highlight anomalies

anomaly_df = plot_df[
    plot_df["QC_Status"] == "⚠️ System Drift/OOS"
]

fig.add_scatter(
    x=anomaly_df["Timepoint_HR"],
    y=anomaly_df["Peak_Area"],
    mode="markers",
    marker=dict(
        size=16,
        symbol="x",
        color="red"
    ),
    name="System Drift/OOS"
)

fig.update_layout(
    template="plotly_dark",
    height=600,
    xaxis_title="Timepoint (Hours)",
    yaxis_title="Peak Area",
    legend_title="Subject"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.markdown("---")

# =========================================================
# EXPORT SECTION
# =========================================================

st.header("Step 4: Export Framework")

export_columns = [
    "Subject_ID",
    "Dose",
    "Timepoint_HR",
    "Analyte_Name",
    "Peak_Area",
    "Internal_Standard_Area",
    "Retention_Time",
    "QC_Status"
]

export_df = parsed_df[export_columns].copy()

csv_buffer = StringIO()

export_df.to_csv(
    csv_buffer,
    index=False
)

st.download_button(
    label="⬇️ Download Phoenix WinNonlin Ready Dataset",
    data=csv_buffer.getvalue(),
    file_name="phoenix_winnonlin_ready.csv",
    mime="text/csv"
)

st.success(
    "Dataset successfully normalized and prepared for "
    "downstream PK modeling workflows."
)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("BioAnalytical Gateway")

st.sidebar.markdown("""
### Workflow Coverage
- Raw LC-MS/MS exports
- CDS parsing
- Injection QC
- PK normalization
- Regulatory-ready structuring

### Simulated Anomaly
- SUBJ02 @ 4 hr
- IS area drops 25%
- Pressure spike +800 Psi
""")

st.sidebar.markdown("---")

st.sidebar.markdown("""
Built for:
- DMPK Scientists
- Bioanalytical CROs
- Clinical Pharmacology Teams
- Translational PK/PD Groups
""")

