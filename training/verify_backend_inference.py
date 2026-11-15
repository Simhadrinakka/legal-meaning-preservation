"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/verify_backend_inference.py
Task: Standalone Verification Script for backend/inference.py (English & Hindi)
=============================================================================
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.inference import JudgeBERTInferenceEngine, DECISION_LABELS, ERROR_TYPE_LABELS


def run_verification():
    print("=" * 70)
    print("JUDGEBERT BACKEND INFERENCE VERIFICATION (CPU MODE)")
    print("=" * 70)

    # 1. Instantiate Inference Engine
    print("\n[Step 1] Initializing JudgeBERTInferenceEngine...")
    t0 = time.time()
    engine = JudgeBERTInferenceEngine(
        weights_path=project_root / "models/judgebert/judgebert_weights.pt",
        tokenizer_dir=project_root / "models/judgebert",
        device="cpu",
    )
    init_time = time.time() - t0
    print(f"Engine successfully initialized in {init_time:.2f} seconds.")

    # 2. English Statutory Pair
    print("\n[Step 2] Evaluating English Statutory Pair...")
    en_original = (
        "(1) Subject to such conditions as may be prescribed, any officer authorised "
        "by the Chief Registrar by a general or special order in this behalf may, "
        "either before or after the institution of criminal proceedings under this Act, "
        "accept from the person who has committed or is reasonably suspected of having "
        "committed an offence under this Act, by way of composition of such offence "
        "a sum of money not exceeding fifty rupees."
    )
    en_simplified = (
        "(1) Subject to prescribed conditions, an officer authorized by the Chief Registrar "
        "by a general or special order may, either before or after criminal proceedings "
        "are initiated under this Act, accept up to fifty rupees to compound an offence "
        "from any person who has committed or is suspected of committing that offence."
    )

    t_en_start = time.time()
    en_result = engine.predict(en_original, en_simplified)
    en_latency = time.time() - t_en_start

    print(f"  Latency: {en_latency * 1000:.1f} ms")
    print(f"  Predicted LMP Score: {en_result['lmp_score']} / 10.0")
    print(f"  Predicted Decision:  {en_result['pred_decision']} (id: {en_result['pred_decision_id']})")
    print(f"  Predicted Error:     {en_result['pred_error']} (id: {en_result['pred_error_id']})")
    print(f"  Preserved Status:    {en_result['is_preserved']}")
    print("  Decision Probabilities:")
    for dec, prob in en_result["decision_probabilities"].items():
        print(f"    - {dec:22s}: {prob:.4f}")
    print("  Top Error Probabilities:")
    sorted_err = sorted(en_result["error_probabilities"].items(), key=lambda x: x[1], reverse=True)[:3]
    for err, prob in sorted_err:
        print(f"    - {err:32s}: {prob:.4f}")

    # Assertions for English
    assert 1.0 <= en_result["lmp_score"] <= 10.0, "Score out of range"
    assert en_result["pred_decision"] in DECISION_LABELS, "Invalid decision"
    assert en_result["pred_error"] in ERROR_TYPE_LABELS, "Invalid error"
    assert abs(sum(en_result["decision_probabilities"].values()) - 1.0) < 0.01, "Decision probs must sum to 1"
    assert abs(sum(en_result["error_probabilities"].values()) - 1.0) < 0.01, "Error probs must sum to 1"

    # 3. Hindi Statutory Pair
    print("\n[Step 3] Evaluating Hindi Statutory Pair...")
    hi_original = (
        "धारा 24 की उपधारा (1) के अधीन किसी अपराध के शमन के लिए कोई भी धनराशि, "
        "जो पचास रुपये से अधिक न हो, ऐसे अधिकारी द्वारा स्वीकार की जा सकेगी "
        "जिसे मुख्य रजिस्ट्रार द्वारा साधारण या विशेष आदेश द्वारा इस निमित्त प्राधिकृत किया गया हो।"
    )
    hi_simplified = (
        "मुख्य रजिस्ट्रार द्वारा प्राधिकृत कोई भी अधिकारी विहित शर्तों के अधीन रहते हुए, "
        "इस अधिनियम के तहत किसी अपराध को समाप्त करने के लिए पचास रुपये तक की राशि "
        "स्वीकार कर सकता है।"
    )

    t_hi_start = time.time()
    hi_result = engine.predict(hi_original, hi_simplified)
    hi_latency = time.time() - t_hi_start

    print(f"  Latency: {hi_latency * 1000:.1f} ms")
    print(f"  Predicted LMP Score: {hi_result['lmp_score']} / 10.0")
    print(f"  Predicted Decision:  {hi_result['pred_decision']} (id: {hi_result['pred_decision_id']})")
    print(f"  Predicted Error:     {hi_result['pred_error']} (id: {hi_result['pred_error_id']})")
    print(f"  Preserved Status:    {hi_result['is_preserved']}")
    print("  Decision Probabilities:")
    for dec, prob in hi_result["decision_probabilities"].items():
        print(f"    - {dec:22s}: {prob:.4f}")
    print("  Top Error Probabilities:")
    sorted_err_hi = sorted(hi_result["error_probabilities"].items(), key=lambda x: x[1], reverse=True)[:3]
    for err, prob in sorted_err_hi:
        print(f"    - {err:32s}: {prob:.4f}")

    # Assertions for Hindi
    assert 1.0 <= hi_result["lmp_score"] <= 10.0, "Score out of range"
    assert hi_result["pred_decision"] in DECISION_LABELS, "Invalid decision"
    assert hi_result["pred_error"] in ERROR_TYPE_LABELS, "Invalid error"
    assert abs(sum(hi_result["decision_probabilities"].values()) - 1.0) < 0.01, "Decision probs must sum to 1"
    assert abs(sum(hi_result["error_probabilities"].values()) - 1.0) < 0.01, "Error probs must sum to 1"

    # 4. Batched Inference Test
    print("\n[Step 4] Testing Batched Inference...")
    t_batch_start = time.time()
    batch_results = engine.predict_batch([
        (en_original, en_simplified),
        (hi_original, hi_simplified),
    ])
    batch_latency = time.time() - t_batch_start
    assert len(batch_results) == 2, "Batch count mismatch"
    print(f"  Batched inference (2 pairs) completed in {batch_latency * 1000:.1f} ms.")

    print("\n" + "=" * 70)
    print("VERIFICATION SUCCESSFUL: backend/inference.py is fully operational!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
