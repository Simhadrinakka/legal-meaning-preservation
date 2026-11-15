"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/verify_backend_explainability.py
Task: Comprehensive Verification Suite for backend/explainability.py
=============================================================================

Tests:
1. English Preserved Statutory Example
2. Hindi Preserved Statutory Example
3. Numerical & Citation Distortions (e.g. 50 -> 500 rupees)
4. Negation & Deontic Modality Distortions (e.g. shall not -> may)
5. Condition & Proviso Omissions (e.g. dropping 'Subject to...')
6. Identical Original & Simplified Texts
7. Empty & Invalid Input Handling
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.explainability import LegalExplainabilityEngine


def test_explainability_suite():
    print("=" * 75)
    print("LEGAL EXPLAINABILITY ENGINE VERIFICATION SUITE")
    print("=" * 75)

    engine = LegalExplainabilityEngine()

    # -------------------------------------------------------------------------
    # Test 1: English Preserved Statutory Example
    # -------------------------------------------------------------------------
    print("\n[Test 1] English Preserved Statutory Example...")
    orig_en = (
        "(1) Subject to such conditions as may be prescribed, any officer authorised "
        "by the Chief Registrar by a general or special order in this behalf may, "
        "either before or after the institution of criminal proceedings under this Act, "
        "accept from the person who has committed or is reasonably suspected of having "
        "committed an offence under this Act, by way of composition of such offence "
        "a sum of money not exceeding fifty rupees."
    )
    simp_en = (
        "(1) Subject to prescribed conditions, an officer authorized by the Chief Registrar "
        "by a general or special order may, either before or after criminal proceedings "
        "are initiated under this Act, accept up to fifty rupees to compound an offence "
        "from any person who has committed or is suspected of committing that offence."
    )
    mock_pred_en = {
        "lmp_score": 9.5,
        "pred_decision": "PRESERVED",
        "pred_error": "NONE",
        "decision_probabilities": {"PRESERVED": 0.95, "MOSTLY_PRESERVED": 0.03},
        "error_probabilities": {"NONE": 0.88, "OMISSION": 0.05},
    }
    res1 = engine.explain(orig_en, simp_en, prediction=mock_pred_en)
    assert res1["predicted_score"] == 9.5
    assert res1["predicted_decision"] == "PRESERVED"
    assert "text_differences" in res1
    assert "method_and_limitations" in res1
    print(f"  Summary: {res1['human_readable_summary']}")
    print(f"  Lexical Overlap: {res1['text_differences']['lexical_overlap_ratio']:.2f}")
    print("  PASS: English preserved explanation structured correctly.")

    # -------------------------------------------------------------------------
    # Test 2: Hindi Preserved Statutory Example
    # -------------------------------------------------------------------------
    print("\n[Test 2] Hindi Preserved Statutory Example...")
    orig_hi = (
        "धारा 24 की उपधारा (1) के अधीन किसी अपराध के शमन के लिए कोई भी धनराशि, "
        "जो पचास रुपये से अधिक न हो, ऐसे अधिकारी द्वारा स्वीकार की जा सकेगी "
        "जिसे मुख्य रजिस्ट्रार द्वारा साधारण या विशेष आदेश द्वारा इस निमित्त प्राधिकृत किया गया हो।"
    )
    simp_hi = (
        "धारा 24(1) के अधीन मुख्य रजिस्ट्रार द्वारा प्राधिकृत अधिकारी अपराध के शमन हेतु "
        "पचास रुपये तक की राशि स्वीकार कर सकेगा।"
    )
    mock_pred_hi = {
        "lmp_score": 9.2,
        "pred_decision": "PRESERVED",
        "pred_error": "NONE",
        "decision_probabilities": {"PRESERVED": 0.92, "MOSTLY_PRESERVED": 0.05},
        "error_probabilities": {"NONE": 0.82, "OMISSION": 0.08},
    }
    res2 = engine.explain(orig_hi, simp_hi, prediction=mock_pred_hi)
    assert res2["predicted_score"] == 9.2
    assert res2["predicted_decision"] == "PRESERVED"
    print(f"  Summary: {res2['human_readable_summary']}")
    print("  PASS: Hindi preserved explanation structured correctly.")

    # -------------------------------------------------------------------------
    # Test 3: Numerical & Section Reference Distortion
    # -------------------------------------------------------------------------
    print("\n[Test 3] Numerical & Reference Discrepancy Detection...")
    orig_num = "The fine shall not exceed fifty rupees under Section 24."
    simp_num = "The fine must not exceed five hundred rupees under Section 99."
    res3 = engine.explain(orig_num, simp_num, prediction={"lmp_score": 4.0, "pred_decision": "MAJOR_LOSS", "pred_error": "NUMERIC_ENTITY_REFERENCE_ERROR"})
    num_shifts = res3["detected_invariant_shifts"]["numerical_reference_shifts"]
    assert len(num_shifts) > 0, "Failed to detect numerical/citation discrepancy"
    print(f"  Detected shifts: {[s['type'] for s in num_shifts]}")
    print(f"  Details: {num_shifts[0]['details']}")
    print("  PASS: Numerical and citation changes successfully flagged.")

    # -------------------------------------------------------------------------
    # Test 4: Negation & Deontic Modality Distortion
    # -------------------------------------------------------------------------
    print("\n[Test 4] Deontic Modality & Prohibition Inversion...")
    orig_modal = "No person shall operate without a valid license. Every applicant shall register."
    simp_modal = "Any person may operate without a license. Applicants should register."
    res4 = engine.explain(orig_modal, simp_modal, prediction={"lmp_score": 2.0, "pred_decision": "FUNDAMENTALLY_ALTERED", "pred_error": "MODALITY_CHANGE"})
    modal_shifts = res4["detected_invariant_shifts"]["modal_shifts"]
    neg_shifts = res4["detected_invariant_shifts"]["negation_prohibition_shifts"]
    assert len(modal_shifts) > 0, "Failed to detect modal shift"
    assert len(neg_shifts) > 0, "Failed to detect dropped negation/prohibition"
    print(f"  Modal shift: {modal_shifts[0]['details']}")
    print(f"  Negation shift: {neg_shifts[0]['details']}")
    print("  PASS: Modality weakening and prohibition removal successfully detected.")

    # -------------------------------------------------------------------------
    # Test 5: Condition & Proviso Omission
    # -------------------------------------------------------------------------
    print("\n[Test 5] Condition & Proviso Omission...")
    orig_cond = "Provided that the State Government may by notification exempt any class of persons."
    simp_cond = "The State Government may exempt anyone."
    res5 = engine.explain(orig_cond, simp_cond, prediction={"lmp_score": 5.0, "pred_decision": "PARTIALLY_PRESERVED", "pred_error": "CONDITION_EXCEPTION_LOSS"})
    cond_shifts = res5["detected_invariant_shifts"]["condition_exception_shifts"]
    assert len(cond_shifts) > 0, "Failed to detect dropped proviso"
    print(f"  Proviso shift: {cond_shifts[0]['details']}")
    print("  PASS: Proviso omission successfully detected.")

    # -------------------------------------------------------------------------
    # Test 6: Identical Original & Simplified Texts
    # -------------------------------------------------------------------------
    print("\n[Test 6] Identical Text Handling...")
    text_identical = "Any person aggrieved by an order may appeal within thirty days."
    res6 = engine.explain(text_identical, text_identical)
    assert res6["predicted_score"] == 10.0
    assert res6["predicted_decision"] == "PRESERVED"
    assert res6["text_differences"]["lexical_overlap_ratio"] == 1.0
    assert len(res6["text_differences"]["omitted_segments"]) == 0
    assert len(res6["text_differences"]["added_segments"]) == 0
    assert sum(len(v) for v in res6["detected_invariant_shifts"].values()) == 0
    print(f"  Summary: {res6['human_readable_summary']}")
    print("  PASS: Identical text correctly evaluated with zero drift and 10.0 score.")

    # -------------------------------------------------------------------------
    # Test 7: Empty & Invalid Input Handling
    # -------------------------------------------------------------------------
    print("\n[Test 7] Empty and Invalid Input Handling...")
    res7_empty = engine.explain("", "Some text")
    assert "error" in res7_empty
    assert res7_empty["predicted_score"] is None

    res7_none = engine.explain(None, None)
    assert "error" in res7_none
    assert res7_none["predicted_score"] is None
    print(f"  Error message: {res7_empty['error']}")
    print("  PASS: Invalid and empty inputs handled gracefully.")

    print("\n" + "=" * 75)
    print("ALL 7 EXPLAINABILITY TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 75)


if __name__ == "__main__":
    test_explainability_suite()
