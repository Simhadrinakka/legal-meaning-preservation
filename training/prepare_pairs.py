"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/prepare_pairs.py
Task: TASK 2 — Prepare LMP Annotation Dataset
=============================================================================

This script extracts high-quality, substantive statutory passages from the
raw MILPaC Acts dataset (data/raw/MILPaC_Acts_dataset.xlsx) to create an
unlabeled annotation template for Legal Meaning Preservation (LMP) evaluation.

Key Design Criteria:
1. Filters out repeated legislative boilerplate clauses and trivial headings.
2. Performs reproducible stratified sampling across the 5 Central Acts.
3. Selects 300 unique statutory passages:
   - 150 English passages (for English legal simplification & LMP evaluation)
   - 150 Hindi passages (for Hindi legal simplification & LMP evaluation)
4. Preserves 0 overlap between English and Hindi passage IDs (300 distinct passages).
5. Exports a standardized CSV template to data/annotations/lmp_annotation_template.csv
   with empty annotation fields (simplified_text, lmp_score, error_type, etc.).
6. Generates a summary report of the sampling distribution.
"""

import os
import sys
from pathlib import Path
import pandas as pd


# Act metadata mapping for readable reporting
ACT_METADATA = {
    "1969_18": "The Registration of Births and Deaths Act, 1969",
    "1976_19": "The Bonded Labour System (Abolition) Act, 1976",
    "2006_4": "The Commissions for Protection of Child Rights Act, 2005",
    "2007_56": "The Maintenance and Welfare of Parents and Senior Citizens Act, 2007",
    "2008_34": "The National Investigation Agency Act, 2008",
}

# Regex patterns for common non-substantive legislative boilerplate
BOILERPLATE_PATTERNS = [
    r"^\s*\d+\.\s*short title",
    r"^\s*\d+\.\s*definitions",
    r"^\s*\(?\d+\)?\s*this act may be called",
    r"^\s*\(?\d+\)?\s*it extends to the whole",
    r"^\s*\d+\.\s*power to make rules",
    r"^\s*\d+\.\s*repeal",
]


def load_raw_dataset(file_path: Path) -> pd.DataFrame:
    """
    Load raw Excel dataset with strict validation and error handling.
    """
    if not file_path.exists():
        raise FileNotFoundError(
            f"Source dataset not found at: {file_path}. "
            "Please ensure data/raw/MILPaC_Acts_dataset.xlsx is available."
        )

    print(f"[INFO] Loading source dataset from: {file_path}")
    try:
        df = pd.read_excel(file_path, sheet_name=0)
    except Exception as e:
        raise RuntimeError(f"Failed to read Excel file {file_path}: {e}") from e

    print(f"[INFO] Loaded {len(df):,} total records.")
    return df


def filter_substantive_passages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract English-Hindi parallel records, filter out trivial boilerplate
    headings, and eliminate duplicates.
    """
    # Filter for English source and Hindi target
    hi_df = df[(df["src_lang"] == "EN") & (df["tgt_lang"] == "HI")].copy()
    initial_count = len(hi_df)
    print(f"[INFO] Initial English-Hindi aligned records: {initial_count}")

    # Extract Act identifier (Year_ActNumber)
    hi_df["act_id"] = hi_df["id"].apply(lambda x: "_".join(str(x).split("_")[:2]))

    # Calculate word lengths
    hi_df["src_word_count"] = hi_df["src"].astype(str).str.split().str.len()
    hi_df["tgt_word_count"] = hi_df["tgt"].astype(str).str.split().str.len()

    # Rule 1: Exclude ultra-short passages (< 10 words in either language)
    # These are typically section titles like "2. Definitions" or "(i) education;"
    substantive = hi_df[
        (hi_df["src_word_count"] >= 10) & (hi_df["tgt_word_count"] >= 10)
    ].copy()
    print(f"[INFO] Passages with >= 10 words in both languages: {len(substantive)}")

    # Rule 2: Exclude common boilerplate title / commencement / repeal phrases
    for pattern in BOILERPLATE_PATTERNS:
        substantive = substantive[
            ~substantive["src"].str.contains(pattern, case=False, regex=True)
        ]
    print(f"[INFO] Passages after removing boilerplate patterns: {len(substantive)}")

    # Rule 3: Drop duplicate texts to ensure distinct legal provisions
    substantive = substantive.drop_duplicates(subset=["src"])
    substantive = substantive.drop_duplicates(subset=["tgt"])
    substantive = substantive.drop_duplicates(subset=["id"])
    print(f"[INFO] Final clean substantive candidate passages: {len(substantive)}")

    return substantive


def sample_balanced_annotation_pairs(
    clean_df: pd.DataFrame,
    total_samples: int = 300,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Perform stratified sampling across the 5 Central Acts to select:
    - 150 English legal passages (30 per Act)
    - 150 Hindi legal passages (30 per Act)
    Total 300 unique passages with ZERO passage ID overlap.
    """
    acts = sorted(clean_df["act_id"].unique())
    num_acts = len(acts)
    samples_per_act = total_samples // num_acts  # 60 per Act
    per_lang_per_act = samples_per_act // 2      # 30 per language per Act

    print(f"\n[INFO] Sampling configuration:")
    print(f"       Total passages required: {total_samples}")
    print(f"       Acts covered: {num_acts} ({acts})")
    print(f"       Passages per Act: {samples_per_act} (30 English, 30 Hindi)")
    print(f"       Random seed: {random_seed} (reproducible)")

    en_records = []
    hi_records = []

    for act in acts:
        act_subset = clean_df[clean_df["act_id"] == act]
        if len(act_subset) < samples_per_act:
            raise ValueError(
                f"Act {act} only has {len(act_subset)} available passages, "
                f"which is less than the required {samples_per_act}."
            )

        # Reproducible random sample of 60 unique passages for this Act
        act_sample = act_subset.sample(n=samples_per_act, random_state=random_seed)

        # Split 30 for English task and 30 for Hindi task
        act_en = act_sample.iloc[:per_lang_per_act].copy()
        act_hi = act_sample.iloc[per_lang_per_act:samples_per_act].copy()

        en_records.append(act_en)
        hi_records.append(act_hi)

    en_sampled_df = pd.concat(en_records, ignore_index=True)
    hi_sampled_df = pd.concat(hi_records, ignore_index=True)

    # Verification of uniqueness and mutual exclusivity
    en_ids = set(en_sampled_df["id"])
    hi_ids = set(hi_sampled_df["id"])
    overlap = en_ids.intersection(hi_ids)

    if overlap:
        raise ValueError(f"Error: Found overlapping passage IDs between EN and HI sets: {overlap}")

    print(f"[INFO] Successfully sampled {len(en_sampled_df)} English and {len(hi_sampled_df)} Hindi passages.")
    print(f"[INFO] Confirmed 0 overlap in passage IDs (Total unique passages = {len(en_ids.union(hi_ids))}).")

    return en_sampled_df, hi_sampled_df


def create_annotation_template(
    en_sampled_df: pd.DataFrame,
    hi_sampled_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construct the standardized CSV template according to project requirements.
    Columns:
      pair_id, language, act_id, original_text, simplified_text,
      lmp_score, error_type, annotation_notes, annotator_id
    """
    rows = []

    # Process English Simplification Task (150 rows)
    for idx, (_, row) in enumerate(en_sampled_df.iterrows(), 1):
        rows.append(
            {
                "pair_id": f"LMP_EN_{idx:03d}",
                "language": "EN",
                "act_id": str(row["act_id"]),
                "original_text": str(row["src"]).strip(),
                "simplified_text": "",
                "lmp_score": "",
                "error_type": "",
                "annotation_notes": "",
                "annotator_id": "",
            }
        )

    # Process Hindi Simplification Task (150 rows)
    for idx, (_, row) in enumerate(hi_sampled_df.iterrows(), 1):
        rows.append(
            {
                "pair_id": f"LMP_HI_{idx:03d}",
                "language": "HI",
                "act_id": str(row["act_id"]),
                "original_text": str(row["tgt"]).strip(),
                "simplified_text": "",
                "lmp_score": "",
                "error_type": "",
                "annotation_notes": "",
                "annotator_id": "",
            }
        )

    template_df = pd.DataFrame(rows)
    return template_df


def generate_summary_report(
    template_df: pd.DataFrame,
    en_df: pd.DataFrame,
    hi_df: pd.DataFrame,
    output_path: Path,
) -> str:
    """
    Generate and save a concise Markdown summary report of the sampled annotation dataset.
    """
    num_en = len(template_df[template_df["language"] == "EN"])
    num_hi = len(template_df[template_df["language"] == "HI"])
    total_unique = len(template_df)

    act_distribution = template_df.groupby(["act_id", "language"]).size().unstack(fill_value=0)
    act_distribution["Total"] = act_distribution.sum(axis=1)

    # Calculate word count statistics
    en_lengths = template_df[template_df["language"] == "EN"]["original_text"].str.split().str.len()
    hi_lengths = template_df[template_df["language"] == "HI"]["original_text"].str.split().str.len()

    report_lines = [
        "# LMP Annotation Dataset Summary Report",
        "",
        f"**Generated File:** `data/annotations/lmp_annotation_template.csv`  ",
        f"**Date:** November 2026  ",
        f"**Project:** Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT  ",
        "",
        "## 1. Overall Dataset Metrics",
        "",
        f"- **Total Annotation Tasks:** {total_unique}",
        f"- **English Passages (`EN`):** {num_en}",
        f"- **Hindi Passages (`HI`):** {num_hi}",
        f"- **Total Unique Legal Passages:** {total_unique} (0 overlap between languages)",
        f"- **Initial Field State:** `simplified_text`, `lmp_score`, `error_type`, `annotation_notes`, and `annotator_id` are strictly EMPTY.",
        "",
        "## 2. Distribution Across Central Acts",
        "",
        "| Act ID | Official Act Title | English (`EN`) | Hindi (`HI`) | Total Passages |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]

    for act_id in sorted(template_df["act_id"].unique()):
        act_title = ACT_METADATA.get(act_id, "Unknown Act")
        en_c = int(act_distribution.loc[act_id, "EN"]) if "EN" in act_distribution.columns else 0
        hi_c = int(act_distribution.loc[act_id, "HI"]) if "HI" in act_distribution.columns else 0
        tot_c = en_c + hi_c
        report_lines.append(f"| `{act_id}` | {act_title} | {en_c} | {hi_c} | {tot_c} |")

    report_lines.extend(
        [
            f"| **Total** | — | **{num_en}** | **{num_hi}** | **{total_unique}** |",
            "",
            "## 3. Passage Length Profile",
            "",
            "| Language | Min Words | Max Words | Mean Words | Median Words |",
            "| :--- | :---: | :---: | :---: | :---: |",
            f"| **English (`EN`)** | {en_lengths.min()} | {en_lengths.max()} | {en_lengths.mean():.1f} | {en_lengths.median():.0f} |",
            f"| **Hindi (`HI`)** | {hi_lengths.min()} | {hi_lengths.max()} | {hi_lengths.mean():.1f} | {hi_lengths.median():.0f} |",
            "",
            "## 4. Annotation Instructions Overview",
            "- **`original_text`**: Unaltered statutory text extracted from official Indian enactments.",
            "- **`simplified_text`**: Plain-language legal simplification produced by human or model.",
            "- **`lmp_score`**: 1 to 5 Likert scale measuring Legal Meaning Preservation.",
            "- **`error_type`**: Classification of legal meaning discrepancy (`NONE`, `MODAL_DRIFT`, `CONDITION_OMISSION`, `ENTITY_DISTORTION`, `SCOPE_ALTERATION`, `PENALTY_INACCURACY`).",
            "- **`annotation_notes`**: Textual justification for the assigned score.",
            "- **`annotator_id`**: Identifier of the annotator.",
        ]
    )

    report_content = "\n".join(report_lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"[INFO] Summary report written to: {output_path}")
    return report_content


def main():
    """
    Main orchestration routine.
    """
    project_root = Path(__file__).resolve().parent.parent
    raw_dataset_path = project_root / "data" / "raw" / "MILPaC_Acts_dataset.xlsx"
    annotation_template_path = project_root / "data" / "annotations" / "lmp_annotation_template.csv"
    summary_report_path = project_root / "reports" / "lmp_annotation_summary.md"

    # Step 1: Load dataset safely
    df = load_raw_dataset(raw_dataset_path)

    # Step 2: Filter substantive non-boilerplate passages
    clean_df = filter_substantive_passages(df)

    # Step 3: Sample 300 unique passages (150 EN, 150 HI)
    en_df, hi_df = sample_balanced_annotation_pairs(
        clean_df, total_samples=300, random_seed=42
    )

    # Step 4: Build standardized CSV template
    template_df = create_annotation_template(en_df, hi_df)

    # Step 5: Save CSV template with utf-8-sig encoding for proper Devanagari display
    annotation_template_path.parent.mkdir(parents=True, exist_ok=True)
    template_df.to_csv(annotation_template_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] Annotation template saved to: {annotation_template_path}")

    # Step 6: Generate summary report
    summary_text = generate_summary_report(
        template_df, en_df, hi_df, summary_report_path
    )

    print("\n" + "=" * 60)
    print(" TASK 2 EXECUTION SUMMARY")
    print("=" * 60)
    print(summary_text)
    print("=" * 60)
    print("[SUCCESS] Dataset preparation pipeline completed successfully.")


if __name__ == "__main__":
    main()

