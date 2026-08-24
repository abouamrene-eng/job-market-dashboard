"""SQLite persistence layer for the job dashboard.

The database is a single file (data/jobs.db) created automatically on first
use - no external database server required.
"""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from config import DB_PATH, ROLE_FILTER_KEYWORDS, SECTOR_FILTER_KEYWORDS

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

-- Single-row store for the market veille (salary grille, target-company
-- negotiation notes, sources) - the synthesis behind the numbers, not the
-- individual job postings it finds (those go through upsert_job as usual).
-- Refreshed periodically by the "Veille marché AMOA/Product IDF" routine
-- via POST /api/veille, so it lives in the app instead of a one-off report.
CREATE TABLE IF NOT EXISTS market_veille (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    updated_at TIMESTAMP,
    target_min INTEGER,
    target_max INTEGER,
    summary TEXT,
    grille_json TEXT,
    targets_json TEXT,
    sources_json TEXT
);
"""

# V5 columns (aeronautique focus - replaces V3's dual Path A/B columns,
# left unused rather than dropped since SQLite can't cheaply drop columns).
# Added via migration rather than the base SCHEMA so a database created by
# an older deploy gets upgraded in place instead of needing a wipe.
# ALTER TABLE ADD COLUMN has no "IF NOT EXISTS" in SQLite, hence the
# try/except-per-column below.
V5_COLUMNS = [
    ("is_aeronautique", "INTEGER DEFAULT 0"),
    ("enac_mentioned", "INTEGER DEFAULT 0"),
    ("company_type", "TEXT"),
    ("analysis", "TEXT"),
    ("reject_reason", "TEXT"),
    ("salary_estimate_min", "INTEGER"),
    ("salary_estimate_max", "INTEGER"),
]


def _migrate_v5_columns(conn):
    for name, coltype in V5_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {coltype}")
        except sqlite3.OperationalError:
            pass  # column already exists


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
        _migrate_v5_columns(conn)


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
                score_location, score_notoriety, score_bonus, status,
                is_aeronautique, enac_mentioned, company_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                int(job.get("is_aeronautique", False)),
                int(job.get("enac_mentioned", False)),
                job.get("company_type", "Autre"),
            ),
        )
        return job_id


def get_jobs(
    sector=None,
    role=None,
    min_salary=None,
    max_salary=None,
    score_tier=None,
    locations=None,
    status=None,
    status_in=None,
    company_type=None,
    only_aeronautique=False,
    only_enac=False,
    date_found=None,
    source=None,
    limit=50,
    offset=0,
):
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if source:
        query += " AND source = ?"
        params.append(source)
    if date_found:
        query += " AND date_found = ?"
        params.append(date_found)
    if sector:
        # Fuzzy match: real posting sector text is far more varied than
        # the filter checkboxes, so match keywords against sector, title
        # and description rather than requiring an exact `sector` value.
        sector_clauses = []
        for sel in sector:
            for kw in SECTOR_FILTER_KEYWORDS.get(sel, [sel.lower()]):
                sector_clauses.append(
                    "(LOWER(sector) LIKE ? OR LOWER(job_title) LIKE ? OR LOWER(job_description) LIKE ?)"
                )
                params.extend([f"%{kw.lower()}%"] * 3)
        query += f" AND ({' OR '.join(sector_clauses)})"
    if role:
        # Fuzzy match against job_title only - role checkboxes map to
        # fairly specific titles, unlike the broader sector matching above.
        role_clauses = []
        for sel in role:
            for kw in ROLE_FILTER_KEYWORDS.get(sel, [sel.lower()]):
                role_clauses.append("LOWER(job_title) LIKE ?")
                params.append(f"%{kw.lower()}%")
        query += f" AND ({' OR '.join(role_clauses)})"
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
    if status_in:
        query += f" AND status IN ({','.join('?' for _ in status_in)})"
        params.extend(status_in)
    if company_type:
        query += f" AND company_type IN ({','.join('?' for _ in company_type)})"
        params.extend(company_type)
    if only_aeronautique:
        query += " AND is_aeronautique = 1"
    if only_enac:
        query += " AND enac_mentioned = 1"

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


def get_job_by_url(job_url: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_url = ?", (job_url,)).fetchone()
        return dict(row) if row else None


def update_job(job_id: str, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [job_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", params)




def get_daily_stats(day=None):
    day = day or date.today().isoformat()
    yesterday = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE date_found = ?", (day,)
        ).fetchone()["c"]
        total_yesterday = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE date_found = ?", (yesterday,)
        ).fetchone()["c"]
        avg_salary_row = conn.execute(
            """SELECT AVG((COALESCE(salary_min,0) + COALESCE(salary_max,0)) / 2.0) a
               FROM jobs WHERE date_found = ? AND (salary_min IS NOT NULL OR salary_max IS NOT NULL)""",
            (day,),
        ).fetchone()
        avg_salary = round(avg_salary_row["a"] or 0)
        market_median_row = conn.execute(
            """SELECT AVG((COALESCE(salary_min,0) + COALESCE(salary_max,0)) / 2.0) a
               FROM jobs WHERE salary_min IS NOT NULL OR salary_max IS NOT NULL"""
        ).fetchone()
        market_median = round(market_median_row["a"] or 0)
        top_matches = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE date_found = ? AND score > 75",
            (day,),
        ).fetchone()["c"]
        applied = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE date_applied = ?", (day,)
        ).fetchone()["c"]
        applied_total = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE status IN ('applied','interview','offer')"
        ).fetchone()["c"]
        saved_total = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE status = 'saved'"
        ).fetchone()["c"]
        rejected_total = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE status = 'rejected'"
        ).fetchone()["c"]
        aero_total = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE is_aeronautique = 1 AND status = 'new'"
        ).fetchone()["c"]
        flux_total = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE status = 'new'"
        ).fetchone()["c"]
        return {
            "total_jobs": total,
            "total_jobs_delta": total - total_yesterday,
            "avg_salary": avg_salary,
            "market_median_salary": market_median,
            "top_matches": top_matches,
            "applied": applied,
            "applied_total": applied_total,
            "saved_total": saved_total,
            "rejected_total": rejected_total,
            "aero_total": aero_total,
            "flux_total": flux_total,
        }


def get_insights():
    with get_conn() as conn:
        salary_by_sector = conn.execute(
            """SELECT sector, AVG((COALESCE(salary_min,salary_max)+COALESCE(salary_max,salary_min))/2.0) avg_salary,
                      COUNT(*) count
               FROM jobs
               WHERE sector IS NOT NULL AND sector != ''
                     AND (salary_min IS NOT NULL OR salary_max IS NOT NULL)
               GROUP BY sector
               HAVING COUNT(*) >= 2
               ORDER BY avg_salary DESC
               LIMIT 12"""
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


def get_veille():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM market_veille WHERE id = 1").fetchone()
        return dict(row) if row else None


def save_veille(**fields):
    """Upserts the single-row market veille record. Pass any subset of
    target_min/target_max/summary/grille_json/targets_json/sources_json -
    only provided fields are touched."""
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    fields["id"] = 1
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    updates = ", ".join(f"{k} = excluded.{k}" for k in fields if k != "id")
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO market_veille ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            list(fields.values()),
        )


