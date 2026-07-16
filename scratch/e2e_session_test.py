"""End-to-end test: session quota + Firecrawl scrape."""
import time
import uuid
import requests

BASE = "http://127.0.0.1:8000"


def main():
    fresh = str(uuid.uuid4())
    print("=== 1. Create session ===")
    r = requests.get(f"{BASE}/api/session", headers={"X-Session-Id": fresh}, timeout=15)
    print(r.status_code, r.json())
    assert r.status_code == 200 and r.json()["uses_left"] == 3
    sid = r.json()["session_id"]
    assert sid == fresh

    print("=== 2. Start scrape (example.com) ===")
    r = requests.post(
        f"{BASE}/api/manual",
        headers={"X-Session-Id": sid, "Content-Type": "application/json"},
        json={"domains": ["example.com"]},
        timeout=30,
    )
    print(r.status_code, r.json())
    assert r.status_code == 200 and r.json()["success"]
    job_id = r.json()["job_id"]
    uses = r.json()["uses_left"]
    print("uses_left after job1:", uses)
    assert uses == 2

    print("=== 3. Poll job status ===")
    final = None
    for i in range(60):
        s = requests.get(f"{BASE}/api/status/{job_id}", timeout=15).json()
        print(
            f"  poll {i+1}: status={s.get('status')} "
            f"action={s.get('current_action')} "
            f"completed={s.get('completed')} errors={s.get('errors')}"
        )
        if s.get("status") in ("completed", "failed"):
            final = s
            break
        time.sleep(4)

    assert final is not None, "job did not finish"
    print("FINAL STATUS:", final["status"])
    print("RESULTS COUNT:", len(final.get("results", [])))
    if final.get("results"):
        r0 = final["results"][0]
        print(
            "SAMPLE:",
            {
                k: r0.get(k)
                for k in ["website", "company_name", "emails", "phones", "confidence"]
            },
        )

    # Scraping should complete successfully (results optional for thin sites)
    assert final["status"] == "completed", f"job failed: {final.get('current_action')}"

    print("=== 4. Consume remaining 2 scrapes ===")
    for n in range(2):
        r = requests.post(
            f"{BASE}/api/manual",
            headers={"X-Session-Id": sid, "Content-Type": "application/json"},
            json={"domains": ["example.org"]},
            timeout=30,
        )
        print(f"  scrape {n+2}:", r.status_code, r.json())
        assert r.status_code == 200

    print("=== 5. 4th scrape must be blocked ===")
    r = requests.post(
        f"{BASE}/api/manual",
        headers={"X-Session-Id": sid, "Content-Type": "application/json"},
        json={"domains": ["example.net"]},
        timeout=30,
    )
    print(r.status_code, r.text)
    assert r.status_code == 401

    print("=== 6. Session endpoint shows 0 ===")
    r = requests.get(f"{BASE}/api/session", headers={"X-Session-Id": sid}, timeout=15)
    print(r.json())
    assert r.json()["uses_left"] == 0

    print()
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
