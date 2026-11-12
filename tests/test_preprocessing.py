"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: tests/test_preprocessing.py
Task: Unit Tests for Preprocessing, Validation, and Splitting Pipeline
=============================================================================
"""

import unittest
import sys
from pathlib import Path

# Add project root to sys.path for test discovery and module imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

# Import the module under test
from training.preprocessing import (
    REQUIRED_COLUMNS,
    VALID_LANGUAGES,
    MIN_LMP_SCORE,
    MAX_LMP_SCORE,
    normalize_text,
    normalize_dataframe,
    validate_annotation_dataset,
    split_dataset,
)


class TestTextNormalization(unittest.TestCase):
    """
    Test cases for Unicode NFKC, whitespace normalization, and legal term preservation.
    """

    def test_unicode_nfkc_normalization(self):
        # Compatibility decomposition (e.g., fullwidth chars, ligatures)
        raw_text = "\uff21\uff43\uff54\u00a0\uff11\uff15\uff14"  # Fullwidth 'Act 154'
        normalized = normalize_text(raw_text)
        self.assertEqual(normalized, "Act 154")

    def test_whitespace_normalization(self):
        raw_text = "  Section  154(1)   shall   apply\t\tto   all  matters.\n\n"
        normalized = normalize_text(raw_text)
        self.assertEqual(normalized, "Section 154(1) shall apply to all matters.")

    def test_legal_punctuation_preserved(self):
        raw_text = '“Notwithstanding anything in sub-section (1), the ‘Central Government’ may—by order—direct:;”'
        normalized = normalize_text(raw_text)
        # Should convert curly quotes to standard quotes and preserve em-dashes and punctuation
        self.assertIn('"', normalized)
        self.assertIn("'", normalized)
        self.assertIn("—", normalized)
        self.assertIn(";", normalized)
        self.assertIn(":", normalized)
        self.assertIn("(", normalized)
        self.assertIn(")", normalized)

    def test_hindi_devanagari_preserved(self):
        raw_hindi = " (1)   इस अधिनियम का   संक्षिप्त नाम बालक अधिकार संरक्षण आयोग अधिनियम, 2005 है। "
        normalized = normalize_text(raw_hindi)
        self.assertEqual(
            normalized,
            "(1) इस अधिनियम का संक्षिप्त नाम बालक अधिकार संरक्षण आयोग अधिनियम, 2005 है।",
        )
        # Check Devanagari Danda preservation
        self.assertTrue(normalized.endswith("है।"))

    def test_hindi_double_danda_preserved(self):
        raw_hindi = "  ॥ श्री गणेशाय नमः ॥  "
        normalized = normalize_text(raw_hindi)
        self.assertIn("॥", normalized)

    def test_modal_verbs_preserved(self):
        raw_text = "The officer shall inspect and may summon any person who must appear."
        normalized = normalize_text(raw_text)
        # Deontic modals must be completely intact
        for modal in ["shall", "may", "must"]:
            self.assertIn(modal, normalized)

    def test_no_stopword_removal(self):
        raw_text = "In this Act, unless the context otherwise requires, a child means a person under 18."
        normalized = normalize_text(raw_text)
        # Function words that define statutory boundaries must be fully retained
        for func_word in ["In", "this", "unless", "the", "otherwise", "under"]:
            self.assertIn(func_word, normalized)

    def test_empty_and_none_input(self):
        self.assertEqual(normalize_text(None), "")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text("   "), "")
        self.assertEqual(normalize_text(np.nan), "")


class TestDatasetValidation(unittest.TestCase):
    """
    Test cases for annotation dataset schema, language, score bounds, and completeness.
    """

    def setUp(self):
        # Base valid 2-row unannotated DataFrame
        self.valid_unannotated_df = pd.DataFrame(
            [
                {
                    "pair_id": "LMP_EN_001",
                    "language": "EN",
                    "act_id": "2006_4",
                    "original_text": "Section 1 shall come into force.",
                    "simplified_text": None,
                    "lmp_score": None,
                    "error_type": None,
                    "annotation_notes": None,
                    "annotator_id": None,
                },
                {
                    "pair_id": "LMP_HI_001",
                    "language": "HI",
                    "act_id": "2006_4",
                    "original_text": "धारा 1 प्रवृत्त होगी।",
                    "simplified_text": None,
                    "lmp_score": None,
                    "error_type": None,
                    "annotation_notes": None,
                    "annotator_id": None,
                },
            ]
        )

    def test_valid_unannotated_template(self):
        summary = validate_annotation_dataset(self.valid_unannotated_df)
        self.assertEqual(summary["status"], "PASSED")
        self.assertEqual(summary["total_records"], 2)
        self.assertEqual(summary["completed_annotations"], 0)
        self.assertEqual(summary["empty_template_rows"], 2)

    def test_valid_completed_annotations(self):
        completed_df = self.valid_unannotated_df.copy()
        completed_df["simplified_text"] = ["Section 1 starts.", "धारा 1 शुरू होती है।"]
        completed_df["lmp_score"] = [8.5, 9.0]
        completed_df["error_type"] = ["NONE", "NONE"]
        completed_df["annotator_id"] = ["ANN_01", "ANN_02"]

        summary = validate_annotation_dataset(completed_df)
        self.assertEqual(summary["status"], "PASSED")
        self.assertEqual(summary["completed_annotations"], 2)
        self.assertEqual(summary["score_statistics"]["min"], 8.5)
        self.assertEqual(summary["score_statistics"]["max"], 9.0)

    def test_missing_required_columns(self):
        invalid_df = self.valid_unannotated_df.drop(columns=["lmp_score"])
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(invalid_df)
        self.assertIn("Missing required columns", str(ctx.exception))

    def test_invalid_language(self):
        invalid_df = self.valid_unannotated_df.copy()
        invalid_df.loc[0, "language"] = "FR"  # French is not supported
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(invalid_df)
        self.assertIn("Invalid language codes found", str(ctx.exception))

    def test_out_of_bounds_score_low(self):
        invalid_df = self.valid_unannotated_df.copy()
        invalid_df["simplified_text"] = ["Simplified", "सरल"]
        invalid_df["lmp_score"] = [0.5, 5.0]  # 0.5 is < MIN_LMP_SCORE (1.0)
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(invalid_df)
        self.assertIn("LMP score must be between 1.0 and 10.0", str(ctx.exception))

    def test_out_of_bounds_score_high(self):
        invalid_df = self.valid_unannotated_df.copy()
        invalid_df["simplified_text"] = ["Simplified", "सरल"]
        invalid_df["lmp_score"] = [11.0, 5.0]  # 11.0 is > MAX_LMP_SCORE (10.0)
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(invalid_df)
        self.assertIn("LMP score must be between 1.0 and 10.0", str(ctx.exception))

    def test_non_numeric_score(self):
        invalid_df = self.valid_unannotated_df.copy()
        invalid_df["simplified_text"] = ["Simplified", "सरल"]
        invalid_df["lmp_score"] = ["excellent", 5.0]
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(invalid_df)
        self.assertIn("Non-numeric LMP scores found", str(ctx.exception))

    def test_partially_completed_row(self):
        # Has simplified_text but missing lmp_score
        invalid_df = self.valid_unannotated_df.copy()
        invalid_df.loc[0, "simplified_text"] = "Simplified legal sentence."
        invalid_df.loc[0, "lmp_score"] = None
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(invalid_df)
        self.assertIn("partially completed annotations", str(ctx.exception))

    def test_empty_dataframe(self):
        empty_df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(empty_df)
        self.assertIn("Annotation dataset is empty", str(ctx.exception))


class TestDatasetSplitting(unittest.TestCase):
    """
    Test cases for reproducible, stratified, leakage-free train/val/test splitting.
    """

    def setUp(self):
        # Create a synthetic 100-row dataset across EN/HI and 2 Acts
        rows = []
        counter = 1
        for lang in ["EN", "HI"]:
            for act in ["2006_4", "1976_19"]:
                for i in range(25):  # 25 per stratum * 4 = 100
                    rows.append(
                        {
                            "pair_id": f"LMP_{lang}_{counter:04d}",
                            "language": lang,
                            "act_id": act,
                            "original_text": f"Statutory provision {counter} for {lang} in Act {act}.",
                            "simplified_text": None,
                            "lmp_score": None,
                            "error_type": None,
                            "annotation_notes": None,
                            "annotator_id": None,
                        }
                    )
                    counter += 1
        self.test_df = pd.DataFrame(rows)

    def test_split_ratios_and_counts(self):
        train_df, val_df, test_df, meta = split_dataset(
            self.test_df,
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            random_seed=42,
        )
        self.assertEqual(len(train_df), 72)  # Balanced rounding across strata
        self.assertEqual(len(val_df), 14)
        self.assertEqual(len(test_df), 14)
        self.assertEqual(len(train_df) + len(val_df) + len(test_df), 100)

    def test_zero_leakage_guarantee(self):
        train_df, val_df, test_df, meta = split_dataset(self.test_df, random_seed=42)

        # Check pair_id disjointness
        train_ids = set(train_df["pair_id"])
        val_ids = set(val_df["pair_id"])
        test_ids = set(test_df["pair_id"])

        self.assertEqual(len(train_ids.intersection(val_ids)), 0)
        self.assertEqual(len(train_ids.intersection(test_ids)), 0)
        self.assertEqual(len(val_ids.intersection(test_ids)), 0)

        # Check original_text disjointness
        train_texts = set(train_df["original_text"])
        val_texts = set(val_df["original_text"])
        test_texts = set(test_df["original_text"])

        self.assertEqual(len(train_texts.intersection(val_texts)), 0)
        self.assertEqual(len(train_texts.intersection(test_texts)), 0)
        self.assertEqual(len(val_texts.intersection(test_texts)), 0)

        # Verify metadata flags
        self.assertFalse(meta["leakage_checks"]["pair_id_leakage"])
        self.assertFalse(meta["leakage_checks"]["text_leakage"])

    def test_reproducibility(self):
        # Run split twice with seed=42
        train_1, val_1, test_1, _ = split_dataset(self.test_df, random_seed=42)
        train_2, val_2, test_2, _ = split_dataset(self.test_df, random_seed=42)

        pd.testing.assert_frame_equal(train_1, train_2)
        pd.testing.assert_frame_equal(val_1, val_2)
        pd.testing.assert_frame_equal(test_1, test_2)

        # Run split with different seed
        train_3, _, _, _ = split_dataset(self.test_df, random_seed=999)
        self.assertFalse(train_1["pair_id"].equals(train_3["pair_id"]))

    def test_invalid_ratios(self):
        with self.assertRaises(ValueError) as ctx:
            split_dataset(
                self.test_df, train_ratio=0.80, val_ratio=0.20, test_ratio=0.10
            )
        self.assertIn("Split ratios must sum to 1.0", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
