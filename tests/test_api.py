"""
================================================================
  X Scraper API - Local Test Suite
  --------------------------------------------------------------
  Run while the server is live (.\run.bat):
      python tests/test_api.py

  What it does:
    1. Health Check         → GET  /health
    2. Auth Guard Test      → POST /scrape with WRONG key (expects 403)
    3. Auth Guard Test      → POST /scrape with NO key    (expects 403)
    4. Valid Scrape Request  → POST /scrape with correct key + mock data
    5. Missing Field Test   → POST /scrape missing required field (expects 422)

  Each test prints ✅ or ❌ so you can see what's happening.
═══════════════════════════════════════════════════════════════
"""

import requests
import json
import sys

# ── Configuration ──
BASE_URL = "http://localhost:8001"
VALID_API_KEY = "TVlfU1VQRVJfU0VDUkVUX0FDQ0VTU19LRVlfMjAyNg=="
FAKE_API_KEY = "this_is_a_fake_key_lol"

# ── Mock Data ──
MOCK_SCRAPE_REQUESTS = [
    {
        "name": "Elon Musk — 5 posts",
        "payload": {
            "username": "elonmusk",
            "limit": 5,
            "destination_id": "-1001234567890",
            "user_id": 99001
        }
    },
    {
        "name": "MKBHD — 10 posts",
        "payload": {
            "username": "MKBHD",
            "limit": 10,
            "destination_id": "-1009876543210",
            "user_id": 99002
        }
    },
    {
        "name": "NASA — Default limit (20)",
        "payload": {
            "username": "NASA",
            "destination_id": "-1005555555555",
            "user_id": 99003
        }
    },
]

# ── Helpers ──
passed = 0
failed = 0

def test(name, condition, response):
    global passed, failed
    status = response.status_code
    if condition:
        print(f"  [PASS] {name}  (HTTP {status})")
        passed += 1
    else:
        print(f"  [FAIL] {name}  (HTTP {status})")
        print(f"     Response: {response.text[:200]}")
        failed += 1

def header(title):
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")

# == TEST 1: Health Check =====================================
header("TEST 1: Health Check - GET /health")

try:
    r = requests.get(f"{BASE_URL}/health")
    test("Server is healthy", r.status_code == 200 and r.json().get("status") == "healthy", r)
    print(f"     Body: {r.json()}")
except requests.ConnectionError:
    print("  [FAIL] Cannot connect to server! Is it running? (run.bat)")
    sys.exit(1)

# == TEST 2: Auth Guard - Wrong API Key =======================
header("TEST 2: Auth Guard - Wrong API Key")

r = requests.post(
    f"{BASE_URL}/scrape",
    headers={"X-API-Key": FAKE_API_KEY},
    json=MOCK_SCRAPE_REQUESTS[0]["payload"]
)
test("Rejected with 403", r.status_code == 403, r)

# == TEST 3: Auth Guard - No API Key ==========================
header("TEST 3: Auth Guard - No API Key at all")

r = requests.post(
    f"{BASE_URL}/scrape",
    json=MOCK_SCRAPE_REQUESTS[0]["payload"]
)
test("Rejected with 403", r.status_code == 403, r)

# == TEST 4: Valid Scrape Requests (Mock Data) ================
header("TEST 4: Valid Scrape Requests - POST /scrape")

for mock in MOCK_SCRAPE_REQUESTS:
    r = requests.post(
        f"{BASE_URL}/scrape",
        headers={"X-API-Key": VALID_API_KEY},
        json=mock["payload"]
    )
    test(
        f"Scrape [{mock['name']}]",
        r.status_code == 200 and r.json().get("status") == "success",
        r
    )
    if r.status_code == 200:
        print(f"     Response: {json.dumps(r.json(), indent=2)}")

# == TEST 5: Validation - Missing Required Field ==============
header("TEST 5: Validation - Missing 'destination_id' field")

r = requests.post(
    f"{BASE_URL}/scrape",
    headers={"X-API-Key": VALID_API_KEY},
    json={"username": "elonmusk", "limit": 5}  # No destination_id!
)
test("Rejected with 422 (Validation Error)", r.status_code == 422, r)

# == RESULTS ===================================================
header("RESULTS")
total = passed + failed
print(f"  Passed: {passed}/{total}")
print(f"  Failed: {failed}/{total}")
print()

if failed > 0:
    print("  [!!] Some tests failed. Check the output above.")
    sys.exit(1)
else:
    print("  [OK] All tests passed! Your API is working correctly.")
    sys.exit(0)
