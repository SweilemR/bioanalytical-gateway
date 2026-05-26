import streamlit as st
import pandas as pd

# ==============================
# SAFE IMPORT HANDLING (ROBUST)
# ==============================

from engines.parser_engine import parse_sample_name
from engines.calibration_engine import fit_linear, back_calculate
from engines.qc_engine import qc_check
from engines.pk_engine import calc_auc
from data.generator_V3 import generate_realistic_cro_dataset

st.header("Step 1: Data Ingestion (Upload or Simulate)")

uploaded_file = st.file_uploader(
    "Upload LC-MS / Empower export CSV",
    type=["csv"]
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("Real dataset uploaded successfully 🧬")

else:
    df = generate_realistic_cro_dataset()
    st.info("No file uploaded → using synthetic CRO dataset")

# ==============================
# STREAMLIT CONFIG
# ==============================
st.set_page_config(
    page_title="BioAnalytical Gateway V2",
    layout="wide"
)

st.title("🧪 BioAnalytical Gateway Engine V2")
st.markdown("CRO-style analytical data processing + QC + PK + Calibration simulation")

st.divider()

# ==============================
# STEP 1 — DATA GENERATION
# ==============================
st.header("Step 1: Data Ingestion")

df = generate_realistic_cro_dataset()

st.success("Synthetic CRO dataset loaded successfully")

st.dataframe(df, use_container_width=True)

st.divider()

# ==============================
# STEP 2 — SAMPLE PARSING
# ==============================
st.header("Step 2: Sample Name Parsing")

if "Sample_Name" in df.columns:
    parsed = df["Sample_Name"].apply(lambda x: parse_sample_name(x))
    parsed_df = pd.json_normalize(parsed)

    st.dataframe(parsed_df, use_container_width=True)
else:
    st.warning("Sample_Name column not found")

st.divider()

# ==============================
# STEP 3 — QC LOGIC DEMO
# ==============================
st.header("Step 3: QC Engine Demo")

if "Peak_Area" in df.columns:

    ref = df["Peak_Area"].mean()

    qc_results = df["Peak_Area"].apply(
        lambda x: qc_check(x, ref)
    )

    qc_df = pd.json_normalize(qc_results)

    df_qc = pd.concat([df, qc_df], axis=1)

    st.write("QC Results (PASS/FAIL based on bias threshold)")

    st.dataframe(df_qc, use_container_width=True)

    pass_rate = df_qc["PASS"].mean()

    st.metric("QC Pass Rate", f"{pass_rate*100:.2f}%")

else:
    st.warning("Peak_Area column not found")

st.divider()

# ==============================
# STEP 4 — PK ANALYSIS (BASIC)
# ==============================
st.header("Step 4: PK Profile Overview")

if {"Timepoint_HR", "Peak_Area"}.issubset(df.columns):

    pk_df = df.groupby("Timepoint_HR")["Peak_Area"].mean().reset_index()

    auc = calc_auc(pk_df["Timepoint_HR"], pk_df["Peak_Area"])

    st.line_chart(pk_df.set_index("Timepoint_HR"))

    st.metric("Approx AUC (Mean Profile)", f"{auc:.2f}")

else:
    st.warning("PK columns missing")

st.divider()

# ==============================
# STEP 5 — QUICK INSIGHTS
# ==============================
st.header("Step 5: Batch Insights")

if "Batch_ID" in df.columns:

    batch_summary = df.groupby("Batch_ID")["Peak_Area"].mean()

    st.bar_chart(batch_summary)

    st.dataframe(batch_summary)

else:
    st.warning("Batch_ID missing")

st.divider()

st.success("V2 Pipeline Execution Complete 🧪")