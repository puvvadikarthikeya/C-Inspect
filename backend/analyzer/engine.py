"""
C-Inspect Static Analysis Engine.
Orchestrates Lexer -> Parser -> Symbol Table -> Semantic/Pattern Checkers.
Demonstrates classical Compiler Design phases with structured output.
"""
from typing import List, Dict, Any, Optional
from .tokens import Token
from .lexer import Lexer
from .parser import Parser
from .ast_nodes import (
    ProgramNode, FunctionDeclNode, BlockNode, VarDeclNode, MultiVarDeclNode,
    IfNode, WhileNode, ForNode, ReturnNode, BreakNode, ContinueNode,
    IdentifierNode, AssignmentNode, BinaryOpNode, UnaryOpNode,
    FunctionCallNode, ArrayAccessNode, ExpressionStmtNode, ASTNode
)
from .symbol_table import SymbolTable, Symbol
from .rules.base import Diagnostic, RULE_CATALOG


class StaticAnalysisEngine:
    def __init__(self):
        self.diagnostics: List[Diagnostic] = []
        self.symbol_table = SymbolTable()

    def analyze(self, source_code: str) -> Dict[str, Any]:
        self.diagnostics = []
        self.symbol_table = SymbolTable()

        # Phase 1: Lexical Analysis
        lexer = Lexer(source_code)
        tokens, lexer_errors = lexer.tokenize()

        for err in lexer_errors:
            self._add_diagnostic(
                rule_id="SYNTAX_ERROR",
                message=err.message,
                severity="error",
                line=err.line,
                col=err.column
            )

        # Phase 2: Syntax Analysis (Parsing)
        parser = Parser(tokens)
        ast, syntax_errors = parser.parse()

        for err in syntax_errors:
            self._add_diagnostic(
                rule_id="SYNTAX_ERROR",
                message=err.message,
                severity="error",
                line=err.line,
                col=err.column
            )

        # Phase 3 & 4: Symbol Table Construction & Semantic Analysis Checks
        self._analyze_program(ast)

        # Phase 5: Post-traversal Checks (Unused variables)
        self._check_unused_locals()

        # Sort diagnostics cleanly by line and column
        self.diagnostics.sort(key=lambda d: (d.line, d.column))

        # Prepare payload
        diag_list = [d.to_dict() for d in self.diagnostics]
        error_count = sum(1 for d in self.diagnostics if d.severity == "error")
        warning_count = sum(1 for d in self.diagnostics if d.severity == "warning")
        info_count = sum(1 for d in self.diagnostics if d.severity == "info")

        return {
            "diagnostics": diag_list,
            "summary": {
                "total": len(self.diagnostics),
                "errors": error_count,
                "warnings": warning_count,
                "infos": info_count,
                "clean": len(self.diagnostics) == 0
            },
            "tokens": [t.to_dict() for t in tokens if t.type.name != "EOF"][:150],  # preview tokens
            "ast": ast.to_dict(),
            "symbol_table": self.symbol_table.to_dict()
        }

    def _add_diagnostic(self, rule_id: str, message: str, severity: str, line: int, col: int,
                        end_line: int = 0, end_col: int = 0, custom_suggestion: str = ""):
        catalog_info = RULE_CATALOG.get(rule_id, {})
        diag = Diagnostic(
            rule_id=rule_id,
            message=message,
            severity=severity or catalog_info.get("severity", "warning"),
            line=max(1, line),
            column=max(1, col),
            end_line=end_line or line,
            end_column=end_col or (col + 5),
            category=catalog_info.get("category", "Semantic"),
            explanation=catalog_info.get("explanation", ""),
            suggestion=custom_suggestion or catalog_info.get("suggestion", ""),
            compiler_concept=catalog_info.get("compiler_concept", "")
        )
        self.diagnostics.append(diag)

    def _analyze_program(self, program: ProgramNode):
        for decl in program.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._analyze_function(decl)
            elif isinstance(decl, VarDeclNode):
                self._analyze_var_decl(decl)
            elif isinstance(decl, MultiVarDeclNode):
                for v in decl.declarations:
                    self._analyze_var_decl(v)

    def _analyze_function(self, func: FunctionDeclNode):
        # Register function in current (global) scope
        fn_sym = Symbol(
            name=func.name,
            kind="function",
            type_name=func.return_type.name,
            line=func.line,
            column=func.column,
            scope_level=0,
            use_count=1  # don't flag function itself as unused
        )
        if not self.symbol_table.define(fn_sym):
            self._add_diagnostic(
                rule_id="DUPLICATE_DECLARATION",
                message=f"You already defined a function named '{func.name}' earlier in this file.",
                severity="error",
                line=func.line,
                col=func.column
            )

        if not func.body:
            return  # function prototype

        # Enter function scope
        self.symbol_table.enter_scope(f"Function: {func.name}")

        # Add parameters to function scope
        for param in func.params:
            if param.name:
                p_sym = Symbol(
                    name=param.name,
                    kind="parameter",
                    type_name=param.type_spec.name,
                    line=param.line,
                    column=param.column,
                    scope_level=self.symbol_table.current_scope.level
                )
                if not self.symbol_table.define(p_sym):
                    self._add_diagnostic(
                        rule_id="DUPLICATE_DECLARATION",
                        message=f"You used the parameter name '{param.name}' twice in function '{func.name}'.",
                        severity="error",
                        line=param.line,
                        col=param.column
                    )

        # Analyze body
        self._analyze_block(func.body, is_function_body=True)

        # Check return statement for non-void function
        if func.return_type.name != "void" and func.name != "main":
            has_return = self._has_return_path(func.body)
            if not has_return:
                self._add_diagnostic(
                    rule_id="MISSING_RETURN",
                    message=f"Function '{func.name}' is supposed to return a value, but some paths don't return anything.",
                    severity="warning",
                    line=func.line,
                    col=func.column,
                    custom_suggestion=f"Add a 'return 0;' (or a {func.return_type.name} value) before the end of '{func.name}'."
                )

        self.symbol_table.exit_scope()

    def _analyze_block(self, block: BlockNode, is_function_body: bool = False):
        if not is_function_body:
            self.symbol_table.enter_scope(f"Block: L{block.line}")

        encountered_terminator = False

        for stmt in block.statements:
            if encountered_terminator:
                self._add_diagnostic(
                    rule_id="UNREACHABLE_CODE",
                    message="The computer can never reach this line because it comes after a return or break statement.",
                    severity="info",
                    line=stmt.line,
                    col=stmt.column
                )

            self._analyze_statement(stmt)

            if isinstance(stmt, (ReturnNode, BreakNode, ContinueNode)):
                encountered_terminator = True

        if not is_function_body:
            self.symbol_table.exit_scope()

    def _analyze_statement(self, stmt: ASTNode):
        if isinstance(stmt, BlockNode):
            self._analyze_block(stmt)
        elif isinstance(stmt, VarDeclNode):
            self._analyze_var_decl(stmt)
        elif isinstance(stmt, MultiVarDeclNode):
            for v in stmt.declarations:
                self._analyze_var_decl(v)
        elif isinstance(stmt, ExpressionStmtNode):
            if stmt.expr:
                self._analyze_expression(stmt.expr)
        elif isinstance(stmt, IfNode):
            self._analyze_if(stmt)
        elif isinstance(stmt, WhileNode):
            self._analyze_while(stmt)
        elif isinstance(stmt, ForNode):
            self._analyze_for(stmt)
        elif isinstance(stmt, ReturnNode):
            if stmt.expr:
                self._analyze_expression(stmt.expr)

    def _analyze_var_decl(self, decl: VarDeclNode):
        # If there's an initializer, analyze it first (uses prior declarations)
        if decl.init_expr:
            self._analyze_expression(decl.init_expr)

        sym = Symbol(
            name=decl.name,
            kind="variable",
            type_name=decl.type_spec.name,
            line=decl.line,
            column=decl.column,
            scope_level=self.symbol_table.current_scope.level
        )
        if not self.symbol_table.define(sym):
            self._add_diagnostic(
                rule_id="DUPLICATE_DECLARATION",
                message=f"You already declared a variable named '{decl.name}' in this same block.",
                severity="error",
                line=decl.line,
                col=decl.column
            )

    def _analyze_if(self, node: IfNode):
        if node.condition:
            self._check_condition_for_assignment(node.condition)
            self._analyze_expression(node.condition)

        if node.then_branch:
            self._analyze_statement(node.then_branch)

        if node.else_branch:
            self._analyze_statement(node.else_branch)

    def _analyze_while(self, node: WhileNode):
        if node.condition:
            self._check_condition_for_assignment(node.condition)
            self._analyze_expression(node.condition)

        if node.body:
            self._analyze_statement(node.body)

    def _analyze_for(self, node: ForNode):
        self.symbol_table.enter_scope(f"ForLoop: L{node.line}")
        if node.init:
            self._analyze_statement(node.init)
        if node.condition:
            self._check_condition_for_assignment(node.condition)
            self._analyze_expression(node.condition)
        if node.update:
            self._analyze_expression(node.update)
        if node.body:
            self._analyze_statement(node.body)
        self.symbol_table.exit_scope()

    def _check_condition_for_assignment(self, expr: ASTNode):
        """Rule: Flag assignment '=' inside conditional expressions."""
        if isinstance(expr, AssignmentNode):
            if expr.op == "=":
                target_name = expr.target.name if isinstance(expr.target, IdentifierNode) else "this variable"
                self._add_diagnostic(
                    rule_id="ASSIGNMENT_IN_CONDITION",
                    message=f"You wrote a single '=' instead of '==' inside the condition for '{target_name}'.",
                    severity="warning",
                    line=expr.line,
                    col=expr.column,
                    custom_suggestion=f"Change '=' to '==' to compare values (for example: write '{target_name} == ...')."
                )
        elif isinstance(expr, BinaryOpNode):
            if expr.left:
                self._check_condition_for_assignment(expr.left)
            if expr.right:
                self._check_condition_for_assignment(expr.right)

    def _analyze_expression(self, expr: ASTNode):
        if not expr:
            return

        if isinstance(expr, IdentifierNode):
            sym = self.symbol_table.lookup(expr.name)
            if not sym:
                self._add_diagnostic(
                    rule_id="UNDECLARED_IDENTIFIER",
                    message=f"'{expr.name}' is being used, but it was never created or declared.",
                    severity="error",
                    line=expr.line,
                    col=expr.column,
                    custom_suggestion=f"Declare '{expr.name}' before using it (for example: 'int {expr.name};') or check your spelling."
                )
            else:
                self.symbol_table.record_usage(expr.name)

        elif isinstance(expr, AssignmentNode):
            if expr.target:
                self._analyze_expression(expr.target)
            if expr.value:
                self._analyze_expression(expr.value)

        elif isinstance(expr, BinaryOpNode):
            if expr.left:
                self._analyze_expression(expr.left)
            if expr.right:
                self._analyze_expression(expr.right)

        elif isinstance(expr, UnaryOpNode):
            if expr.operand:
                self._analyze_expression(expr.operand)

        elif isinstance(expr, FunctionCallNode):
            if expr.callee:
                self._analyze_expression(expr.callee)
            for arg in expr.args:
                self._analyze_expression(arg)

        elif isinstance(expr, ArrayAccessNode):
            if expr.array:
                self._analyze_expression(expr.array)
            if expr.index:
                self._analyze_expression(expr.index)

    def _check_unused_locals(self):
        unused_symbols = self.symbol_table.get_unused_locals()
        for sym in unused_symbols:
            self._add_diagnostic(
                rule_id="UNUSED_LOCAL_VARIABLE",
                message=f"You created variable '{sym.name}', but you never used it anywhere.",
                severity="warning",
                line=sym.line,
                col=sym.column,
                custom_suggestion=f"Use '{sym.name}' in your calculations, or delete this line if you don't need it."
            )

    def _has_return_path(self, block: Optional[BlockNode]) -> bool:
        if not block or not block.statements:
            return False
        for stmt in block.statements:
            if isinstance(stmt, ReturnNode):
                return True
            if isinstance(stmt, IfNode):
                if stmt.then_branch and stmt.else_branch:
                    then_ret = False
                    else_ret = False
                    if isinstance(stmt.then_branch, BlockNode):
                        then_ret = self._has_return_path(stmt.then_branch)
                    elif isinstance(stmt.then_branch, ReturnNode):
                        then_ret = True
                    if isinstance(stmt.else_branch, BlockNode):
                        else_ret = self._has_return_path(stmt.else_branch)
                    elif isinstance(stmt.else_branch, ReturnNode):
                        else_ret = True
                    if then_ret and else_ret:
                        return True
        return False
