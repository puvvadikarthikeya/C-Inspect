"""
Abstract Syntax Tree (AST) node definitions for C-Inspect.
Designed for pedagogical clarity, static analysis rule inspection,
and interactive visualization in the C-Inspect frontend.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class ASTNode:
    line: int = 0
    column: int = 0
    end_line: int = 0
    end_column: int = 0

    def to_dict(self) -> dict[str, Any]:
        result = {"node_type": self.__class__.__name__, "line": self.line, "col": self.column}
        for k, v in self.__dict__.items():
            if k in ("line", "column", "end_line", "end_column"):
                continue
            if isinstance(v, ASTNode):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [item.to_dict() if isinstance(item, ASTNode) else item for item in v]
            else:
                result[k] = v
        return result


@dataclass
class ProgramNode(ASTNode):
    declarations: List[ASTNode] = field(default_factory=list)


@dataclass
class TypeSpecifierNode(ASTNode):
    name: str = "int"
    is_pointer: bool = False
    is_const: bool = False


@dataclass
class ParameterNode(ASTNode):
    type_spec: TypeSpecifierNode = field(default_factory=TypeSpecifierNode)
    name: str = ""


@dataclass
class FunctionDeclNode(ASTNode):
    return_type: TypeSpecifierNode = field(default_factory=TypeSpecifierNode)
    name: str = ""
    params: List[ParameterNode] = field(default_factory=list)
    body: Optional['BlockNode'] = None
    is_definition: bool = True


@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)


@dataclass
class VarDeclNode(ASTNode):
    type_spec: TypeSpecifierNode = field(default_factory=TypeSpecifierNode)
    name: str = ""
    init_expr: Optional[ASTNode] = None


@dataclass
class MultiVarDeclNode(ASTNode):
    declarations: List[VarDeclNode] = field(default_factory=list)


@dataclass
class ExpressionStmtNode(ASTNode):
    expr: Optional[ASTNode] = None


@dataclass
class IfNode(ASTNode):
    condition: Optional[ASTNode] = None
    then_branch: Optional[ASTNode] = None
    else_branch: Optional[ASTNode] = None


@dataclass
class WhileNode(ASTNode):
    condition: Optional[ASTNode] = None
    body: Optional[ASTNode] = None


@dataclass
class ForNode(ASTNode):
    init: Optional[ASTNode] = None
    condition: Optional[ASTNode] = None
    update: Optional[ASTNode] = None
    body: Optional[ASTNode] = None


@dataclass
class ReturnNode(ASTNode):
    expr: Optional[ASTNode] = None


@dataclass
class BreakNode(ASTNode):
    pass


@dataclass
class ContinueNode(ASTNode):
    pass


# Expressions
@dataclass
class IdentifierNode(ASTNode):
    name: str = ""


@dataclass
class LiteralNode(ASTNode):
    value: Any = None
    literal_type: str = "int"


@dataclass
class BinaryOpNode(ASTNode):
    op: str = "+"
    left: Optional[ASTNode] = None
    right: Optional[ASTNode] = None


@dataclass
class AssignmentNode(ASTNode):
    op: str = "="
    target: Optional[ASTNode] = None
    value: Optional[ASTNode] = None


@dataclass
class UnaryOpNode(ASTNode):
    op: str = "!"
    operand: Optional[ASTNode] = None
    is_prefix: bool = True


@dataclass
class FunctionCallNode(ASTNode):
    callee: Optional[ASTNode] = None
    args: List[ASTNode] = field(default_factory=list)


@dataclass
class ArrayAccessNode(ASTNode):
    array: Optional[ASTNode] = None
    index: Optional[ASTNode] = None


@dataclass
class ErrorNode(ASTNode):
    message: str = ""
