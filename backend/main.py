"""
FastAPI Server for C-Inspect.
Exposes REST APIs for:
- Live static analysis (Lexer -> Parser -> Symbol Table -> Rules)
- Explicit submission checkpoints & finding persistence
- Recurrence history tracking across sessions
- Rule catalog & compiler design stage inspection
- External GCC/Clang compilation and execution
- Static Web UI hosting
"""
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from backend.analyzer.engine import StaticAnalysisEngine
from backend.analyzer.rules.base import RULE_CATALOG
from backend.storage.db import HistoryDatabase
from backend.compiler.adapter import CompilerAdapter

app = FastAPI(
    title="C-Inspect API",
    description="Real-Time, History-Aware Static Analysis Tool for C Programming",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
engine = StaticAnalysisEngine()
db = HistoryDatabase("cinspect.db")
compiler = CompilerAdapter()


# --- Pydantic Request Models ---
class AnalyzeRequest(BaseModel):
    code: str
    student_id: Optional[str] = "student_demo"


class SubmitRequest(BaseModel):
    code: str
    file_name: Optional[str] = "main.c"
    student_id: Optional[str] = "student_demo"


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(open|corrected|dismissed)$")


class RunRequest(BaseModel):
    code: str
    stdin: Optional[str] = ""


class CreateStudentRequest(BaseModel):
    display_name: str


# --- API Endpoints ---

@app.post("/api/analyze")
def analyze_code(req: AnalyzeRequest):
    """
    Live debounced analysis endpoint.
    Performs Lexical, Syntax, Symbol Table, and Semantic checks.
    Attaches historical recurrence counts for the active student profile.
    """
    result = engine.analyze(req.code)
    
    # Retrieve past occurrences count for each detected rule
    rule_ids = [d["rule_id"] for d in result["diagnostics"]]
    recurrence_map = db.get_recurrence_for_rules(req.student_id or "student_demo", rule_ids)
    
    for diag in result["diagnostics"]:
        prior = recurrence_map.get(diag["rule_id"], 0)
        diag["prior_recurrence"] = prior
        diag["is_recurring"] = prior > 0

    return result


@app.post("/api/submit")
def submit_code(req: SubmitRequest):
    """
    Explicit submission / checkpoint action.
    Persists findings to SQLite and permanently updates the student's recurrence history.
    """
    analysis_res = engine.analyze(req.code)
    record = db.record_submission(
        student_id=req.student_id or "student_demo",
        file_name=req.file_name or "main.c",
        code=req.code,
        diagnostics=analysis_res["diagnostics"]
    )
    return {
        "success": True,
        "submission": record,
        "summary": analysis_res["summary"]
    }


@app.get("/api/history")
def get_history(student_id: str = Query("student_demo")):
    """Retrieves student submission history, recurring mistake breakdown, and statistics."""
    return db.get_student_history(student_id)


@app.patch("/api/findings/{finding_id}")
def update_finding_status(finding_id: str, req: StatusUpdateRequest):
    """Updates a finding status to 'open', 'corrected', or 'dismissed'."""
    ok = db.update_finding_status(finding_id, req.status)
    if not ok:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"success": True, "finding_id": finding_id, "status": req.status}


@app.get("/api/students")
def get_students():
    """Lists all student profiles for profile isolation."""
    return db.get_students()


@app.post("/api/students")
def create_student(req: CreateStudentRequest):
    """Registers a new student profile."""
    if not req.display_name.strip():
        raise HTTPException(status_code=400, detail="Display name cannot be empty")
    return db.create_student(req.display_name.strip())


@app.get("/api/rules")
def get_rules():
    """Returns rule catalog with educational descriptions and compiler design mappings."""
    return RULE_CATALOG


@app.post("/api/run")
def compile_and_run(req: RunRequest):
    """Compiles and runs code via GCC/Clang or safe educational simulator."""
    return compiler.compile_and_run(req.code, req.stdin or "")


@app.get("/api/compiler-status")
def get_compiler_status():
    """Returns availability and version info for host GCC/Clang."""
    return compiler.detect_compiler()


@app.get("/api/samples")
def get_sample_programs():
    """Returns official sample test case files with name and contents for quick loading in editor."""
    samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "C-Inspect_Sample_Test_Cases"))
    samples = []
    if os.path.exists(samples_dir):
        descriptions = {
            "01_valid_program.c": "01: Clean / Valid Program (0 errors expected)",
            "02_static_analysis_issues.c": "02: Static Analysis Issues Demo (7 issues)",
            "03A_history_first_submission.c": "03A: History Submission 1 (total_area)",
            "03B_history_repeat_submission.c": "03B: History Submission 2 (total_cost recurrence)"
        }
        for fname in sorted(os.listdir(samples_dir)):
            if fname.endswith(".c"):
                fpath = os.path.join(samples_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        code = f.read()
                    samples.append({
                        "file_name": fname,
                        "title": descriptions.get(fname, fname),
                        "code": code
                    })
                except Exception:
                    pass
    return samples


# Serve Frontend static assets
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
