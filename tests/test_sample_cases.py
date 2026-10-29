"""
Automated unit tests for official C-Inspect sample test cases in C-Inspect_Sample_Test_Cases/.
Verifies:
- 01_valid_program.c produces no diagnostics.
- 02_static_analysis_issues.c produces all 7 intended static analysis issues.
- 03A and 03B demonstrate recurrence tracking across submissions using the same student profile.
"""
import unittest
import os
import tempfile
from backend.analyzer.engine import StaticAnalysisEngine
from backend.storage.db import HistoryDatabase


class TestSampleCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = StaticAnalysisEngine()
        cls.base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "C-Inspect_Sample_Test_Cases")
        )

    def _read_file(self, filename: str) -> str:
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def test_01_valid_program(self):
        """01_valid_program.c should produce no intentional static-analysis findings."""
        code = self._read_file("01_valid_program.c")
        result = self.engine.analyze(code)
        self.assertEqual(len(result["diagnostics"]), 0, f"Expected 0 findings, got: {result['diagnostics']}")

    def test_02_static_analysis_issues(self):
        """02_static_analysis_issues.c should detect all 7 intentional static-analysis issues."""
        code = self._read_file("02_static_analysis_issues.c")
        result = self.engine.analyze(code)
        rule_ids = [d["rule_id"] for d in result["diagnostics"]]

        # 1. Unused local variable (unused_value, unused_main_value)
        unused = [d for d in result["diagnostics"] if d["rule_id"] == "UNUSED_LOCAL_VARIABLE"]
        self.assertGreaterEqual(len(unused), 2)
        unused_names = [d["message"] for d in unused]
        self.assertTrue(any("unused_value" in m for m in unused_names))
        self.assertTrue(any("unused_main_value" in m for m in unused_names))

        # 2. Assignment in condition: if (value = limit)
        self.assertIn("ASSIGNMENT_IN_CONDITION", rule_ids)

        # 3. Missing return path in missing_return()
        self.assertIn("MISSING_RETURN", rule_ids)

        # 4. Duplicate declaration of result
        self.assertIn("DUPLICATE_DECLARATION", rule_ids)

        # 5. Undeclared identifier grand_total
        self.assertIn("UNDECLARED_IDENTIFIER", rule_ids)
        undeclared = [d for d in result["diagnostics"] if d["rule_id"] == "UNDECLARED_IDENTIFIER"]
        self.assertTrue(any("grand_total" in d["message"] for d in undeclared))

        # 6. Statement after return: unreachable code
        self.assertIn("UNREACHABLE_CODE", rule_ids)

    def test_03_history_and_recurrence(self):
        """
        03A and 03B should trigger UNDECLARED_IDENTIFIER with different variable spellings,
        and the recurrence count should increase across submissions.
        """
        code_3a = self._read_file("03A_history_first_submission.c")
        code_3b = self._read_file("03B_history_repeat_submission.c")

        res_3a = self.engine.analyze(code_3a)
        res_3b = self.engine.analyze(code_3b)

        rule_ids_3a = [d["rule_id"] for d in res_3a["diagnostics"]]
        rule_ids_3b = [d["rule_id"] for d in res_3b["diagnostics"]]

        self.assertIn("UNDECLARED_IDENTIFIER", rule_ids_3a)
        self.assertIn("UNDECLARED_IDENTIFIER", rule_ids_3b)

        # Test recurrence count via SQLite database
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db.close()
        try:
            db = HistoryDatabase(temp_db.name)
            student_id = "student_history_test"
            db.create_student("History Test Student")

            # 1st Submission (03A)
            sub1 = db.record_submission(student_id, "03A_history_first_submission.c", code_3a, res_3a["diagnostics"])
            find1 = next(f for f in sub1["findings"] if f["rule_id"] == "UNDECLARED_IDENTIFIER")
            self.assertEqual(find1["recurrence_count"], 1)

            # 2nd Submission (03B)
            sub2 = db.record_submission(student_id, "03B_history_repeat_submission.c", code_3b, res_3b["diagnostics"])
            find2 = next(f for f in sub2["findings"] if f["rule_id"] == "UNDECLARED_IDENTIFIER")
            self.assertEqual(find2["recurrence_count"], 2)

            # Recurrence map should reflect 2
            rec_map = db.get_recurrence_for_rules(student_id, ["UNDECLARED_IDENTIFIER"])
            self.assertEqual(rec_map["UNDECLARED_IDENTIFIER"], 2)
        finally:
            if os.path.exists(temp_db.name):
                try:
                    os.remove(temp_db.name)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
