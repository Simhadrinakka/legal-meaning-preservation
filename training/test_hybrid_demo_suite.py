"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/test_hybrid_demo_suite.py
Task: Automated Verification Suite for Hybrid Neuro-Symbolic Engine (10 Cases)
=============================================================================

This test suite rigorously evaluates the hybrid neuro-symbolic engine across
the 10 mandatory evaluation benchmarks:
1. Correct semantic paraphrase (Meaning Preserved, 'not exceeding 50' <=> 'up to 50')
2. Shall -> May modality weakening (Major Loss, MODALITY_CHANGE)
3. Prohibition reversed (Critical Contradiction, CONTRADICTION)
4. 50,000 -> 500,000 fine threshold alteration (Major Loss, NUMERIC_ENTITY_REFERENCE_ERROR)
5. Material condition removed (Condition Loss, CONDITION_EXCEPTION_LOSS)
6. Statutory exception removed (Exception Loss, CONDITION_EXCEPTION_LOSS)
7. Legal scope expanded (Scope Alteration, SCOPE_CHANGE)
8. Hindi modality weakening ('करेगा' -> 'कर सकेगा', MODALITY_CHANGE)
9. Harmless wording change (Meaning Preserved, NONE)
10. Verbatim identical texts (Full Legal Preservation, PRESERVED, NONE)
"""

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.explainability import LegalExplainabilityEngine
from backend.inference import JudgeBERTInferenceEngine

# Define the 10 canonical test cases
TEST_CASES = [
    {
        "id": 1,
        "name": "Correct Semantic Paraphrase",
        "language": "en",
        "description": "Standard statutory plain-language simplification with upper-bound equivalence ('not exceeding fifty rupees' <=> 'up to fifty rupees').",
        "original": "(1) Subject to such conditions as may be prescribed, any officer authorised by the Chief Registrar by a general or special order in this behalf may accept from the person who has committed an offence under this Act a sum of money not exceeding fifty rupees.",
        "simplified": "(1) Subject to prescribed conditions, an officer authorized by the Chief Registrar by a general or special order may accept up to fifty rupees to compound an offence from any person who has committed that offence.",
        "expected_score_min": 9.0,
        "expected_score_max": 10.0,
        "expected_decision": "PRESERVED",
        "expected_error": "NONE",
        "expected_adjustment": False,
    },
    {
        "id": 2,
        "name": "Shall -> May Modality Weakening",
        "language": "en",
        "description": "Mandatory statutory duty ('shall pay') softened into permissive discretion ('may pay').",
        "original": "The employer shall pay the full amount of gratuity to the employee within thirty days from the date it becomes payable.",
        "simplified": "The employer may pay the full amount of gratuity to the employee within thirty days from the date it becomes payable.",
        "expected_score_min": 3.0,
        "expected_score_max": 4.5,
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "MODALITY_CHANGE",
        "expected_adjustment": True,
    },
    {
        "id": 3,
        "name": "Prohibition Reversed",
        "language": "en",
        "description": "Statutory prohibition ('No person shall operate...') inverted into explicit permission ('Any person may operate...'). Potential liability inversion.",
        "original": "No person shall operate any unregistered motor vehicle on any public highway or road.",
        "simplified": "Any person may operate an unregistered motor vehicle on any public highway or road.",
        "expected_score_min": 1.0,
        "expected_score_max": 2.0,
        "expected_decision": "FUNDAMENTALLY_ALTERED",
        "expected_error": "CONTRADICTION",
        "expected_adjustment": True,
    },
    {
        "id": 4,
        "name": "50,000 -> 500,000 Fine Alteration",
        "language": "en",
        "description": "Statutory fine ceiling distorted tenfold from 50,000 to 500,000 rupees.",
        "original": "Any licensee who contravenes the terms of the license shall be liable to a penalty not exceeding 50,000 rupees.",
        "simplified": "Any licensee who contravenes the terms of the license shall be liable to a penalty not exceeding 500,000 rupees.",
        "expected_score_min": 3.0,
        "expected_score_max": 4.0,
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "expected_adjustment": True,
    },
    {
        "id": 5,
        "name": "Material Condition Removed",
        "language": "en",
        "description": "Statutory condition precedent ('Subject to the prior approval of the State Government') dropped entirely.",
        "original": "Subject to the prior approval of the State Government, the Board may make regulations to carry out the purposes of this Act.",
        "simplified": "The Board may make regulations to carry out the purposes of this Act.",
        "expected_score_min": 4.0,
        "expected_score_max": 5.0,
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "CONDITION_EXCEPTION_LOSS",
        "expected_adjustment": True,
    },
    {
        "id": 6,
        "name": "Statutory Exception Removed",
        "language": "en",
        "description": "Statutory exclusion carveout ('except transactions under ten thousand rupees') omitted, making audit universal.",
        "original": "All financial transactions under Section 12 shall be subject to mandatory external audit, except transactions under ten thousand rupees.",
        "simplified": "All financial transactions under Section 12 must undergo mandatory external audit.",
        "expected_score_min": 4.0,
        "expected_score_max": 5.0,
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "CONDITION_EXCEPTION_LOSS",
        "expected_adjustment": True,
    },
    {
        "id": 7,
        "name": "Legal Scope Expanded",
        "language": "en",
        "description": "Geographical and institutional restriction ('applies only to registered cooperative societies in scheduled tribal districts') broadened to universal application.",
        "original": "This regulation applies only to registered cooperative credit societies operating in scheduled tribal districts.",
        "simplified": "This regulation applies to all cooperative credit societies in all districts without restriction.",
        "expected_score_min": 4.5,
        "expected_score_max": 5.5,
        "expected_decision": "PARTIALLY_PRESERVED",
        "expected_error": "SCOPE_CHANGE",
        "expected_adjustment": True,
    },
    {
        "id": 8,
        "name": "Hindi Modality Weakening",
        "language": "hi",
        "description": "Hindi mandatory verbal inflection ('भुगतान करेगा') weakened to discretionary permission ('भुगतान कर सकेगा').",
        "original": "नियोक्ता तीस दिनों की कालावधि के भीतर कर्मचारी को देय उपदान का संदाय करेगा।",
        "simplified": "नियोक्ता तीस दिनों की अवधि में कर्मचारी को देय उपदान का भुगतान कर सकेगा।",
        "expected_score_min": 3.5,
        "expected_score_max": 4.5,
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "MODALITY_CHANGE",
        "expected_adjustment": True,
    },
    {
        "id": 9,
        "name": "Harmless Vocabulary Change",
        "language": "en",
        "description": "Permissive discretion retained using equivalent plain-language formulation ('is authorized to' <=> 'may, at his discretion').",
        "original": "The Commissioner may, at his discretion, grant an extension of time for filing the statement.",
        "simplified": "The Commissioner is authorized to grant more time for filing the statement.",
        "expected_score_min": 9.0,
        "expected_score_max": 10.0,
        "expected_decision": "PRESERVED",
        "expected_error": "NONE",
        "expected_adjustment": False,
    },
    {
        "id": 10,
        "name": "Verbatim Identical Texts",
        "language": "hi",
        "description": "Source and candidate are identical Devanagari Hindi text.",
        "original": "धारा 24(1) के अधीन मुख्य रजिस्ट्रार द्वारा प्राधिकृत अधिकारी अपराध के शमन हेतु पचास रुपये तक की राशि स्वीकार कर सकेगा।",
        "simplified": "धारा 24(1) के अधीन मुख्य रजिस्ट्रार द्वारा प्राधिकृत अधिकारी अपराध के शमन हेतु पचास रुपये तक की राशि स्वीकार कर सकेगा।",
        "expected_score_min": 9.5,
        "expected_score_max": 10.0,
        "expected_decision": "PRESERVED",
        "expected_error": "NONE",
        "expected_adjustment": False,
    },
]


def run_hybrid_demo_suite():
    print("=" * 80)
    print("RUNNING JUDGEBERT HYBRID NEURO-SYMBOLIC DEMONSTRATION SUITE")
    print("=" * 80)
    print("Initializing JUDGEBERT Inference Engine & Explainability Engine...")

    t0 = time.time()
    inference_engine = JudgeBERTInferenceEngine(
        weights_path="models/judgebert/judgebert_weights.pt",
        tokenizer_dir="models/judgebert",
        device="cpu",
    )
    explainability_engine = LegalExplainabilityEngine()
    print(f"Engines initialized in {time.time() - t0:.2f}s\n")

    results = []
    all_passed = True

    print(f"{'#':<3} | {'Test Case Name':<34} | {'Raw (Neural)':<22} | {'Hybrid (Neuro-Symbolic)':<26} | {'Status'}")
    print("-" * 105)

    for case in TEST_CASES:
        orig = case["original"]
        simp = case["simplified"]

        # 1. Run raw neural inference
        raw_pred = inference_engine.predict(orig, simp)
        raw_score = raw_pred["lmp_score"]
        raw_dec = raw_pred["pred_decision"]
        raw_err = raw_pred["pred_error"]

        # 2. Run hybrid explainability synthesis
        explanation = explainability_engine.explain(
            original_text=orig,
            simplified_text=simp,
            prediction=raw_pred,
        )
        hybrid_pred = explanation["hybrid_prediction"]
        hybrid_score = hybrid_pred["lmp_score"]
        hybrid_dec = hybrid_pred["pred_decision"]
        hybrid_err = hybrid_pred["pred_error"]
        adj_applied = hybrid_pred["hybrid_adjustment_applied"]
        adj_reason = hybrid_pred["adjustment_reason"]

        # 3. Assertions
        score_ok = case["expected_score_min"] <= hybrid_score <= case["expected_score_max"]
        dec_ok = (hybrid_dec == case["expected_decision"])
        err_ok = (hybrid_err == case["expected_error"])
        adj_ok = (adj_applied == case["expected_adjustment"])

        passed = score_ok and dec_ok and err_ok and adj_ok
        if not passed:
            all_passed = False

        status_str = "PASS [OK]" if passed else "FAIL [X]"

        raw_str = f"{raw_score:.2f} | {raw_dec[:4]} | {raw_err[:4]}"
        hybrid_str = f"{hybrid_score:.2f} | {hybrid_dec[:4]} | {hybrid_err[:4]} | {'Adj' if adj_applied else 'Clean'}"

        print(f"{case['id']:<3} | {case['name']:<34} | {raw_str:<22} | {hybrid_str:<26} | {status_str}")

        results.append({
            "case": case,
            "raw_pred": raw_pred,
            "hybrid_pred": hybrid_pred,
            "explanation": explanation,
            "passed": passed,
            "score_ok": score_ok,
            "dec_ok": dec_ok,
            "err_ok": err_ok,
            "adj_ok": adj_ok,
        })

    print("-" * 105)
    print(f"Overall Suite Result: {'ALL 10 TESTS PASSED [SUCCESS]' if all_passed else 'SOME TESTS FAILED'}\n")

    # Detailed Inspection Printout
    print("=" * 80)
    print("DETAILED CASE-BY-CASE AUDIT & GROUNDING BREAKDOWN")
    print("=" * 80)
    for res in results:
        case = res["case"]
        raw = res["raw_pred"]
        hyb = res["hybrid_pred"]
        exp = res["explanation"]

        print(f"\nCase #{case['id']}: {case['name']} ({case['language'].upper()})")
        print(f"  Description:   {case['description']}")
        print(f"  Original:      \"{case['original'][:90]}...\"")
        print(f"  Simplified:    \"{case['simplified'][:90]}...\"")
        print(f"  Raw Neural:    Score: {raw['lmp_score']:.2f} | Decision: {raw['pred_decision']} | Error: {raw['pred_error']}")
        print(f"  Hybrid Result: Score: {hyb['lmp_score']:.2f} | Decision: {hyb['pred_decision']} | Error: {hyb['pred_error']}")
        print(f"  Adjustment:    {hyb['hybrid_adjustment_applied']} | Reason: {hyb['adjustment_reason']}")
        shifts_summary = [s['type'] for cat in exp['detected_invariant_shifts'].values() for s in cat]
        print(f"  Detected Invariants: {shifts_summary or 'Zero Invariant Violations (Preserved)'}")
        print(f"  Synthesis:     {exp['human_readable_summary']}")
        print(f"  Test Verdict:  {'PASSED' if res['passed'] else 'FAILED'}")

    return all_passed


if __name__ == "__main__":
    success = run_hybrid_demo_suite()
    sys.exit(0 if success else 1)
