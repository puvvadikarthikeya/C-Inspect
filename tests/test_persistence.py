"""
Unit tests for Persistence, Recurrence logic, and Profile isolation.
Verifies PRD Requirements FR-06, FR-07, FR-08, FR-11.
"""
import unittest
import os
import tempfile
from backend.storage.db import HistoryDatabase


class TestHistoryDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db = HistoryDatabase(self.temp_db.name)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass

    def test_student_profiles(self):
        students = self.db.get_students()
        self.assertGreaterEqual(len(students), 2)  # pre-seeded students

        new_student = self.db.create_student("Jordan Lee")
        self.assertTrue(new_student["student_id"].startswith("student_"))
        self.assertEqual(new_student["display_name"], "Jordan Lee")

    def test_recurrence_counting(self):
        student_id = "student_test_recurrence"
        self.db.create_student("Test Student")

        diag_sample = [{
            "rule_id": "ASSIGNMENT_IN_CONDITION",
            "message": "Suspicious assignment '=' in condition",
            "severity": "warning",
            "line": 3,
            "column": 9,
            "explanation": "Assignment in condition"
        }]

        # 1st Submission
        sub1 = self.db.record_submission(student_id, "lab1.c", "code1", diag_sample)
        self.assertEqual(len(sub1["findings"]), 1)
        self.assertEqual(sub1["findings"][0]["recurrence_count"], 1)

        # 2nd Submission (same rule)
        sub2 = self.db.record_submission(student_id, "lab2.c", "code2", diag_sample)
        self.assertEqual(len(sub2["findings"]), 1)
        self.assertEqual(sub2["findings"][0]["recurrence_count"], 2)

        # Verify live recurrence check mapping
        rec_map = self.db.get_recurrence_for_rules(student_id, ["ASSIGNMENT_IN_CONDITION"])
        self.assertEqual(rec_map["ASSIGNMENT_IN_CONDITION"], 2)

    def test_profile_isolation(self):
        """Verify Student A and Student B have separate mistake counts (FR-11)."""
        student_a = "student_a"
        student_b = "student_b"
        diag = [{
            "rule_id": "UNDECLARED_IDENTIFIER",
            "message": "Undeclared identifier 'x'",
            "severity": "error",
            "line": 2,
            "column": 5
        }]

        # Student A makes 2 submissions with this error
        self.db.record_submission(student_a, "task1.c", "...", diag)
        self.db.record_submission(student_a, "task2.c", "...", diag)

        # Student B makes 1 submission with this error
        sub_b = self.db.record_submission(student_b, "task1.c", "...", diag)

        self.assertEqual(sub_b["findings"][0]["recurrence_count"], 1)
        rec_map_a = self.db.get_recurrence_for_rules(student_a, ["UNDECLARED_IDENTIFIER"])
        rec_map_b = self.db.get_recurrence_for_rules(student_b, ["UNDECLARED_IDENTIFIER"])
        self.assertEqual(rec_map_a["UNDECLARED_IDENTIFIER"], 2)
        self.assertEqual(rec_map_b["UNDECLARED_IDENTIFIER"], 1)

    def test_finding_status_update(self):
        """Verify FR-08: user can mark finding as corrected or dismissed."""
        student_id = "student_status_test"
        diag = [{
            "rule_id": "UNUSED_LOCAL_VARIABLE",
            "message": "Unused variable 'val'",
            "severity": "warning",
            "line": 2,
            "column": 5
        }]
        sub = self.db.record_submission(student_id, "prog.c", "...", diag)
        finding_id = sub["findings"][0]["finding_id"]

        # Mark as corrected
        ok = self.db.update_finding_status(finding_id, "corrected")
        self.assertTrue(ok)

        history = self.db.get_student_history(student_id)
        stat = next(s for s in history["rule_stats"] if s["rule_id"] == "UNUSED_LOCAL_VARIABLE")
        self.assertEqual(stat["corrected_count"], 1)
        self.assertEqual(stat["open_count"], 0)


if __name__ == "__main__":
    unittest.main()
