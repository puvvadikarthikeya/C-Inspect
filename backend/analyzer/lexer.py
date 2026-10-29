"""
Lexer (Lexical Analyzer) for C-Inspect.
Tokenizes a subset of C source code into a stream of Token objects
with exact line, column, and character offset tracking.
"""
from typing import List, Tuple
from .tokens import Token, TokenType, C_KEYWORDS


class LexerError:
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column

    def to_dict(self):
        return {
            "message": self.message,
            "line": self.line,
            "column": self.column
        }


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []
        self.errors: List[LexerError] = []

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx < self.length:
            return self.source[idx]
        return '\0'

    def _advance(self) -> str:
        if self.pos >= self.length:
            return '\0'
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self) -> Tuple[List[Token], List[LexerError]]:
        self.tokens = []
        self.errors = []
        self.pos = 0
        self.line = 1
        self.col = 1

        while self.pos < self.length:
            ch = self._peek()

            # Skip whitespace
            if ch in ' \t\r\n':
                self._advance()
                continue

            # Preprocessor directives (e.g. #include <stdio.h>)
            if ch == '#':
                start_line = self.line
                start_col = self.col
                start_pos = self.pos
                val = ""
                while self._peek() != '\0' and self._peek() != '\n':
                    val += self._advance()
                # We skip preprocessor directives from AST for single-file analysis
                # but could emit token if needed. For now, continue cleanly.
                continue

            # Comments
            if ch == '/' and self._peek(1) == '/':
                self._advance()
                self._advance()
                while self._peek() != '\0' and self._peek() != '\n':
                    self._advance()
                continue

            if ch == '/' and self._peek(1) == '*':
                start_line = self.line
                start_col = self.col
                self._advance()
                self._advance()
                closed = False
                while self._peek() != '\0':
                    if self._peek() == '*' and self._peek(1) == '/':
                        self._advance()
                        self._advance()
                        closed = True
                        break
                    self._advance()
                if not closed:
                    self.errors.append(LexerError("Unterminated multi-line comment /*", start_line, start_col))
                continue

            # String literals
            if ch == '"':
                self._lex_string()
                continue

            # Character literals
            if ch == "'":
                self._lex_char()
                continue

            # Numbers
            if ch.isdigit():
                self._lex_number()
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == '_':
                self._lex_identifier()
                continue

            # Operators and Delimiters
            self._lex_operator_or_delimiter()

        # Emit EOF
        self.tokens.append(Token(
            type=TokenType.EOF,
            value="",
            line=self.line,
            column=self.col,
            start_pos=self.pos,
            end_pos=self.pos
        ))
        return self.tokens, self.errors

    def _lex_string(self):
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        self._advance()  # consume opening "
        val = ""
        closed = False
        while self._peek() != '\0':
            c = self._peek()
            if c == '\n':
                break
            if c == '\\':
                self._advance()
                escaped = self._advance()
                val += '\\' + escaped
                continue
            if c == '"':
                self._advance()
                closed = True
                break
            val += self._advance()

        if not closed:
            self.errors.append(LexerError("Unterminated string literal", start_line, start_col))
        self.tokens.append(Token(
            type=TokenType.STRING_LITERAL,
            value=val,
            line=start_line,
            column=start_col,
            start_pos=start_pos,
            end_pos=self.pos
        ))

    def _lex_char(self):
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        self._advance()  # consume opening '
        val = ""
        closed = False
        while self._peek() != '\0':
            c = self._peek()
            if c == '\n':
                break
            if c == '\\':
                self._advance()
                escaped = self._advance()
                val += '\\' + escaped
                continue
            if c == "'":
                self._advance()
                closed = True
                break
            val += self._advance()

        if not closed:
            self.errors.append(LexerError("Unterminated character constant", start_line, start_col))
        self.tokens.append(Token(
            type=TokenType.CHAR_LITERAL,
            value=val,
            line=start_line,
            column=start_col,
            start_pos=start_pos,
            end_pos=self.pos
        ))

    def _lex_number(self):
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        val = ""
        is_float = False

        while self._peek().isdigit():
            val += self._advance()

        if self._peek() == '.' and self._peek(1).isdigit():
            is_float = True
            val += self._advance()  # '.'
            while self._peek().isdigit():
                val += self._advance()

        # Scientific notation (e.g. 1e10)
        if self._peek() in ('e', 'E'):
            is_float = True
            val += self._advance()
            if self._peek() in ('+', '-'):
                val += self._advance()
            while self._peek().isdigit():
                val += self._advance()

        # Suffixes like L, U, f
        while self._peek() in ('f', 'F', 'l', 'L', 'u', 'U'):
            val += self._advance()

        self.tokens.append(Token(
            type=TokenType.NUMBER_FLOAT if is_float else TokenType.NUMBER_INT,
            value=val,
            line=start_line,
            column=start_col,
            start_pos=start_pos,
            end_pos=self.pos
        ))

    def _lex_identifier(self):
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        val = ""
        while self._peek().isalnum() or self._peek() == '_':
            val += self._advance()

        token_type = TokenType.KEYWORD if val in C_KEYWORDS else TokenType.IDENTIFIER
        self.tokens.append(Token(
            type=token_type,
            value=val,
            line=start_line,
            column=start_col,
            start_pos=start_pos,
            end_pos=self.pos
        ))

    def _lex_operator_or_delimiter(self):
        start_line = self.line
        start_col = self.col
        start_pos = self.pos
        ch = self._advance()
        next_ch = self._peek()

        two_char = ch + next_ch
        two_char_map = {
            "==": TokenType.EQ,
            "!=": TokenType.NEQ,
            "<=": TokenType.LTE,
            ">=": TokenType.GTE,
            "&&": TokenType.LOGICAL_AND,
            "||": TokenType.LOGICAL_OR,
            "++": TokenType.INCREMENT,
            "--": TokenType.DECREMENT,
            "+=": TokenType.PLUS_ASSIGN,
            "-=": TokenType.MINUS_ASSIGN,
            "*=": TokenType.STAR_ASSIGN,
            "/=": TokenType.SLASH_ASSIGN,
            "->": TokenType.ARROW,
        }

        if two_char in two_char_map:
            self._advance()
            self.tokens.append(Token(
                type=two_char_map[two_char],
                value=two_char,
                line=start_line,
                column=start_col,
                start_pos=start_pos,
                end_pos=self.pos
            ))
            return

        single_char_map = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '=': TokenType.ASSIGN,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '!': TokenType.LOGICAL_NOT,
            '&': TokenType.BIT_AND,
            '|': TokenType.BIT_OR,
            '^': TokenType.BIT_XOR,
            '~': TokenType.BIT_NOT,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            ';': TokenType.SEMICOLON,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            ':': TokenType.COLON,
            '?': TokenType.QUESTION
        }

        if ch in single_char_map:
            self.tokens.append(Token(
                type=single_char_map[ch],
                value=ch,
                line=start_line,
                column=start_col,
                start_pos=start_pos,
                end_pos=self.pos
            ))
        else:
            self.errors.append(LexerError(f"Unexpected character '{ch}'", start_line, start_col))
            self.tokens.append(Token(
                type=TokenType.UNKNOWN,
                value=ch,
                line=start_line,
                column=start_col,
                start_pos=start_pos,
                end_pos=self.pos
            ))
