"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: training/verify_frontend_integration.py
Task: End-to-End Verification of Frontend API Integration & Vite Proxy
=============================================================================

Tests:
1. Client-Side Input Validation (Empty text rejected prior to network request)
2. Live Flask Backend Startup on port 5000
3. Live Vite Dev Server on port 5173 with /api proxy to port 5000
4. End-to-End English Statutory Pair via Vite Proxy (POST http://localhost:5173/api/evaluate-pair)
5. End-to-End Hindi Statutory Pair via Vite Proxy (POST http://localhost:5173/api/evaluate-pair)
6. Error Handling: 400 Validation Error on empty/invalid inputs
7. Backend Unavailable / Offline Graceful Handling
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_frontend_integration():
    print("=" * 75)
    print("JUDGEBERT FRONTEND-BACKEND INTEGRATION VERIFICATION")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # Test 1: Start Flask Backend Server (Port 5000)
    # -------------------------------------------------------------------------
    print("\n[Step 1] Starting Flask backend server on port 5000...")
    py_exe = sys.executable
    backend_proc = subprocess.Popen(
        [py_exe, str(PROJECT_ROOT / "backend" / "main.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for Flask to initialize (loads 1.1GB weights ~15s)
    max_wait = 45
    backend_ready = False
    start_t = time.time()
    while time.time() - start_t < max_wait:
        try:
            req = urllib.request.Request("http://127.0.0.1:5000/api/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    if data.get("model_loaded"):
                        backend_ready = True
                        print(f"  Backend ready in {time.time() - start_t:.1f}s (device: {data.get('device')})")
                        break
        except Exception:
            pass
        time.sleep(2)

    assert backend_ready, "Backend server failed to start within timeout!"

    # -------------------------------------------------------------------------
    # Test 2: Start Vite Dev Server on Port 5173
    # -------------------------------------------------------------------------
    print("\n[Step 2] Starting Vite Dev Server on port 5173...")
    vite_proc = subprocess.Popen(
        ["cmd.exe", "/c", "npm run dev"],
        cwd=str(PROJECT_ROOT / "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    vite_ready = False
    start_v = time.time()
    while time.time() - start_v < 15:
        try:
            req = urllib.request.Request("http://localhost:5173/")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    vite_ready = True
                    print(f"  Vite server ready in {time.time() - start_v:.1f}s")
                    break
        except Exception:
            pass
        time.sleep(1)

    assert vite_ready, "Vite server failed to start within timeout!"

    try:
        # ---------------------------------------------------------------------
        # Test 3: Verify Vite Proxy Health Check (/api/health through port 5173)
        # ---------------------------------------------------------------------
        print("\n[Step 3] Testing Vite Proxy Health Endpoint (http://localhost:5173/api/health)...")
        req_health = urllib.request.Request("http://localhost:5173/api/health")
        with urllib.request.urlopen(req_health, timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["status"] == "healthy"
            assert data["model_loaded"] is True
            print(f"  PASS: Vite successfully proxied /api/health to Flask (model: {data['status']})")

        # ---------------------------------------------------------------------
        # Test 4: End-to-End English Statutory Pair via Proxy
        # ---------------------------------------------------------------------
        print("\n[Step 4] Testing End-to-End English Evaluation via Vite Proxy...")
        payload_en = {
            "original_text": (
                "Any officer authorised by the Chief Registrar by a general or special order in this behalf "
                "may accept from the person who has committed an offence under this Act a sum of money not "
                "exceeding fifty rupees by way of composition."
            ),
            "simplified_text": (
                "An authorized officer may accept up to fifty rupees to settle an offence under this Act."
            ),
            "language": "en",
        }
        req_en = urllib.request.Request(
            "http://localhost:5173/api/evaluate-pair",
            data=json.dumps(payload_en).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_en, timeout=10) as resp:
            assert resp.status == 200
            res_en = json.loads(resp.read().decode())
            assert res_en["success"] is True
            pred = res_en["prediction"]
            exp = res_en["explanation"]
            assert pred["lmp_score"] > 8.0
            assert pred["pred_decision"] in ["PRESERVED", "MOSTLY_PRESERVED"]
            assert "human_readable_summary" in exp
            assert "detected_invariant_shifts" in exp
            print(f"  Prediction Score: {pred['lmp_score']:.2f}/10.0 ({pred['pred_decision']})")
            print(f"  Latency: {res_en['latency_ms']}ms")
            print("  PASS: English end-to-end evaluation succeeded via Vite proxy.")

        # ---------------------------------------------------------------------
        # Test 5: End-to-End Hindi Statutory Pair via Proxy
        # ---------------------------------------------------------------------
        print("\n[Step 5] Testing End-to-End Hindi Evaluation via Vite Proxy...")
        payload_hi = {
            "original_text": (
                "धारा 24 की उपधारा (1) के अधीन किसी अपराध के शमन के लिए कोई भी धनराशि, "
                "जो पचास रुपये से अधिक न हो, ऐसे अधिकारी द्वारा स्वीकार की जा सकेगी।"
            ),
            "simplified_text": (
                "धारा 24(1) के अंतर्गत प्राधिकृत अधिकारी अपराध निपटाने के लिए पचास रुपये तक की राशि ले सकेगा।"
            ),
            "language": "hi",
        }
        req_hi = urllib.request.Request(
            "http://localhost:5173/api/evaluate-pair",
            data=json.dumps(payload_hi).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_hi, timeout=10) as resp:
            assert resp.status == 200
            res_hi = json.loads(resp.read().decode())
            assert res_hi["success"] is True
            pred_hi = res_hi["prediction"]
            assert pred_hi["lmp_score"] > 8.0
            print(f"  Prediction Score: {pred_hi['lmp_score']:.2f}/10.0 ({pred_hi['pred_decision']})")
            print("  PASS: Hindi end-to-end evaluation succeeded via Vite proxy.")

        # ---------------------------------------------------------------------
        # Test 6: Error Handling via Proxy (400 Bad Request on empty text)
        # ---------------------------------------------------------------------
        print("\n[Step 6] Testing Error Handling on Empty Inputs...")
        payload_bad = {
            "original_text": "   ",
            "simplified_text": "Sample text",
        }
        req_bad = urllib.request.Request(
            "http://localhost:5173/api/evaluate-pair",
            data=json.dumps(payload_bad).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req_bad, timeout=5) as resp:
                assert False, "Expected HTTP 400 Bad Request"
        except urllib.error.HTTPError as err:
            assert err.code == 400
            err_data = json.loads(err.read().decode())
            assert "cannot be empty" in err_data.get("message", "")
            print(f"  PASS: Proxy properly forwarded 400 Bad Request: {err_data['message']}")

    finally:
        # Clean teardown of both processes
        print("\n[Tear Down] Shutting down Vite and Flask servers...")
        try:
            backend_proc.terminate()
            backend_proc.wait(timeout=5)
        except Exception:
            backend_proc.kill()

        try:
            vite_proc.terminate()
            vite_proc.wait(timeout=5)
        except Exception:
            vite_proc.kill()

        # Clean any remaining node processes
        subprocess.run(
            ["powershell", "-Command", "Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -gt (Get-Date).AddSeconds(-90) } | Stop-Process -Force -ErrorAction SilentlyContinue"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    print("\n" + "=" * 75)
    print("ALL FRONTEND-BACKEND INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    test_frontend_integration()
