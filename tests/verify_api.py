"""
End-to-end integration verification script for C-Inspect API server.
"""
import requests

base = "http://127.0.0.1:8000"

def run_checks():
    # 1. Compiler status
    print("1. Testing /api/compiler-status...")
    r = requests.get(f"{base}/api/compiler-status")
    print("Compiler status response:", r.status_code, r.json())
    assert r.status_code == 200

    # 2. Analyze demo code
    demo_code = """int main(void) {
    int marks = 90;
    if (marks = 50) {
        return 1;
    }
    return 0;
}"""
    print("\n2. Testing /api/analyze with PRD demo code...")
    r = requests.post(f"{base}/api/analyze", json={"code": demo_code, "student_id": "student_demo"})
    assert r.status_code == 200
    data = r.json()
    rule_ids = [d["rule_id"] for d in data["diagnostics"]]
    print("Rule IDs detected:", rule_ids)
    assert "ASSIGNMENT_IN_CONDITION" in rule_ids
    print("Summary:", data["summary"])

    # 3. Checkpoint submission 1
    print("\n3. Testing /api/submit (First submission)...")
    r = requests.post(f"{base}/api/submit", json={"code": demo_code, "student_id": "student_demo", "file_name": "lab1.c"})
    assert r.status_code == 200
    sub1 = r.json()
    rec1 = sub1["submission"]["findings"][0]["recurrence_count"]
    print("Submission 1 ID:", sub1["submission"]["submission_id"])
    print("Submission 1 recurrence count for ASSIGNMENT_IN_CONDITION:", rec1)

    # 4. Checkpoint submission 2
    print("\n4. Testing /api/submit (Second submission - recurrence test)...")
    r = requests.post(f"{base}/api/submit", json={"code": demo_code, "student_id": "student_demo", "file_name": "lab2.c"})
    assert r.status_code == 200
    sub2 = r.json()
    rec2 = sub2["submission"]["findings"][0]["recurrence_count"]
    print("Submission 2 recurrence count for ASSIGNMENT_IN_CONDITION:", rec2)
    assert rec2 > rec1

    # 5. History retrieval
    print("\n5. Testing /api/history...")
    r = requests.get(f"{base}/api/history?student_id=student_demo")
    assert r.status_code == 200
    hist = r.json()
    print("Submissions in history:", hist["submissions_count"])
    print("Rule statistics:", hist["rule_stats"])

    # 6. Run compiler / simulation
    print("\n6. Testing /api/run...")
    r = requests.post(f"{base}/api/run", json={"code": demo_code})
    assert r.status_code == 200
    run_res = r.json()
    print("Run response stage:", run_res["stage"])
    print("Program output preview:\n", run_res["runtime_output"][:200])

    # 7. Test /api/samples
    print("\n7. Testing /api/samples...")
    r = requests.get(f"{base}/api/samples")
    assert r.status_code == 200
    samples = r.json()
    print(f"Loaded {len(samples)} sample test case files.")
    assert len(samples) >= 4

    # 8. Test PATCH /api/findings/{finding_id} status update (FR-08)
    print("\n8. Testing PATCH /api/findings/{finding_id}...")
    finding_id = sub1["submission"]["findings"][0]["finding_id"]
    r = requests.patch(f"{base}/api/findings/{finding_id}", json={"status": "corrected"})
    assert r.status_code == 200
    assert r.json()["status"] == "corrected"
    print(f"Finding {finding_id} updated to 'corrected'.")

    # 9. Completed API checks
    print("\n>>> ALL API CHECKS COMPLETED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_checks()
