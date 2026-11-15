"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: tests/test_preprocessing.py
Task: Unit Tests for Preprocessing, Validation, and Splitting Pipeline
=============================================================================
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path for test discovery and module imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

# Import the module under test
from training.preprocessing import (
    AI_DRAFT_REQUIRED_COLUMNS,
    DECISION_TO_ID,
    ERROR_TYPE_TO_ID,
    MAX_LMP_SCORE,
    MIN_LMP_SCORE,
    REQUIRED_COLUMNS,
    VALID_LANGUAGES,
    add_supervision_targets,
    normalize_dataframe,
    normalize_text,
    save_processed_splits,
    split_dataset,
    validate_annotation_dataset,
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
                for _ in range(25):  # 25 per stratum * 4 = 100
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


class TestAIDraftPreprocessing(unittest.TestCase):
    """
    Test cases for AI-draft dataset validation, supervision target generation,
    NEEDS_REVIEW handling, sample weighting, and clean training splits.
    """

    def setUp(self):
        # Create a valid synthetic AI draft DataFrame
        self.valid_ai_df = pd.DataFrame(
            [
                {
                    "pair_id": "LMP_EN_001",
                    "language": "EN",
                    "act_id": "1969_18",
                    "original_text": "Section 1 shall apply to the whole of India.",
                    "simplified_text": "Section 1 applies across all of India.",
                    "context_note": "Preliminary jurisdiction",
                    "simplification_status": "SIMPLIFIED",
                    "ai_lmp_score": 9,
                    "ai_preservation_decision": "PRESERVED",
                    "ai_error_type": "NONE",
                    "ai_explanation": "All legal obligations and scope preserved.",
                    "ai_confidence": "HIGH",
                    "human_lmp_score": "",
                    "human_error_type": "",
                    "human_explanation": "",
                    "annotation_status": "AI_DRAFTED",
                },
                {
                    "pair_id": "LMP_HI_001",
                    "language": "HI",
                    "act_id": "1969_18",
                    "original_text": "धारा 1 संपूर्ण भारत पर लागू होगी।",
                    "simplified_text": "धारा 1 पूरे भारत पर लागू होती है।",
                    "context_note": "प्रारंभिक क्षेत्राधिकार",
                    "simplification_status": "NEEDS_REVIEW",
                    "ai_lmp_score": 8,
                    "ai_preservation_decision": "MOSTLY_PRESERVED",
                    "ai_error_type": "SCOPE_CHANGE",
                    "ai_explanation": "मामूली शब्दावली परिवर्तन।",
                    "ai_confidence": "MEDIUM",
                    "human_lmp_score": "",
                    "human_error_type": "",
                    "human_explanation": "",
                    "annotation_status": "AI_DRAFTED",
                },
            ]
        )

    def test_valid_ai_draft_validation(self):
        summary = validate_annotation_dataset(self.valid_ai_df)
        self.assertEqual(summary["status"], "PASSED")
        self.assertEqual(summary["schema_type"], "ai_draft")
        self.assertEqual(summary["total_records"], 2)
        self.assertEqual(summary["simplified_count"], 1)
        self.assertEqual(summary["needs_review_count"], 1)
        self.assertEqual(summary["human_fields_status"], "VERIFIED_BLANK")

    def test_ai_draft_populated_human_fields_fails(self):
        bad_df = self.valid_ai_df.copy()
        bad_df.loc[0, "human_lmp_score"] = 9.0  # Must be blank in AI draft
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(bad_df)
        self.assertIn("Human annotation columns must remain blank", str(ctx.exception))

    def test_ai_draft_invalid_error_type_fails(self):
        bad_df = self.valid_ai_df.copy()
        bad_df.loc[0, "ai_error_type"] = "UNKNOWN_ERROR"
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(bad_df)
        self.assertIn("Invalid ai_error_type found", str(ctx.exception))

    def test_supervision_targets_generation(self):
        df_targets = add_supervision_targets(self.valid_ai_df)
        # Check generated target columns exist
        expected_cols = [
            "ai_supervision_score",
            "ai_supervision_score_norm",
            "ai_supervision_decision_id",
            "ai_supervision_error_id",
            "is_ai_preserved",
            "target_score",
            "target_score_norm",
            "target_decision_id",
            "target_error_id",
            "is_preserved",
            "is_needs_review",
            "is_primary_train",
            "sample_weight_clean",
            "sample_weight_soft",
        ]
        for col in expected_cols:
            self.assertIn(col, df_targets.columns)

        # Check values for row 0 (SIMPLIFIED, HIGH, score 9)
        row0 = df_targets.iloc[0]
        self.assertEqual(row0["target_score"], 9.0)
        self.assertEqual(row0["target_score_norm"], 0.9)
        self.assertEqual(row0["target_decision_id"], DECISION_TO_ID["PRESERVED"])
        self.assertEqual(row0["target_error_id"], ERROR_TYPE_TO_ID["NONE"])
        self.assertEqual(row0["is_preserved"], 1)
        self.assertFalse(row0["is_needs_review"])
        self.assertTrue(row0["is_primary_train"])
        self.assertEqual(row0["sample_weight_clean"], 1.0)
        self.assertEqual(row0["sample_weight_soft"], 1.0)  # HIGH (1.0) * SIMPLIFIED (1.0)

        # Check values for row 1 (NEEDS_REVIEW, MEDIUM, score 8)
        row1 = df_targets.iloc[1]
        self.assertEqual(row1["target_score"], 8.0)
        self.assertEqual(row1["target_score_norm"], 0.8)
        self.assertEqual(row1["target_decision_id"], DECISION_TO_ID["MOSTLY_PRESERVED"])
        self.assertEqual(row1["target_error_id"], ERROR_TYPE_TO_ID["SCOPE_CHANGE"])
        self.assertEqual(row1["is_preserved"], 0)
        self.assertTrue(row1["is_needs_review"])
        self.assertFalse(row1["is_primary_train"])
        self.assertEqual(row1["sample_weight_clean"], 0.0)  # Excluded under clean
        self.assertAlmostEqual(row1["sample_weight_soft"], 0.85 * 0.50, places=3)  # MEDIUM * NEEDS_REVIEW

    def test_clean_train_saving(self):
        import tempfile
        df_targets = add_supervision_targets(self.valid_ai_df)
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = {
                "supervision_metadata": {"is_human_gold": False},
                "total_records": 2,
            }
            paths = save_processed_splits(
                train_df=df_targets,
                val_df=df_targets.iloc[:1],
                test_df=df_targets.iloc[1:],
                full_df=df_targets,
                output_dir=Path(tmpdir),
                metadata=meta,
            )
            self.assertTrue(paths["train_clean"].exists())
            clean_saved = pd.read_csv(paths["train_clean"])
            # Only row 0 was SIMPLIFIED / is_primary_train=True
            self.assertEqual(len(clean_saved), 1)
            self.assertEqual(clean_saved.iloc[0]["pair_id"], "LMP_EN_001")

    def test_valid_ai_audited_validation(self):
        audited_df = self.valid_ai_df.copy()
        audited_df["annotation_status"] = "AI_AUDITED"
        summary = validate_annotation_dataset(audited_df)
        self.assertEqual(summary["status"], "PASSED")
        self.assertEqual(summary["schema_type"], "ai_audited")

    def test_invalid_annotation_status_fails(self):
        bad_df = self.valid_ai_df.copy()
        bad_df.loc[0, "annotation_status"] = "HUMAN_GOLD"  # Invalid status
        with self.assertRaises(ValueError) as ctx:
            validate_annotation_dataset(bad_df)
        self.assertIn("Invalid annotation_status found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

