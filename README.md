# C-Inspect: Real-Time, History-Aware Static Analysis for C

**C-Inspect** is a browser-based coding environment and static analysis platform built for students learning C programming and Compiler Design. It bridges foundational compiler theory—lexical scanning, recursive-descent parsing, AST generation, and scoped symbol tables—with interactive, educational feedback that tracks and remembers recurring student mistakes over time.

---

## Key Features

1. **Live Debounced Static Analysis (PRD FR-01 & FR-02)**
   - Powered by a Monaco Code Editor with custom dark theme, line numbers, and syntax highlighting.
   - Debounced background analysis triggers automatically as students type, displaying in-editor squiggly markers and diagnostic cards.

2. **7 Core Static Analysis Rules (PRD FR-03 & FR-05)**
   - `SYNTAX_ERROR`: Catches unclosed brackets, missing semicolons, or invalid character sequences during Lexing and Parsing.
   - `UNDECLARED_IDENTIFIER`: Detects variables/functions used without prior declaration via Symbol Table lookups.
   - `DUPLICATE_DECLARATION`: Flags redeclarations in the same lexical block.
   - `ASSIGNMENT_IN_CONDITION`: Warns on suspicious single `=` inside `if` or `while` conditions (e.g. `if (x = 10)` instead of `==`).
   - `UNUSED_LOCAL_VARIABLE`: Identifies variables defined but never read or referenced.
   - `MISSING_RETURN`: Verifies non-void functions have a return statement along valid execution paths.
   - `UNREACHABLE_CODE`: Identifies dead statements located directly after `return`, `break`, or `continue`.

3. **Compiler Design Stages Inspector (PRD FR-04)**
   - **Lexer Token Stream**: Inspect scanned tokens, types, coordinates, and raw lexemes.
   - **Abstract Syntax Tree (AST)**: Visualizes the parsed statement hierarchy in JSON tree format.
   - **Scoped Symbol Table**: Real-time view of symbol bindings, lexical scope depths, and usage reference counts.

4. **Persistent Recurrence Tracking & Profile Isolation (PRD FR-06, FR-07, FR-11)**
   - **Checkpoint Submissions**: Students explicitly checkpoint and submit code to SQLite (`cinspect.db`).
   - **Recurrence Badges**: Highlights repeated mistakes with badges like *"⚠️ Repeated Mistake: Seen 3 times before"*.
   - **Student Profile Isolation**: Switch between student profiles or create new profiles with fully isolated mistake history.

5. **Finding Status Management (PRD FR-08)**
   - Students can track their learning progress by marking past findings as **"Mark Corrected"** or **"Dismiss"** in the History tab.

6. **External Compiler Integration & Sandbox (PRD FR-09 & FR-10)**
   - Detects local GCC or Clang on the machine and executes code with strict 5-second compilation and execution timeouts.
   - Provides standard input (`stdin`) pass-through for interactive programs.
   - Includes a built-in **Educational AST Simulator** when a host C compiler is not yet installed in PATH.

7. **Sample Test Case Quick Loader**
   - Built-in selector to instantly load official test cases (`01_valid_program.c`, `02_static_analysis_issues.c`, `03A`, `03B`) with one click.

---

## Project Structure

```text
cd/
├── backend/
│   ├── analyzer/
│   │   ├── tokens.py            # Token definitions & C keywords
│   │   ├── lexer.py             # Lexical scanner & tokenizer
│   │   ├── ast_nodes.py         # AST node dataclasses
│   │   ├── parser.py            # Recursive descent parser
│   │   ├── symbol_table.py      # Scoped symbol table & scope tree
│   │   ├── engine.py            # StaticAnalysisEngine orchestrator
│   │   └── rules/
│   │       └── base.py          # Rule catalog & Diagnostic structures
│   ├── compiler/
│   │   └── adapter.py           # GCC/Clang subprocess adapter & fallback
│   ├── storage/
│   │   └── db.py                # SQLite database service & queries
│   └── main.py                  # FastAPI REST API & static file server
├── frontend/
│   ├── index.html               # Main application layout
│   ├── style.css                # Polished dark UI & responsive design
│   └── app.js                   # Client controller & Monaco editor integration
├── C-Inspect_Sample_Test_Cases/ # Official sample test files (01, 02, 03A, 03B)
├── tests/
│   ├── test_engine.py           # Unit tests for analyzer engine
│   ├── test_persistence.py      # Unit tests for SQLite recurrence tracking
│   ├── test_sample_cases.py     # Unit tests for all 4 official sample files
│   └── verify_api.py            # End-to-end REST API integration tests
├── run.bat                      # Windows batch startup script
└── run.ps1                      # Windows PowerShell startup script
```

---

## Getting Started

### 1. Requirements
- Python 3.8+
- Required packages: `fastapi`, `uvicorn`, `requests`
  ```bash
  pip install fastapi uvicorn requests
  ```

### 2. Launching the Application

#### Option A: Quick-start script (Windows)
Double-click `run.bat` or run via PowerShell:
```powershell
.\run.ps1
```

#### Option B: Manual command
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running, open your browser at **http://127.0.0.1:8000**.

---

## Running Automated Tests

Run the full test suite (13 unit tests across engine, persistence, and official sample cases):
```bash
python -m unittest discover tests
```

To run the end-to-end REST API integration check against a live server:
```bash
python tests/verify_api.py
```

---

## REST API Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Live static analysis with recurrence metadata |
| `POST` | `/api/submit` | Checkpoint submission and finding persistence |
| `GET` | `/api/history` | Submissions, rule statistics, and recent findings |
| `PATCH`| `/api/findings/{id}` | Update finding status (`open`, `corrected`, `dismissed`) |
| `GET` | `/api/students` | List student profiles |
| `POST` | `/api/students` | Register a new student profile |
| `GET` | `/api/rules` | Fetch static rule catalog & compiler mappings |
| `GET` | `/api/samples` | List sample test case programs |
| `POST` | `/api/run` | Execute code with GCC/Clang or educational simulator |
| `GET` | `/api/compiler-status` | Detect availability of host GCC/Clang toolchain |
