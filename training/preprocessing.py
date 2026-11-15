"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/preprocessing.py
Task: Preprocessing, Validation, and Splitting Pipeline (AI Draft & Canonical)
=============================================================================

This module provides a legally-grounded preprocessing, validation, target-encoding,
and splitting pipeline for English and Hindi statutory meaning preservation datasets.

Core Principles:
1. Unicode NFKC Normalization & Whitespace Standardization:
   - Preserves legal deontic modals ("shall", "may", "must", "होगा", "सकेगा", "करेगा").
   - Preserves legal punctuation, quotation marks, and Hindi Devanagari Danda (।, ॥).
   - Preserves statutory section references, dates, and numbers.
   - NO stopword removal (function words define statutory rights, duties, and conditions).
   - NO stemming/lemmatization (morphological tense/voice defines legal force).

2. Dual Schema Support & Validation:
   - Modern AI Draft Schema (16 columns from lmp_ai_draft_300.csv):
     • Preserves AI labels as AI supervision targets (weak / draft labels), NEVER as human gold.
     • Validates numeric AI score range [1.0, 10.0], preservation decisions, and error types.
     • Verifies that human annotation fields remain 100% blank for future human adjudication.
   - Legacy Canonical Template Schema (for backward compatibility).

3. Identifiability of NEEDS_REVIEW & Training Set Handling:
   - Retains simplification_status on all rows and generates explicit boolean flags:
     • is_needs_review: True for flagged original passages.
     • is_primary_train: True only for clean SIMPLIFIED passages.
   - Supports two training exclusion / weighting paradigms:
     • Option A (Strict Exclusion): sample_weight_clean = 0.0 for NEEDS_REVIEW (and train_clean.csv).
     • Option B (Soft Down-weighting): sample_weight_soft discounted for confidence & source quality.

4. Partition Independence & Generalization Clarification:
   - Level 1: Exact pair_id disjointness verified (zero overlap).
   - Level 2: Exact normalized original_text disjointness verified (zero overlap).
   - Level 3: Statutory Domain Overlap: Clarified that sections from the same 5 Central Acts
     are present across partitions due to stratified sampling, so exact lexical/ID disjointness
     is distinct from out-of-domain statutory generalization.
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


# -----------------------------------------------------------------------------
# SCHEMA DEFINITIONS AND CONSTANTS
# -----------------------------------------------------------------------------

# Legacy required schema (for backward compatibility with unannotated templates)
LEGACY_REQUIRED_COLUMNS = [
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

# Backward compatibility alias
REQUIRED_COLUMNS = LEGACY_REQUIRED_COLUMNS

# Modern AI-draft annotation schema (16 canonical columns)
AI_DRAFT_REQUIRED_COLUMNS = [
    "pair_id",
    "language",
    "act_id",
    "original_text",
    "simplified_text",
    "context_note",
    "simplification_status",
    "ai_lmp_score",
    "ai_preservation_decision",
    "ai_error_type",
    "ai_explanation",
    "ai_confidence",
    "human_lmp_score",
    "human_error_type",
    "human_explanation",
    "annotation_status",
]

VALID_LANGUAGES = {"EN", "HI"}
MIN_LMP_SCORE = 1.0
MAX_LMP_SCORE = 10.0

# Official 5-category preservation decision mapping
DECISION_TO_ID = {
    "FUNDAMENTALLY_ALTERED": 0,
    "MAJOR_LOSS": 1,
    "PARTIALLY_PRESERVED": 2,
    "MOSTLY_PRESERVED": 3,
    "PRESERVED": 4,
}
ID_TO_DECISION = {v: k for k, v in DECISION_TO_ID.items()}

# Official 8-category error taxonomy mapping
ERROR_TYPE_TO_ID = {
    "NONE": 0,
    "OMISSION": 1,
    "HALLUCINATION_ADDITION": 2,
    "CONTRADICTION": 3,
    "MODALITY_CHANGE": 4,
    "CONDITION_EXCEPTION_LOSS": 5,
    "SCOPE_CHANGE": 6,
    "NUMERIC_ENTITY_REFERENCE_ERROR": 7,
}
ID_TO_ERROR_TYPE = {v: k for k, v in ERROR_TYPE_TO_ID.items()}

VALID_SIMPLIFICATION_STATUSES = {"SIMPLIFIED", "NEEDS_REVIEW"}
VALID_CONFIDENCES = {"HIGH", "MEDIUM", "LOW"}


# -----------------------------------------------------------------------------
# TEXT NORMALIZATION (LEGALLY PRESERVATIVE)
# -----------------------------------------------------------------------------

def normalize_text(text: Any) -> str:
    """
    Applies Unicode NFKC normalization and whitespace standardization to legal text.

    Preserves:
    - Hindi Devanagari script, matras, virama, and punctuation (। and ॥).
    - English and Hindi modal verbs ('shall', 'may', 'must', 'सकेगा', 'होगा', 'करेगा').
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


# -----------------------------------------------------------------------------
# DATASET VALIDATION (AI DRAFT & CANONICAL)
# -----------------------------------------------------------------------------

def detect_dataset_schema(df: pd.DataFrame) -> str:
    """
    Detects whether the input DataFrame uses the AI draft schema, AI audited schema, or legacy schema.
    """
    ai_markers = {"ai_lmp_score", "ai_preservation_decision", "ai_error_type"}
    if any(marker in df.columns for marker in ai_markers):
        if "annotation_status" in df.columns and (df["annotation_status"] == "AI_AUDITED").any():
            return "ai_audited"
        return "ai_draft"
    return "legacy"


def validate_annotation_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validates the annotation dataset against project integrity requirements.
    Supports legacy schema, modern AI-draft schema, and AI-audited schema.
    """
    if len(df) == 0:
        raise ValueError("Validation failed: Annotation dataset is empty (0 rows).")

    schema_type = detect_dataset_schema(df)

    if schema_type in ("ai_draft", "ai_audited"):
        return _validate_ai_draft_dataset(df)
    else:
        return _validate_legacy_dataset(df)


def _validate_ai_draft_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validates an AI-draft annotation dataset (e.g., lmp_ai_draft_300.csv).
    """
    # 1. Required columns check
    missing_cols = [col for col in AI_DRAFT_REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Validation failed: Missing required AI draft columns: {missing_cols}. "
            f"Expected schema: {AI_DRAFT_REQUIRED_COLUMNS}"
        )

    # 2. Language validation
    invalid_langs = set(df["language"].dropna().unique()) - VALID_LANGUAGES
    if invalid_langs:
        raise ValueError(
            f"Validation failed: Invalid language codes found: {invalid_langs}. "
            f"Allowed languages are: {sorted(VALID_LANGUAGES)}"
        )

    # 3. Pair ID format validation
    invalid_ids = [
        pid for pid in df["pair_id"]
        if not re.match(r"^LMP_(EN|HI)_[0-9]{3}$", str(pid))
    ]
    if invalid_ids:
        raise ValueError(
            f"Validation failed: Invalid pair_id formats found: {invalid_ids[:5]}"
        )

    # 4. Simplification status check
    invalid_simp_statuses = set(df["simplification_status"].dropna().unique()) - VALID_SIMPLIFICATION_STATUSES
    if invalid_simp_statuses:
        raise ValueError(
            f"Validation failed: Invalid simplification_status found: {invalid_simp_statuses}. "
            f"Allowed: {sorted(VALID_SIMPLIFICATION_STATUSES)}"
        )

    # 5. AI score bounds and numeric check
    numeric_scores = pd.to_numeric(df["ai_lmp_score"], errors="coerce")
    if numeric_scores.isna().any():
        bad_scores = df.loc[numeric_scores.isna(), "ai_lmp_score"].tolist()
        raise ValueError(
            f"Validation failed: Non-numeric AI LMP scores found: {bad_scores[:5]}"
        )

    out_of_bounds = numeric_scores[
        (numeric_scores < MIN_LMP_SCORE) | (numeric_scores > MAX_LMP_SCORE)
    ]
    if not out_of_bounds.empty:
        raise ValueError(
            f"Validation failed: AI LMP score must be between {MIN_LMP_SCORE} and {MAX_LMP_SCORE}. "
            f"Found out-of-range values: {out_of_bounds.tolist()[:5]}"
        )

    # 6. Preservation decision check
    invalid_decisions = set(df["ai_preservation_decision"].dropna().unique()) - set(DECISION_TO_ID.keys())
    if invalid_decisions:
        raise ValueError(
            f"Validation failed: Invalid ai_preservation_decision found: {invalid_decisions}. "
            f"Allowed: {sorted(DECISION_TO_ID.keys())}"
        )

    # 7. Error type check
    invalid_errors = set(df["ai_error_type"].dropna().unique()) - set(ERROR_TYPE_TO_ID.keys())
    if invalid_errors:
        raise ValueError(
            f"Validation failed: Invalid ai_error_type found: {invalid_errors}. "
            f"Allowed: {sorted(ERROR_TYPE_TO_ID.keys())}"
        )

    # 8. Confidence check
    invalid_conf = set(df["ai_confidence"].dropna().unique()) - VALID_CONFIDENCES
    if invalid_conf:
        raise ValueError(
            f"Validation failed: Invalid ai_confidence found: {invalid_conf}. "
            f"Allowed: {sorted(VALID_CONFIDENCES)}"
        )

    # 9. Annotation status check
    invalid_statuses = set(df["annotation_status"].dropna().unique()) - {"AI_DRAFTED", "AI_AUDITED"}
    if invalid_statuses:
        raise ValueError(
            f"Validation failed: Invalid annotation_status found: {invalid_statuses}. "
            f"Allowed: ['AI_DRAFTED', 'AI_AUDITED']"
        )

    # 10. Verify human annotation columns are unpopulated (reserved for human review)
    human_cols = ["human_lmp_score", "human_error_type", "human_explanation"]
    populated_human = {}
    for hcol in human_cols:
        non_empty = df[hcol].dropna().astype(str).str.strip()
        populated_count = (non_empty != "").sum()
        if populated_count > 0:
            populated_human[hcol] = int(populated_count)

    if populated_human:
        raise ValueError(
            f"Validation failed: Human annotation columns must remain blank in AI draft dataset. "
            f"Found populated entries: {populated_human}"
        )

    # Summary statistics
    total_records = len(df)
    needs_review_count = int((df["simplification_status"] == "NEEDS_REVIEW").sum())
    simplified_count = int((df["simplification_status"] == "SIMPLIFIED").sum())

    score_stats = {
        "min": float(numeric_scores.min()),
        "max": float(numeric_scores.max()),
        "mean": round(float(numeric_scores.mean()), 2),
        "median": round(float(numeric_scores.median()), 2),
    }

    is_audited = ("annotation_status" in df.columns and (df["annotation_status"] == "AI_AUDITED").any())
    schema_name = "ai_audited" if is_audited else "ai_draft"

    validation_summary = {
        "status": "PASSED",
        "schema_type": schema_name,
        "total_records": total_records,
        "simplified_count": simplified_count,
        "needs_review_count": needs_review_count,
        "languages": df["language"].value_counts().to_dict(),
        "acts": df["act_id"].value_counts().to_dict(),
        "score_statistics": score_stats,
        "decision_counts": df["ai_preservation_decision"].value_counts().to_dict(),
        "error_type_counts": df["ai_error_type"].value_counts().to_dict(),
        "confidence_counts": df["ai_confidence"].value_counts().to_dict(),
        "human_fields_status": "VERIFIED_BLANK",
    }
    return validation_summary


def _validate_legacy_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validates a legacy template annotation dataset (backward compatibility).
    """
    # 1. Validate required columns
    missing_cols = [col for col in LEGACY_REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Validation failed: Missing required columns: {missing_cols}. "
            f"Expected schema: {LEGACY_REQUIRED_COLUMNS}"
        )

    # 2. Validate language codes
    invalid_langs = set(df["language"].dropna().unique()) - VALID_LANGUAGES
    if invalid_langs:
        raise ValueError(
            f"Validation failed: Invalid language codes found: {invalid_langs}. "
            f"Allowed languages are: {sorted(VALID_LANGUAGES)}"
        )

    total_records = len(df)

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

    if partial_mask.any():
        partial_ids = df.loc[partial_mask, "pair_id"].tolist()
        raise ValueError(
            f"Validation failed: Found {len(partial_ids)} partially completed annotations. "
            f"Completed annotations must have BOTH simplified_text and lmp_score populated. "
            f"Violating pair_ids: {partial_ids[:10]}"
        )

    completed_count = int(completed_mask.sum())
    empty_count = int(empty_mask.sum())
    score_stats: dict[str, Any] = {}

    if completed_count > 0:
        completed_scores = df.loc[completed_mask, "lmp_score"]
        numeric_scores = pd.to_numeric(completed_scores, errors="coerce")
        if numeric_scores.isna().any():
            invalid_vals = completed_scores[numeric_scores.isna()].tolist()
            raise ValueError(
                f"Validation failed: Non-numeric LMP scores found in completed rows: {invalid_vals[:5]}"
            )

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

    validation_summary = {
        "status": "PASSED",
        "schema_type": "legacy",
        "total_records": total_records,
        "completed_annotations": completed_count,
        "empty_template_rows": empty_count,
        "languages": df["language"].value_counts().to_dict(),
        "acts": df["act_id"].value_counts().to_dict(),
        "score_statistics": score_stats,
    }
    return validation_summary


# -----------------------------------------------------------------------------
# TARGET ENCODING & SUPERVISION TARGET GENERATION
# -----------------------------------------------------------------------------

def add_supervision_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Appends modeling supervision targets, quality flags, and sample weights to
    an AI-draft annotation DataFrame.

    IMPORTANT:
    All generated supervision targets represent AI-assisted drafts (weak supervision).
    They are NEVER represented as human gold labels.
    Human annotation columns remain completely unpopulated.

    Generated Columns:
    - ai_supervision_score: Raw AI LMP score (float, 1.0 - 10.0)
    - ai_supervision_score_norm: Normalized score (float, 0.1 - 1.0)
    - ai_supervision_decision_id: Integer [0-4] mapping of ai_preservation_decision
    - ai_supervision_error_id: Integer [0-7] mapping of ai_error_type
    - is_ai_preserved: Binary indicator (1 if ai_lmp_score >= 9 else 0)
    - target_score, target_score_norm, target_decision_id, target_error_id, is_preserved:
        Drop-in alias columns for model training, mapped directly from AI supervision.
    - is_needs_review: Boolean flag indicating if source original was flagged NEEDS_REVIEW.
    - is_primary_train: Boolean flag indicating if row qualifies for clean primary training
        (True ONLY for SIMPLIFIED rows).
    - sample_weight_clean: 1.0 for clean SIMPLIFIED rows, 0.0 for NEEDS_REVIEW rows (Option A).
    - sample_weight_soft: Continuous reliability weight discounted for confidence & review (Option B).
    """
    df_out = df.copy()

    # Determine numeric scores
    if "ai_lmp_score" in df_out.columns:
        scores = pd.to_numeric(df_out["ai_lmp_score"], errors="coerce").astype(float)
        decisions = df_out["ai_preservation_decision"].astype(str)
        errors = df_out["ai_error_type"].astype(str)
        confidences = df_out["ai_confidence"].astype(str)
        statuses = df_out["simplification_status"].astype(str)

        # AI supervision target columns
        df_out["ai_supervision_score"] = scores
        df_out["ai_supervision_score_norm"] = (scores / 10.0).round(4)
        df_out["ai_supervision_decision_id"] = decisions.map(DECISION_TO_ID).fillna(-1).astype(int)
        df_out["ai_supervision_error_id"] = errors.map(ERROR_TYPE_TO_ID).fillna(-1).astype(int)
        df_out["is_ai_preserved"] = (scores >= 9.0).astype(int)

        # Modeling target aliases for training pipelines
        df_out["target_score"] = df_out["ai_supervision_score"]
        df_out["target_score_norm"] = df_out["ai_supervision_score_norm"]
        df_out["target_decision_id"] = df_out["ai_supervision_decision_id"]
        df_out["target_error_id"] = df_out["ai_supervision_error_id"]
        df_out["is_preserved"] = df_out["is_ai_preserved"]

        # Identifiability of NEEDS_REVIEW passages
        df_out["is_needs_review"] = (statuses == "NEEDS_REVIEW")
        df_out["is_primary_train"] = (statuses == "SIMPLIFIED")

        # Option A: Strict Exclusion weight (NEEDS_REVIEW = 0.0)
        df_out["sample_weight_clean"] = np.where(statuses == "SIMPLIFIED", 1.0, 0.0)

        # Option B: Soft Down-weighting
        # Confidence discounting: HIGH = 1.0, MEDIUM = 0.85
        # Status discounting: SIMPLIFIED = 1.0, NEEDS_REVIEW = 0.50
        conf_weights = confidences.map({"HIGH": 1.0, "MEDIUM": 0.85, "LOW": 0.50}).fillna(0.70)
        status_weights = statuses.map({"SIMPLIFIED": 1.0, "NEEDS_REVIEW": 0.50}).fillna(0.50)
        df_out["sample_weight_soft"] = (conf_weights * status_weights).round(4)

    return df_out


# -----------------------------------------------------------------------------
# STRATIFIED SPLITTING & LEAKAGE VERIFICATION
# -----------------------------------------------------------------------------

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
    - Exact 70% / 15% / 15% partitioning (210 train, 45 val, 45 test for 300 rows).
    - Stratified across (language, act_id) for balanced legal representation.
    - Level 1 & Level 2 Disjointness:
      • Passage IDs are strictly disjoint (train ∩ val = ∅, train ∩ test = ∅, val ∩ test = ∅).
      • Normalized original texts are strictly disjoint across partitions.
    - Level 3 Clarification:
      • All 5 Central Acts are represented across train, val, and test partitions
        by design of the stratified split. This guarantees balanced domain coverage
        within the known acts, but does NOT constitute zero statutory/cross-section overlap.
        Broader out-of-domain generalization requires cross-act evaluation.
    - Fully reproducible via random_seed.
    """
    if stratify_cols is None:
        stratify_cols = ["language", "act_id"]

    ratio_sum = train_ratio + val_ratio + test_ratio
    if not np.isclose(ratio_sum, 1.0):
        raise ValueError(
            f"Split ratios must sum to 1.0. Given: train={train_ratio}, val={val_ratio}, test={test_ratio}"
        )

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

        # Balance odd splits across strata
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

    # -------------------------------------------------------------------------
    # PARTITION INDEPENDENCE VERIFICATION
    # -------------------------------------------------------------------------
    train_ids = set(train_df["pair_id"])
    val_ids = set(val_df["pair_id"])
    test_ids = set(test_df["pair_id"])

    id_tv_overlap = train_ids.intersection(val_ids)
    id_tt_overlap = train_ids.intersection(test_ids)
    id_vt_overlap = val_ids.intersection(test_ids)

    if id_tv_overlap or id_tt_overlap or id_vt_overlap:
        raise RuntimeError(
            f"Partition leakage detected in pair_id! "
            f"Train-Val: {len(id_tv_overlap)}, "
            f"Train-Test: {len(id_tt_overlap)}, "
            f"Val-Test: {len(id_vt_overlap)}"
        )

    train_texts = set(train_df["original_text"])
    val_texts = set(val_df["original_text"])
    test_texts = set(test_df["original_text"])

    text_tv_overlap = train_texts.intersection(val_texts)
    text_tt_overlap = train_texts.intersection(test_texts)
    text_vt_overlap = val_texts.intersection(test_texts)

    if text_tv_overlap or text_tt_overlap or text_vt_overlap:
        raise RuntimeError(
            f"Partition leakage detected in original_text content! "
            f"Train-Val: {len(text_tv_overlap)}, "
            f"Train-Test: {len(text_tt_overlap)}, "
            f"Val-Test: {len(text_vt_overlap)}"
        )

    def format_strata(df_part: pd.DataFrame) -> dict[str, int]:
        counts = df_part.groupby(stratify_cols).size()
        return {
            f"{k[0]}_{k[1]}" if isinstance(k, tuple) else str(k): int(v)
            for k, v in counts.items()
        }

    total_len = len(df)

    # Calculate review stats per split if available
    def get_review_breakdown(df_part: pd.DataFrame) -> dict[str, int]:
        if "simplification_status" in df_part.columns:
            return {
                "SIMPLIFIED": int((df_part["simplification_status"] == "SIMPLIFIED").sum()),
                "NEEDS_REVIEW": int((df_part["simplification_status"] == "NEEDS_REVIEW").sum()),
            }
        return {}

    def get_distribution(df_part: pd.DataFrame, col: str) -> dict[str, int]:
        if col in df_part.columns:
            return {str(k): int(v) for k, v in df_part[col].value_counts().items()}
        return {}

    is_audited = ("annotation_status" in df.columns and (df["annotation_status"] == "AI_AUDITED").any())
    supervision_type = "AI_ASSISTED_AUDITED" if is_audited else "AI_ASSISTED_DRAFT"
    supervision_desc = (
        "Supervision targets are AI-assisted audited evaluations reflecting systematic legal invariant checks. "
        "They are weak supervision targets and have not been validated by human legal scholars. "
        "Human annotation columns are preserved as blank."
        if is_audited
        else (
            "Supervision targets are AI-assisted draft evaluations and have not been validated "
            "by human legal experts. Human annotation columns are preserved as blank."
        )
    )

    clean_train_count = int(train_df["is_primary_train"].sum()) if "is_primary_train" in train_df.columns else len(train_df)

    split_metadata = {
        "random_seed": random_seed,
        "supervision_metadata": {
            "supervision_type": supervision_type,
            "is_human_gold": False,
            "description": supervision_desc,
        },
        "total_records": total_len,
        "train_count": len(train_df),
        "train_percent": round((len(train_df) / total_len) * 100, 2),
        "train_clean_count": clean_train_count,
        "val_count": len(val_df),
        "val_percent": round((len(val_df) / total_len) * 100, 2),
        "test_count": len(test_df),
        "test_percent": round((len(test_df) / total_len) * 100, 2),
        "needs_review_breakdown": {
            "train": get_review_breakdown(train_df),
            "val": get_review_breakdown(val_df),
            "test": get_review_breakdown(test_df),
        },
        "leakage_checks": {
            "pair_id_leakage": False,
            "text_leakage": False,
            "train_val_overlap": len(id_tv_overlap),
            "train_test_overlap": len(id_tt_overlap),
            "val_test_overlap": len(id_vt_overlap),
        },
        "disjointness_checks": {
            "level_1_pair_id_disjoint": True,
            "level_2_exact_text_disjoint": True,
            "pair_id_overlap": {
                "train_val": len(id_tv_overlap),
                "train_test": len(id_tt_overlap),
                "val_test": len(id_vt_overlap),
            },
            "original_text_overlap": {
                "train_val": len(text_tv_overlap),
                "train_test": len(text_tt_overlap),
                "val_test": len(text_vt_overlap),
            },
            "level_3_statutory_generalization_note": (
                "Passages across train, val, and test are from the same 5 Central Acts. "
                "While exact instance and lexical disjointness is mathematically verified (0 overlap), "
                "models are exposed to shared statutory terminology within these Acts. "
                "True cross-statute zero-leakage generalization requires out-of-domain Act evaluation."
            ),
        },
        "strata_balance": {
            "train": format_strata(train_df),
            "val": format_strata(val_df),
            "test": format_strata(test_df),
        },
        "score_distribution": {
            "train": get_distribution(train_df, "ai_lmp_score"),
            "train_clean": get_distribution(train_df[train_df["is_primary_train"]], "ai_lmp_score") if "is_primary_train" in train_df.columns else {},
            "val": get_distribution(val_df, "ai_lmp_score"),
            "test": get_distribution(test_df, "ai_lmp_score"),
        },
        "decision_distribution": {
            "train": get_distribution(train_df, "ai_preservation_decision"),
            "train_clean": get_distribution(train_df[train_df["is_primary_train"]], "ai_preservation_decision") if "is_primary_train" in train_df.columns else {},
            "val": get_distribution(val_df, "ai_preservation_decision"),
            "test": get_distribution(test_df, "ai_preservation_decision"),
        },
        "error_type_distribution": {
            "train": get_distribution(train_df, "ai_error_type"),
            "train_clean": get_distribution(train_df[train_df["is_primary_train"]], "ai_error_type") if "is_primary_train" in train_df.columns else {},
            "val": get_distribution(val_df, "ai_error_type"),
            "test": get_distribution(test_df, "ai_error_type"),
        },
    }

    return train_df, val_df, test_df, split_metadata


# -----------------------------------------------------------------------------
# SAVING PROCESSED OUTPUTS
# -----------------------------------------------------------------------------

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
    Also exports train_clean.csv (Option A: excluding NEEDS_REVIEW passages).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "train": output_dir / "train.csv",
        "train_clean": output_dir / "train_clean.csv",
        "val": output_dir / "val.csv",
        "test": output_dir / "test.csv",
        "full": output_dir / "preprocessed_full.csv",
        "metadata": output_dir / "split_metadata.json",
    }

    train_df.to_csv(paths["train"], index=False, encoding="utf-8-sig")

    # Export clean train subset if is_primary_train exists
    if "is_primary_train" in train_df.columns:
        train_clean_df = train_df[train_df["is_primary_train"]].copy().reset_index(drop=True)
        train_clean_df.to_csv(paths["train_clean"], index=False, encoding="utf-8-sig")
    else:
        # Fallback for legacy
        train_df.to_csv(paths["train_clean"], index=False, encoding="utf-8-sig")

    val_df.to_csv(paths["val"], index=False, encoding="utf-8-sig")
    test_df.to_csv(paths["test"], index=False, encoding="utf-8-sig")
    full_df.to_csv(paths["full"], index=False, encoding="utf-8-sig")

    serializable_meta = json.loads(
        json.dumps(metadata, default=lambda o: str(o))
    )
    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(serializable_meta, f, indent=2, ensure_ascii=False)

    return paths


# -----------------------------------------------------------------------------
# PIPELINE EXECUTION
# -----------------------------------------------------------------------------

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
    Executes the full preprocessing pipeline:
    1. Read input dataset.
    2. Normalize text (NFKC + Whitespace, preserving legal terms).
    3. Validate dataset schema and integrity.
    4. Encode modeling supervision targets and flags.
    5. Perform stratified splitting with instance and text disjointness verification.
    6. Save processed files and export metadata.
    """
    print(f"[INFO] Starting Preprocessing Pipeline")
    print(f"[INFO] Input file: {input_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"[INFO] Loaded {len(df)} records from {input_path.name}")

    # Step 1: Text normalization
    print(f"[INFO] Applying Unicode NFKC & whitespace normalization...")
    df_normalized = normalize_dataframe(df)

    # Step 2: Validation
    print(f"[INFO] Validating dataset integrity...")
    val_summary = validate_annotation_dataset(df_normalized)
    print(f"[SUCCESS] Validation Passed! Schema: {val_summary['schema_type']}")
    print(f"          Total records: {val_summary['total_records']}")
    if val_summary["schema_type"] == "ai_draft":
        print(f"          Simplified rows: {val_summary['simplified_count']}")
        print(f"          NEEDS_REVIEW rows: {val_summary['needs_review_count']}")
        print(f"          Human fields status: {val_summary['human_fields_status']}")
    print(f"          Languages: {val_summary['languages']}")
    print(f"          Central Acts: {val_summary['acts']}")

    # Step 3: Add supervision targets
    print(f"[INFO] Generating AI supervision targets and sample weights...")
    df_enriched = add_supervision_targets(df_normalized)

    if skip_split:
        output_dir.mkdir(parents=True, exist_ok=True)
        norm_path = output_dir / "preprocessed_full.csv"
        df_enriched.to_csv(norm_path, index=False, encoding="utf-8-sig")
        print(f"[INFO] Normalized dataset saved to: {norm_path}")
        return {"validation": val_summary, "output_path": str(norm_path)}

    # Step 4: Stratified splitting
    print(f"[INFO] Partitioning dataset into Train ({train_ratio*100:.0f}%), "
          f"Val ({val_ratio*100:.0f}%), Test ({test_ratio*100:.0f}%)...")
    train_df, val_df, test_df, split_meta = split_dataset(
        df_enriched,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        random_seed=random_seed,
    )

    print(f"[SUCCESS] Splitting Complete (Seed={random_seed}):")
    print(f"          • Train: {split_meta['train_count']} ({split_meta['train_percent']}%)")
    if "needs_review_breakdown" in split_meta:
        tb = split_meta["needs_review_breakdown"]["train"]
        print(f"            - Primary Clean: {tb.get('SIMPLIFIED', 0)}")
        print(f"            - Flagged NEEDS_REVIEW: {tb.get('NEEDS_REVIEW', 0)}")
    print(f"          • Val:   {split_meta['val_count']} ({split_meta['val_percent']}%)")
    print(f"          • Test:  {split_meta['test_count']} ({split_meta['test_percent']}%)")
    print(f"          • Level 1 & 2 Disjointness: Verified (0 ID / 0 Text Overlap).")

    # Step 5: Save outputs
    saved_paths = save_processed_splits(
        train_df, val_df, test_df, df_enriched, output_dir, split_meta
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
        default=Path("data/annotations/lmp_ai_audited_300.csv"),
        help="Path to input annotation CSV file.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("data/processed/audited"),
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
