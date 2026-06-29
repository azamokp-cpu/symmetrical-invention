# Dokumentasi Proyek: Simulasi Kompilasi Konstruksi *While Loop*

---

## 1. Identitas Proyek

| Atribut | Keterangan |
|---|---|
| **Konstruksi Dipilih** | Perulangan / *Looping* — `while` |
| **Bahasa Implementasi** | Python 3 |
| **Nama File** | `while_compiler.py` |

---

## 2. Pola Sintaks — *Backus-Naur Form* (BNF)

Aturan tata bahasa yang mendefinisikan konstruksi `while` yang diimplementasikan:

```
<while_stmt>  ::= "while" "(" <condition> ")" "{" <statements> "}"

<condition>   ::= <expr> <op_rel> <expr>

<op_rel>      ::= "<=" | ">=" | "==" | "!=" | "<" | ">"

<statements>  ::= { <decl_stmt> | <assign_stmt> }

<decl_stmt>   ::= <type> <identifier> "=" <expr> ";"

<assign_stmt> ::= <identifier> "=" <expr> ";"

<expr>        ::= <term> { <op_arith> <term> }

<term>        ::= <NUMBER> | <BOOL> | <identifier>

<type>        ::= "int" | "float" | "bool"

<op_arith>    ::= "+" | "-" | "*" | "/"
```

**Contoh input valid yang digunakan:**

```
while ( i <= 10 ) {
    int temp = i + 1 ;
    sum = sum + temp ;
    i = i + 1 ;
}
```

---

## 3. Penjelasan Tahapan Kompilasi

### 3.1 Analisis Leksikal (*Lexer*)

**Tujuan:** Memecah teks sumber menjadi deretan *token* yang bermakna, dan membuang karakter yang tidak relevan seperti spasi dan baris baru.

**Cara Kerja:**  
Digunakan `re` (Regular Expression) Python dengan satu pola gabungan (`MASTER_RE`) yang terdiri dari beberapa sub-pola bernama. Setiap kali pola cocok dengan karakter berikutnya dalam input, sebuah objek `Token` dibuat dengan tiga atribut: `type`, `value`, dan `line`.

**Tabel Jenis Token yang Dikenali:**

| Tipe Token | Contoh | Pola Regex |
|---|---|---|
| `WHILE` | `while` | `\bwhile\b` |
| `IDENT` | `i`, `sum`, `temp` | `[A-Za-z_][A-Za-z0-9_]*` |
| `NUMBER` | `10`, `1` | `\d+(\.\d*)?` |
| `OP_REL` | `<=`, `==` | `<=\|>=\|==\|!=\|<\|>` |
| `OP_ARITH` | `+`, `-`, `*` | `[+\-*/]` |
| `ASSIGN` | `=` | `=` |
| `INT` | `int` | `\bint\b` |
| `LPAREN` | `(` | `\(` |
| `RPAREN` | `)` | `\)` |
| `LBRACE` | `{` | `\{` |
| `RBRACE` | `}` | `\}` |
| `SEMICOLON` | `;` | `;` |

**Hasil Leksikal untuk Input Contoh:**

```
Baris  2  |  WHILE       |  'while'
Baris  2  |  LPAREN      |  '('
Baris  2  |  IDENT       |  'i'
Baris  2  |  OP_REL      |  '<='
Baris  2  |  NUMBER      |  '10'
Baris  2  |  RPAREN      |  ')'
Baris  2  |  LBRACE      |  '{'
Baris  3  |  INT         |  'int'
Baris  3  |  IDENT       |  'temp'
Baris  3  |  ASSIGN      |  '='
...
```

---

### 3.2 Analisis Sintaksis — *Abstract Syntax Tree* (AST)

**Tujuan:** Memverifikasi bahwa urutan *token* sesuai dengan tata bahasa (BNF), lalu membangun *Abstract Syntax Tree* (AST) yang merepresentasikan struktur hierarkis kode.

**Cara Kerja:**  
Digunakan teknik *Recursive Descent Parsing*. Kelas `Parser` memiliki satu metode untuk setiap aturan produksi BNF:

| Metode | Aturan BNF yang Diimplementasikan |
|---|---|
| `parse_while()` | `<while_stmt>` |
| `parse_condition()` | `<condition>` |
| `parse_expr()` | `<expr>` |
| `parse_term()` | `<term>` |
| `parse_statements()` | `<statements>` |
| `parse_decl()` | `<decl_stmt>` |
| `parse_assign()` | `<assign_stmt>` |

Setiap metode memanggil `consume(type)` yang memverifikasi token berikutnya sesuai yang diharapkan, lalu menggeser posisi baca ke depan.

**Struktur AST yang Dihasilkan:**

```
[WhileStmt]
  [Condition]  →  '<='
    [IDENT]    →  'i'
    [NUMBER]   →  '10'
  [Block]
    [Decl]     →  'int temp'
      [BinOp]  →  '+'
        [IDENT]  →  'i'
        [NUMBER] →  '1'
    [Assign]   →  'sum'
      [BinOp]  →  '+'
        [IDENT]  →  'sum'
        [IDENT]  →  'temp'
    [Assign]   →  'i'
      [BinOp]  →  '+'
        [IDENT]  →  'i'
        [NUMBER] →  '1'
```

**Penjelasan Node AST:**

| Node | Makna |
|---|---|
| `WhileStmt` | Akar dari seluruh perulangan, memiliki dua anak: kondisi dan blok tubuh |
| `Condition` | Perbandingan relasional; atribut `value` menyimpan operator (`<=`) |
| `Block` | Kumpulan pernyataan di dalam kurung kurawal `{ }` |
| `Decl` | Deklarasi variabel baru; `value` = `"int temp"` |
| `Assign` | Penugasan ke variabel yang sudah ada; `value` = nama variabel |
| `BinOp` | Operasi biner aritmetika; `value` = operator, anak kiri/kanan = operand |
| `IDENT` | Daun: referensi ke variabel |
| `NUMBER` | Daun: literal angka |

---

### 3.3 Analisis Semantik

**Tujuan:** Memeriksa kebenaran *makna* kode yang sudah valid secara sintaksis. Pengecekan yang dilakukan:

1. **Deklarasi ganda** — Variabel tidak boleh dideklarasikan lebih dari sekali dalam scope yang sama.
2. **Variabel tidak dideklarasikan** — Setiap variabel yang direferensikan harus sudah ada dalam *symbol table*.

**Cara Kerja:**  
Kelas `SemanticAnalyzer` menelusuri AST secara rekursif. Ia mempertahankan sebuah `symbol_table` (kamus `nama → tipe`) dan sekumpulan `declared_vars`. Sebelum analisis dimulai, variabel yang sudah ada sebelum *loop* (misalnya `i` dan `sum`) di-*pre-populate* ke dalam tabel simbol.

**Tabel Simbol Setelah Analisis:**

| Variabel | Tipe |
|---|---|
| `i` | `int` (dari sebelum loop) |
| `sum` | `int` (dari sebelum loop) |
| `temp` | `int` (dideklarasikan di dalam loop) |

**Contoh Kasus Error Semantik:**

```python
# Jika input mengandung: int temp = ...; int temp = ...;
# Output: [Semantik] Variabel 'temp' sudah dideklarasikan.

# Jika input mengandung: x = x + 1; (tanpa deklarasi x sebelumnya)
# Output: [Semantik] Variabel 'x' tidak dideklarasikan.
```

---

### 3.4 Generasi *Three-Address Code* (TAC)

**Tujuan:** Menghasilkan kode antara (*intermediate code*) dalam format *Three-Address Code*, di mana setiap instruksi memiliki paling banyak tiga operand.

**Cara Kerja:**  
Kelas `TACGenerator` menelusuri AST secara rekursif (post-order untuk ekspresi). Ia menggunakan:
- **Variabel Sementara** (`t1`, `t2`, ...) — Untuk menyimpan hasil subekspresi.
- **Label** (`L1`, `L2`, ...) — Untuk menandai titik lompatan dalam alur kontrol.

**Pola TAC untuk `while`:**

```
L_start:
    t_cond = <kiri> <op_rel> <kanan>
    ifFalse t_cond goto L_end
    <tubuh loop>
    goto L_start
L_end:
```

**TAC yang Dihasilkan dari Input Contoh:**

```
 1.  L1:                      ← Label awal loop (titik kembali)
 2.  t1 = i <= 10             ← Evaluasi kondisi
 3.  ifFalse t1 goto L2       ← Jika kondisi false, keluar dari loop
 4.  t2 = i + 1               ← Hitung i + 1
 5.  temp = t2                ← Simpan ke temp (deklarasi int temp)
 6.  t3 = sum + temp          ← Hitung sum + temp
 7.  sum = t3                 ← Simpan ke sum
 8.  t4 = i + 1               ← Hitung i + 1
 9.  i = t4                   ← Simpan ke i (increment)
10.  goto L1                  ← Kembali ke awal loop
11.  L2:                      ← Label akhir (titik keluar loop)
```

---

## 4. Diagram Alur Kompilasi

```
Kode Sumber (teks mentah)
         │
         ▼
┌─────────────────────┐
│  ANALISIS LEKSIKAL  │  → Token: WHILE, LPAREN, IDENT, OP_REL, ...
│      (Lexer)        │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ ANALISIS SINTAKSIS  │  → Abstract Syntax Tree (AST)
│     (Parser)        │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ ANALISIS SEMANTIK   │  → Tabel Simbol + Validasi Error
│ (SemanticAnalyzer)  │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  GENERASI TAC       │  → Three-Address Code (kode antara)
│  (TACGenerator)     │
└─────────────────────┘
         │
         ▼
  Kode Antara (TAC)
  siap untuk tahap
  optimasi & generasi
  kode mesin
```

---

## 5. Cara Menjalankan Program

### Prasyarat
- Python 3.7 atau lebih baru (tanpa dependensi eksternal)

### Langkah

```bash
python while_compiler.py
```

### Mengubah Input

Modifikasi variabel `SOURCE_CODE` dan `DECLARED_BEFORE` di bagian bawah file:

```python
SOURCE_CODE = """
while ( x < 100 ) {
    x = x + 5 ;
}
"""

DECLARED_BEFORE = {"x": "int"}
```

---

## 6. Struktur Kode

```
while_compiler.py
├── Token (dataclass)          — Representasi satu token
├── lexer(source)              — Analisis leksikal
├── ASTNode (dataclass)        — Node pohon sintaksis abstrak
├── Parser
│   ├── parse_while()
│   ├── parse_condition()
│   ├── parse_expr()
│   ├── parse_term()
│   ├── parse_statements()
│   ├── parse_decl()
│   └── parse_assign()
├── SemanticAnalyzer
│   └── analyze(node)
├── TACGenerator
│   └── generate(node)
└── main block                 — Menjalankan semua tahap & mencetak output
```

---

## 7. Referensi

- Aho, A. V., Lam, M. S., Sethi, R., & Ullman, J. D. (2006). *Compilers: Principles, Techniques, and Tools* (2nd ed.). Pearson.
- Grune, D., et al. (2012). *Modern Compiler Design* (2nd ed.). Springer.

