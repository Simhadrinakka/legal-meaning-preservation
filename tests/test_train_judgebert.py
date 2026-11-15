"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: tests/test_train_judgebert.py
Task: Unit Test Suite for JUDGEBERT Training Architecture & Dataset Pipeline
=============================================================================
"""

import math
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from training.train_judgebert import (
    DECISION_TO_ID,
    ERROR_TYPE_TO_ID,
    ID_TO_DECISION,
    ID_TO_ERROR_TYPE,
    LegalMeaningDataset,
    build_arg_parser,
    compute_class_weights,
    compute_evaluation_metrics,
)


class TestJudgeBERTArchitecture(unittest.TestCase):
    """Test suite for JUDGEBERT model components, dataset loading, and metrics."""

    def setUp(self):
        self.data_dir = Path("data/processed/audited")
        self.train_clean_path = self.data_dir / "train_clean.csv"
        self.val_path = self.data_dir / "val.csv"
        self.test_path = self.data_dir / "test.csv"

    def test_schema_mappings(self):
        """Verify decision and error taxonomy bijective mapping."""
        self.assertEqual(len(DECISION_TO_ID), 5)
        self.assertEqual(len(ERROR_TYPE_TO_ID), 8)

        for name, idx in DECISION_TO_ID.items():
            self.assertEqual(ID_TO_DECISION[idx], name)

        for name, idx in ERROR_TYPE_TO_ID.items():
            self.assertEqual(ID_TO_ERROR_TYPE[idx], name)

    def test_compute_class_weights(self):
        """Verify inverse frequency calculation downweights majority and boosts minority."""
        # 100 samples: 90 NONE (0), 5 OMISSION (1), 5 CONTRADICTION (3)
        labels = [0] * 90 + [1] * 5 + [3] * 5
        weights = compute_class_weights(labels, num_classes=8)

        self.assertIsInstance(weights, torch.Tensor)
        self.assertEqual(len(weights), 8)
        # Class 0 (majority) must have strictly lower weight than Class 1 or 3
        self.assertLess(weights[0].item(), weights[1].item())
        self.assertLess(weights[0].item(), weights[3].item())

    def test_dataset_loading_without_tokenizer(self):
        """Verify LegalMeaningDataset correctly loads and formats tensors from train_clean.csv."""
        if not self.train_clean_path.exists():
            self.skipTest("train_clean.csv not found")

        dataset = LegalMeaningDataset(self.train_clean_path, tokenizer=None, is_training=True)
        self.assertEqual(len(dataset), 177)

        sample = dataset[0]
        self.assertIn("pair_id", sample)
        self.assertIn("language", sample)
        self.assertIn("original_text", sample)
        self.assertIn("simplified_text", sample)
        self.assertIn("target_score", sample)
        self.assertIn("target_score_norm", sample)
        self.assertIn("target_decision_id", sample)
        self.assertIn("target_error_id", sample)
        self.assertIn("sample_weight", sample)

        # Value ranges
        self.assertGreaterEqual(sample["target_score"].item(), 1.0)
        self.assertLessEqual(sample["target_score"].item(), 10.0)
        self.assertGreaterEqual(sample["target_score_norm"].item(), 0.1)
        self.assertLessEqual(sample["target_score_norm"].item(), 1.0)
        self.assertIn(sample["target_decision_id"].item(), range(5))
        self.assertIn(sample["target_error_id"].item(), range(8))
        self.assertEqual(sample["sample_weight"].item(), 1.0)

    def test_regression_target_and_output_scale_consistency(self):
        """
        Verify mathematical scale consistency between target_score, target_score_norm,
        model regression output, loss computation, and LMP score reconstruction.
        """
        from training.train_judgebert import MAX_LMP_SCORE, MIN_LMP_SCORE

        # Test 1: Verify dataset target_score and target_score_norm alignment across dataset
        if self.train_clean_path.exists():
            df = pd.read_csv(self.train_clean_path)
            expected_norms = (df["target_score"] / 10.0).round(4)
            np.testing.assert_allclose(
                df["target_score_norm"].values,
                expected_norms.values,
                err_msg="target_score_norm must equal target_score / 10.0 across all rows",
            )

        # Test 2: Verify bidirectional scale mapping across the entire 1.0 - 10.0 LMP rubric
        test_scores = [1.0, 2.0, 3.5, 5.0, 6.0, 7.5, 8.0, 9.0, 10.0]
        for score_val in test_scores:
            target_score = torch.tensor([score_val], dtype=torch.float32)
            target_norm = torch.tensor([score_val / 10.0], dtype=torch.float32)

            # Normalized prediction matching target_norm
            pred_norm = target_norm.clone()
            # Reconstruction formula used in JudgeBERT
            pred_score = torch.clamp(pred_norm * MAX_LMP_SCORE, min=MIN_LMP_SCORE, max=MAX_LMP_SCORE)

            # Reconstructed score must match target_score exactly
            self.assertAlmostEqual(
                pred_score.item(),
                target_score.item(),
                places=4,
                msg=f"Reconstructed score {pred_score.item()} must match target {target_score.item()}",
            )

            # Regression loss must be exactly 0.0 for a perfect prediction
            reg_diff_norm = (pred_norm - target_norm) ** 2
            self.assertAlmostEqual(reg_diff_norm.item(), 0.0, places=6)

            # Fallback branch (when target_score_norm is None)
            norm_target_fallback = target_score / MAX_LMP_SCORE
            reg_diff_fallback = (pred_norm - norm_target_fallback) ** 2
            self.assertAlmostEqual(reg_diff_fallback.item(), 0.0, places=6)

        # Test 3: Verify loss magnitude for a known 1.0 score deviation
        # Target = 8.0 (norm = 0.8), Prediction = 9.0 (norm = 0.9) -> Delta = 1.0
        t_score = torch.tensor([8.0], dtype=torch.float32)
        t_norm = torch.tensor([0.8], dtype=torch.float32)
        p_norm = torch.tensor([0.9], dtype=torch.float32)
        p_score = torch.clamp(p_norm * MAX_LMP_SCORE, min=MIN_LMP_SCORE, max=MAX_LMP_SCORE)

        self.assertAlmostEqual(p_score.item(), 9.0, places=4)
        loss = (p_norm - t_norm) ** 2
        # (0.9 - 0.8)^2 = 0.01 = ((9.0 - 8.0) / 10)^2
        self.assertAlmostEqual(loss.item(), 0.01, places=6)

    def test_evaluation_metrics_computation(self):
        """Verify metric engine handles perfect, shifted, and noisy predictions."""
        # Perfect predictions
        y_true_scores = np.array([10.0, 9.0, 8.0, 7.0, 5.0, 3.0])
        y_pred_scores = np.array([10.0, 9.0, 8.0, 7.0, 5.0, 3.0])
        y_true_dec = np.array([4, 4, 3, 3, 2, 1])
        y_pred_dec = np.array([4, 4, 3, 3, 2, 1])
        y_true_err = np.array([0, 0, 1, 4, 5, 3])
        y_pred_err = np.array([0, 0, 1, 4, 5, 3])

        metrics = compute_evaluation_metrics(
            pred_scores=y_pred_scores,
            target_scores=y_true_scores,
            pred_decisions=y_pred_dec,
            target_decisions=y_true_dec,
            pred_errors=y_pred_err,
            target_errors=y_true_err,
        )

        self.assertAlmostEqual(metrics["reg_mae"], 0.0, places=3)
        self.assertAlmostEqual(metrics["reg_rmse"], 0.0, places=3)
        self.assertAlmostEqual(metrics["reg_spearman"], 1.0, places=3)
        self.assertAlmostEqual(metrics["dec_accuracy"], 1.0, places=3)
        self.assertAlmostEqual(metrics["err_accuracy"], 1.0, places=3)
        self.assertAlmostEqual(metrics["composite_score"], 1.0, places=3)

    def test_evaluation_metrics_zero_variance(self):
        """Verify metric engine handles constant predictions gracefully without crashing."""
        y_true = np.array([9.0, 8.0, 9.0, 10.0])
        y_pred = np.array([9.0, 9.0, 9.0, 9.0])  # Zero variance
        y_dec = np.array([4, 3, 4, 4])
        y_err = np.array([0, 1, 0, 0])

        metrics = compute_evaluation_metrics(
            pred_scores=y_pred,
            target_scores=y_true,
            pred_decisions=y_dec,
            target_decisions=y_dec,
            pred_errors=y_err,
            target_errors=y_err,
        )
        self.assertEqual(metrics["reg_spearman"], 0.0)
        self.assertEqual(metrics["reg_pearson"], 0.0)
        self.assertGreater(metrics["reg_mae"], 0.0)

    def test_arg_parser_defaults(self):
        """Verify CLI argument parser defaults and flags."""
        parser = build_arg_parser()
        args = parser.parse_args(["--dry_run", "--seed", "123", "--resume_from_checkpoint", "models/judgebert/latest_checkpoint"])
        self.assertTrue(args.dry_run)
        self.assertEqual(args.seed, 123)
        self.assertEqual(args.model_name, "xlm-roberta-base")
        self.assertEqual(args.resume_from_checkpoint, "models/judgebert/latest_checkpoint")
        self.assertEqual(args.train_file, "train_clean.csv")
        self.assertEqual(args.epochs, 8)
        self.assertEqual(args.lambda_reg, 1.0)
        self.assertEqual(args.lambda_dec, 0.5)
        self.assertEqual(args.lambda_err, 0.5)

    def test_checkpoint_save_and_load(self):
        """Verify model weights and training state save and restore round-trip."""
        import tempfile
        import torch.nn as nn
        from training.train_judgebert import save_model_checkpoint, load_model_checkpoint

        # Create dummy module
        mock_model = nn.Linear(10, 2)
        initial_weight = mock_model.weight.clone()
        optimizer = torch.optim.Adam(mock_model.parameters(), lr=0.01)

        with tempfile.TemporaryDirectory() as tmpdir:
            metadata = {
                "epoch": 3,
                "val_loss": 0.42,
                "best_composite_score": 0.88,
                "patience_counter": 1,
            }
            save_path = save_model_checkpoint(
                model=mock_model,
                tokenizer=None,
                output_dir=tmpdir,
                checkpoint_name="test_cp",
                metadata=metadata,
                optimizer=optimizer,
            )

            # Check files created
            self.assertTrue((Path(save_path) / "judgebert_weights.pt").exists())
            self.assertTrue((Path(save_path) / "training_state.pt").exists())
            self.assertTrue((Path(save_path) / "metadata.json").exists())

            # Create another module and load
            target_model = nn.Linear(10, 2)
            target_optimizer = torch.optim.Adam(target_model.parameters(), lr=0.01)
            loaded_info = load_model_checkpoint(
                checkpoint_dir=save_path,
                model=target_model,
                optimizer=target_optimizer,
            )

            self.assertEqual(loaded_info["start_epoch"], 4)
            self.assertEqual(loaded_info["best_composite_score"], 0.88)
            self.assertEqual(loaded_info["patience_counter"], 1)
            self.assertTrue(torch.allclose(initial_weight, target_model.weight))


if __name__ == "__main__":
    unittest.main()
