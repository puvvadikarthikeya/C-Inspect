"""
Token definitions and data structures for C-Inspect lexical analysis.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Any


class TokenType(Enum):
    # Special
    EOF = auto()
    UNKNOWN = auto()
    
    # Identifiers & Literals
    IDENTIFIER = auto()
    NUMBER_INT = auto()
    NUMBER_FLOAT = auto()
    STRING_LITERAL = auto()
    CHAR_LITERAL = auto()
    
    # Keywords
    KEYWORD = auto()
    
    # Operators
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %
    ASSIGN = auto()         # =
    PLUS_ASSIGN = auto()    # +=
    MINUS_ASSIGN = auto()   # -=
    STAR_ASSIGN = auto()    # *=
    SLASH_ASSIGN = auto()   # /=
    
    EQ = auto()             # ==
    NEQ = auto()            # !=
    LT = auto()             # <
    GT = auto()             # >
    LTE = auto()            # <=
    GTE = auto()            # >=
    
    LOGICAL_AND = auto()    # &&
    LOGICAL_OR = auto()     # ||
    LOGICAL_NOT = auto()    # !
    
    BIT_AND = auto()        # &
    BIT_OR = auto()         # |
    BIT_XOR = auto()        # ^
    BIT_NOT = auto()        # ~
    
    INCREMENT = auto()      # ++
    DECREMENT = auto()      # --
    
    # Delimiters
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    SEMICOLON = auto()      # ;
    COMMA = auto()          # ,
    DOT = auto()            # .
    ARROW = auto()          # ->
    COLON = auto()          # :
    QUESTION = auto()       # ?


C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Bool", "_Complex", "_Imaginary"
}

TYPE_KEYWORDS = {
    "void", "char", "short", "int", "long", "float", "double", "signed",
    "unsigned", "_Bool"
}


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    start_pos: int
    end_pos: int
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.name,
            "value": self.value,
            "line": self.line,
            "column": self.column,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos
        }
