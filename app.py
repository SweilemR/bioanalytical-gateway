import numpy as np
import pandas as pd
import random


def generate_bioanalytical_dataset(
    n_subjects=20,
    injections_per_subject=60,
    n_batches=3,
    seed=42
):
    """
    V3-grade synthetic LC-MS/MS dataset generator for CRO-style workflows.
    Supports:
    - Calibration standards (STD1–STD8)
    - QC Low/Mid/High
    - Unknown samples
    - Multi-analyte system
    - Batch structure
    - Instrument drift simulation
    """

    np.random.seed(seed)
    random.seed(seed)

    subjects = [f"SUBJ{str(i).zfill(2)}" for i in range(1, n_subjects + 1)]

    analytes = ["Parent", "Metabolite", "Internal_Standard"]

    species = "Rat"
    project = "AZ99"

    timepoints = [0, 0.25, 0.5, 1, 2, 4, 8, 12, 24]

    std_levels = list(range(1, 9))  # STD1–STD8

    qc_levels = ["LOW", "MID", "HIGH"]

    rows = []
    inj_id = 1

    for batch in range(1, n_batches + 1):

        batch_id = f"BATCH_{str(batch).zfill(3)}"

        for subj in subjects:

            # subject-specific PK variability
            dose_factor = np.random.uniform(0.7, 1.3) * 1_000_000
            elimination_rate = np.random.uniform(0.20, 0.40)

            for _ in range(injections_per_subject):

                tp = random.choice(timepoints)

                # -------------------------------------------------
                # SAMPLE TYPE DECISION
                # -------------------------------------------------

                sample_type = random.choices(
                    ["Unknown", "QC", "Standard"],
                    weights=[0.70, 0.20, 0.10],
                    k=1
                )[0]

                analyte = random.choice(analytes)

                # -------------------------------------------------
                # SAMPLE NAME GENERATION (REAL CDS STYLE VARIABILITY)
                # -------------------------------------------------

                if sample_type == "Unknown":
                    tp_label = "BLANK" if tp == 0 else f"{tp}hr"

                    sample_name = random.choice([
                        f"{project}_{species}_{subj}_10mg_{tp_label}",
                        f"{project}-{species}-{subj}-10mg-{tp_label}",
                        f"{project}_{species}_{subj}_10mg_{tp_label}_rep1"
                    ])

                elif sample_type == "QC":
                    qc = random.choice(qc_levels)
                    sample_name = f"{project}_{species}_QC_{qc}"

                else:  # Standard
                    std = random.choice(std_levels)
                    sample_name = f"{project}_{species}_STD_{std}"

                # -------------------------------------------------
                # SIGNAL GENERATION
                # -------------------------------------------------

                true_signal = dose_factor * np.exp(-elimination_rate * tp)

                if analyte == "Metabolite":
                    true_signal *= 0.25

                if analyte == "Internal_Standard":
                    true_signal = np.random.normal(100_000, 3000)

                peak_area = true_signal + np.random.normal(0, true_signal * 0.05)

                # -------------------------------------------------
                # RETENTION TIME (SYSTEM DRIFT MODEL)
                # -------------------------------------------------

                rt_base = 2.45 + np.random.normal(0, 0.02)

                # slow drift per batch
                rt_drift = batch * 0.02
                retention_time = rt_base + rt_drift

                # -------------------------------------------------
                # INTERNAL STANDARD (QC CRITICAL)
                # -------------------------------------------------

                internal_std = 100_000 + np.random.normal(0, 2500)

                # rare instrument failure
                if random.random() < 0.02:
                    internal_std *= np.random.uniform(0.6, 0.85)

                # -------------------------------------------------
                # SYSTEM PRESSURE
                # -------------------------------------------------

                pressure = 3000 + np.random.normal(0, 50)

                # clog event
                if random.random() < 0.01:
                    pressure += np.random.uniform(500, 900)

                # -------------------------------------------------
                # MISSING DATA SIMULATION
                # -------------------------------------------------

                if random.random() < 0.01:
                    peak_area = np.nan

                # -------------------------------------------------
                # ROW ASSEMBLY
                # -------------------------------------------------

                rows.append({
                    "Injection_ID": inj_id,
                    "Batch_ID": batch_id,
                    "Project": project,
                    "Species": species,

                    "Subject_ID": subj,
                    "Timepoint_HR": tp,

                    "Sample_Name": sample_name,
                    "Sample_Type": sample_type,

                    "Analyte": analyte,

                    "Peak_Area": (
                        max(peak_area, 0)
                        if not pd.isna(peak_area)
                        else np.nan
                    ),

                    "Retention_Time": retention_time,

                    "Internal_Standard_Area": max(internal_std, 0),

                    "System_Pressure_Psi": max(pressure, 0)
                })

                inj_id += 1

    df = pd.DataFrame(rows)

    # -------------------------------------------------
    # EXPORT
    # -------------------------------------------------

    file_name = "bioanalytical_gateway_dataset_v3.csv"
    df.to_csv(file_name, index=False)

    print("\n==============================")
    print("BIOANALYTICAL DATASET GENERATED")
    print("==============================")
    print("File:", file_name)
    print("Rows:", len(df))
    print("Subjects:", n_subjects)
    print("Batches:", n_batches)
    print("==============================\n")

    return df


# -------------------------------------------------
# RUN DIRECTLY
# -------------------------------------------------

if __name__ == "__main__":
    generate_bioanalytical_dataset()
