"""
Unit tests for C-Inspect Static Analysis Engine.
Verifies PRD Acceptance Criteria:
- Syntax Error detection
- Undeclared Identifier detection
- Duplicate Declaration detection
- Assignment in Condition detection (Demo scenario)
- Unused Local Variable detection
- Unreachable Code detection
"""
import unittest
from backend.analyzer.engine import StaticAnalysisEngine


class TestStaticAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = StaticAnalysisEngine()

    def test_demo_scenario_assignment_in_condition(self):
        code = """int main(void) {
    int marks = 90;
    if (marks = 50) {
        return 1;
    }
    return 0;
}"""
        res = self.engine.analyze(code)
        rule_ids = [d["rule_id"] for d in res["diagnostics"]]
        self.assertIn("ASSIGNMENT_IN_CONDITION", rule_ids)
        
        # Verify diagnostic details
        diag = next(d for d in res["diagnostics"] if d["rule_id"] == "ASSIGNMENT_IN_CONDITION")
        self.assertEqual(diag["line"], 3)
        self.assertEqual(diag["severity"], "warning")
        self.assertIn("==", diag["suggestion"])

    def test_undeclared_identifier(self):
        code = """int main(void) {
    total = 100;
    return 0;
}"""
        res = self.engine.analyze(code)
        rule_ids = [d["rule_id"] for d in res["diagnostics"]]
        self.assertIn("UNDECLARED_IDENTIFIER", rule_ids)
        diag = next(d for d in res["diagnostics"] if d["rule_id"] == "UNDECLARED_IDENTIFIER")
        self.assertEqual(diag["line"], 2)
        self.assertIn("total", diag["message"])

    def test_duplicate_declaration(self):
        code = """int main(void) {
    int score = 10;
    int score = 20;
    return score;
}"""
        res = self.engine.analyze(code)
        rule_ids = [d["rule_id"] for d in res["diagnostics"]]
        self.assertIn("DUPLICATE_DECLARATION", rule_ids)
        diag = next(d for d in res["diagnostics"] if d["rule_id"] == "DUPLICATE_DECLARATION")
        self.assertEqual(diag["line"], 3)

    def test_unused_local_variable(self):
        code = """int main(void) {
    int unused_val = 42;
    int used_val = 10;
    return used_val;
}"""
        res = self.engine.analyze(code)
        rule_ids = [d["rule_id"] for d in res["diagnostics"]]
        self.assertIn("UNUSED_LOCAL_VARIABLE", rule_ids)
        diag = next(d for d in res["diagnostics"] if d["rule_id"] == "UNUSED_LOCAL_VARIABLE")
        self.assertIn("unused_val", diag["message"])

    def test_syntax_error(self):
        code = """int main(void) {
    int x = ;
    return 0;
}"""
        res = self.engine.analyze(code)
        rule_ids = [d["rule_id"] for d in res["diagnostics"]]
        self.assertIn("SYNTAX_ERROR", rule_ids)

    def test_unreachable_code(self):
        code = """int main(void) {
    return 0;
    int dead = 5;
}"""
        res = self.engine.analyze(code)
        rule_ids = [d["rule_id"] for d in res["diagnostics"]]
        self.assertIn("UNREACHABLE_CODE", rule_ids)


if __name__ == "__main__":
    unittest.main()
