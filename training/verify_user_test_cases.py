"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/verify_user_test_cases.py
Task: Comprehensive Verification of the 8 Mandated Benchmark Cases (A through H)
=============================================================================
"""

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import create_app, registry

TEST_CASES = [
    {
        "key": "A",
        "name": "Shall -> May Modality Weakening",
        "original": "The employer shall pay the full amount of gratuity to the employee within thirty days.",
        "simplified": "The employer may pay the full amount of gratuity to the employee within thirty days.",
        "expected_score_range": (3.5, 4.5),
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "MODALITY_CHANGE",
        "expected_adjustment": True,
    },
    {
        "key": "B",
        "name": "Prohibition Reversal",
        "original": "No person shall operate any unregistered motor vehicle on any public road.",
        "simplified": "Any person may operate an unregistered motor vehicle on any public road.",
        "expected_score_range": (1.0, 2.0),
        "expected_decision": "FUNDAMENTALLY_ALTERED",
        "expected_error": "CONTRADICTION",
        "expected_adjustment": True,
    },
    {
        "key": "C",
        "name": "Numeric Threshold Changed",
        "original": "Any licensee who contravenes the terms of the license shall be liable to a penalty not exceeding 50,000 rupees.",
        "simplified": "Any licensee who contravenes the terms of the license shall be liable to a penalty not exceeding 500,000 rupees.",
        "expected_score_range": (3.0, 4.0),
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "expected_adjustment": True,
    },
    {
        "key": "D",
        "name": "Condition Removed (User's Exact Example)",
        "original": "A person may construct a building subject to prior approval from the competent authority.",
        "simplified": "A person may construct a building.",
        "expected_score_range": (4.0, 5.0),
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "CONDITION_EXCEPTION_LOSS",
        "expected_adjustment": True,
    },
    {
        "key": "E",
        "name": "Exception Removed",
        "original": "All financial transactions under Section 12 shall be subject to mandatory external audit, except transactions under ten thousand rupees.",
        "simplified": "All financial transactions under Section 12 must undergo mandatory external audit.",
        "expected_score_range": (4.0, 5.0),
        "expected_decision": "MAJOR_LOSS",
        "expected_error": "CONDITION_EXCEPTION_LOSS",
        "expected_adjustment": True,
    },
    {
        "key": "F",
        "name": "Scope Expanded",
        "original": "This regulation applies only to registered cooperative credit societies operating in scheduled tribal districts.",
        "simplified": "This regulation applies to all cooperative credit societies in all districts without restriction.",
        "expected_score_range": (4.5, 5.5),
        "expected_decision": "PARTIALLY_PRESERVED",
        "expected_error": "SCOPE_CHANGE",
        "expected_adjustment": True,
    },
    {
        "key": "G",
        "name": "Correct Paraphrase",
        "original": "(1) Subject to such conditions as may be prescribed, any officer authorised by the Chief Registrar by a general or special order in this behalf may accept from the person who has committed an offence under this Act a sum of money not exceeding fifty rupees.",
        "simplified": "(1) Subject to prescribed conditions, an officer authorized by the Chief Registrar by a general or special order may accept up to fifty rupees to compound an offence from any person who has committed that offence.",
        "expected_score_range": (9.0, 10.0),
        "expected_decision": "PRESERVED",
        "expected_error": "NONE",
        "expected_adjustment": False,
    },
    {
        "key": "H",
        "name": "Harmless Wording Change",
        "original": "The Commissioner may, at his discretion, grant an extension of time for filing the statement.",
        "simplified": "The Commissioner is authorized to grant more time for filing the statement.",
        "expected_score_range": (9.0, 10.0),
        "expected_decision": "PRESERVED",
        "expected_error": "NONE",
        "expected_adjustment": False,
    },
]


def run_verification():
    print("=" * 90)
    print("VERIFICATION OF 8 MANDATED BENCHMARK CASES (A THROUGH H)")
    print("=" * 90)

    app = create_app()
    client = app.test_client()

    results = []
    all_passed = True

    header = f"{'Case':<4} | {'Benchmark Name':<28} | {'Raw Neural':<14} | {'Hybrid Score':<14} | {'Decision':<14} | {'Error Category':<22} | {'Frontend Match'}"
    print(header)
    print("-" * 115)

    for case in TEST_CASES:
        payload = {
            "original_text": case["original"],
            "simplified_text": case["simplified"],
        }

        resp = client.post("/api/evaluate-pair", json=payload)
        assert resp.status_code == 200, f"API failed with {resp.status_code}"
        data = resp.get_json()

        # API responses
        api_pred = data["prediction"]
        api_raw = data["raw_prediction"]
        api_exp = data["explanation"]

        raw_score = api_raw["lmp_score"]
        hybrid_score = api_pred["lmp_score"]
        final_dec = api_pred["pred_decision"]
        final_err = api_pred["pred_error"]
        adj_applied = api_pred["hybrid_adjustment_applied"]

        # Simulate Frontend App.jsx exact rendering extraction logic
        fe_score = (
            api_pred.get("lmp_score")
            if api_pred.get("lmp_score") is not None
            else api_exp.get("predicted_score")
        )
        fe_decision = (
            api_pred.get("pred_decision")
            or api_pred.get("decision")
            or api_exp.get("predicted_decision")
        )
        fe_error = (
            api_pred.get("pred_error")
            or api_pred.get("error_type")
            or api_exp.get("predicted_error")
        )

        frontend_matches_api = (
            fe_score == hybrid_score
            and fe_decision == final_dec
            and fe_error == final_err
        )

        # Invariant checks
        shifts = api_exp.get("detected_invariant_shifts", {})
        shift_types = [s["type"] for cat in shifts.values() for s in cat]

        # Validations
        score_ok = case["expected_score_range"][0] <= hybrid_score <= case["expected_score_range"][1]
        dec_ok = (final_dec == case["expected_decision"])
        err_ok = (final_err == case["expected_error"])
        adj_ok = (adj_applied == case["expected_adjustment"])

        passed = score_ok and dec_ok and err_ok and adj_ok and frontend_matches_api
        if not passed:
            all_passed = False

        row = (
            f"[{case['key']}]  | "
            f"{case['name']:<28} | "
            f"{raw_score:<14.2f} | "
            f"{hybrid_score:<14.2f} | "
            f"{final_dec:<14} | "
            f"{final_err:<22} | "
            f"{'EXACT MATCH' if frontend_matches_api else 'MISMATCH'}"
        )
        print(row)

        results.append({
            "case": case,
            "raw_score": raw_score,
            "hybrid_score": hybrid_score,
            "final_dec": final_dec,
            "final_err": final_err,
            "shift_types": shift_types,
            "adj_applied": adj_applied,
            "adj_reason": api_pred.get("adjustment_reason"),
            "fe_score": fe_score,
            "frontend_matches_api": frontend_matches_api,
            "passed": passed,
        })

    print("-" * 115)
    print(f"Overall Benchmark Status: {'ALL 8 CASES PASSED [SUCCESS]' if all_passed else 'SOME CASES FAILED'}\n")

    print("=" * 90)
    print("DETAILED GROUNDING & INVARIANT AUDIT BREAKDOWN")
    print("=" * 90)
    for r in results:
        c = r["case"]
        print(f"\nCase [{c['key']}]: {c['name']}")
        print(f"  Original:        \"{c['original']}\"")
        print(f"  Simplified:      \"{c['simplified']}\"")
        print(f"  Raw Neural:      Score: {r['raw_score']:.2f}")
        print(f"  Hybrid Calib:    Score: {r['hybrid_score']:.2f} | Decision: {r['final_dec']} | Error: {r['final_err']}")
        print(f"  Invariants:      {r['shift_types'] or 'Zero Invariants (Full Legal Preservation)'}")
        print(f"  Adjustment:      Applied: {r['adj_applied']} | Reason: {r['adj_reason']}")
        print(f"  Frontend Render: Displayed Score: {r['fe_score']:.2f} == API Hybrid Score: {r['hybrid_score']:.2f} -> Match: {r['frontend_matches_api']}")
        print(f"  Verdict:         {'PASSED [OK]' if r['passed'] else 'FAILED'}")

    return all_passed


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
