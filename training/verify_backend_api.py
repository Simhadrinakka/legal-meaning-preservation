"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/verify_backend_api.py
Task: End-to-End Verification Suite for Flask REST API in backend/main.py
=============================================================================

This verification script tests all API endpoints and behaviors:
1. Health endpoint (GET /api/health)
2. Model-info endpoint (GET /api/model-info)
3. English prediction (POST /api/predict)
4. Hindi prediction (POST /api/predict)
5. Explainability endpoint (POST /api/explain)
6. Combined evaluate-pair endpoint (POST /api/evaluate-pair)
7. Invalid request handling (non-JSON, missing fields, wrong types)
8. Empty / whitespace-only text handling
9. HTTP status codes (200, 400, 404, 405)
10. Model initialized only once (singleton reuse verification)
"""

import json
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app, registry


def run_api_verification():
    print("=" * 75)
    print("JUDGEBERT FLASK REST API VERIFICATION SUITE")
    print("=" * 75)

    client = app.test_client()

    # -------------------------------------------------------------------------
    # Test 1: Single Model Initialization Check
    # -------------------------------------------------------------------------
    print("\n[Test 1] Verifying Single Engine Initialization...")
    assert registry.is_initialized is True, "Registry was not initialized!"
    engine_id_1 = id(registry.inference_engine)
    explain_id_1 = id(registry.explainability_engine)

    # Calling initialize again should do nothing
    registry.initialize()
    engine_id_2 = id(registry.inference_engine)
    assert engine_id_1 == engine_id_2, "Inference engine was re-instantiated!"
    assert explain_id_1 == id(registry.explainability_engine), "Explainability engine was re-instantiated!"
    print(f"  PASS: Inference engine ({hex(engine_id_1)}) is a singleton and reused across calls.")

    # -------------------------------------------------------------------------
    # Test 2: GET /api/health
    # -------------------------------------------------------------------------
    print("\n[Test 2] Testing GET /api/health ...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.get_json()
    assert data["status"] == "healthy", f"Status not healthy: {data}"
    assert data["model_loaded"] is True
    assert data["device"] in ["cpu", "cuda"]
    assert "uptime_seconds" in data
    assert "init_duration_seconds" in data
    print(f"  Response: status={data['status']}, device={data['device']}, uptime={data['uptime_seconds']}s")
    print("  PASS: Health endpoint functioning correctly.")

    # -------------------------------------------------------------------------
    # Test 3: GET /api/model-info
    # -------------------------------------------------------------------------
    print("\n[Test 3] Testing GET /api/model-info ...")
    resp = client.get("/api/model-info")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    info = resp.get_json()
    assert "model_name" in info
    assert "backbone" in info
    assert "task_heads" in info
    assert "lmp_score_regression" in info["task_heads"]
    assert "preservation_decision" in info["task_heads"]
    assert "legal_error_classification" in info["task_heads"]
    assert len(info["task_heads"]["preservation_decision"]["classes"]) == 5
    assert len(info["task_heads"]["legal_error_classification"]["classes"]) == 8
    print(f"  Model: {info['model_name']}")
    print(f"  Backbone: {info['backbone']}")
    print(f"  Validation Macro-F1: {info.get('validation_metrics', {}).get('dec_macro_f1')}")
    print("  PASS: Model info metadata and taxonomy mappings verified.")

    # -------------------------------------------------------------------------
    # Test 4: POST /api/predict (English Statutory Pair)
    # -------------------------------------------------------------------------
    print("\n[Test 4] Testing POST /api/predict (English Statutory Pair) ...")
    payload_en = {
        "original_text": (
            "Any officer authorised by the Chief Registrar by a general or special order in this behalf "
            "may accept from the person who has committed an offence under this Act a sum of money not "
            "exceeding fifty rupees by way of composition."
        ),
        "simplified_text": (
            "An authorized officer may accept up to fifty rupees to settle an offence under this Act."
        ),
    }
    resp = client.post("/api/predict", json=payload_en)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    pred_data = resp.get_json()
    assert pred_data["success"] is True
    assert "prediction" in pred_data
    pred = pred_data["prediction"]
    assert 1.0 <= pred["lmp_score"] <= 10.0
    assert pred["pred_decision"] in ["PRESERVED", "MOSTLY_PRESERVED", "PARTIALLY_PRESERVED", "MAJOR_LOSS", "FUNDAMENTALLY_ALTERED"]
    assert pred["pred_error"] in ["NONE", "OMISSION", "HALLUCINATION_ADDITION", "CONTRADICTION", "MODALITY_CHANGE", "CONDITION_EXCEPTION_LOSS", "SCOPE_CHANGE", "NUMERIC_ENTITY_REFERENCE_ERROR"]
    assert len(pred["decision_probabilities"]) == 5
    assert len(pred["error_probabilities"]) == 8
    print(f"  Prediction: Score={pred['lmp_score']:.2f}, Decision={pred['pred_decision']}, Error={pred['pred_error']}")
    print(f"  Latency: {pred_data['latency_ms']:.1f}ms")
    print("  PASS: English prediction returned valid multi-task outputs.")

    # -------------------------------------------------------------------------
    # Test 5: POST /api/predict (Hindi Statutory Pair)
    # -------------------------------------------------------------------------
    print("\n[Test 5] Testing POST /api/predict (Hindi Statutory Pair) ...")
    payload_hi = {
        "original_text": (
            "धारा 24 की उपधारा (1) के अधीन किसी अपराध के शमन के लिए कोई भी धनराशि, "
            "जो पचास रुपये से अधिक न हो, ऐसे अधिकारी द्वारा स्वीकार की जा सकेगी।"
        ),
        "simplified_text": (
            "धारा 24(1) के अंतर्गत प्राधिकृत अधिकारी अपराध निपटाने के लिए पचास रुपये तक की राशि ले सकेगा।"
        ),
    }
    resp = client.post("/api/predict", json=payload_hi)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    pred_hi = resp.get_json()["prediction"]
    assert 1.0 <= pred_hi["lmp_score"] <= 10.0
    print(f"  Prediction: Score={pred_hi['lmp_score']:.2f}, Decision={pred_hi['pred_decision']}, Error={pred_hi['pred_error']}")
    print("  PASS: Hindi prediction returned valid multi-task outputs.")

    # -------------------------------------------------------------------------
    # Test 6: POST /api/explain
    # -------------------------------------------------------------------------
    print("\n[Test 6] Testing POST /api/explain ...")
    resp = client.post("/api/explain", json=payload_en)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    exp_data = resp.get_json()
    assert exp_data["success"] is True
    assert "explanation" in exp_data
    exp = exp_data["explanation"]
    assert "human_readable_summary" in exp
    assert "text_differences" in exp
    assert "detected_invariant_shifts" in exp
    assert "method_and_limitations" in exp
    print(f"  Summary: {exp['human_readable_summary']}")
    print("  PASS: Explain endpoint returned structured explainability payload.")

    # -------------------------------------------------------------------------
    # Test 7: POST /api/evaluate-pair (Combined Single-Pass)
    # -------------------------------------------------------------------------
    print("\n[Test 7] Testing POST /api/evaluate-pair (Single-Pass Execution) ...")
    resp = client.post("/api/evaluate-pair", json=payload_en)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"
    eval_data = resp.get_json()
    assert eval_data["success"] is True
    assert "prediction" in eval_data
    assert "explanation" in eval_data
    assert eval_data["prediction"]["lmp_score"] == eval_data["explanation"]["predicted_score"]
    assert eval_data["prediction"]["pred_decision"] == eval_data["explanation"]["predicted_decision"]
    print(f"  Combined Latency: {eval_data['latency_ms']:.1f}ms")
    print(f"  Synchronized Score: {eval_data['prediction']['lmp_score']} == {eval_data['explanation']['predicted_score']}")
    print("  PASS: evaluate-pair combines prediction and explanation with zero divergence.")

    # -------------------------------------------------------------------------
    # Test 8: Invalid Request Handling
    # -------------------------------------------------------------------------
    print("\n[Test 8] Testing Invalid Request Handling (Malformed / Missing Fields) ...")

    # 8a: Non-JSON content type
    resp_non_json = client.post(
        "/api/predict",
        data="raw string text",
        content_type="text/plain",
    )
    assert resp_non_json.status_code == 400
    assert "Content-Type must be 'application/json'" in resp_non_json.get_json()["message"]
    print("  PASS: Non-JSON request rejected with 400 Bad Request.")

    # 8b: Missing simplified_text
    resp_missing = client.post(
        "/api/predict",
        json={"original_text": "Sample text"},
    )
    assert resp_missing.status_code == 400
    assert "Missing required fields" in resp_missing.get_json()["message"]
    print("  PASS: Missing required field rejected with 400 Bad Request.")

    # 8c: Non-string input
    resp_type = client.post(
        "/api/predict",
        json={"original_text": 12345, "simplified_text": "Text"},
    )
    assert resp_type.status_code == 400
    assert "must be strings" in resp_type.get_json()["message"]
    print("  PASS: Non-string type rejected with 400 Bad Request.")

    # -------------------------------------------------------------------------
    # Test 9: Empty & Whitespace-Only Text Handling
    # -------------------------------------------------------------------------
    print("\n[Test 9] Testing Empty & Whitespace-Only Text Handling ...")
    resp_empty = client.post(
        "/api/evaluate-pair",
        json={"original_text": "   ", "simplified_text": "Some text"},
    )
    assert resp_empty.status_code == 400
    assert "cannot be empty" in resp_empty.get_json()["message"]
    print("  PASS: Whitespace-only text rejected with 400 Bad Request.")

    # -------------------------------------------------------------------------
    # Test 10: HTTP Status Codes & Error Handlers
    # -------------------------------------------------------------------------
    print("\n[Test 10] Testing HTTP Status Codes & Routing (404, 405) ...")

    # 10a: 404 Not Found
    resp_404 = client.get("/api/unknown-endpoint")
    assert resp_404.status_code == 404
    assert resp_404.get_json()["error"] == "Not Found"
    print("  PASS: Unknown route returned 404 with structured JSON.")

    # 10b: 405 Method Not Allowed
    resp_405 = client.get("/api/predict")
    assert resp_405.status_code == 405
    assert resp_405.get_json()["error"] == "Method Not Allowed"
    print("  PASS: Unsupported method returned 405 with structured JSON.")

    print("\n" + "=" * 75)
    print("ALL 10 API VERIFICATION TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 75)


if __name__ == "__main__":
    run_api_verification()
