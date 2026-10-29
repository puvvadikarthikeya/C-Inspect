"""
Recursive-descent Parser for C-Inspect.
Parses a token stream into an AST for a pedagogical C subset.
Includes robust syntax error recovery to provide live diagnostics
without crashing on partially typed code.
"""
from typing import List, Optional, Tuple
from .tokens import Token, TokenType, TYPE_KEYWORDS
from .ast_nodes import (
    ProgramNode, FunctionDeclNode, ParameterNode, TypeSpecifierNode,
    BlockNode, VarDeclNode, MultiVarDeclNode, ExpressionStmtNode,
    IfNode, WhileNode, ForNode, ReturnNode, BreakNode, ContinueNode,
    IdentifierNode, LiteralNode, BinaryOpNode, AssignmentNode,
    UnaryOpNode, FunctionCallNode, ArrayAccessNode, ErrorNode, ASTNode
)


class SyntaxErrorItem:
    def __init__(self, message: str, line: int, column: int, expected: str = ""):
        self.message = message
        self.line = line
        self.column = column
        self.expected = expected

    def to_dict(self):
        return {
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "expected": self.expected
        }


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: List[SyntaxErrorItem] = []

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF token

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def _is_at_end(self) -> bool:
        return self._current().type == TokenType.EOF

    def _check(self, token_type: TokenType) -> bool:
        return self._current().type == token_type

    def _advance(self) -> Token:
        token = self._current()
        if not self._is_at_end():
            self.pos += 1
        return token

    def _match(self, *token_types: TokenType) -> Optional[Token]:
        if self._current().type in token_types:
            return self._advance()
        return None

    def _expect(self, token_type: TokenType, err_msg: str) -> Optional[Token]:
        if self._check(token_type):
            return self._advance()
        curr = self._current()
        friendly_msgs = {
            TokenType.SEMICOLON: "You are missing a semicolon ';' at the end of this statement",
            TokenType.RPAREN: "You forgot to close the parenthesis with ')'",
            TokenType.LPAREN: "You are missing an opening parenthesis '(' here",
            TokenType.RBRACE: "You forgot to close this code block with a curly bracket '}'",
            TokenType.LBRACE: "You are missing an opening curly bracket '{' to start the block",
            TokenType.IDENTIFIER: "Expected a variable or function name here"
        }
        base_msg = friendly_msgs.get(token_type, err_msg)
        found_txt = f" (found '{curr.value}' instead)" if curr.value else ""
        self.errors.append(SyntaxErrorItem(
            message=f"{base_msg}{found_txt}.",
            line=curr.line,
            column=curr.column,
            expected=token_type.name
        ))
        return None

    def _synchronize_statement(self):
        """Synchronize parser state after a syntax error in a statement."""
        self._advance()
        while not self._is_at_end():
            if self.tokens[self.pos - 1].type == TokenType.SEMICOLON:
                return
            if self._current().type in (
                TokenType.RBRACE, TokenType.KEYWORD, TokenType.EOF
            ):
                if self._current().value in ("if", "while", "for", "return", "int", "float", "char", "void"):
                    return
            self._advance()

    def parse(self) -> Tuple[ProgramNode, List[SyntaxErrorItem]]:
        self.pos = 0
        self.errors = []
        program = ProgramNode(line=1, column=1)

        while not self._is_at_end():
            try:
                decl = self._parse_top_level_declaration()
                if decl:
                    program.declarations.append(decl)
                else:
                    # Incomplete or unexpected token at top level
                    curr = self._current()
                    if not self._is_at_end():
                        self.errors.append(SyntaxErrorItem(
                            message=f"Unexpected token '{curr.value}' at global scope",
                            line=curr.line,
                            column=curr.column
                        ))
                        self._advance()
            except Exception as e:
                curr = self._current()
                self.errors.append(SyntaxErrorItem(
                    message=f"Parse error: {str(e)}",
                    line=curr.line,
                    column=curr.column
                ))
                self._synchronize_statement()

        return program, self.errors

    def _is_type_specifier(self, token: Token) -> bool:
        return token.type == TokenType.KEYWORD and token.value in TYPE_KEYWORDS

    def _parse_type_specifier(self) -> Optional[TypeSpecifierNode]:
        curr = self._current()
        if not self._is_type_specifier(curr):
            return None
        self._advance()
        is_pointer = False
        if self._check(TokenType.STAR):
            self._advance()
            is_pointer = True
        return TypeSpecifierNode(
            line=curr.line,
            column=curr.column,
            name=curr.value,
            is_pointer=is_pointer
        )

    def _parse_top_level_declaration(self) -> Optional[ASTNode]:
        start_tok = self._current()
        type_spec = self._parse_type_specifier()
        if not type_spec:
            return None

        # Next token should be identifier (function name or variable name)
        ident_tok = self._match(TokenType.IDENTIFIER)
        if not ident_tok:
            self.errors.append(SyntaxErrorItem(
                message=f"Expected identifier after type '{type_spec.name}'",
                line=self._current().line,
                column=self._current().column
            ))
            return None

        # Check if function: next is '('
        if self._check(TokenType.LPAREN):
            return self._parse_function_decl(type_spec, ident_tok)
        
        # Otherwise global variable declaration
        return self._parse_var_decl_rest(type_spec, ident_tok)

    def _parse_function_decl(self, ret_type: TypeSpecifierNode, name_tok: Token) -> Optional[FunctionDeclNode]:
        self._expect(TokenType.LPAREN, "Expected '(' after function name")
        params: List[ParameterNode] = []

        if not self._check(TokenType.RPAREN):
            # Check for 'void' as single parameter
            if self._check(TokenType.KEYWORD) and self._current().value == "void" and self._peek().type == TokenType.RPAREN:
                self._advance()  # consume 'void'
            else:
                while True:
                    param_type = self._parse_type_specifier()
                    if not param_type:
                        self.errors.append(SyntaxErrorItem(
                            message="Expected parameter type in function parameter list",
                            line=self._current().line,
                            column=self._current().column
                        ))
                        break
                    param_name_tok = self._match(TokenType.IDENTIFIER)
                    param_name = param_name_tok.value if param_name_tok else ""
                    params.append(ParameterNode(
                        line=param_type.line,
                        column=param_type.column,
                        type_spec=param_type,
                        name=param_name
                    ))
                    if not self._match(TokenType.COMMA):
                        break

        self._expect(TokenType.RPAREN, "Expected ')' after parameter list")

        # Function definition with body '{' or prototype ';'
        if self._check(TokenType.LBRACE):
            body = self._parse_block()
            return FunctionDeclNode(
                line=name_tok.line,
                column=name_tok.column,
                return_type=ret_type,
                name=name_tok.value,
                params=params,
                body=body,
                is_definition=True
            )
        elif self._check(TokenType.SEMICOLON):
            self._advance()
            return FunctionDeclNode(
                line=name_tok.line,
                column=name_tok.column,
                return_type=ret_type,
                name=name_tok.value,
                params=params,
                body=None,
                is_definition=False
            )
        else:
            self.errors.append(SyntaxErrorItem(
                message=f"Expected '{{' or ';' after function header for '{name_tok.value}'",
                line=self._current().line,
                column=self._current().column
            ))
            return None

    def _parse_var_decl_rest(self, type_spec: TypeSpecifierNode, name_tok: Token) -> Optional[ASTNode]:
        decls: List[VarDeclNode] = []
        curr_name = name_tok

        while True:
            init_expr = None
            if self._match(TokenType.ASSIGN):
                init_expr = self._parse_expression()
                if not init_expr:
                    self.errors.append(SyntaxErrorItem(
                        message=f"Expected expression after '=' in declaration of '{curr_name.value}'",
                        line=self._current().line,
                        column=self._current().column
                    ))
            
            decls.append(VarDeclNode(
                line=curr_name.line,
                column=curr_name.column,
                type_spec=type_spec,
                name=curr_name.value,
                init_expr=init_expr
            ))

            if self._match(TokenType.COMMA):
                next_ident = self._match(TokenType.IDENTIFIER)
                if not next_ident:
                    self.errors.append(SyntaxErrorItem(
                        message="Expected variable identifier after comma",
                        line=self._current().line,
                        column=self._current().column
                    ))
                    break
                curr_name = next_ident
            else:
                break

        self._expect(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        if len(decls) == 1:
            return decls[0]
        return MultiVarDeclNode(line=type_spec.line, column=type_spec.column, declarations=decls)

    def _parse_block(self) -> BlockNode:
        lbrace = self._expect(TokenType.LBRACE, "Expected '{' to start block")
        start_line = lbrace.line if lbrace else self._current().line
        start_col = lbrace.column if lbrace else self._current().column
        block = BlockNode(line=start_line, column=start_col)

        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmt = self._parse_statement()
            if stmt:
                block.statements.append(stmt)

        self._expect(TokenType.RBRACE, "Expected '}' to close block")
        return block

    def _parse_statement(self) -> Optional[ASTNode]:
        curr = self._current()

        # Block
        if self._check(TokenType.LBRACE):
            return self._parse_block()

        # Variable declaration inside block
        if self._is_type_specifier(curr):
            type_spec = self._parse_type_specifier()
            name_tok = self._expect(TokenType.IDENTIFIER, "Expected identifier in variable declaration")
            if not name_tok:
                self._synchronize_statement()
                return None
            return self._parse_var_decl_rest(type_spec, name_tok)

        # Keyword statements
        if curr.type == TokenType.KEYWORD:
            val = curr.value
            if val == "if":
                return self._parse_if_stmt()
            elif val == "while":
                return self._parse_while_stmt()
            elif val == "for":
                return self._parse_for_stmt()
            elif val == "return":
                return self._parse_return_stmt()
            elif val == "break":
                tok = self._advance()
                self._expect(TokenType.SEMICOLON, "Expected ';' after break")
                return BreakNode(line=tok.line, column=tok.column)
            elif val == "continue":
                tok = self._advance()
                self._expect(TokenType.SEMICOLON, "Expected ';' after continue")
                return ContinueNode(line=tok.line, column=tok.column)

        # Expression statement (including assignment, call, etc.)
        expr = self._parse_expression()
        if expr:
            self._expect(TokenType.SEMICOLON, "Expected ';' after expression")
            return ExpressionStmtNode(line=expr.line, column=expr.column, expr=expr)
        
        # Empty statement
        if self._match(TokenType.SEMICOLON):
            return None

        # Unexpected token
        tok = self._advance()
        self.errors.append(SyntaxErrorItem(
            message=f"Unexpected statement token '{tok.value}'",
            line=tok.line,
            column=tok.column
        ))
        return None

    def _parse_if_stmt(self) -> IfNode:
        if_tok = self._advance()  # consume 'if'
        self._expect(TokenType.LPAREN, "Expected '(' after 'if'")
        condition = self._parse_expression()
        self._expect(TokenType.RPAREN, "Expected ')' after if-condition")

        then_branch = self._parse_statement()
        else_branch = None

        if self._check(TokenType.KEYWORD) and self._current().value == "else":
            self._advance()  # consume 'else'
            else_branch = self._parse_statement()

        return IfNode(
            line=if_tok.line,
            column=if_tok.column,
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch
        )

    def _parse_while_stmt(self) -> WhileNode:
        while_tok = self._advance()
        self._expect(TokenType.LPAREN, "Expected '(' after 'while'")
        condition = self._parse_expression()
        self._expect(TokenType.RPAREN, "Expected ')' after while-condition")
        body = self._parse_statement()
        return WhileNode(line=while_tok.line, column=while_tok.column, condition=condition, body=body)

    def _parse_for_stmt(self) -> ForNode:
        for_tok = self._advance()
        self._expect(TokenType.LPAREN, "Expected '(' after 'for'")
        
        init = None
        if not self._check(TokenType.SEMICOLON):
            if self._is_type_specifier(self._current()):
                type_spec = self._parse_type_specifier()
                name_tok = self._expect(TokenType.IDENTIFIER, "Expected identifier in for-loop initializer")
                if name_tok:
                    init = self._parse_var_decl_rest(type_spec, name_tok)
            else:
                expr = self._parse_expression()
                self._expect(TokenType.SEMICOLON, "Expected ';' after for-loop initialization")
                init = ExpressionStmtNode(line=expr.line, column=expr.column, expr=expr) if expr else None
        else:
            self._advance()

        cond = None
        if not self._check(TokenType.SEMICOLON):
            cond = self._parse_expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after for-loop condition")

        update = None
        if not self._check(TokenType.RPAREN):
            update = self._parse_expression()
        self._expect(TokenType.RPAREN, "Expected ')' after for-loop update clause")

        body = self._parse_statement()
        return ForNode(line=for_tok.line, column=for_tok.column, init=init, condition=cond, update=update, body=body)

    def _parse_return_stmt(self) -> ReturnNode:
        ret_tok = self._advance()
        expr = None
        if not self._check(TokenType.SEMICOLON):
            expr = self._parse_expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after return statement")
        return ReturnNode(line=ret_tok.line, column=ret_tok.column, expr=expr)

    # Expression parsing with precedence
    def _parse_expression(self) -> Optional[ASTNode]:
        return self._parse_assignment()

    def _parse_assignment(self) -> Optional[ASTNode]:
        node = self._parse_logical_or()
        if not node:
            return None

        assign_ops = (
            TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
            TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN
        )
        if self._current().type in assign_ops:
            op_tok = self._advance()
            val = self._parse_assignment()
            return AssignmentNode(
                line=node.line,
                column=node.column,
                op=op_tok.value,
                target=node,
                value=val
            )
        return node

    def _parse_logical_or(self) -> Optional[ASTNode]:
        node = self._parse_logical_and()
        while self._match(TokenType.LOGICAL_OR):
            op = "||"
            right = self._parse_logical_and()
            node = BinaryOpNode(line=node.line, column=node.column, op=op, left=node, right=right)
        return node

    def _parse_logical_and(self) -> Optional[ASTNode]:
        node = self._parse_equality()
        while self._match(TokenType.LOGICAL_AND):
            op = "&&"
            right = self._parse_equality()
            node = BinaryOpNode(line=node.line, column=node.column, op=op, left=node, right=right)
        return node

    def _parse_equality(self) -> Optional[ASTNode]:
        node = self._parse_relational()
        while self._current().type in (TokenType.EQ, TokenType.NEQ):
            op_tok = self._advance()
            right = self._parse_relational()
            node = BinaryOpNode(line=node.line, column=node.column, op=op_tok.value, left=node, right=right)
        return node

    def _parse_relational(self) -> Optional[ASTNode]:
        node = self._parse_additive()
        while self._current().type in (TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op_tok = self._advance()
            right = self._parse_additive()
            node = BinaryOpNode(line=node.line, column=node.column, op=op_tok.value, left=node, right=right)
        return node

    def _parse_additive(self) -> Optional[ASTNode]:
        node = self._parse_multiplicative()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right = self._parse_multiplicative()
            node = BinaryOpNode(line=node.line, column=node.column, op=op_tok.value, left=node, right=right)
        return node

    def _parse_multiplicative(self) -> Optional[ASTNode]:
        node = self._parse_unary()
        while self._current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._advance()
            right = self._parse_unary()
            node = BinaryOpNode(line=node.line, column=node.column, op=op_tok.value, left=node, right=right)
        return node

    def _parse_unary(self) -> Optional[ASTNode]:
        curr = self._current()
        if curr.type in (TokenType.LOGICAL_NOT, TokenType.BIT_NOT, TokenType.MINUS, TokenType.PLUS, TokenType.INCREMENT, TokenType.DECREMENT, TokenType.STAR, TokenType.BIT_AND):
            op_tok = self._advance()
            operand = self._parse_unary()
            return UnaryOpNode(line=op_tok.line, column=op_tok.column, op=op_tok.value, operand=operand, is_prefix=True)
        return self._parse_postfix()

    def _parse_postfix(self) -> Optional[ASTNode]:
        node = self._parse_primary()
        if not node:
            return None

        while True:
            if self._check(TokenType.LPAREN):
                # Function call
                self._advance()
                args: List[ASTNode] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        arg = self._parse_expression()
                        if arg:
                            args.append(arg)
                        if not self._match(TokenType.COMMA):
                            break
                self._expect(TokenType.RPAREN, "Expected ')' after function arguments")
                node = FunctionCallNode(line=node.line, column=node.column, callee=node, args=args)
            elif self._check(TokenType.LBRACKET):
                # Array index
                self._advance()
                idx = self._parse_expression()
                self._expect(TokenType.RBRACKET, "Expected ']' after array index")
                node = ArrayAccessNode(line=node.line, column=node.column, array=node, index=idx)
            elif self._current().type in (TokenType.INCREMENT, TokenType.DECREMENT):
                op_tok = self._advance()
                node = UnaryOpNode(line=node.line, column=node.column, op=op_tok.value, operand=node, is_prefix=False)
            else:
                break

        return node

    def _parse_primary(self) -> Optional[ASTNode]:
        curr = self._current()

        if curr.type == TokenType.NUMBER_INT:
            self._advance()
            return LiteralNode(line=curr.line, column=curr.column, value=int(curr.value), literal_type="int")

        if curr.type == TokenType.NUMBER_FLOAT:
            self._advance()
            return LiteralNode(line=curr.line, column=curr.column, value=float(curr.value), literal_type="float")

        if curr.type == TokenType.STRING_LITERAL:
            self._advance()
            return LiteralNode(line=curr.line, column=curr.column, value=curr.value, literal_type="string")

        if curr.type == TokenType.CHAR_LITERAL:
            self._advance()
            return LiteralNode(line=curr.line, column=curr.column, value=curr.value, literal_type="char")

        if curr.type == TokenType.IDENTIFIER:
            self._advance()
            return IdentifierNode(line=curr.line, column=curr.column, name=curr.value)

        if curr.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        return None
