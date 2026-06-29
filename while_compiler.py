# ============================================================
# Simulasi Kompilasi Konstruksi While Loop
# Tahapan: Leksikal → Sintaksis (AST) → Semantik → TAC
# ============================================================

import re
from dataclasses import dataclass, field
from typing import List, Optional, Any

# ─────────────────────────────────────────────
# 1. ANALISIS LEKSIKAL (Lexer)
# ─────────────────────────────────────────────

TOKEN_SPEC = [
    ("NUMBER",    r"\d+(\.\d*)?"),
    ("BOOL",      r"\b(true|false)\b"),
    ("WHILE",     r"\bwhile\b"),
    ("INT",       r"\bint\b"),
    ("FLOAT",     r"\bfloat\b"),
    ("BOOL_T",    r"\bbool\b"),
    ("IDENT",     r"[A-Za-z_][A-Za-z0-9_]*"),
    ("LBRACE",    r"\{"),
    ("RBRACE",    r"\}"),
    ("LPAREN",    r"\("),
    ("RPAREN",    r"\)"),
    ("SEMICOLON", r";"),
    ("OP_REL",    r"<=|>=|==|!=|<|>"),
    ("OP_ARITH",  r"[+\-*/]"),
    ("ASSIGN",    r"="),
    ("SKIP",      r"[ \t\n]+"),
    ("MISMATCH",  r"."),
]

MASTER_RE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
)

@dataclass
class Token:
    type: str
    value: str
    line: int

def lexer(source: str) -> List[Token]:
    tokens = []
    line = 1
    for mo in MASTER_RE.finditer(source):
        kind  = mo.lastgroup
        value = mo.group()
        if kind == "SKIP":
            line += value.count("\n")
            continue
        elif kind == "MISMATCH":
            raise SyntaxError(f"[Leksikal] Token tidak dikenal: '{value}' pada baris {line}")
        tokens.append(Token(kind, value, line))
    return tokens


# ─────────────────────────────────────────────
# 2. ANALISIS SINTAKSIS → AST
# ─────────────────────────────────────────────

@dataclass
class ASTNode:
    node_type: str
    children:  List[Any] = field(default_factory=list)
    value:     Optional[str] = None

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos    = 0

    def peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type: str) -> Token:
        tok = self.peek()
        if tok is None:
            raise SyntaxError(f"[Sintaksis] Diharapkan '{expected_type}', tetapi input sudah habis.")
        if tok.type != expected_type:
            raise SyntaxError(
                f"[Sintaksis] Baris {tok.line}: Diharapkan '{expected_type}', "
                f"didapat '{tok.type}' ('{tok.value}')"
            )
        self.pos += 1
        return tok

    # while_stmt ::= "while" "(" condition ")" "{" statements "}"
    def parse_while(self) -> ASTNode:
        self.consume("WHILE")
        self.consume("LPAREN")
        cond = self.parse_condition()
        self.consume("RPAREN")
        self.consume("LBRACE")
        body = self.parse_statements()
        self.consume("RBRACE")
        return ASTNode("WhileStmt", children=[cond, body])

    # condition ::= expr OP_REL expr
    def parse_condition(self) -> ASTNode:
        left = self.parse_expr()
        op   = self.consume("OP_REL")
        right= self.parse_expr()
        return ASTNode("Condition", children=[left, right], value=op.value)

    # expr ::= term (OP_ARITH term)*
    def parse_expr(self) -> ASTNode:
        node = self.parse_term()
        while self.peek() and self.peek().type == "OP_ARITH":
            op   = self.consume("OP_ARITH")
            right= self.parse_term()
            node = ASTNode("BinOp", children=[node, right], value=op.value)
        return node

    # term ::= NUMBER | BOOL | IDENT
    def parse_term(self) -> ASTNode:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("[Sintaksis] Ekspresi tidak lengkap.")
        if tok.type in ("NUMBER", "BOOL", "IDENT"):
            self.pos += 1
            return ASTNode(tok.type, value=tok.value)
        raise SyntaxError(
            f"[Sintaksis] Baris {tok.line}: Token tidak terduga '{tok.value}' dalam ekspresi."
        )

    # statements ::= (decl_stmt | assign_stmt)*
    def parse_statements(self) -> ASTNode:
        stmts = ASTNode("Block")
        while self.peek() and self.peek().type != "RBRACE":
            tok = self.peek()
            if tok.type in ("INT", "FLOAT", "BOOL_T"):
                stmts.children.append(self.parse_decl())
            elif tok.type == "IDENT":
                stmts.children.append(self.parse_assign())
            else:
                raise SyntaxError(
                    f"[Sintaksis] Baris {tok.line}: Pernyataan tidak valid dimulai dengan '{tok.value}'."
                )
        return stmts

    # decl_stmt ::= type IDENT "=" expr ";"
    def parse_decl(self) -> ASTNode:
        type_tok = self.peek()
        self.pos += 1
        name_tok = self.consume("IDENT")
        self.consume("ASSIGN")
        expr = self.parse_expr()
        self.consume("SEMICOLON")
        return ASTNode("Decl", children=[expr],
                       value=f"{type_tok.value} {name_tok.value}")

    # assign_stmt ::= IDENT "=" expr ";"
    def parse_assign(self) -> ASTNode:
        name_tok = self.consume("IDENT")
        self.consume("ASSIGN")
        expr = self.parse_expr()
        self.consume("SEMICOLON")
        return ASTNode("Assign", children=[expr], value=name_tok.value)


# ─────────────────────────────────────────────
# 3. ANALISIS SEMANTIK
# ─────────────────────────────────────────────

class SemanticAnalyzer:
    def __init__(self):
        # symbol_table: nama → tipe
        self.symbol_table: dict = {}
        self.errors: List[str] = []

    def analyze(self, node: ASTNode, declared_vars: Optional[set] = None):
        if declared_vars is None:
            declared_vars = set(self.symbol_table.keys())

        if node.node_type == "WhileStmt":
            self.analyze(node.children[0], declared_vars)   # kondisi
            self.analyze(node.children[1], declared_vars)   # body

        elif node.node_type == "Condition":
            self.analyze(node.children[0], declared_vars)
            self.analyze(node.children[1], declared_vars)

        elif node.node_type == "Block":
            for stmt in node.children:
                self.analyze(stmt, declared_vars)

        elif node.node_type == "Decl":
            type_name, var_name = node.value.split(" ", 1)
            if var_name in declared_vars:
                self.errors.append(
                    f"[Semantik] Variabel '{var_name}' sudah dideklarasikan."
                )
            else:
                self.symbol_table[var_name] = type_name
                declared_vars.add(var_name)
            self.analyze(node.children[0], declared_vars)

        elif node.node_type == "Assign":
            if node.value not in declared_vars:
                self.errors.append(
                    f"[Semantik] Variabel '{node.value}' digunakan sebelum dideklarasikan."
                )
            self.analyze(node.children[0], declared_vars)

        elif node.node_type == "IDENT":
            if node.value not in declared_vars:
                self.errors.append(
                    f"[Semantik] Variabel '{node.value}' tidak dideklarasikan."
                )

        elif node.node_type in ("NUMBER", "BOOL"):
            pass  # literal selalu valid

        elif node.node_type == "BinOp":
            self.analyze(node.children[0], declared_vars)
            self.analyze(node.children[1], declared_vars)


# ─────────────────────────────────────────────
# 4. GENERASI THREE-ADDRESS CODE (TAC)
# ─────────────────────────────────────────────

class TACGenerator:
    def __init__(self):
        self.temp_count  = 0
        self.label_count = 0
        self.code: List[str] = []

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, instruction: str):
        self.code.append(instruction)

    def generate(self, node: ASTNode) -> Optional[str]:
        if node.node_type == "WhileStmt":
            label_start = self.new_label()
            label_end   = self.new_label()
            self.emit(f"{label_start}:")
            cond_temp = self.generate(node.children[0])
            self.emit(f"ifFalse {cond_temp} goto {label_end}")
            self.generate(node.children[1])
            self.emit(f"goto {label_start}")
            self.emit(f"{label_end}:")

        elif node.node_type == "Condition":
            left  = self.generate(node.children[0])
            right = self.generate(node.children[1])
            t     = self.new_temp()
            self.emit(f"{t} = {left} {node.value} {right}")
            return t

        elif node.node_type == "Block":
            for stmt in node.children:
                self.generate(stmt)

        elif node.node_type == "Decl":
            _, var_name = node.value.split(" ", 1)
            val = self.generate(node.children[0])
            self.emit(f"{var_name} = {val}")

        elif node.node_type == "Assign":
            val = self.generate(node.children[0])
            self.emit(f"{node.value} = {val}")

        elif node.node_type == "BinOp":
            left  = self.generate(node.children[0])
            right = self.generate(node.children[1])
            t     = self.new_temp()
            self.emit(f"{t} = {left} {node.value} {right}")
            return t

        elif node.node_type in ("NUMBER", "BOOL", "IDENT"):
            return node.value

        return None


# ─────────────────────────────────────────────
# UTILITAS: Pretty-print AST
# ─────────────────────────────────────────────

def print_ast(node: ASTNode, indent: int = 0):
    label = f"[{node.node_type}]"
    if node.value:
        label += f"  →  '{node.value}'"
    print("  " * indent + label)
    for child in node.children:
        print_ast(child, indent + 1)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

SOURCE_CODE = """
while ( i <= 10 ) {
    int temp = i + 1 ;
    sum = sum + temp ;
    i = i + 1 ;
}
"""

DECLARED_BEFORE = {"i": "int", "sum": "int"}   # variabel yang sudah ada sebelum loop

if __name__ == "__main__":
    print("=" * 55)
    print("  SIMULASI KOMPILASI: KONSTRUKSI WHILE LOOP")
    print("=" * 55)
    print(f"\nSumber kode:\n{SOURCE_CODE}")

    # --- 1. LEKSIKAL ---
    print("─" * 55)
    print("TAHAP 1 — ANALISIS LEKSIKAL (Tokenisasi)")
    print("─" * 55)
    tokens = lexer(SOURCE_CODE)
    for tok in tokens:
        print(f"  Baris {tok.line:2d}  |  {tok.type:<12} |  '{tok.value}'")

    # --- 2. SINTAKSIS ---
    print("\n" + "─" * 55)
    print("TAHAP 2 — ANALISIS SINTAKSIS (AST)")
    print("─" * 55)
    parser = Parser(tokens)
    ast    = parser.parse_while()
    print_ast(ast)

    # --- 3. SEMANTIK ---
    print("\n" + "─" * 55)
    print("TAHAP 3 — ANALISIS SEMANTIK")
    print("─" * 55)
    sem = SemanticAnalyzer()
    sem.symbol_table = dict(DECLARED_BEFORE)   # pre-populate
    sem.analyze(ast)
    if sem.errors:
        for e in sem.errors:
            print(f"  ✗ {e}")
    else:
        print("  ✓ Tidak ada kesalahan semantik ditemukan.")
    print("\n  Tabel Simbol (setelah analisis):")
    for var, typ in sem.symbol_table.items():
        print(f"    {var:<10} : {typ}")

    # --- 4. TAC ---
    print("\n" + "─" * 55)
    print("TAHAP 4 — GENERASI THREE-ADDRESS CODE (TAC)")
    print("─" * 55)
    tac_gen = TACGenerator()
    tac_gen.generate(ast)
    for i, line in enumerate(tac_gen.code, 1):
        print(f"  {i:2d}.  {line}")

    print("\n" + "=" * 55)
    print("  KOMPILASI SELESAI")
    print("=" * 55)
