"""
Scoped Symbol Table for C-Inspect.
Models lexical scopes (Global, Function, and Block), tracking declarations,
types, and usage counts. Demonstrates core Compiler Design concepts and provides
data for Semantic Analysis and the UI visualizer.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class Symbol:
    name: str
    kind: str           # 'variable', 'function', 'parameter'
    type_name: str
    line: int
    column: int
    scope_level: int
    use_count: int = 0
    is_defined: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "type_name": self.type_name,
            "line": self.line,
            "column": self.column,
            "scope_level": self.scope_level,
            "use_count": self.use_count,
            "is_defined": self.is_defined
        }


class Scope:
    def __init__(self, name: str, parent: Optional['Scope'] = None, scope_id: int = 0):
        self.scope_id = scope_id
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List['Scope'] = []
        self.level = parent.level + 1 if parent else 0

    def define(self, symbol: Symbol) -> bool:
        """
        Defines a symbol in the current scope.
        Returns False if already declared in this exact scope (duplicate declaration).
        """
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str, current_only: bool = False) -> Optional[Symbol]:
        """
        Looks up a symbol. If current_only is False, searches up through parent scopes.
        """
        if name in self.symbols:
            return self.symbols[name]
        if not current_only and self.parent:
            return self.parent.lookup(name, current_only=False)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope_id": self.scope_id,
            "name": self.name,
            "level": self.level,
            "symbols": [sym.to_dict() for sym in self.symbols.values()],
            "children": [child.to_dict() for child in self.children]
        }


# Standard library builtins to avoid false undeclared identifier errors
STANDARD_BUILTINS = [
    ("printf", "function", "int"),
    ("scanf", "function", "int"),
    ("puts", "function", "int"),
    ("putchar", "function", "int"),
    ("getchar", "function", "int"),
    ("malloc", "function", "void*"),
    ("calloc", "function", "void*"),
    ("free", "function", "void"),
    ("exit", "function", "void"),
    ("strlen", "function", "int"),
    ("strcpy", "function", "char*"),
    ("strcmp", "function", "int"),
    ("abs", "function", "int"),
    ("sqrt", "function", "double"),
]


class SymbolTable:
    def __init__(self):
        self._next_scope_id = 0
        self.global_scope = Scope(name="Global Scope", parent=None, scope_id=self._get_scope_id())
        self.current_scope = self.global_scope
        self.all_scopes: List[Scope] = [self.global_scope]
        self._populate_builtins()

    def _get_scope_id(self) -> int:
        sid = self._next_scope_id
        self._next_scope_id += 1
        return sid

    def _populate_builtins(self):
        for name, kind, ret_type in STANDARD_BUILTINS:
            sym = Symbol(
                name=name,
                kind=kind,
                type_name=ret_type,
                line=0,
                column=0,
                scope_level=0,
                use_count=1,
                is_defined=True
            )
            self.global_scope.define(sym)

    def enter_scope(self, name: str) -> Scope:
        new_scope = Scope(
            name=name,
            parent=self.current_scope,
            scope_id=self._get_scope_id()
        )
        self.current_scope.children.append(new_scope)
        self.all_scopes.append(new_scope)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self) -> Optional[Scope]:
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
        return self.current_scope

    def define(self, symbol: Symbol) -> bool:
        symbol.scope_level = self.current_scope.level
        return self.current_scope.define(symbol)

    def lookup(self, name: str, current_only: bool = False) -> Optional[Symbol]:
        return self.current_scope.lookup(name, current_only)

    def record_usage(self, name: str) -> Optional[Symbol]:
        sym = self.lookup(name, current_only=False)
        if sym:
            sym.use_count += 1
        return sym

    def get_unused_locals(self) -> List[Symbol]:
        unused = []
        for scope in self.all_scopes:
            # We only flag variables in non-global scopes (locals and parameters)
            if scope.level > 0:
                for sym in scope.symbols.values():
                    if sym.kind == "variable" and sym.use_count == 0:
                        unused.append(sym)
        return unused

    def to_dict(self) -> Dict[str, Any]:
        return self.global_scope.to_dict()
