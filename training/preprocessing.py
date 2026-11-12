"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/preprocessing.py
Task: TASK 3 — Preprocessing and Validation Pipeline
=============================================================================

This module provides a legally-aware preprocessing, validation, and splitting
pipeline for the English and Hindi statutory meaning preservation dataset.

Core Principles:
1. Unicode NFKC Normalization & Whitespace Normalization.
2. Complete Preservation of:
   - Deontic modal verbs ("shall", "may", "must", "होगा", "सकेगा").
   - Legal punctuation, symbols, and Hindi Devanagari Danda (।, ॥).
   - Numbers, dates, section references, and named legal entities.
3. Strict Non-Destruction:
   - NO stopword removal (function words define legal obligations & rights).
   - NO stemming or lemmatization (morphology reflects tense, voice, and force).
4. Robust Dataset Validation:
   - Verification of required schema.
   - Validation of language codes ('EN', 'HI').
   - Range validation for LMP scores (1 to 10).
   - Consistency check: completed annotations must have both simplified text
     and an LMP score.
   - Safe handling of unannotated / empty annotation templates.
5. Leakage-Free Stratified Splitting:
   - 70% Train, 15% Validation, 15% Test.
   - Stratified across (language, act_id).
   - Zero passage leakage between train, val, and test partitions.
   - Deterministic and reproducible with configurable random seed.
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Optional, Tuple

import numpy as np
import pandas as pd


# Required schema for the LMP annotation dataset
REQUIRED_COLUMNS = [
    "pair_id",
    "language",
    "act_id",
    "original_text",
    "simplified_text",
    "lmp_score",
    "error_type",
    "annotation_notes",
    "annotator_id",
]

VALID_LANGUAGES = {"EN", "HI"}
MIN_LMP_SCORE = 1.0
MAX_LMP_SCORE = 10.0


def normalize_text(text: Any) -> str:
    """
    Applies Unicode NFKC normalization and whitespace normalization to legal text.
    
    Preserves:
    - Hindi Devanagari script, matras, virama, and punctuation (। and ॥).
    - English and Hindi modal verbs ('shall', 'may', 'must', 'सकेगा', 'होगा').
    - Legal punctuation: .,;:()[]""''`—–-/%
    - Statutory section and clause references, numbers, and dates.
    
    Does NOT remove stopwords and does NOT perform stemming/lemmatization.
    """
    if text is None or pd.isna(text):
        return ""

    text = str(text)

    # Step 1: Unicode NFKC normalization (standardizes compatibility chars & ligatures)
    normalized = unicodedata.normalize("NFKC", text)

    # Step 2: Standardize quotation marks without stripping them
    normalized = re.sub(r"[\u201c\u201d\u201e\u201f\u00ab\u00bb]", '"', normalized)
    normalized = re.sub(r"[\u2018\u2019\u201a\u201b`]", "'", normalized)

    # Step 3: Standardize hyphens and dashes (preserve em-dashes and hyphens)
    normalized = re.sub(r"[\u2013\u2014\u2015\u2500]", "—", normalized)

    # Step 4: Whitespace normalization
    # Replace non-breaking spaces and Unicode whitespace variants with standard space
    normalized = re.sub(
        r"[\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]", " ", normalized
    )
    # Collapse consecutive spaces, tabs, and linebreaks into a single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Strip leading and trailing whitespace
    return normalized.strip()


def normalize_dataframe(
    df: pd.DataFrame,
    text_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Applies normalize_text to specified text columns in a DataFrame.
    """
    if text_columns is None:
        text_columns = ["original_text", "simplified_text"]

    df_norm = df.copy()
    for col in text_columns:
        if col in df_norm.columns:
            df_norm[col] = df_norm[col].apply(normalize_text)

    return df_norm


def validate_annotation_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validates the annotation dataset against project integrity requirements:
    1. All required columns exist.
    2. Language is strictly 'EN' or 'HI'.
    3. Empty annotation rows are recognized and handled safely.
    4. Completed annotations have both non-empty simplified_text and a valid lmp_score.
    5. LMP scores are numeric and within [1.0, 10.0].

    Returns a comprehensive validation report dictionary.
    Raises ValueError with specific diagnostic messages if requirements fail.
    """
    # 1. Validate required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Validation failed: Missing required columns: {missing_cols}. "
            f"Expected schema: {REQUIRED_COLUMNS}"
        )

    # 2. Validate language codes
    invalid_langs = set(df["language"].dropna().unique()) - VALID_LANGUAGES
    if invalid_langs:
        raise ValueError(
            f"Validation failed: Invalid language codes found: {invalid_langs}. "
            f"Allowed languages are: {sorted(VALID_LANGUAGES)}"
        )

    total_records = len(df)
    if total_records == 0:
        raise ValueError("Validation failed: Annotation dataset is empty (0 rows).")

    # 3. Categorize completed vs. empty annotation rows
    has_simplified = df["simplified_text"].notna() & (
        df["simplified_text"].astype(str).str.strip() != ""
    )
    has_score = df["lmp_score"].notna() & (
        df["lmp_score"].astype(str).str.strip() != ""
    )

    completed_mask = has_simplified & has_score
    empty_mask = (~has_simplified) & (~has_score)
    partial_mask = has_simplified != has_score

    # Check for partially filled rows
    if partial_mask.any():
        partial_ids = df.loc[partial_mask, "pair_id"].tolist()
        raise ValueError(
            f"Validation failed: Found {len(partial_ids)} partially completed annotations. "
            f"Completed annotations must have BOTH simplified_text and lmp_score populated. "
            f"Violating pair_ids: {partial_ids[:10]}"
        )

    # 4. Validate LMP scores on completed annotations
    completed_count = int(completed_mask.sum())
    empty_count = int(empty_mask.sum())
    score_stats: dict[str, Any] = {}

    if completed_count > 0:
        completed_scores = df.loc[completed_mask, "lmp_score"]

        # Validate numeric conversion
        numeric_scores = pd.to_numeric(completed_scores, errors="coerce")
        nan_scores_mask = numeric_scores.isna()
        if nan_scores_mask.any():
            invalid_vals = completed_scores[nan_scores_mask].tolist()
            raise ValueError(
                f"Validation failed: Non-numeric LMP scores found in completed rows: {invalid_vals[:5]}"
            )

        # Validate score bounds [1.0, 10.0]
        out_of_bounds = numeric_scores[
            (numeric_scores < MIN_LMP_SCORE) | (numeric_scores > MAX_LMP_SCORE)
        ]
        if not out_of_bounds.empty:
            raise ValueError(
                f"Validation failed: LMP score must be between {MIN_LMP_SCORE} and {MAX_LMP_SCORE}. "
                f"Found out-of-range values: {out_of_bounds.tolist()[:5]}"
            )

        score_stats = {
            "min": float(numeric_scores.min()),
            "max": float(numeric_scores.max()),
            "mean": round(float(numeric_scores.mean()), 2),
            "median": round(float(numeric_scores.median()), 2),
        }

    lang_counts = df["language"].value_counts().to_dict()
    act_counts = df["act_id"].value_counts().to_dict()

    validation_summary = {
        "status": "PASSED",
        "total_records": total_records,
        "completed_annotations": completed_count,
        "empty_template_rows": empty_count,
        "languages": lang_counts,
        "acts": act_counts,
        "score_statistics": score_stats,
    }

    return validation_summary


def split_dataset(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
    stratify_cols: Optional[list[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Splits the dataset into train, validation, and test sets.
    
    Guarantees:
    - Exact 70% / 15% / 15% partitioning (or configured ratios).
    - Stratified across (language, act_id) for balanced legal representation.
    - Leakage prevention: passage IDs and normalized original texts are verified
      to be strictly disjoint across train, val, and test sets.
    - Fully reproducible via random_seed.
    """
    if stratify_cols is None:
        stratify_cols = ["language", "act_id"]

    ratio_sum = train_ratio + val_ratio + test_ratio
    if not np.isclose(ratio_sum, 1.0):
        raise ValueError(
            f"Split ratios must sum to 1.0. Given: train={train_ratio}, val={val_ratio}, test={test_ratio} (sum={ratio_sum})"
        )

    # Initialize reproducible random generator
    rng = np.random.default_rng(random_seed)

    train_indices: list[int] = []
    val_indices: list[int] = []
    test_indices: list[int] = []

    # Perform stratified sampling across strata
    grouped = list(df.groupby(stratify_cols))
    for i, (_, stratum) in enumerate(grouped):
        stratum_idx = stratum.index.to_numpy(copy=True)
        rng.shuffle(stratum_idx)
        n = len(stratum_idx)

        n_train = int(round(n * train_ratio))
        remaining = n - n_train

        # Balance odd splits across strata (e.g., 4.5 -> alternate 5/4 and 4/5)
        if i % 2 == 0:
            n_val = int(np.ceil(remaining * (val_ratio / (val_ratio + test_ratio))))
            n_test = remaining - n_val
        else:
            n_test = int(np.ceil(remaining * (test_ratio / (val_ratio + test_ratio))))
            n_val = remaining - n_test

        train_indices.extend(stratum_idx[:n_train])
        val_indices.extend(stratum_idx[n_train : n_train + n_val])
        test_indices.extend(stratum_idx[n_train + n_val :])

    train_df = df.loc[train_indices].copy().reset_index(drop=True)
    val_df = df.loc[val_indices].copy().reset_index(drop=True)
    test_df = df.loc[test_indices].copy().reset_index(drop=True)

    # =========================================================================
    # LEAKAGE PREVENTION & INTEGRITY VERIFICATION
    # =========================================================================
    train_ids = set(train_df["pair_id"])
    val_ids = set(val_df["pair_id"])
    test_ids = set(test_df["pair_id"])

    id_train_val_leakage = train_ids.intersection(val_ids)
    id_train_test_leakage = train_ids.intersection(test_ids)
    id_val_test_leakage = val_ids.intersection(test_ids)

    if id_train_val_leakage or id_train_test_leakage or id_val_test_leakage:
        raise RuntimeError(
            f"Data leakage detected in pair_id partition! "
            f"Train-Val: {len(id_train_val_leakage)}, "
            f"Train-Test: {len(id_train_test_leakage)}, "
            f"Val-Test: {len(id_val_test_leakage)}"
        )

    # Check for text leakage across normalized original text
    train_texts = set(train_df["original_text"])
    val_texts = set(val_df["original_text"])
    test_texts = set(test_df["original_text"])

    text_train_val_leakage = train_texts.intersection(val_texts)
    text_train_test_leakage = train_texts.intersection(test_texts)
    text_val_test_leakage = val_texts.intersection(test_texts)

    if text_train_val_leakage or text_train_test_leakage or text_val_test_leakage:
        raise RuntimeError(
            f"Data leakage detected in original_text content! "
            f"Train-Val: {len(text_train_val_leakage)}, "
            f"Train-Test: {len(text_train_test_leakage)}, "
            f"Val-Test: {len(text_val_test_leakage)}"
        )

    # Format strata balance with string keys for JSON serialization
    def format_strata(df_part: pd.DataFrame) -> dict[str, int]:
        counts = df_part.groupby(stratify_cols).size()
        return {
            f"{k[0]}_{k[1]}" if isinstance(k, tuple) else str(k): int(v)
            for k, v in counts.items()
        }

    total_len = len(df)
    split_metadata = {
        "random_seed": random_seed,
        "total_records": total_len,
        "train_count": len(train_df),
        "train_percent": round((len(train_df) / total_len) * 100, 2),
        "val_count": len(val_df),
        "val_percent": round((len(val_df) / total_len) * 100, 2),
        "test_count": len(test_df),
        "test_percent": round((len(test_df) / total_len) * 100, 2),
        "leakage_checks": {
            "pair_id_leakage": False,
            "text_leakage": False,
            "train_val_overlap": 0,
            "train_test_overlap": 0,
            "val_test_overlap": 0,
        },
        "strata_balance": {
            "train": format_strata(train_df),
            "val": format_strata(val_df),
            "test": format_strata(test_df),
        },
    }

    return train_df, val_df, test_df, split_metadata


def save_processed_splits(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    full_df: pd.DataFrame,
    output_dir: Path,
    metadata: dict[str, Any],
) -> dict[str, Path]:
    """
    Saves preprocessed and split DataFrames to disk using utf-8-sig encoding.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "train": output_dir / "train.csv",
        "val": output_dir / "val.csv",
        "test": output_dir / "test.csv",
        "full": output_dir / "preprocessed_full.csv",
        "metadata": output_dir / "split_metadata.json",
    }

    train_df.to_csv(paths["train"], index=False, encoding="utf-8-sig")
    val_df.to_csv(paths["val"], index=False, encoding="utf-8-sig")
    test_df.to_csv(paths["test"], index=False, encoding="utf-8-sig")
    full_df.to_csv(paths["full"], index=False, encoding="utf-8-sig")

    # Convert non-string tuple keys for JSON serialization
    serializable_meta = json.loads(
        json.dumps(metadata, default=lambda o: str(o))
    )
    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(serializable_meta, f, indent=2, ensure_ascii=False)

    return paths


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
    skip_split: bool = False,
) -> dict[str, Any]:
    """
    Executes the full pipeline:
    1. Read input dataset.
    2. Normalize text (NFKC + Whitespace, preserving legal terms).
    3. Validate dataset schema and integrity.
    4. Perform leakage-free stratified splitting.
    5. Save processed files and export metadata.
    """
    print(f"[INFO] Starting Preprocessing Pipeline")
    print(f"[INFO] Input file: {input_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Read dataset
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"[INFO] Loaded {len(df)} records from {input_path.name}")

    # Step 1: Text normalization
    print(f"[INFO] Applying Unicode NFKC & whitespace normalization...")
    df_normalized = normalize_dataframe(df)

    # Step 2: Validation
    print(f"[INFO] Validating dataset integrity...")
    val_summary = validate_annotation_dataset(df_normalized)
    print(f"[SUCCESS] Validation Passed!")
    print(f"          Total records: {val_summary['total_records']}")
    print(f"          Completed annotations: {val_summary['completed_annotations']}")
    print(f"          Empty template rows: {val_summary['empty_template_rows']}")
    print(f"          Languages: {val_summary['languages']}")
    print(f"          Central Acts: {val_summary['acts']}")

    if skip_split:
        output_dir.mkdir(parents=True, exist_ok=True)
        norm_path = output_dir / "preprocessed_full.csv"
        df_normalized.to_csv(norm_path, index=False, encoding="utf-8-sig")
        print(f"[INFO] Normalized dataset saved to: {norm_path}")
        return {"validation": val_summary, "output_path": str(norm_path)}

    # Step 3: Leakage-free stratified splitting
    print(f"[INFO] Partitioning dataset into Train ({train_ratio*100:.0f}%), "
          f"Val ({val_ratio*100:.0f}%), Test ({test_ratio*100:.0f}%)...")
    train_df, val_df, test_df, split_meta = split_dataset(
        df_normalized,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        random_seed=random_seed,
    )

    print(f"[SUCCESS] Splitting Complete (Seed={random_seed}):")
    print(f"          • Train: {split_meta['train_count']} ({split_meta['train_percent']}%)")
    print(f"          • Val:   {split_meta['val_count']} ({split_meta['val_percent']}%)")
    print(f"          • Test:  {split_meta['test_count']} ({split_meta['test_percent']}%)")
    print(f"          • Leakage check: Disjoint partitions verified (Zero Overlap).")

    # Step 4: Save outputs
    saved_paths = save_processed_splits(
        train_df, val_df, test_df, df_normalized, output_dir, split_meta
    )
    print(f"[INFO] Output files saved to: {output_dir}")
    for split_name, path in saved_paths.items():
        print(f"       - {split_name}: {path.name}")

    return {
        "validation": val_summary,
        "split_metadata": split_meta,
        "saved_paths": {k: str(v) for k, v in saved_paths.items()},
    }


def main():
    """
    CLI interface for the preprocessing pipeline.
    """
    parser = argparse.ArgumentParser(
        description="Preprocessing & Validation Pipeline for Legal Meaning Preservation (JUDGEBERT)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/annotations/lmp_annotation_template.csv"),
        help="Path to input annotation CSV file.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory to save preprocessed splits.",
    )
    parser.add_argument(
        "--train_ratio",
        type=float,
        default=0.70,
        help="Proportion of dataset for training (0.0 to 1.0).",
    )
    parser.add_argument(
        "--val_ratio",
        type=float,
        default=0.15,
        help="Proportion of dataset for validation (0.0 to 1.0).",
    )
    parser.add_argument(
        "--test_ratio",
        type=float,
        default=0.15,
        help="Proportion of dataset for testing (0.0 to 1.0).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible stratified splitting.",
    )
    parser.add_argument(
        "--skip_split",
        action="store_true",
        help="Only validate and normalize without partitioning into train/val/test splits.",
    )

    args = parser.parse_args()

    try:
        run_pipeline(
            input_path=args.input,
            output_dir=args.output_dir,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            random_seed=args.seed,
            skip_split=args.skip_split,
        )
    except Exception as e:
        print(f"\n[ERROR] Preprocessing failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
