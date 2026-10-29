"""
SQLite Database and History Service for C-Inspect.
Implements student profiles, explicit submission checkpoints,
persistent findings storage, mistake recurrence tracking, and status updates.
"""
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


class HistoryDatabase:
    def __init__(self, db_path: str = "cinspect.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Students table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Submissions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    submission_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    code TEXT NOT NULL,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id)
                );
            """)

            # 3. Findings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    finding_id TEXT PRIMARY KEY,
                    submission_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    column_number INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    explanation TEXT,
                    status TEXT DEFAULT 'open', -- 'open', 'corrected', 'dismissed'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
                    FOREIGN KEY (student_id) REFERENCES students(student_id)
                );
            """)

            # Pre-seed default student if table empty
            cursor.execute("SELECT COUNT(*) as count FROM students")
            if cursor.fetchone()["count"] == 0:
                cursor.execute(
                    "INSERT INTO students (student_id, display_name) VALUES (?, ?)",
                    ("student_demo", "Alex Chen (CS101)")
                )
                cursor.execute(
                    "INSERT INTO students (student_id, display_name) VALUES (?, ?)",
                    ("student_maya", "Maya Patel (CS101)")
                )
            conn.commit()

    # --- Student Profiles ---
    def get_students(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, display_name, created_at FROM students ORDER BY display_name")
            return [dict(row) for row in cursor.fetchall()]

    def create_student(self, display_name: str) -> Dict[str, Any]:
        student_id = f"student_{uuid.uuid4().hex[:8]}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO students (student_id, display_name) VALUES (?, ?)",
                (student_id, display_name)
            )
            conn.commit()
        return {"student_id": student_id, "display_name": display_name}

    # --- Submissions & Findings Checkpoints ---
    def record_submission(self, student_id: str, file_name: str, code: str,
                          diagnostics: List[Dict[str, Any]]) -> Dict[str, Any]:
        submission_id = f"sub_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Record submission
            cursor.execute(
                """
                INSERT INTO submissions (submission_id, student_id, file_name, code, submitted_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (submission_id, student_id, file_name, code, now)
            )

            # Record each finding and attach recurrence count
            saved_findings = []
            for d in diagnostics:
                finding_id = f"find_{uuid.uuid4().hex[:10]}"
                rule_id = d.get("rule_id", "UNKNOWN")

                # Count previous occurrences for this student
                cursor.execute(
                    """
                    SELECT COUNT(*) as cnt FROM findings
                    WHERE student_id = ? AND rule_id = ?
                    """,
                    (student_id, rule_id)
                )
                prior_count = cursor.fetchone()["cnt"]
                current_recurrence = prior_count + 1

                cursor.execute(
                    """
                    INSERT INTO findings (
                        finding_id, submission_id, student_id, rule_id,
                        severity, line_number, column_number, message, explanation, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        finding_id, submission_id, student_id, rule_id,
                        d.get("severity", "warning"),
                        d.get("line", 1),
                        d.get("column", 1),
                        d.get("message", ""),
                        d.get("explanation", "")
                    )
                )

                f_dict = dict(d)
                f_dict["finding_id"] = finding_id
                f_dict["submission_id"] = submission_id
                f_dict["status"] = "open"
                f_dict["recurrence_count"] = current_recurrence
                saved_findings.append(f_dict)

            conn.commit()

        return {
            "submission_id": submission_id,
            "student_id": student_id,
            "submitted_at": now,
            "file_name": file_name,
            "findings": saved_findings
        }

    def get_recurrence_for_rules(self, student_id: str, rule_ids: List[str]) -> Dict[str, int]:
        """
        Returns a mapping of rule_id -> count of past occurrences for this student.
        Used by live debounced analysis to show recurring badges before submission.
        """
        if not rule_ids:
            return {}
        
        counts = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for r_id in set(rule_ids):
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM findings WHERE student_id = ? AND rule_id = ?",
                    (student_id, r_id)
                )
                counts[r_id] = cursor.fetchone()["cnt"]
        return counts

    def update_finding_status(self, finding_id: str, status: str) -> bool:
        if status not in ("open", "corrected", "dismissed"):
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE findings SET status = ? WHERE finding_id = ?",
                (status, finding_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_student_history(self, student_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Submissions
            cursor.execute(
                """
                SELECT submission_id, file_name, submitted_at,
                       (SELECT COUNT(*) FROM findings WHERE findings.submission_id = submissions.submission_id) as findings_count
                FROM submissions
                WHERE student_id = ?
                ORDER BY submitted_at DESC
                """,
                (student_id,)
            )
            submissions = [dict(r) for r in cursor.fetchall()]

            # Findings grouped by rule_id
            cursor.execute(
                """
                SELECT rule_id, severity, COUNT(*) as total_occurrences,
                       SUM(CASE WHEN status = 'corrected' THEN 1 ELSE 0 END) as corrected_count,
                       SUM(CASE WHEN status = 'dismissed' THEN 1 ELSE 0 END) as dismissed_count,
                       SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_count
                FROM findings
                WHERE student_id = ?
                GROUP BY rule_id, severity
                ORDER BY total_occurrences DESC
                """,
                (student_id,)
            )
            rule_stats = [dict(r) for r in cursor.fetchall()]

            # Recent findings list
            cursor.execute(
                """
                SELECT f.finding_id, f.submission_id, f.rule_id, f.severity,
                       f.line_number, f.column_number, f.message, f.explanation, f.status,
                       s.file_name, s.submitted_at
                FROM findings f
                JOIN submissions s ON f.submission_id = s.submission_id
                WHERE f.student_id = ?
                ORDER BY s.submitted_at DESC, f.line_number ASC
                LIMIT 50
                """,
                (student_id,)
            )
            recent_findings = [dict(r) for r in cursor.fetchall()]

            return {
                "student_id": student_id,
                "submissions_count": len(submissions),
                "submissions": submissions,
                "rule_stats": rule_stats,
                "recent_findings": recent_findings
            }
