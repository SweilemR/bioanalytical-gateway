import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
from io import StringIO

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="BioAnalytical Gateway Engine V2",
    layout="wide"
)

# =========================================================
# GLOBAL CONSTANTS (SIMULATED BIOANALYTICAL STANDARDS)
# =========================================================

QC_LIMITS = {
    "LOW": {"target": 3.0, "tol": 0.15},
    "MID": {"target": 50.0, "tol": 0.15},
    "HIGH": {"target": 400.0, "tol": 0.15},
}

RT_WINDOW = 0.2  # ±0.2 min acceptance window


# =========================================================
# SYNTHETIC DATA GENERATOR (V1 ENHANCED)
# =========================================================

def generate_synthetic_data():
    subjects = ["SUBJ01", "SUBJ02", "SUBJ03"]
    timepoints = [0, 0.25, 0.5, 1, 2, 4, 8, 12, 24]

    analytes = ["Parent", "Metabolite", "IS"]
    batch_id = "BATCH_001"

    rows = []
    inj = 1000

    for subj in subjects:
        for tp in timepoints:
            for an in analytes:

                base = 500000 * np.exp(-0.18 * tp)

                if an == "Metabolite":
                    base *= 0.3
                if an == "IS":
                    base = np.random.normal(100000, 4000)

                noise = np.random.normal(0, base * 0.05)
                peak = max(base + noise, 100)

                rt = np.random.normal(2.45, 0.03)

                # Inject anomaly
                if subj == "SUBJ02" and tp == 4 and an == "IS":
                    peak *= 0.7

                rows.append({
                    "Injection_ID": inj,
                    "Batch_ID": batch_id,
                    "Sample_Name": f"AZ99_Rat_{subj}_10mg_{tp}hr",
                    "Subject_ID": subj,
                    "Timepoint_HR": tp,
                    "Analyte": an,
                    "Peak_Area": peak,
                    "Retention_Time": rt
                })
                inj += 1

    return pd.DataFrame(rows)


# =========================================================
# REGEX PARSER (IMPROVED)
# =========================================================

def parse_sample_name(name):
    pattern = r"(?P<Project>[^_]+)_(?P<Species>[^_]+)_(?P<Subject_ID>SUBJ\d+)_(?P<Dose>[^_]+)_(?P<Timepoint>.+)"
    m = re.match(pattern, name)

    if not m:
        return {}

    d = m.groupdict()

    tp = d["Timepoint"].replace("hr", "")
    try:
        d["Timepoint_HR"] = float(tp)
    except:
        d["Timepoint_HR"] = 0.0

    return d


# =========================================================
# CALIBRATION CURVE ENGINE
# =========================================================

def generate_calibration_curve(analyte="Parent"):
    concentrations = np.array([1, 2, 5, 10, 25, 50, 100, 250])

    slope = 5000 if analyte == "Parent" else 2000
    intercept = 1000

    area = slope * concentrations + intercept + np.random.normal(0, 2000, len(concentrations))

    return pd.DataFrame({
        "STD_Level": [f"STD{i}" for i in range(1, 9)],
        "Concentration": concentrations,
        "Peak_Area": area
    })


def fit_regression(curve, model="linear"):
    x = curve["Concentration"].values
    y = curve["Peak_Area"].values

    if model == "linear":
        coef = np.polyfit(x, y, 1)
        pred = np.polyval(coef, x)

    elif model == "1/x":
        coef = np.polyfit(1/x, y, 1)
        pred = coef[0]*(1/x) + coef[1]

    elif model == "1/x2":
        coef = np.polyfit(1/(x**2), y, 1)
        pred = coef[0]*(1/(x**2)) + coef[1]

    else:
        raise ValueError("Unknown model")

    residuals = y - pred
    return coef, residuals


def back_calculate(area, coef):
    slope, intercept = coef
    return (area - intercept) / slope


# =========================================================
# QC ENGINE (CRO-STYLE RULES)
# =========================================================

def qc_logic(df):
    results = []

    for _, row in df.iterrows():

        analyte = row["Analyte"]
        conc = row.get("Back_Calc_Conc", np.nan)

        if pd.isna(conc):
            results.append("N/A")
            continue

        # simulate QC assignment
        if row["Sample_Name"].find("QC") != -1:
            if "LOW" in row["Sample_Name"]:
                ref = QC_LIMITS["LOW"]["target"]
                tol = QC_LIMITS["LOW"]["tol"]
            elif "MID" in row["Sample_Name"]:
                ref = QC_LIMITS["MID"]["target"]
                tol = QC_LIMITS["MID"]["tol"]
            else:
                ref = QC_LIMITS["HIGH"]["target"]
                tol = QC_LIMITS["HIGH"]["tol"]

            bias = ((conc - ref) / ref) * 100

            if abs(bias) <= tol * 100:
                results.append("PASS")
            else:
                results.append("FAIL")

        else:
            results.append("N/A")

    df["QC_Result"] = results
    return df


# =========================================================
# RETENTION TIME QC
# =========================================================

def rt_qc(df):
    mean_rt = df["Retention_Time"].mean()
    df["RT_Deviation"] = abs(df["Retention_Time"] - mean_rt)

    df["RT_QC"] = np.where(df["RT_Deviation"] > RT_WINDOW, "FAIL", "PASS")

    return df, mean_rt


# =========================================================
# STREAMLIT UI
# =========================================================

st.title("🧪 BioAnalytical Gateway Engine V2")

st.markdown("---")

# STEP 1
st.header("Step 1 — Data Input")

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
else:
    st.info("No file uploaded — using synthetic multi-analyte batch data")
    df = generate_synthetic_data()

st.markdown("---")

# STEP 2
st.header("Step 2 — Parsing + QC + Batch Logic")

df, mean_rt = rt_qc(df)

df["Back_Calc_Conc"] = df["Peak_Area"] / 5000  # simplified quant model

df = qc_logic(df)

# batch summary
batch_summary = df.groupby("Batch_ID").agg({
    "Peak_Area": "mean",
    "QC_Result": lambda x: (x == "FAIL").sum(),
    "RT_QC": lambda x: (x == "FAIL").sum()
}).rename(columns={"QC_Result": "QC_Fails", "RT_QC": "RT_Fails"})

st.dataframe(df, use_container_width=True)

st.subheader("Batch Summary")
st.dataframe(batch_summary)

# STEP 3
st.header("Step 3 — Calibration Curves")

curve = generate_calibration_curve()

model = st.selectbox("Regression Model", ["linear", "1/x", "1/x2"])

coef, residuals = fit_regression(curve, model=model)

st.dataframe(curve)

fig = px.scatter(curve, x="Concentration", y="Peak_Area", title="Calibration Curve")
st.plotly_chart(fig, use_container_width=True)

# STEP 4
st.header("Step 4 — PK Visualization")

pk = df[df["Analyte"] == "Parent"]

fig2 = px.line(pk, x="Timepoint_HR", y="Peak_Area", color="Subject_ID", markers=True)
st.plotly_chart(fig2, use_container_width=True)

# EXPORT
st.download_button(
    "Download PK-Ready Dataset",
    df.to_csv(index=False),
    "pk_ready_v2.csv",
    "text/csv"
)