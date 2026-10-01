"""
Synthetic University Dataset Generator with Known Injected Errors.
Implements Section 7.1 of the STA308 Detailed Project Plan.
Generates baseline ground-truth files and synthetic test suites:
- clean_baseline.xlsx
- messy_headers.xlsx
- mixed_dates.xlsx
- typos_categories.xlsx
- missing_heavy.xlsx
- outliers_invalid.xlsx
- duplicates.xlsx
- gold_clean.xlsx
"""

import os
import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "tests", "fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)

DEPARTMENTS = [
    "Computer Science",
    "Mathematics & Statistics",
    "Electrical Engineering",
    "Biology",
    "Economics",
    "Psychology",
]

PROGRAMS = ["Undergraduate", "Postgraduate", "Doctoral"]


def generate_clean_student_data(n_rows: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate clean synthetic student/course records."""
    random.seed(seed)
    np.random.seed(seed)

    records = []
    start_date = datetime(2020, 9, 1)

    for i in range(1, n_rows + 1):
        student_id = f"STU{10000 + i}"
        dept = random.choice(DEPARTMENTS)
        program = random.choice(PROGRAMS)
        age = random.randint(18, 30)

        # Entrance Exam Score ~ Normal(75, 12) clamped to [40, 100]
        entrance_score = round(float(np.clip(np.random.normal(75, 12), 40, 100)), 1)

        # GPA positively correlated with entrance score + noise
        gpa_latent = 2.0 + (entrance_score / 100.0) * 1.8 + np.random.normal(0, 0.25)
        gpa = round(float(np.clip(gpa_latent, 2.0, 4.0)), 2)

        # Credits earned
        credits = random.randint(12, 120)

        # Enrolled Date
        enrolled = start_date + timedelta(days=random.randint(0, 700))
        enrolled_str = enrolled.strftime("%Y-%m-%d")

        records.append({
            "student_id": student_id,
            "department": dept,
            "program": program,
            "age": age,
            "entrance_score": entrance_score,
            "gpa": gpa,
            "credits_earned": credits,
            "enrolled_date": enrolled_str,
        })

    return pd.DataFrame(records)


def main():
    print("Generating synthetic datasets according to STA308 Plan...")
    clean_df = generate_clean_student_data(n_rows=400)

    # 1. Clean Baseline
    clean_path = os.path.join(FIXTURES_DIR, "clean_baseline.xlsx")
    clean_df.to_excel(clean_path, index=False)
    print(f"-> Created {clean_path}")

    # 2. Messy Headers (Title banner, blank rows above, duplicate headers)
    messy_headers_path = os.path.join(FIXTURES_DIR, "messy_headers.xlsx")
    with pd.ExcelWriter(messy_headers_path, engine="openpyxl") as writer:
        # Create sheet with metadata above table
        meta_data = [
            ["STA308 Final Project - University Gradebook Export", "", "", "", "", "", "", ""],
            ["Generated on 2024-05-15 | Confidential Internal Records", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "", "", ""],  # Blank row
            # Column headers with issues (trailing space, casing, duplicates)
            ["Student ID ", "Department", "Program Level", "Age", "Entrance Score", "GPA", "Credits", "Date Enrolled"],
        ]
        # Append data rows
        for _, row in clean_df.head(150).iterrows():
            meta_data.append(row.tolist())
        # Append trailing total row
        meta_data.append(["Grand Total / Average", "", "", "", 74.8, 3.22, 5400, ""])

        pd.DataFrame(meta_data).to_excel(writer, header=False, index=False)
    print(f"-> Created {messy_headers_path}")

    # 3. Mixed Dates (Multiple formats, Excel serials, ambiguous dates)
    mixed_dates_df = clean_df.copy().head(200)
    date_variants = []
    for i, d_str in enumerate(mixed_dates_df["enrolled_date"]):
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        if i % 4 == 0:
            # ISO
            date_variants.append(dt.strftime("%Y-%m-%d"))
        elif i % 4 == 1:
            # UK/Intl DD/MM/YYYY
            date_variants.append(dt.strftime("%d/%m/%Y"))
        elif i % 4 == 2:
            # Excel serial number
            excel_serial = (dt - datetime(1899, 12, 30)).days
            date_variants.append(excel_serial)
        else:
            # Word format DD-Mon-YYYY
            date_variants.append(dt.strftime("%d-%b-%Y"))

    mixed_dates_df["enrolled_date"] = date_variants
    mixed_dates_path = os.path.join(FIXTURES_DIR, "mixed_dates.xlsx")
    mixed_dates_df.to_excel(mixed_dates_path, index=False)
    print(f"-> Created {mixed_dates_path}")

    # 4. Typos in Categories (Misspellings)
    typo_df = clean_df.copy().head(200)
    typo_map = {
        "Computer Science": ["Computr Science", "Comp Sci", "Computer  Science", "Computer Scince"],
        "Electrical Engineering": ["Electrcal Eng", "Elec Engineering", "Electrical Eng."],
        "Mathematics & Statistics": ["Math & Stats", "Mathemtics & Statistics"],
    }
    new_depts = []
    for dept in typo_df["department"]:
        if dept in typo_map and random.random() < 0.35:
            new_depts.append(random.choice(typo_map[dept]))
        else:
            new_depts.append(dept)
    typo_df["department"] = new_depts
    typos_path = os.path.join(FIXTURES_DIR, "typos_categories.xlsx")
    typo_df.to_excel(typos_path, index=False)
    print(f"-> Created {typos_path}")

    # 5. Missing Heavy (5%, 30%, 60% missingness and null tokens 'N/A', '-', 'null')
    missing_df = clean_df.copy().head(200)
    null_tokens = ["N/A", "-", "null", "missing", ""]

    # Age: 5% missing
    age_col = missing_df["age"].astype(object).copy()
    for idx in range(len(age_col)):
        if random.random() < 0.05:
            age_col.iloc[idx] = random.choice(null_tokens)
    missing_df["age"] = age_col

    # Entrance score: 30% missing
    score_col = missing_df["entrance_score"].astype(object).copy()
    for idx in range(len(score_col)):
        if random.random() < 0.30:
            score_col.iloc[idx] = random.choice(null_tokens)
    missing_df["entrance_score"] = score_col

    # GPA: 55% missing (High missingness test)
    gpa_col = missing_df["gpa"].astype(object).copy()
    for idx in range(len(gpa_col)):
        if random.random() < 0.55:
            gpa_col.iloc[idx] = random.choice(null_tokens)
    missing_df["gpa"] = gpa_col

    missing_path = os.path.join(FIXTURES_DIR, "missing_heavy.xlsx")
    missing_df.to_excel(missing_path, index=False)
    print(f"-> Created {missing_path}")

    # 6. Outliers & Invalid Values (Grades of -5, 150, 999; Ages of -2, 140)
    outliers_df = clean_df.copy().head(200)
    # Inject invalid entrance scores
    outliers_df.loc[10, "entrance_score"] = -5.0
    outliers_df.loc[25, "entrance_score"] = 150.0
    outliers_df.loc[45, "entrance_score"] = 999.0
    # Inject invalid ages
    outliers_df.loc[15, "age"] = -2
    outliers_df.loc[60, "age"] = 145

    outliers_path = os.path.join(FIXTURES_DIR, "outliers_invalid.xlsx")
    outliers_df.to_excel(outliers_path, index=False)
    print(f"-> Created {outliers_path}")

    # 7. Duplicates (Exact duplicates and key duplicates)
    dupes_df = clean_df.copy().head(180)
    # Append exact duplicate rows
    dup_rows = dupes_df.iloc[[5, 12, 20, 35, 50]].copy()
    # Create key duplicate (same student_id, different gpa)
    key_dup = dupes_df.iloc[8].copy()
    key_dup["gpa"] = 3.95
    dupes_combined = pd.concat([dupes_df, dup_rows, pd.DataFrame([key_dup])], ignore_index=True)

    dupes_path = os.path.join(FIXTURES_DIR, "duplicates.xlsx")
    dupes_combined.to_excel(dupes_path, index=False)
    print(f"-> Created {dupes_path}")

    # 8. Gold Hand-Cleaned Reference File
    gold_path = os.path.join(FIXTURES_DIR, "gold_clean.xlsx")
    clean_df.head(150).to_excel(gold_path, index=False)
    print(f"-> Created {gold_path}")

    print("\nAll 8 synthetic test fixtures successfully generated in tests/fixtures/!")


if __name__ == "__main__":
    main()
