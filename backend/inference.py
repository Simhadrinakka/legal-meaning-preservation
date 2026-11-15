"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: backend/inference.py
Task: High-Fidelity Multilingual Legal Meaning Preservation Inference Engine
=============================================================================

This module provides the core inference engine for JUDGEBERT.
It reconstructs the exact multi-task architecture fine-tuned on XLM-RoBERTa,
loads local tokenizers and weights strictly, and evaluates statutory text pairs
in both English and Hindi.
"""

import logging
import unicodedata
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from transformers import AutoTokenizer, XLMRobertaConfig, XLMRobertaModel

logger = logging.getLogger("JUDGEBERT_INFERENCE")
if not logger.handlers:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

# -----------------------------------------------------------------------------
# CONSTANTS & TAXONOMY LABELS
# -----------------------------------------------------------------------------
DEFAULT_WEIGHTS_PATH = "models/judgebert/judgebert_weights.pt"
DEFAULT_TOKENIZER_DIR = "models/judgebert"
DEFAULT_MAX_LENGTH = 256
MIN_LMP_SCORE = 1.0
MAX_LMP_SCORE = 10.0

DECISION_LABELS = [
    "FUNDAMENTALLY_ALTERED",  # 0
    "MAJOR_LOSS",             # 1
    "PARTIALLY_PRESERVED",    # 2
    "MOSTLY_PRESERVED",       # 3
    "PRESERVED",              # 4
]

ERROR_TYPE_LABELS = [
    "NONE",                            # 0
    "OMISSION",                        # 1
    "HALLUCINATION_ADDITION",          # 2
    "CONTRADICTION",                   # 3
    "MODALITY_CHANGE",                 # 4
    "CONDITION_EXCEPTION_LOSS",         # 5
    "SCOPE_CHANGE",                    # 6
    "NUMERIC_ENTITY_REFERENCE_ERROR",  # 7
]


# -----------------------------------------------------------------------------
# TEXT NORMALIZATION (PRESERVES LEGAL INVARIANTS)
# -----------------------------------------------------------------------------
def normalize_legal_text(text: Any) -> str:
    """
    Applies legally-preservative Unicode NFKC normalization and whitespace standardization.
    Preserves Hindi Devanagari punctuation (।, ॥), quotes, section references, and modals.
    """
    if text is None:
        return ""
    text = str(text)
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)
    # Standardize quotation marks without stripping
    text = re.sub(r"[\u201c\u201d\u201e\u201f\u00ab\u00bb]", '"', text)
    text = re.sub(r"[\u2018\u2019\u201a\u201b`]", "'", text)
    # Standardize hyphens/dashes
    text = re.sub(r"[\u2013\u2014\u2015\u2500]", "—", text)
    # Normalize whitespaces
    text = re.sub(r"[\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# -----------------------------------------------------------------------------
# EXACT JUDGEBERT MODEL ARCHITECTURE
# -----------------------------------------------------------------------------
class JudgeBERTModel(nn.Module):
    """
    Exact PyTorch model architecture for JUDGEBERT.
    Backbone: XLMRobertaModel (12 layers, 768 hidden, 12 attention heads)
    Task Heads:
      1. Regression Head: Linear(768, 256) -> GELU -> Dropout(0.2) -> Linear(256, 1)
      2. Decision Head:   Linear(768, 256) -> GELU -> Dropout(0.2) -> Linear(256, 5)
      3. Error Head:      Linear(768, 256) -> GELU -> Dropout(0.2) -> Linear(256, 8)
    """

    def __init__(
        self,
        config: XLMRobertaConfig,
        head_hidden_dim: int = 256,
        dropout_prob: float = 0.2,
    ):
        super().__init__()
        self.config = config
        self.encoder = XLMRobertaModel(config)
        hidden_size = config.hidden_size

        self.dropout = nn.Dropout(dropout_prob)

        # Head 1: LMP Score Regression
        self.regression_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(head_hidden_dim, 1),
        )

        # Head 2: Preservation Decision Classification (5 classes)
        self.decision_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(head_hidden_dim, len(DECISION_LABELS)),
        )

        # Head 3: Error Taxonomy Classification (8 classes)
        self.error_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_prob),
            nn.Linear(head_hidden_dim, len(ERROR_TYPE_LABELS)),
        )

        # Buffer present in trained weights
        self.register_buffer("error_class_weights", torch.zeros(len(ERROR_TYPE_LABELS)))

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        kwargs: Dict[str, Any] = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "return_dict": True,
        }
        if token_type_ids is not None:
            kwargs["token_type_ids"] = token_type_ids

        outputs = self.encoder(**kwargs)
        sequence_output = outputs.last_hidden_state

        # First token <s> / [CLS] pooled representation
        pooled_cls = sequence_output[:, 0, :]
        pooled = self.dropout(pooled_cls)

        # 1. Regression Output
        raw_reg = self.regression_head(pooled).squeeze(-1)
        pred_norm = torch.sigmoid(raw_reg)
        pred_score = torch.clamp(pred_norm * MAX_LMP_SCORE, min=MIN_LMP_SCORE, max=MAX_LMP_SCORE)

        # 2. Decision Logits & Probabilities
        decision_logits = self.decision_head(pooled)
        decision_probs = torch.softmax(decision_logits, dim=-1)

        # 3. Error Logits & Probabilities
        error_logits = self.error_head(pooled)
        error_probs = torch.softmax(error_logits, dim=-1)

        return {
            "pred_score": pred_score,
            "pred_norm": pred_norm,
            "decision_logits": decision_logits,
            "decision_probs": decision_probs,
            "error_logits": error_logits,
            "error_probs": error_probs,
            "attentions": outputs.attentions if hasattr(outputs, "attentions") else None,
        }


# -----------------------------------------------------------------------------
# REUSABLE INFERENCE ENGINE CLASS
# -----------------------------------------------------------------------------
class JudgeBERTInferenceEngine:
    """
    Reusable production inference engine for Multilingual Legal Meaning Preservation.
    Handles offline model instantiation, strict weight loading, batching,
    and structured prediction output formatting.
    """

    def __init__(
        self,
        weights_path: Union[str, Path] = DEFAULT_WEIGHTS_PATH,
        tokenizer_dir: Union[str, Path] = DEFAULT_TOKENIZER_DIR,
        device: str = "cpu",
        max_length: int = DEFAULT_MAX_LENGTH,
    ):
        self.weights_path = Path(weights_path)
        self.tokenizer_dir = Path(tokenizer_dir)
        self.device = torch.device(device)
        self.max_length = max_length

        logger.info(f"Initializing JudgeBERTInferenceEngine on device: {self.device}")

        # 1. Load local tokenizer
        self.tokenizer = self._load_tokenizer()

        # 2. Reconstruct exact model architecture offline
        self.model = self._build_model()

        # 3. Load trained weights strictly
        self._load_weights_strictly()

        # 4. Set model to eval mode
        self.model.eval()
        self.model.to(self.device)
        logger.info("JudgeBERTInferenceEngine successfully initialized and ready for inference.")

    def _load_tokenizer(self) -> AutoTokenizer:
        """Loads local tokenizer from models/judgebert/ directory."""
        if not self.tokenizer_dir.exists():
            raise FileNotFoundError(f"Tokenizer directory not found: {self.tokenizer_dir}")

        logger.info(f"Loading local tokenizer from: {self.tokenizer_dir}")
        try:
            tokenizer = AutoTokenizer.from_pretrained(str(self.tokenizer_dir))
            logger.info(f"Tokenizer loaded ({type(tokenizer).__name__}, vocab: {len(tokenizer)})")
            return tokenizer
        except Exception as e:
            logger.error(f"Failed to load tokenizer from {self.tokenizer_dir}: {e}")
            raise

    def _build_model(self) -> JudgeBERTModel:
        """
        Creates the XLMRobertaConfig and model architecture offline
        without downloading base model weights from the hub.
        """
        config = XLMRobertaConfig(
            vocab_size=250002,
            hidden_size=768,
            num_hidden_layers=12,
            num_attention_heads=12,
            intermediate_size=3072,
            hidden_act="gelu",
            hidden_dropout_prob=0.1,
            attention_probs_dropout_prob=0.1,
            max_position_embeddings=514,
            type_vocab_size=1,
            initializer_range=0.02,
            layer_norm_eps=1e-05,
            pad_token_id=1,
            bos_token_id=0,
            eos_token_id=2,
            output_attentions=True,
            output_hidden_states=True,
        )
        model = JudgeBERTModel(config=config, head_hidden_dim=256, dropout_prob=0.2)
        return model

    def _load_weights_strictly(self) -> None:
        """
        Loads state dictionary into model with strict key verification.
        Explicitly audits and logs missing or unexpected keys.
        """
        if not self.weights_path.exists():
            raise FileNotFoundError(f"Model weights checkpoint not found: {self.weights_path}")

        logger.info(f"Loading checkpoint weights from: {self.weights_path}")
        state_dict = torch.load(self.weights_path, map_location="cpu")

        # Load with strict=True
        load_result = self.model.load_state_dict(state_dict, strict=True)
        missing_keys = load_result.missing_keys
        unexpected_keys = load_result.unexpected_keys

        if missing_keys:
            logger.error(f"CRITICAL: Missing keys in checkpoint: {missing_keys}")
            raise RuntimeError(f"Missing keys when loading weights: {missing_keys}")
        if unexpected_keys:
            logger.error(f"CRITICAL: Unexpected keys in checkpoint: {unexpected_keys}")
            raise RuntimeError(f"Unexpected keys when loading weights: {unexpected_keys}")

        logger.info(f"Strict weight loading verified: 100% of {len(state_dict)} tensors matched exactly.")

    def predict(
        self,
        original_text: str,
        simplified_text: str,
    ) -> Dict[str, Any]:
        """
        Performs inference for a single original–simplified legal text pair.

        Args:
            original_text: Statutory source passage (English or Hindi).
            simplified_text: Plain-language simplified passage.

        Returns:
            Structured dictionary with:
              - lmp_score: Continuous score in [1.0, 10.0]
              - pred_decision: Highest-probability preservation decision
              - pred_decision_id: Integer decision ID (0-4)
              - pred_error: Highest-probability legal error type
              - pred_error_id: Integer error ID (0-7)
              - decision_probabilities: Full probability distribution over 5 decisions
              - error_probabilities: Full probability distribution over 8 error types
              - is_preserved: Boolean flag (score >= 9.0 and decision == PRESERVED)
        """
        batch_results = self.predict_batch([(original_text, simplified_text)])
        return batch_results[0]

    def predict_batch(
        self,
        pairs: List[Tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Performs batched inference over multiple legal text pairs.
        """
        if not pairs:
            return []

        # 1. Normalize input texts
        normalized_pairs = [
            (normalize_legal_text(orig), normalize_legal_text(simp))
            for orig, simp in pairs
        ]

        # 2. Tokenize pairwise: <s> orig </s></s> simp </s>
        encodings = self.tokenizer(
            [orig for orig, _ in normalized_pairs],
            [simp for _, simp in normalized_pairs],
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        input_ids = encodings["input_ids"].to(self.device)
        attention_mask = encodings["attention_mask"].to(self.device)
        token_type_ids = encodings.get("token_type_ids")
        if token_type_ids is not None:
            token_type_ids = token_type_ids.to(self.device)

        # 3. Model forward pass with torch.inference_mode()
        with torch.inference_mode():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
            )

        # 4. Extract and format outputs
        pred_scores = outputs["pred_score"].cpu().numpy()
        pred_norms = outputs["pred_norm"].cpu().numpy()
        decision_probs = outputs["decision_probs"].cpu().numpy()
        error_probs = outputs["error_probs"].cpu().numpy()

        results = []
        for i in range(len(pairs)):
            # Score
            score_val = float(pred_scores[i]) if pred_scores.ndim > 0 else float(pred_scores)
            norm_val = float(pred_norms[i]) if pred_norms.ndim > 0 else float(pred_norms)

            # Decision
            dec_row = decision_probs[i]
            dec_id = int(dec_row.argmax())
            dec_name = DECISION_LABELS[dec_id]
            dec_dict = {
                DECISION_LABELS[j]: round(float(dec_row[j]), 4)
                for j in range(len(DECISION_LABELS))
            }

            # Error
            err_row = error_probs[i]
            err_id = int(err_row.argmax())
            err_name = ERROR_TYPE_LABELS[err_id]
            err_dict = {
                ERROR_TYPE_LABELS[k]: round(float(err_row[k]), 4)
                for k in range(len(ERROR_TYPE_LABELS))
            }

            # Preservation status flag
            is_preserved = bool(score_val >= 9.0 and dec_name == "PRESERVED")

            results.append({
                "lmp_score": round(score_val, 2),
                "lmp_score_norm": round(norm_val, 4),
                "pred_decision": dec_name,
                "pred_decision_id": dec_id,
                "pred_error": err_name,
                "pred_error_id": err_id,
                "decision_probabilities": dec_dict,
                "error_probabilities": err_dict,
                "is_preserved": is_preserved,
            })

        return results
