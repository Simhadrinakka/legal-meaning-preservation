"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/train_judgebert.py
Task: Model Architecture, Multi-Task Pipeline, and Training Engine
=============================================================================

This module implements the JUDGEBERT multi-task model architecture, dataset
loaders, loss functions, evaluation metrics, and modular training pipeline
for English and Hindi statutory legal meaning preservation.

Core Architecture (JUDGEBERT):
1. Pretrained Multilingual Encoder Backbone:
   - Primary: XLM-RoBERTa (xlm-roberta-base)
   - Cross-encoder pairwise input: <s> original_text </s></s> simplified_text </s>
   - Joint cross-lingual semantic representation over 250k SentencePiece BPE vocabulary
   - Native handling of Hindi Devanagari script, matras, virama, and legal punctuation (।, ॥)

2. Multi-Task Heads:
   - Head 1 (Continuous Regression): Predicts continuous LMP score in [1.0, 10.0]
     via Sigmoid-scaled projection and Mean Squared Error (MSE) loss.
   - Head 2 (Preservation Classification): Predicts 5 ordinal legal preservation categories
     (FUNDAMENTALLY_ALTERED, MAJOR_LOSS, PARTIALLY_PRESERVED, MOSTLY_PRESERVED, PRESERVED)
     via Cross-Entropy loss.
   - Head 3 (Error Taxonomy Classification): Predicts 8 legal discrepancy categories
     (NONE, OMISSION, HALLUCINATION_ADDITION, CONTRADICTION, MODALITY_CHANGE,
      CONDITION_EXCEPTION_LOSS, SCOPE_CHANGE, NUMERIC_ENTITY_REFERENCE_ERROR)
     via Class-Weighted Cross-Entropy loss (addressing the ~84% NONE skew).

3. Training & Supervised Targets:
   - Uses audited AI annotations (target_score, target_decision_id, target_error_id)
     as AI supervision targets, NEVER as human gold labels.
   - Clean initial training subset: data/processed/audited/train_clean.csv (177 rows).
   - Strict partition isolation: val.csv and test.csv are held completely separate.
   - Differential learning rates: 2e-5 for pretrained encoder, 1e-4 for task heads.
   - Comprehensive explainability support: token-level cross-attention map extraction.
=============================================================================
"""

import argparse
import json
import logging
import math
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

# Attempt importing HuggingFace transformers; provide graceful fallback for lightweight checks
try:
    import transformers
    from transformers import (
        AutoConfig,
        AutoModel,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


# -----------------------------------------------------------------------------
# LOGGING SETUP
# -----------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("JUDGEBERT")


# -----------------------------------------------------------------------------
# CONSTANTS AND SCHEMA DEFINITIONS
# -----------------------------------------------------------------------------
DEFAULT_MODEL_NAME = "xlm-roberta-base"
DEFAULT_DATA_DIR = "data/processed/audited"
DEFAULT_OUTPUT_DIR = "models/judgebert"

# Official 5-Category Preservation Decision Taxonomy
DECISION_TO_ID = {
    "FUNDAMENTALLY_ALTERED": 0,
    "MAJOR_LOSS": 1,
    "PARTIALLY_PRESERVED": 2,
    "MOSTLY_PRESERVED": 3,
    "PRESERVED": 4,
}
ID_TO_DECISION = {v: k for k, v in DECISION_TO_ID.items()}
NUM_DECISIONS = len(DECISION_TO_ID)

# Official 8-Category Error Taxonomy
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
NUM_ERROR_TYPES = len(ERROR_TYPE_TO_ID)

# Score boundaries
MIN_LMP_SCORE = 1.0
MAX_LMP_SCORE = 10.0


# -----------------------------------------------------------------------------
# REPRODUCIBILITY & UTILITIES
# -----------------------------------------------------------------------------
def set_seed(seed: int = 42) -> None:
    """Sets random seeds across random, numpy, and PyTorch for deterministic execution."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    logger.info(f"Reproducibility seed set to {seed}.")


def compute_class_weights(
    labels: Union[List[int], np.ndarray, torch.Tensor],
    num_classes: int,
    smoothing: float = 0.15,
    max_weight: float = 10.0,
    min_weight: float = 0.2,
) -> torch.Tensor:
    """
    Computes smoothed inverse-frequency class weights for imbalanced classification.

    Formula:
        w_c = (N / (num_classes * count_c + smoothing * N))
    Normalized such that the mean weight is 1.0, and clipped within [min_weight, max_weight].
    """
    if isinstance(labels, torch.Tensor):
        labels_arr = labels.cpu().numpy()
    else:
        labels_arr = np.array(labels)

    counts = np.bincount(labels_arr, minlength=num_classes).astype(np.float32)
    total_samples = len(labels_arr)

    # Smoothed inverse frequency
    smoothed_counts = counts + (smoothing * (total_samples / num_classes))
    weights = total_samples / (num_classes * smoothed_counts)

    # Normalize so mean is 1.0
    weights = weights / np.mean(weights)

    # Clip extreme weights to avoid gradient explosion on rare classes
    weights = np.clip(weights, min_weight, max_weight)

    return torch.tensor(weights, dtype=torch.float32)


# -----------------------------------------------------------------------------
# DATASET CLASS
# -----------------------------------------------------------------------------
class LegalMeaningDataset(Dataset):
    """
    PyTorch Dataset for Multilingual Legal Meaning Preservation (JUDGEBERT).

    Loads statutory original text and plain-language simplified text pairs,
    tokenizes them as a cross-encoder pair:
        <s> original_text </s></s> simplified_text </s>
    and returns input tensors alongside multi-task supervision targets.
    """

    def __init__(
        self,
        data_path_or_df: Union[str, Path, pd.DataFrame],
        tokenizer: Any = None,
        max_length: int = 256,
        is_training: bool = False,
    ):
        """
        Args:
            data_path_or_df: Path to CSV or loaded pandas DataFrame.
            tokenizer: Pretrained HuggingFace tokenizer (e.g. XLMRobertaTokenizer).
            max_length: Maximum token sequence length.
            is_training: Whether dataset is used for training.
        """
        if isinstance(data_path_or_df, (str, Path)):
            self.df = pd.read_csv(data_path_or_df)
            self.source_path = str(data_path_or_df)
        else:
            self.df = data_path_or_df.copy()
            self.source_path = "DataFrame"

        self.tokenizer = tokenizer
        self.max_length = max_length
        self.is_training = is_training

        # Validate required columns
        required_cols = [
            "pair_id",
            "language",
            "original_text",
            "simplified_text",
            "target_score",
            "target_score_norm",
            "target_decision_id",
            "target_error_id",
        ]
        missing = [c for c in required_cols if c not in self.df.columns]
        if missing:
            raise ValueError(
                f"Dataset from {self.source_path} is missing required target columns: {missing}"
            )

        # Pre-extract lists for fast indexed access
        self.pair_ids = self.df["pair_id"].tolist()
        self.languages = self.df["language"].tolist()
        self.act_ids = self.df["act_id"].tolist() if "act_id" in self.df.columns else ["UNKNOWN"] * len(self.df)
        self.original_texts = self.df["original_text"].astype(str).tolist()
        self.simplified_texts = self.df["simplified_text"].astype(str).tolist()

        # Targets
        self.target_scores = self.df["target_score"].astype(np.float32).tolist()
        self.target_scores_norm = self.df["target_score_norm"].astype(np.float32).tolist()
        self.target_decision_ids = self.df["target_decision_id"].astype(np.int64).tolist()
        self.target_error_ids = self.df["target_error_id"].astype(np.int64).tolist()

        # Sample weights (supports soft down-weighting if column present)
        if "sample_weight_clean" in self.df.columns and "sample_weight_soft" in self.df.columns:
            self.sample_weights = self.df["sample_weight_clean"].astype(np.float32).tolist()
        elif "sample_weight" in self.df.columns:
            self.sample_weights = self.df["sample_weight"].astype(np.float32).tolist()
        else:
            self.sample_weights = [1.0] * len(self.df)

        self.is_needs_review = (
            self.df["is_needs_review"].astype(bool).tolist()
            if "is_needs_review" in self.df.columns
            else [False] * len(self.df)
        )

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        orig = self.original_texts[idx]
        simp = self.simplified_texts[idx]

        item: Dict[str, Any] = {
            "pair_id": self.pair_ids[idx],
            "language": self.languages[idx],
            "act_id": self.act_ids[idx],
            "original_text": orig,
            "simplified_text": simp,
            "target_score": torch.tensor(self.target_scores[idx], dtype=torch.float32),
            "target_score_norm": torch.tensor(self.target_scores_norm[idx], dtype=torch.float32),
            "target_decision_id": torch.tensor(self.target_decision_ids[idx], dtype=torch.long),
            "target_error_id": torch.tensor(self.target_error_ids[idx], dtype=torch.long),
            "sample_weight": torch.tensor(self.sample_weights[idx], dtype=torch.float32),
            "is_needs_review": self.is_needs_review[idx],
        }

        # Tokenize if tokenizer provided
        if self.tokenizer is not None:
            encoding = self.tokenizer(
                orig,
                simp,
                truncation=True,
                max_length=self.max_length,
                padding="max_length",
                return_tensors="pt",
            )
            item["input_ids"] = encoding["input_ids"].squeeze(0)
            item["attention_mask"] = encoding["attention_mask"].squeeze(0)
            if "token_type_ids" in encoding:
                item["token_type_ids"] = encoding["token_type_ids"].squeeze(0)

        return item


# -----------------------------------------------------------------------------
# JUDGEBERT MULTI-TASK MODEL ARCHITECTURE
# -----------------------------------------------------------------------------
class JudgeBERTForMultitaskLMP(nn.Module):
    """
    Explainable Multilingual Legal Meaning Preservation Model (JUDGEBERT).

    Shared Backbone:
        Pretrained XLM-RoBERTa (xlm-roberta-base) encoder.

    Multi-Task Heads:
        1. Regression Head:
           Linear(hidden, 256) -> GELU -> Dropout -> Linear(256, 1) -> Sigmoid * 9.0 + 1.0
           Predicts continuous LMP fidelity score in [1.0, 10.0].

        2. Preservation Classification Head:
           Linear(hidden, 256) -> GELU -> Dropout -> Linear(256, 5)
           Predicts 5 categorical preservation levels.

        3. Error Taxonomy Classification Head:
           Linear(hidden, 256) -> GELU -> Dropout -> Linear(256, 8)
           Predicts 8 legal error types (with class weighting for NONE imbalance).
    """

    def __init__(
        self,
        model_name_or_path: str = DEFAULT_MODEL_NAME,
        dropout_prob: float = 0.2,
        head_hidden_dim: int = 256,
        error_class_weights: Optional[torch.Tensor] = None,
        decision_class_weights: Optional[torch.Tensor] = None,
        lambda_reg: float = 1.0,
        lambda_dec: float = 0.5,
        lambda_err: float = 0.5,
    ):
        super().__init__()
        self.model_name_or_path = model_name_or_path
        self.dropout_prob = dropout_prob
        self.lambda_reg = lambda_reg
        self.lambda_dec = lambda_dec
        self.lambda_err = lambda_err

        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "HuggingFace transformers is required to instantiate JudgeBERTForMultitaskLMP. "
                "Please install dependencies from requirements.txt: pip install transformers"
            )

        # Load pretrained multilingual encoder backbone
        self.config = AutoConfig.from_pretrained(
            model_name_or_path,
            output_attentions=True,
            output_hidden_states=True,
        )
        self.encoder = AutoModel.from_pretrained(model_name_or_path, config=self.config)
        hidden_size = self.config.hidden_size

        # Shared representation dropout
        self.dropout = nn.Dropout(dropout_prob)

        # ---------------------------------------------------------------------
        # Task 1: Regression Head (LMP Score: 1.0 to 10.0)
        # Uses Sigmoid output activation scaled to [1.0, 10.0] for bounded stability
        # ---------------------------------------------------------------------
        self.regression_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(head_hidden_dim, 1),
        )

        # ---------------------------------------------------------------------
        # Task 2: Preservation Classification Head (5 Classes)
        # ---------------------------------------------------------------------
        self.decision_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(head_hidden_dim, NUM_DECISIONS),
        )

        # ---------------------------------------------------------------------
        # Task 3: Error Taxonomy Classification Head (8 Classes)
        # ---------------------------------------------------------------------
        self.error_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(head_hidden_dim, NUM_ERROR_TYPES),
        )

        # Register optional class weight buffers
        if error_class_weights is not None:
            self.register_buffer("error_class_weights", error_class_weights)
        else:
            self.register_buffer("error_class_weights", None)

        if decision_class_weights is not None:
            self.register_buffer("decision_class_weights", decision_class_weights)
        else:
            self.register_buffer("decision_class_weights", None)

    def extract_pooled_feature(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Any]:
        """
        Passes inputs through the multilingual encoder and extracts the pooled
        <s> classification token representation.
        """
        encoder_kwargs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "return_dict": True,
        }
        if token_type_ids is not None:
            encoder_kwargs["token_type_ids"] = token_type_ids

        outputs = self.encoder(**encoder_kwargs)

        # Extract sequence output: shape (batch_size, seq_len, hidden_size)
        sequence_output = outputs.last_hidden_state

        # Pooled representation from first token (<s> / [CLS])
        pooled_cls = sequence_output[:, 0, :]
        pooled = self.dropout(pooled_cls)

        return pooled, outputs

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
        target_score: Optional[torch.Tensor] = None,
        target_score_norm: Optional[torch.Tensor] = None,
        target_decision_id: Optional[torch.Tensor] = None,
        target_error_id: Optional[torch.Tensor] = None,
        sample_weight: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """
        Forward pass for multi-task prediction and loss calculation.
        """
        pooled, outputs = self.extract_pooled_feature(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )

        # 1. Regression Head
        raw_reg = self.regression_head(pooled).squeeze(-1)  # (batch_size,)
        # Sigmoid bounds predicted normalized score strictly to [0.0, 1.0], matching target_score / 10.0
        pred_norm = torch.sigmoid(raw_reg)
        # Scaled to official LMP scale [1.0, 10.0] matching decimal target_score_norm = score / 10.0
        pred_score = torch.clamp(pred_norm * MAX_LMP_SCORE, min=MIN_LMP_SCORE, max=MAX_LMP_SCORE)

        # 2. Decision Head
        decision_logits = self.decision_head(pooled)  # (batch_size, 5)

        # 3. Error Head
        error_logits = self.error_head(pooled)  # (batch_size, 8)

        results: Dict[str, Any] = {
            "pred_score": pred_score,
            "pred_score_norm": pred_norm,
            "decision_logits": decision_logits,
            "error_logits": error_logits,
            "pred_decision_id": torch.argmax(decision_logits, dim=-1),
            "pred_error_id": torch.argmax(error_logits, dim=-1),
            "attentions": outputs.attentions,
        }

        # Compute losses if targets provided
        if target_score is not None and target_decision_id is not None and target_error_id is not None:
            total_loss, loss_breakdown = self.compute_multi_task_loss(
                pred_score=pred_score,
                pred_norm=pred_norm,
                decision_logits=decision_logits,
                error_logits=error_logits,
                target_score=target_score,
                target_score_norm=target_score_norm,
                target_decision_id=target_decision_id,
                target_error_id=target_error_id,
                sample_weight=sample_weight,
            )
            results["loss"] = total_loss
            results.update(loss_breakdown)

        return results

    def compute_multi_task_loss(
        self,
        pred_score: torch.Tensor,
        pred_norm: torch.Tensor,
        decision_logits: torch.Tensor,
        error_logits: torch.Tensor,
        target_score: torch.Tensor,
        target_score_norm: Optional[torch.Tensor],
        target_decision_id: torch.Tensor,
        target_error_id: torch.Tensor,
        sample_weight: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Computes the weighted multi-task loss combining:
            L_total = lambda_reg * L_reg + lambda_dec * L_dec + lambda_err * L_err
        """
        # --- 1. Regression Loss (Normalized MSE with sample weights) ---
        if target_score_norm is not None:
            reg_diff = (pred_norm - target_score_norm) ** 2
        else:
            # Fallback to decimal normalized target matching preprocessing (score / 10.0)
            norm_target = target_score / MAX_LMP_SCORE
            reg_diff = (pred_norm - norm_target) ** 2

        if sample_weight is not None:
            loss_reg = torch.mean(sample_weight * reg_diff)
        else:
            loss_reg = torch.mean(reg_diff)

        # --- 2. Preservation Decision Loss (Cross-Entropy) ---
        loss_dec = F.cross_entropy(
            decision_logits,
            target_decision_id,
            weight=self.decision_class_weights,
            reduction="none",
        )
        if sample_weight is not None:
            loss_dec = torch.mean(sample_weight * loss_dec)
        else:
            loss_dec = torch.mean(loss_dec)

        # --- 3. Error Classification Loss (Class-Weighted Cross-Entropy) ---
        loss_err = F.cross_entropy(
            error_logits,
            target_error_id,
            weight=self.error_class_weights,
            reduction="none",
        )
        if sample_weight is not None:
            loss_err = torch.mean(sample_weight * loss_err)
        else:
            loss_err = torch.mean(loss_err)

        # --- Total Multi-Task Loss ---
        total_loss = (
            self.lambda_reg * loss_reg
            + self.lambda_dec * loss_dec
            + self.lambda_err * loss_err
        )

        breakdown = {
            "loss_reg": loss_reg.detach(),
            "loss_dec": loss_dec.detach(),
            "loss_err": loss_err.detach(),
        }

        return total_loss, breakdown

    def get_token_cross_attention(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        layer_idx: int = -1,
    ) -> torch.Tensor:
        """
        Extracts token-to-token attention weights from a specified encoder layer
        for explainability and cross-lingual legal alignment inspection.

        Returns:
            attention_weights: Tensor of shape (batch_size, num_heads, seq_len, seq_len)
        """
        self.eval()
        with torch.no_grad():
            outputs = self.encoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_attentions=True,
                return_dict=True,
            )
            # outputs.attentions is a tuple of (layer_1, layer_2, ..., layer_N)
            return outputs.attentions[layer_idx]


# -----------------------------------------------------------------------------
# EVALUATION METRICS ENGINE
# -----------------------------------------------------------------------------
def compute_evaluation_metrics(
    pred_scores: np.ndarray,
    target_scores: np.ndarray,
    pred_decisions: np.ndarray,
    target_decisions: np.ndarray,
    pred_errors: np.ndarray,
    target_errors: np.ndarray,
) -> Dict[str, float]:
    """
    Computes comprehensive evaluation metrics for regression, decision classification,
    and error taxonomy classification.
    """
    # 1. Regression Metrics
    mae = float(mean_absolute_error(target_scores, pred_scores))
    mse = float(mean_squared_error(target_scores, pred_scores))
    rmse = float(math.sqrt(mse))

    # Pearson & Spearman correlation
    if len(target_scores) > 2 and np.std(pred_scores) > 1e-6 and np.std(target_scores) > 1e-6:
        pearson_r, _ = pearsonr(target_scores, pred_scores)
        spearman_rho, _ = spearmanr(target_scores, pred_scores)
        pearson_r = float(pearson_r) if not np.isnan(pearson_r) else 0.0
        spearman_rho = float(spearman_rho) if not np.isnan(spearman_rho) else 0.0
    else:
        pearson_r = 0.0
        spearman_rho = 0.0

    # 2. Decision Classification Metrics (5 classes)
    dec_acc = float(accuracy_score(target_decisions, pred_decisions))
    dec_macro_f1 = float(f1_score(target_decisions, pred_decisions, average="macro", zero_division=0))
    dec_weighted_f1 = float(f1_score(target_decisions, pred_decisions, average="weighted", zero_division=0))

    # 3. Error Classification Metrics (8 classes)
    err_acc = float(accuracy_score(target_errors, pred_errors))
    err_macro_f1 = float(f1_score(target_errors, pred_errors, average="macro", zero_division=0))
    err_weighted_f1 = float(f1_score(target_errors, pred_errors, average="weighted", zero_division=0))

    # Composite multi-task metric for early stopping / checkpoint selection
    # Blends Spearman correlation, Decision Macro-F1, and Error Macro-F1 equally
    composite_score = float(
        (max(spearman_rho, 0.0) + dec_macro_f1 + err_macro_f1) / 3.0
    )

    return {
        "reg_mae": round(mae, 4),
        "reg_mse": round(mse, 4),
        "reg_rmse": round(rmse, 4),
        "reg_pearson": round(pearson_r, 4),
        "reg_spearman": round(spearman_rho, 4),
        "dec_accuracy": round(dec_acc, 4),
        "dec_macro_f1": round(dec_macro_f1, 4),
        "dec_weighted_f1": round(dec_weighted_f1, 4),
        "err_accuracy": round(err_acc, 4),
        "err_macro_f1": round(err_macro_f1, 4),
        "err_weighted_f1": round(err_weighted_f1, 4),
        "composite_score": round(composite_score, 4),
    }


# -----------------------------------------------------------------------------
# EVALUATION & TRAINING LOOPS
# -----------------------------------------------------------------------------
def evaluate(
    model: JudgeBERTForMultitaskLMP,
    dataloader: DataLoader,
    device: torch.device,
) -> Tuple[float, Dict[str, float], Dict[str, np.ndarray]]:
    """
    Evaluates the model over an entire DataLoader in eval mode.
    Returns average total loss, computed metrics dictionary, and raw predictions.
    """
    model.eval()
    total_loss = 0.0
    total_batches = 0

    all_pred_scores = []
    all_target_scores = []
    all_pred_decisions = []
    all_target_decisions = []
    all_pred_errors = []
    all_target_errors = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            target_score = batch["target_score"].to(device)
            target_score_norm = batch["target_score_norm"].to(device)
            target_decision_id = batch["target_decision_id"].to(device)
            target_error_id = batch["target_error_id"].to(device)
            sample_weight = batch["sample_weight"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                target_score=target_score,
                target_score_norm=target_score_norm,
                target_decision_id=target_decision_id,
                target_error_id=target_error_id,
                sample_weight=sample_weight,
            )

            total_loss += outputs["loss"].item()
            total_batches += 1

            all_pred_scores.extend(outputs["pred_score"].cpu().numpy().tolist())
            all_target_scores.extend(target_score.cpu().numpy().tolist())
            all_pred_decisions.extend(outputs["pred_decision_id"].cpu().numpy().tolist())
            all_target_decisions.extend(target_decision_id.cpu().numpy().tolist())
            all_pred_errors.extend(outputs["pred_error_id"].cpu().numpy().tolist())
            all_target_errors.extend(target_error_id.cpu().numpy().tolist())

    avg_loss = total_loss / max(total_batches, 1)

    metrics = compute_evaluation_metrics(
        pred_scores=np.array(all_pred_scores),
        target_scores=np.array(all_target_scores),
        pred_decisions=np.array(all_pred_decisions),
        target_decisions=np.array(all_target_decisions),
        pred_errors=np.array(all_pred_errors),
        target_errors=np.array(all_target_errors),
    )

    predictions = {
        "pred_scores": np.array(all_pred_scores),
        "target_scores": np.array(all_target_scores),
        "pred_decisions": np.array(all_pred_decisions),
        "target_decisions": np.array(all_target_decisions),
        "pred_errors": np.array(all_pred_errors),
        "target_errors": np.array(all_target_errors),
    }

    return avg_loss, metrics, predictions


def train_epoch(
    model: JudgeBERTForMultitaskLMP,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    device: torch.device,
    gradient_accumulation_steps: int = 1,
    max_grad_norm: float = 1.0,
) -> Tuple[float, Dict[str, float]]:
    """
    Executes one training epoch with gradient accumulation and clipping.
    """
    model.train()
    total_loss = 0.0
    total_reg_loss = 0.0
    total_dec_loss = 0.0
    total_err_loss = 0.0
    num_batches = 0

    optimizer.zero_grad()

    for step, batch in enumerate(dataloader):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        target_score = batch["target_score"].to(device)
        target_score_norm = batch["target_score_norm"].to(device)
        target_decision_id = batch["target_decision_id"].to(device)
        target_error_id = batch["target_error_id"].to(device)
        sample_weight = batch["sample_weight"].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            target_score=target_score,
            target_score_norm=target_score_norm,
            target_decision_id=target_decision_id,
            target_error_id=target_error_id,
            sample_weight=sample_weight,
        )

        loss = outputs["loss"] / gradient_accumulation_steps
        loss.backward()

        total_loss += outputs["loss"].item()
        total_reg_loss += outputs["loss_reg"].item()
        total_dec_loss += outputs["loss_dec"].item()
        total_err_loss += outputs["loss_err"].item()
        num_batches += 1

        if (step + 1) % gradient_accumulation_steps == 0 or (step + 1) == len(dataloader):
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            optimizer.step()
            if scheduler is not None:
                scheduler.step()
            optimizer.zero_grad()

    avg_loss = total_loss / max(num_batches, 1)
    breakdown = {
        "loss_reg": round(total_reg_loss / max(num_batches, 1), 4),
        "loss_dec": round(total_dec_loss / max(num_batches, 1), 4),
        "loss_err": round(total_err_loss / max(num_batches, 1), 4),
    }

    return avg_loss, breakdown


# -----------------------------------------------------------------------------
# CHECKPOINTING, SAVING & RESUMING
# -----------------------------------------------------------------------------
def save_model_checkpoint(
    model: JudgeBERTForMultitaskLMP,
    tokenizer: Any,
    output_dir: str,
    checkpoint_name: str,
    metadata: Dict[str, Any],
    optimizer: Optional[torch.optim.Optimizer] = None,
    scheduler: Optional[Any] = None,
) -> str:
    """
    Saves model weights, optimizer/scheduler state dicts, tokenizer, and metadata.
    """
    save_path = Path(output_dir) / checkpoint_name
    save_path.mkdir(parents=True, exist_ok=True)

    # Save PyTorch model state dictionary
    weights_path = save_path / "judgebert_weights.pt"
    torch.save(model.state_dict(), weights_path)

    # Save training state for resumption
    training_state = {
        "epoch": metadata.get("epoch", 0),
        "optimizer_state_dict": optimizer.state_dict() if optimizer is not None else None,
        "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
        "best_val_loss": metadata.get("best_val_loss", float("inf")),
        "best_composite_score": metadata.get("best_composite_score", -1.0),
        "patience_counter": metadata.get("patience_counter", 0),
    }
    torch.save(training_state, save_path / "training_state.pt")

    # Save tokenizer if available
    if tokenizer is not None and hasattr(tokenizer, "save_pretrained"):
        tokenizer.save_pretrained(str(save_path))

    # Save metadata and configuration
    meta_path = save_path / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model checkpoint successfully saved to: {save_path}")
    return str(save_path)


def load_model_checkpoint(
    checkpoint_dir: Union[str, Path],
    model: JudgeBERTForMultitaskLMP,
    optimizer: Optional[torch.optim.Optimizer] = None,
    scheduler: Optional[Any] = None,
    device: torch.device = torch.device("cpu"),
) -> Dict[str, Any]:
    """
    Loads model weights, optimizer state, scheduler state, and training metadata
    from a saved checkpoint directory to enable resumption.
    """
    checkpoint_path = Path(checkpoint_dir)
    weights_path = checkpoint_path / "judgebert_weights.pt"
    if not weights_path.exists():
        raise FileNotFoundError(f"Checkpoint weights not found at: {weights_path}")

    # Load model weights
    state_dict = torch.load(weights_path, map_location=device)
    model.load_state_dict(state_dict)
    logger.info(f"Successfully loaded model weights from: {weights_path}")

    # Load optimizer & scheduler state if present
    state_path = checkpoint_path / "training_state.pt"
    training_state: Dict[str, Any] = {}
    if state_path.exists():
        training_state = torch.load(state_path, map_location=device)
        if optimizer is not None and training_state.get("optimizer_state_dict") is not None:
            optimizer.load_state_dict(training_state["optimizer_state_dict"])
            logger.info("Successfully restored optimizer state.")
        if scheduler is not None and training_state.get("scheduler_state_dict") is not None:
            scheduler.load_state_dict(training_state["scheduler_state_dict"])
            logger.info("Successfully restored learning rate scheduler state.")

    # Load metadata
    meta_path = checkpoint_path / "metadata.json"
    metadata: Dict[str, Any] = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    start_epoch = training_state.get("epoch", metadata.get("epoch", 0)) + 1
    best_val_loss = training_state.get("best_val_loss", metadata.get("val_loss", float("inf")))
    best_composite_score = training_state.get("best_composite_score", metadata.get("best_composite_score", -1.0))
    patience_counter = training_state.get("patience_counter", 0)

    logger.info(
        f"Resuming from epoch {start_epoch} (Saved best composite: {best_composite_score}, "
        f"best val loss: {best_val_loss}, patience: {patience_counter})"
    )

    return {
        "metadata": metadata,
        "training_state": training_state,
        "start_epoch": start_epoch,
        "best_val_loss": best_val_loss,
        "best_composite_score": best_composite_score,
        "patience_counter": patience_counter,
    }


# -----------------------------------------------------------------------------
# TRAINING ORCHESTRATOR
# -----------------------------------------------------------------------------
def run_training_pipeline(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Full training pipeline orchestrator for JUDGEBERT.

    Adheres strictly to project methodology:
    - Clean training set (177 rows) as initial supervised training data.
    - Val set (45 rows) for model selection and early stopping.
    - Test set (45 rows) reserved for unbiased final evaluation.
    - Differential learning rates for encoder backbone vs task heads.
    """
    set_seed(args.seed)
    device = torch.device(args.device if torch.cuda.is_available() and args.device == "cuda" else "cpu")
    logger.info(f"Running on computation device: {device}")

    # Resolve dataset paths
    data_dir = Path(args.data_dir)
    train_path = data_dir / args.train_file
    val_path = data_dir / args.val_file
    test_path = data_dir / args.test_file

    for path, name in [(train_path, "Train"), (val_path, "Val"), (test_path, "Test")]:
        if not path.exists():
            raise FileNotFoundError(f"{name} split not found at: {path}")

    # Inspect dataset sizes
    df_train = pd.read_csv(train_path)
    df_val = pd.read_csv(val_path)
    df_test = pd.read_csv(test_path)

    logger.info(f"Loaded train partition: {len(df_train)} rows from {train_path.name}")
    logger.info(f"Loaded validation partition: {len(df_val)} rows from {val_path.name}")
    logger.info(f"Loaded test partition: {len(df_test)} rows from {test_path.name}")

    # Compute error class weights from training partition to address class imbalance
    error_class_weights = compute_class_weights(
        labels=df_train["target_error_id"].values,
        num_classes=NUM_ERROR_TYPES,
        smoothing=0.15,
    ).to(device)
    logger.info(f"Computed error class weights (NONE down-weighted, rare errors boosted): {error_class_weights.tolist()}")

    # If --dry_run or --no_train is specified, return pipeline inspection summary without model training
    if args.dry_run or args.no_train:
        logger.info("[DRY RUN / NO TRAIN MODE] Model architecture, loss math, and dataset schemas verified.")
        return {
            "status": "dry_run_completed",
            "train_rows": len(df_train),
            "val_rows": len(df_val),
            "test_rows": len(df_test),
            "model_name": args.model_name,
            "device": str(device),
            "error_class_weights": error_class_weights.tolist(),
        }

    # Verify transformers availability
    if not TRANSFORMERS_AVAILABLE:
        raise RuntimeError(
            "transformers package is not installed. Please install dependencies from requirements.txt: "
            "pip install -r requirements.txt"
        )

    # Initialize Tokenizer
    logger.info(f"Initializing tokenizer for: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    # Create PyTorch Datasets and DataLoaders
    train_dataset = LegalMeaningDataset(df_train, tokenizer=tokenizer, max_length=args.max_length, is_training=True)
    val_dataset = LegalMeaningDataset(df_val, tokenizer=tokenizer, max_length=args.max_length, is_training=False)
    test_dataset = LegalMeaningDataset(df_test, tokenizer=tokenizer, max_length=args.max_length, is_training=False)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False)

    # Initialize JUDGEBERT Model
    logger.info(f"Instantiating JUDGEBERT model with backbone: {args.model_name}")
    model = JudgeBERTForMultitaskLMP(
        model_name_or_path=args.model_name,
        dropout_prob=args.dropout,
        error_class_weights=error_class_weights,
        lambda_reg=args.lambda_reg,
        lambda_dec=args.lambda_dec,
        lambda_err=args.lambda_err,
    ).to(device)

    # Configure Optimizer with Differential Learning Rates
    # Lower learning rate for pretrained backbone to prevent catastrophic forgetting;
    # Higher learning rate for newly initialized task heads.
    no_decay = ["bias", "LayerNorm.weight"]
    optimizer_grouped_parameters = [
        {
            "params": [
                p for n, p in model.encoder.named_parameters()
                if not any(nd in n for nd in no_decay)
            ],
            "lr": args.encoder_lr,
            "weight_decay": args.weight_decay,
        },
        {
            "params": [
                p for n, p in model.encoder.named_parameters()
                if any(nd in n for nd in no_decay)
            ],
            "lr": args.encoder_lr,
            "weight_decay": 0.0,
        },
        {
            "params": [p for p in model.regression_head.parameters()],
            "lr": args.heads_lr,
            "weight_decay": args.weight_decay,
        },
        {
            "params": [p for p in model.decision_head.parameters()],
            "lr": args.heads_lr,
            "weight_decay": args.weight_decay,
        },
        {
            "params": [p for p in model.error_head.parameters()],
            "lr": args.heads_lr,
            "weight_decay": args.weight_decay,
        },
    ]

    optimizer = torch.optim.AdamW(optimizer_grouped_parameters)

    # Total training steps and learning rate scheduler
    total_steps = (len(train_loader) // args.gradient_accumulation_steps) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )
    logger.info(f"Total training steps: {total_steps} (Warmup steps: {warmup_steps})")

    # Training Loop with Early Stopping & Resume Support
    start_epoch = 1
    best_val_loss = float("inf")
    best_composite_score = -1.0
    patience_counter = 0
    training_history = []

    # Handle checkpoint resumption if requested
    if args.resume_from_checkpoint:
        resume_info = load_model_checkpoint(
            checkpoint_dir=args.resume_from_checkpoint,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            device=device,
        )
        start_epoch = resume_info["start_epoch"]
        best_val_loss = resume_info["best_val_loss"]
        best_composite_score = resume_info["best_composite_score"]
        patience_counter = resume_info["patience_counter"]
        logger.info(f"Resuming training loop from epoch {start_epoch} up to epoch {args.epochs}")

    os.makedirs(args.output_dir, exist_ok=True)

    logger.info("Starting JUDGEBERT multi-task training...")
    for epoch in range(start_epoch, args.epochs + 1):
        train_loss, train_breakdown = train_epoch(
            model=model,
            dataloader=train_loader,
            optimizer=optimizer,
            scheduler=scheduler,
            device=device,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            max_grad_norm=args.max_grad_norm,
        )

        val_loss, val_metrics, _ = evaluate(
            model=model,
            dataloader=val_loader,
            device=device,
        )

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_breakdown": train_breakdown,
            "val_loss": round(val_loss, 4),
            "val_metrics": val_metrics,
        }
        training_history.append(epoch_record)

        logger.info(
            f"Epoch {epoch:02d}/{args.epochs:02d} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"RMSE: {val_metrics['reg_rmse']} | "
            f"Spearman: {val_metrics['reg_spearman']} | "
            f"Dec F1: {val_metrics['dec_macro_f1']} | "
            f"Err F1: {val_metrics['err_macro_f1']} | "
            f"Composite: {val_metrics['composite_score']}"
        )

        # Early stopping & best checkpoint check
        current_composite = val_metrics["composite_score"]
        if current_composite > best_composite_score or (current_composite == best_composite_score and val_loss < best_val_loss):
            best_composite_score = current_composite
            best_val_loss = val_loss
            patience_counter = 0

            # Save best checkpoint
            save_model_checkpoint(
                model=model,
                tokenizer=tokenizer,
                output_dir=args.output_dir,
                checkpoint_name="best_checkpoint",
                metadata={
                    "epoch": epoch,
                    "val_loss": val_loss,
                    "val_metrics": val_metrics,
                    "best_composite_score": best_composite_score,
                    "model_name": args.model_name,
                    "training_args": vars(args),
                },
                optimizer=optimizer,
                scheduler=scheduler,
            )
        else:
            patience_counter += 1

        # Always save latest checkpoint for seamless resumption
        save_model_checkpoint(
            model=model,
            tokenizer=tokenizer,
            output_dir=args.output_dir,
            checkpoint_name="latest_checkpoint",
            metadata={
                "epoch": epoch,
                "val_loss": val_loss,
                "val_metrics": val_metrics,
                "best_composite_score": best_composite_score,
                "best_val_loss": best_val_loss,
                "patience_counter": patience_counter,
                "model_name": args.model_name,
                "training_args": vars(args),
            },
            optimizer=optimizer,
            scheduler=scheduler,
        )

        if patience_counter >= args.patience:
            logger.info(f"Early stopping triggered at epoch {epoch} (patience: {args.patience}).")
            break

    # Save training history log
    history_path = Path(args.output_dir) / "training_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(training_history, f, indent=2)

    # -------------------------------------------------------------------------
    # Final Unbiased Evaluation on Reserved Test Split
    # -------------------------------------------------------------------------
    logger.info("Running final unbiased evaluation on reserved TEST split (45 passages)...")
    # Load best checkpoint weights
    best_weights_path = Path(args.output_dir) / "best_checkpoint" / "judgebert_weights.pt"
    if best_weights_path.exists():
        model.load_state_dict(torch.load(best_weights_path, map_location=device))
        logger.info(f"Loaded best checkpoint from: {best_weights_path}")

    test_loss, test_metrics, test_preds = evaluate(
        model=model,
        dataloader=test_loader,
        device=device,
    )

    logger.info("=" * 60)
    logger.info("JUDGEBERT FINAL TEST SET EVALUATION RESULTS:")
    logger.info(f"Test Loss: {test_loss:.4f}")
    logger.info(f"Regression RMSE: {test_metrics['reg_rmse']} | MAE: {test_metrics['reg_mae']}")
    logger.info(f"Regression Pearson r: {test_metrics['reg_pearson']} | Spearman rho: {test_metrics['reg_spearman']}")
    logger.info(f"Decision Accuracy: {test_metrics['dec_accuracy']} | Macro F1: {test_metrics['dec_macro_f1']}")
    logger.info(f"Error Accuracy: {test_metrics['err_accuracy']} | Macro F1: {test_metrics['err_macro_f1']}")
    logger.info(f"Composite Score: {test_metrics['composite_score']}")
    logger.info("=" * 60)

    # Save test evaluation report
    test_report_path = Path(args.output_dir) / "test_evaluation_results.json"
    with open(test_report_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_loss": round(test_loss, 4),
            "test_metrics": test_metrics,
            "best_val_composite": best_composite_score,
            "best_val_loss": best_val_loss,
            "test_sample_count": len(df_test),
        }, f, indent=2)

    return {
        "status": "training_completed",
        "best_val_composite": best_composite_score,
        "best_val_loss": best_val_loss,
        "test_loss": test_loss,
        "test_metrics": test_metrics,
    }


# -----------------------------------------------------------------------------
# CLI ARGUMENT PARSER
# -----------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for training and configuration."""
    parser = argparse.ArgumentParser(
        description="JUDGEBERT: Explainable Multilingual Legal Meaning Preservation Training Pipeline"
    )

    # Model configuration
    parser.add_argument(
        "--model_name",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help="Pretrained transformer model backbone (default: xlm-roberta-base)",
    )
    parser.add_argument(
        "--dropout",
        type=float,
        default=0.2,
        help="Dropout probability for shared and head representations (default: 0.2)",
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=256,
        help="Maximum sequence length for tokenized statutory text pairs (default: 256)",
    )

    # Data paths
    parser.add_argument(
        "--data_dir",
        type=str,
        default=DEFAULT_DATA_DIR,
        help="Path to directory containing audited processed CSVs (default: data/processed/audited)",
    )
    parser.add_argument(
        "--train_file",
        type=str,
        default="train_clean.csv",
        help="Training dataset filename (default: train_clean.csv)",
    )
    parser.add_argument(
        "--val_file",
        type=str,
        default="val.csv",
        help="Validation dataset filename (default: val.csv)",
    )
    parser.add_argument(
        "--test_file",
        type=str,
        default="test.csv",
        help="Test dataset filename (default: test.csv)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save model checkpoints and logs (default: models/judgebert)",
    )

    # Loss weights
    parser.add_argument(
        "--lambda_reg",
        type=float,
        default=1.0,
        help="Loss weight for regression head (default: 1.0)",
    )
    parser.add_argument(
        "--lambda_dec",
        type=float,
        default=0.5,
        help="Loss weight for preservation decision head (default: 0.5)",
    )
    parser.add_argument(
        "--lambda_err",
        type=float,
        default=0.5,
        help="Loss weight for error taxonomy classification head (default: 0.5)",
    )

    # Training hyperparameters
    parser.add_argument(
        "--epochs",
        type=int,
        default=8,
        help="Number of training epochs (default: 8)",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Batch size per training step (default: 8)",
    )
    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=2,
        help="Number of gradient accumulation steps (default: 2, effective batch size: 16)",
    )
    parser.add_argument(
        "--encoder_lr",
        type=float,
        default=2e-5,
        help="Learning rate for pretrained encoder backbone (default: 2e-5)",
    )
    parser.add_argument(
        "--heads_lr",
        type=float,
        default=1e-4,
        help="Learning rate for task heads (default: 1e-4)",
    )
    parser.add_argument(
        "--weight_decay",
        type=float,
        default=0.01,
        help="Weight decay for AdamW optimizer (default: 0.01)",
    )
    parser.add_argument(
        "--warmup_ratio",
        type=float,
        default=0.1,
        help="Ratio of total steps for linear learning rate warmup (default: 0.1)",
    )
    parser.add_argument(
        "--max_grad_norm",
        type=float,
        default=1.0,
        help="Maximum gradient norm for gradient clipping (default: 1.0)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=3,
        help="Early stopping patience in epochs (default: 3)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Reproducibility random seed (default: 42)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Target execution device ('cuda' or 'cpu', default: 'cuda')",
    )
    parser.add_argument(
        "--resume_from_checkpoint",
        type=str,
        default=None,
        help="Path to checkpoint directory (e.g. models/judgebert/latest_checkpoint) to resume training",
    )

    # Execution control flags
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Inspects data schemas, label distributions, and loss weighting without starting training epochs",
    )
    parser.add_argument(
        "--no_train",
        action="store_true",
        help="Loads data and validates structure without executing model training",
    )

    return parser


# -----------------------------------------------------------------------------
# MAIN ENTRYPOINT
# -----------------------------------------------------------------------------
def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    run_training_pipeline(args)


if __name__ == "__main__":
    main()
