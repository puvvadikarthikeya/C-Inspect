"""
Base definitions and catalog for C-Inspect static analysis rules and diagnostics.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class Diagnostic:
    rule_id: str
    message: str
    severity: str          # 'error', 'warning', 'info'
    line: int
    column: int
    end_line: int = 0
    end_column: int = 0
    category: str = "Semantic"  # 'Syntax', 'Semantic', 'Suspicious Pattern', 'Control Flow'
    explanation: str = ""
    suggestion: str = ""
    compiler_concept: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line or self.line,
            "end_column": self.end_column or (self.column + 5),
            "category": self.category,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "compiler_concept": self.compiler_concept,
        }


RULE_CATALOG = {
    "SYNTAX_ERROR": {
        "rule_id": "SYNTAX_ERROR",
        "name": "Syntax Error",
        "severity": "error",
        "category": "Syntax",
        "compiler_concept": "Parsing (Syntax Analysis)",
        "explanation": "Something is missing or typed incorrectly in your C code. This usually happens if you forgot a semicolon ';', left a bracket open, or missed a value.",
        "suggestion": "Check the code right before this spot for a missing semicolon ';' or unmatched brackets."
    },
    "UNDECLARED_IDENTIFIER": {
        "rule_id": "UNDECLARED_IDENTIFIER",
        "name": "Undeclared Identifier",
        "severity": "error",
        "category": "Semantic",
        "compiler_concept": "Symbol Table Lookup & Scope Resolution",
        "explanation": "You are trying to use a variable or function that was never declared. In C, you must tell the computer the type of every variable (like 'int', 'float', or 'char') before using it.",
        "suggestion": "Declare the variable before using it (for example: 'int x;') or check if the name is spelled correctly."
    },
    "DUPLICATE_DECLARATION": {
        "rule_id": "DUPLICATE_DECLARATION",
        "name": "Duplicate Declaration",
        "severity": "error",
        "category": "Semantic",
        "compiler_concept": "Symbol Table Collision Check",
        "explanation": "You declared two variables with the exact same name in the same block of code. The computer won't know which one you want to use.",
        "suggestion": "Give this variable a different name or remove the second declaration."
    },
    "ASSIGNMENT_IN_CONDITION": {
        "rule_id": "ASSIGNMENT_IN_CONDITION",
        "name": "Assignment in Condition",
        "severity": "warning",
        "category": "Suspicious Pattern",
        "compiler_concept": "AST Pattern Inspection (Semantic Pass)",
        "explanation": "You wrote a single '=' inside an 'if' or 'while' condition. In C, a single '=' assigns a value, while '==' compares two values. Writing 'if (x = 5)' actually changes x to 5 instead of testing if it is 5.",
        "suggestion": "Change '=' to '==' to compare values (for example: write 'if (marks == 50)' instead of 'if (marks = 50)')."
    },
    "UNUSED_LOCAL_VARIABLE": {
        "rule_id": "UNUSED_LOCAL_VARIABLE",
        "name": "Unused Local Variable",
        "severity": "warning",
        "category": "Semantic",
        "compiler_concept": "Symbol Table Usage Tracking",
        "explanation": "You created a variable, but you never used it anywhere in your code. It is taking up memory without being read or calculated.",
        "suggestion": "Use the variable in your calculations, or delete this line if you don't need it."
    },
    "MISSING_RETURN": {
        "rule_id": "MISSING_RETURN",
        "name": "Missing Return Statement",
        "severity": "warning",
        "category": "Control Flow",
        "compiler_concept": "Control Flow Graph / Return Path Analysis",
        "explanation": "This function is set up to return a value, but some paths finish without returning anything. Non-void functions must always send back a value.",
        "suggestion": "Add a return statement before the closing brace (for example: 'return 0;')."
    },
    "UNREACHABLE_CODE": {
        "rule_id": "UNREACHABLE_CODE",
        "name": "Unreachable Code",
        "severity": "info",
        "category": "Control Flow",
        "compiler_concept": "Control Flow Analysis (Dead Code Detection)",
        "explanation": "The computer can never run this line because it comes directly after a 'return', 'break', or 'continue' statement. The program exits before reaching here.",
        "suggestion": "Move this line above the return statement, or remove it."
    }
}
