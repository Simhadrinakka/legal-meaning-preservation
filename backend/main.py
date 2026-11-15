"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: backend/main.py
Task: Production Flask REST API with CORS, Health, Prediction, and Explainability
=============================================================================

This module implements the Flask REST API serving JUDGEBERT neural inference
and multilingual statutory explainability for English and Hindi legal text pairs.

Endpoints:
- GET  /api/health        -> Application health, uptime, and model status
- GET  /api/model-info    -> Architecture, backbone, heads, label maps, and metadata
- POST /api/predict       -> JUDGEBERT multi-task inference
- POST /api/explain       -> Rule-based & neural explainability synthesis
- POST /api/evaluate-pair -> Combined inference + explainability (single-pass)
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from flask import Flask, jsonify, request
from flask_cors import CORS

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.explainability import LegalExplainabilityEngine
from backend.inference import (
    DECISION_LABELS,
    ERROR_TYPE_LABELS,
    JudgeBERTInferenceEngine,
)

ID_TO_DECISION = {i: label for i, label in enumerate(DECISION_LABELS)}
ID_TO_ERROR = {i: label for i, label in enumerate(ERROR_TYPE_LABELS)}

# -----------------------------------------------------------------------------
# LOGGING SETUP
# -----------------------------------------------------------------------------
logger = logging.getLogger("JUDGEBERT_API")
if not logger.handlers:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

APP_START_TIME = time.time()


# -----------------------------------------------------------------------------
# ENGINE REGISTRY & METADATA LOADER
# -----------------------------------------------------------------------------
class EngineRegistry:
    """
    Singleton registry holding initialized model inference and explainability
    engines to prevent reloading large weights on every HTTP request.
    """

    def __init__(self):
        self.inference_engine: Optional[JudgeBERTInferenceEngine] = None
        self.explainability_engine: Optional[LegalExplainabilityEngine] = None
        self.metadata: Dict[str, Any] = {}
        self.init_error: Optional[str] = None
        self.init_duration_s: float = 0.0
        self.is_initialized: bool = False

    def initialize(
        self,
        weights_path: Optional[str] = None,
        tokenizer_dir: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        """Initialize both engines exactly once."""
        if self.is_initialized:
            logger.info("Engines already initialized. Skipping redundant setup.")
            return

        start_t = time.perf_counter()
        logger.info("Initializing JudgeBERT backend engines...")

        try:
            kwargs = {}
            if weights_path is not None:
                kwargs["weights_path"] = weights_path
            if tokenizer_dir is not None:
                kwargs["tokenizer_dir"] = tokenizer_dir
            if device is not None:
                kwargs["device"] = device

            # 1. Initialize inference engine (loads tokenizer and weights)
            self.inference_engine = JudgeBERTInferenceEngine(**kwargs)

            # 2. Initialize explainability engine
            self.explainability_engine = LegalExplainabilityEngine()

            # 3. Load model training metadata if present
            meta_path = (
                Path(tokenizer_dir) / "metadata.json"
                if tokenizer_dir
                else PROJECT_ROOT / "models" / "judgebert" / "metadata.json"
            )
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                logger.info("Loaded model metadata from %s", meta_path)
            else:
                logger.warning("Metadata file not found at %s", meta_path)
                self.metadata = {}

            self.init_duration_s = time.perf_counter() - start_t
            self.is_initialized = True
            logger.info(
                "Backend engines initialized successfully in %.2fs (device: %s)",
                self.init_duration_s,
                self.inference_engine.device,
            )
        except Exception as exc:
            self.init_duration_s = time.perf_counter() - start_t
            self.init_error = str(exc)
            logger.error("Engine initialization failed: %s", exc, exc_info=True)


registry = EngineRegistry()


# -----------------------------------------------------------------------------
# REQUEST VALIDATION HELPERS
# -----------------------------------------------------------------------------
def validate_text_pair(
    json_data: Any,
) -> Tuple[Optional[str], Optional[str], Optional[Tuple[Dict[str, str], int]]]:
    """
    Validates that the incoming request payload contains non-empty strings
    for both 'original_text' and 'simplified_text'.

    Returns:
        (original_text, simplified_text, None) on success, or
        (None, None, (error_dict, status_code)) on validation failure.
    """
    if not isinstance(json_data, dict):
        return None, None, (
            {
                "error": "Bad Request",
                "message": "Request payload must be a valid JSON object.",
            },
            400,
        )

    if "original_text" not in json_data or "simplified_text" not in json_data:
        return None, None, (
            {
                "error": "Validation Error",
                "message": "Missing required fields: 'original_text' and 'simplified_text' are both required.",
            },
            400,
        )

    orig = json_data.get("original_text")
    simp = json_data.get("simplified_text")

    if not isinstance(orig, str) or not isinstance(simp, str):
        return None, None, (
            {
                "error": "Validation Error",
                "message": "Both 'original_text' and 'simplified_text' must be strings.",
            },
            400,
        )

    orig_clean = orig.strip()
    simp_clean = simp.strip()

    if not orig_clean or not simp_clean:
        return None, None, (
            {
                "error": "Validation Error",
                "message": "'original_text' and 'simplified_text' cannot be empty or whitespace-only.",
            },
            400,
        )

    return orig_clean, simp_clean, None


# -----------------------------------------------------------------------------
# FLASK APPLICATION FACTORY
# -----------------------------------------------------------------------------
def create_app(
    weights_path: Optional[str] = None,
    tokenizer_dir: Optional[str] = None,
    device: Optional[str] = None,
) -> Flask:
    """
    Application factory for creating and configuring the Flask API instance.
    """
    app = Flask(__name__)

    # Enable Cross-Origin Resource Sharing (CORS) for frontend clients
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=False,
    )

    # Initialize model engines once
    registry.initialize(
        weights_path=weights_path,
        tokenizer_dir=tokenizer_dir,
        device=device,
    )

    # -------------------------------------------------------------------------
    # ERROR HANDLERS (Clean JSON, zero stack-trace leakage)
    # -------------------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request_handler(e):
        return (
            jsonify({
                "error": "Bad Request",
                "message": (
                    e.description
                    if hasattr(e, "description")
                    else "Malformed or invalid request."
                ),
            }),
            400,
        )

    @app.errorhandler(404)
    def not_found_handler(e):
        return (
            jsonify({
                "error": "Not Found",
                "message": "The requested API endpoint does not exist.",
            }),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed_handler(e):
        return (
            jsonify({
                "error": "Method Not Allowed",
                "message": "The requested HTTP method is not permitted for this endpoint.",
            }),
            405,
        )

    @app.errorhandler(500)
    def internal_error_handler(e):
        logger.error("Internal Server Error: %s", e)
        return (
            jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected server error occurred during processing.",
            }),
            500,
        )

    @app.errorhandler(Exception)
    def unhandled_exception_handler(exc):
        logger.error("Unhandled Exception: %s", exc, exc_info=True)
        return (
            jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected server error occurred during processing.",
            }),
            500,
        )

    # -------------------------------------------------------------------------
    # API ENDPOINTS
    # -------------------------------------------------------------------------

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """
        GET /api/health
        Returns system health, model readiness, and server uptime.
        """
        uptime_s = time.time() - APP_START_TIME
        is_ready = (
            registry.is_initialized
            and registry.inference_engine is not None
            and registry.explainability_engine is not None
        )

        status_code = 200 if is_ready else 503
        status_text = (
            "healthy"
            if is_ready
            else ("unhealthy" if registry.init_error else "initializing")
        )

        return (
            jsonify({
                "status": status_text,
                "model_loaded": is_ready,
                "device": (
                    str(getattr(registry.inference_engine, "device", "cpu"))
                    if is_ready
                    else None
                ),
                "uptime_seconds": round(uptime_s, 2),
                "init_duration_seconds": round(registry.init_duration_s, 2),
                "version": "1.0.0",
                "error": registry.init_error,
            }),
            status_code,
        )

    @app.route("/api/model-info", methods=["GET"])
    def model_info():
        """
        GET /api/model-info
        Returns model architecture, backbone details, head configurations,
        label mappings, and validation metrics.
        """
        if not registry.is_initialized or registry.inference_engine is None:
            return (
                jsonify({
                    "error": "Service Unavailable",
                    "message": "Model inference engine is not ready.",
                }),
                503,
            )

        meta = registry.metadata
        return (
            jsonify({
                "model_name": "JUDGEBERT (Explainable Multilingual Legal Meaning Preservation)",
                "backbone": meta.get("model_name", "FacebookAI/xlm-roberta-base"),
                "device": str(registry.inference_engine.device),
                "max_seq_length": registry.inference_engine.max_length,
                "task_heads": {
                    "lmp_score_regression": {
                        "description": "Continuous Legal Meaning Preservation score",
                        "range": [1.0, 10.0],
                        "loss_function": "SmoothL1Loss (Huber)",
                        "lambda_weight": meta.get("training_args", {}).get(
                            "lambda_reg", 1.0
                        ),
                    },
                    "preservation_decision": {
                        "description": "5-class categorical preservation decision",
                        "num_classes": len(DECISION_LABELS),
                        "classes": DECISION_LABELS,
                        "id_to_label": ID_TO_DECISION,
                        "lambda_weight": meta.get("training_args", {}).get(
                            "lambda_dec", 0.5
                        ),
                    },
                    "legal_error_classification": {
                        "description": "8-class statutory legal error taxonomy",
                        "num_classes": len(ERROR_TYPE_LABELS),
                        "classes": ERROR_TYPE_LABELS,
                        "id_to_label": ID_TO_ERROR,
                        "lambda_weight": meta.get("training_args", {}).get(
                            "lambda_err", 0.5
                        ),
                    },
                },
                "validation_metrics": meta.get("val_metrics", {}),
                "best_epoch": meta.get("epoch", 3),
                "best_composite_score": meta.get("best_composite_score", None),
                "training_parameters": meta.get("training_args", {}),
            }),
            200,
        )

    @app.route("/api/predict", methods=["POST"])
    def predict():
        """
        POST /api/predict
        Runs JUDGEBERT multi-task inference on original and simplified text pair.

        Request JSON:
            {
                "original_text": "...",
                "simplified_text": "..."
            }
        """
        if not registry.is_initialized or registry.inference_engine is None:
            return (
                jsonify({
                    "error": "Service Unavailable",
                    "message": "Model inference engine is not ready.",
                }),
                503,
            )

        if not request.is_json:
            return (
                jsonify({
                    "error": "Bad Request",
                    "message": "Content-Type must be 'application/json'.",
                }),
                400,
            )

        json_data = request.get_json(silent=True)
        orig, simp, err = validate_text_pair(json_data)
        if err:
            return jsonify(err[0]), err[1]

        start_t = time.perf_counter()
        raw_prediction = registry.inference_engine.predict(orig, simp)
        explanation = registry.explainability_engine.explain(
            original_text=orig,
            simplified_text=simp,
            prediction=raw_prediction,
        )
        hybrid_prediction = explanation.get("hybrid_prediction", raw_prediction)
        latency_ms = (time.perf_counter() - start_t) * 1000.0

        logger.info(
            "Predict completed in %.1fms | Hybrid Score: %.2f | Raw Score: %.2f | Decision: %s | Error: %s",
            latency_ms,
            hybrid_prediction["lmp_score"],
            raw_prediction["lmp_score"],
            hybrid_prediction["pred_decision"],
            hybrid_prediction["pred_error"],
        )

        return (
            jsonify({
                "success": True,
                "prediction": hybrid_prediction,
                "raw_prediction": raw_prediction,
                "latency_ms": round(latency_ms, 2),
            }),
            200,
        )

    @app.route("/api/explain", methods=["POST"])
    def explain():
        """
        POST /api/explain
        Produces transparent, rule-based and neural explainability analysis.

        Request JSON:
            {
                "original_text": "...",
                "simplified_text": "...",
                "prediction": {...}  # Optional: precomputed prediction
            }
        """
        if not registry.is_initialized or registry.explainability_engine is None:
            return (
                jsonify({
                    "error": "Service Unavailable",
                    "message": "Explainability engine is not ready.",
                }),
                503,
            )

        if not request.is_json:
            return (
                jsonify({
                    "error": "Bad Request",
                    "message": "Content-Type must be 'application/json'.",
                }),
                400,
            )

        json_data = request.get_json(silent=True)
        orig, simp, err = validate_text_pair(json_data)
        if err:
            return jsonify(err[0]), err[1]

        start_t = time.perf_counter()

        # Check if caller supplied precomputed prediction; if not, run inference
        pred = json_data.get("prediction")
        if (
            pred is None
            and registry.inference_engine is not None
        ):
            pred = registry.inference_engine.predict(orig, simp)

        explanation = registry.explainability_engine.explain(
            original_text=orig,
            simplified_text=simp,
            prediction=pred,
        )
        latency_ms = (time.perf_counter() - start_t) * 1000.0

        logger.info(
            "Explain completed in %.1fms | Score: %.2f | Decision: %s",
            latency_ms,
            explanation.get("predicted_score") or 0.0,
            explanation.get("predicted_decision") or "NONE",
        )

        return (
            jsonify({
                "success": True,
                "explanation": explanation,
                "latency_ms": round(latency_ms, 2),
            }),
            200,
        )

    @app.route("/api/evaluate-pair", methods=["POST"])
    def evaluate_pair():
        """
        POST /api/evaluate-pair
        Combined endpoint: executes neural inference once and feeds results
        directly into the explainability engine to avoid redundant computation.

        Request JSON:
            {
                "original_text": "...",
                "simplified_text": "..."
            }
        """
        if (
            not registry.is_initialized
            or registry.inference_engine is None
            or registry.explainability_engine is None
        ):
            return (
                jsonify({
                    "error": "Service Unavailable",
                    "message": "Backend engines are not ready.",
                }),
                503,
            )

        if not request.is_json:
            return (
                jsonify({
                    "error": "Bad Request",
                    "message": "Content-Type must be 'application/json'.",
                }),
                400,
            )

        json_data = request.get_json(silent=True)
        orig, simp, err = validate_text_pair(json_data)
        if err:
            return jsonify(err[0]), err[1]

        start_t = time.perf_counter()

        # Step 1: Run raw neural inference ONCE
        raw_prediction = registry.inference_engine.predict(orig, simp)

        # Step 2: Feed raw prediction directly into explainability engine for hybrid synthesis
        explanation = registry.explainability_engine.explain(
            original_text=orig,
            simplified_text=simp,
            prediction=raw_prediction,
        )
        hybrid_prediction = explanation.get("hybrid_prediction", raw_prediction)

        latency_ms = (time.perf_counter() - start_t) * 1000.0

        logger.info(
            "Evaluate-pair completed in %.1fms | Hybrid Score: %.2f | Raw Score: %.2f | Decision: %s | Error: %s",
            latency_ms,
            hybrid_prediction["lmp_score"],
            raw_prediction["lmp_score"],
            hybrid_prediction["pred_decision"],
            hybrid_prediction["pred_error"],
        )

        return (
            jsonify({
                "success": True,
                "prediction": hybrid_prediction,
                "raw_prediction": raw_prediction,
                "explanation": explanation,
                "latency_ms": round(latency_ms, 2),
            }),
            200,
        )

    return app


# Default application instance for WSGI servers / direct run
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info("Starting JUDGEBERT API server on %s:%d ...", host, port)
    app.run(host=host, port=port, debug=False)
