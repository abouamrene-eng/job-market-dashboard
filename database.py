"""SQLite persistence layer for the job dashboard.

The database is a single file (data/jobs.db) created automatically on first
use - no external database server required.
"""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    date_found DATE NOT NULL,
    job_title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    sector TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    job_url TEXT UNIQUE NOT NULL,
    job_description TEXT,
    source TEXT,
    score REAL DEFAULT 0,
    score_salary REAL DEFAULT 0,
    score_job_match REAL DEFAULT 0,
    score_sector REAL DEFAULT 0,
    score_location REAL DEFAULT 0,
    score_notoriety REAL DEFAULT 0,
    score_bonus REAL DEFAULT 0,
    status TEXT DEFAULT 'new',
    date_applied DATE,
    notes TEXT,
    cv_adapted_path TEXT,
    lm_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_date_found ON jobs(date_found);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_job(job: dict) -> str:
    """Insert a job, deduplicated on job_url. Returns the job id.

    If the URL already exists, the row is left untouched (score/status are
    not clobbered by a re-scrape) and its id is returned.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM jobs WHERE job_url = ?", (job["job_url"],)
        ).fetchone()
        if row:
            return row["id"]

        job_id = job.get("id") or str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO jobs (
                id, date_found, job_title, company, location, sector,
                salary_min, salary_max, job_url, job_description, source,
                score, score_salary, score_job_match, score_sector,
                score_location, score_notoriety, score_bonus, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                job.get("date_found", date.today().isoformat()),
                job["job_title"],
                job["company"],
                job.get("location", ""),
                job.get("sector", ""),
                job.get("salary_min"),
                job.get("salary_max"),
                job["job_url"],
                job.get("job_description", ""),
                job.get("source", ""),
                job.get("score", 0),
                job.get("score_salary", 0),
                job.get("score_job_match", 0),
                job.get("score_sector", 0),
                job.get("score_location", 0),
                job.get("score_notoriety", 0),
                job.get("score_bonus", 0),
                job.get("status", "new"),
            ),
        )
        return job_id


def get_jobs(
    sector=None,
    min_salary=None,
    max_salary=None,
    score_tier=None,
    locations=None,
    status=None,
    date_found=None,
    limit=50,
    offset=0,
):
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if date_found:
        query += " AND date_found = ?"
        params.append(date_found)
    if sector:
        placeholders = ",".join("?" for _ in sector)
        query += f" AND sector IN ({placeholders})"
        params.extend(sector)
    if min_salary:
        query += " AND (salary_max IS NULL OR salary_max >= ?)"
        params.append(min_salary)
    if max_salary:
        query += " AND (salary_min IS NULL OR salary_min <= ?)"
        params.append(max_salary)
    if score_tier == "top":
        query += " AND score > 75"
    elif score_tier == "good":
        query += " AND score BETWEEN 60 AND 75"
    if locations:
        loc_clause = " OR ".join("location LIKE ?" for _ in locations)
        query += f" AND ({loc_clause})"
        params.extend(f"%{loc}%" for loc in locations)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def count_jobs(**filters):
    filters.pop("limit", None)
    filters.pop("offset", None)
    jobs = get_jobs(limit=1_000_000, offset=0, **filters)
    return len(jobs)


def get_job(job_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def update_job(job_id: str, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [job_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", params)


def delete_jobs_by_source(source: str, exclude_applied: bool = True):
    """Removes demo/seed postings once real sources start delivering
    enough results, so they stop competing with real offers. Never
    deletes a job the user has already applied to / tracked, even if it
    was a demo posting."""
    query = "DELETE FROM jobs WHERE source = ?"
    params = [source]
    if exclude_applied:
        query += " AND status = 'new'"
    with get_conn() as conn:
        conn.execute(query, params)


def get_daily_stats(day=None):
    day = day or date.today().isoformat()
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE date_found = ?", (day,)
        ).fetchone()["c"]
        avg_salary_row = conn.execute(
            """SELECT AVG((COALESCE(salary_min,0) + COALESCE(salary_max,0)) / 2.0) a
               FROM jobs WHERE date_found = ? AND (salary_min IS NOT NULL OR salary_max IS NOT NULL)""",
            (day,),
        ).fetchone()
        avg_salary = round(avg_salary_row["a"] or 0)
        top_matches = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE date_found = ? AND score > 75",
            (day,),
        ).fetchone()["c"]
        applied = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE date_applied = ?", (day,)
        ).fetchone()["c"]
        return {
            "total_jobs": total,
            "avg_salary": avg_salary,
            "top_matches": top_matches,
            "applied": applied,
        }


def get_insights():
    with get_conn() as conn:
        salary_by_sector = conn.execute(
            """SELECT sector, AVG((COALESCE(salary_min,0)+COALESCE(salary_max,0))/2.0) avg_salary,
                      COUNT(*) count
               FROM jobs WHERE sector IS NOT NULL AND sector != ''
               GROUP BY sector ORDER BY avg_salary DESC"""
        ).fetchall()
        top_companies = conn.execute(
            """SELECT company, COUNT(*) count, AVG(score) avg_score
               FROM jobs GROUP BY company ORDER BY count DESC LIMIT 10"""
        ).fetchall()
        trend = conn.execute(
            """SELECT date_found, COUNT(*) count FROM jobs
               GROUP BY date_found ORDER BY date_found DESC LIMIT 14"""
        ).fetchall()
        total_applied = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE status != 'new'"
        ).fetchone()["c"]

        return {
            "salary_by_sector": [dict(r) for r in salary_by_sector],
            "top_companies": [dict(r) for r in top_companies],
            "trend": [dict(r) for r in trend],
            "total_applied": total_applied,
        }
