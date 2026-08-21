"""Flask backend for Amine's Job Market Dashboard."""
import logging
import os
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, Response, jsonify, request, send_file, render_template

import database as db
import scraper
import tracking_store
from cv_generator import generate_cv
from letter_generator import generate_letter
from scorer import score_job
from config import DATA_DIR, EXPORT_DIR

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

app = Flask(__name__)

# This app is entirely single-origin (Flask serves both the frontend and the
# API), so there is no legitimate cross-origin use case - Flask-CORS was
# unused surface area, dropped rather than configured.

DASHBOARD_USER = os.environ.get("DASHBOARD_USER", "amine")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")

if not DASHBOARD_PASSWORD:
    logger.warning(
        "DASHBOARD_PASSWORD is not set - the app is running with NO "
        "authentication. Fine for local dev, never for a public deployment: "
        "this app serves personal contact details in generated CVs and lets "
        "anyone trigger scraping."
    )


@app.before_request
def require_auth():
    if not DASHBOARD_PASSWORD:
        return  # local dev convenience only - see warning above
    auth = request.authorization
    valid = (
        auth is not None
        and secrets.compare_digest(auth.username, DASHBOARD_USER)
        and secrets.compare_digest(auth.password, DASHBOARD_PASSWORD)
    )
    if not valid:
        return Response(
            "Authentification requise.", 401,
            {"WWW-Authenticate": 'Basic realm="Job Dashboard"'},
        )

# In-memory tracking for background scraping runs. Fine for a single-process
# deployment (this app's Procfile pins --workers 1); status is lost on
# restart, which is an acceptable trade-off for a personal tool.
SCRAPE_TASKS = {}
MAX_DAILY_RETRIES = 2  # 7h -> 8h -> 9h


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)


def seed_if_empty():
    """Fast, network-free seed so the dashboard has content immediately at
    boot. The real multi-source scrape only ever runs via an explicit
    refresh or the daily cron - never blocking app startup."""
    if db.count_jobs() == 0:
        for job in scraper.generate_seed_jobs(8):
            job.update(score_job(job))
            db.upsert_job(job)
        logger.info("Seeded empty database with demo postings")


def _store_jobs(jobs):
    inserted = 0
    for job in jobs:
        job.update(score_job(job))
        job_id = db.upsert_job(job)
        if job_id:
            inserted += 1
    return inserted


def reconcile_tracking():
    """Overlays durable tracking data (Supabase) onto whatever jobs were
    just (re)scraped into the local, ephemeral SQLite cache - so a job
    the user already applied to shows correctly again after a redeploy
    wiped the local database, instead of reappearing as untouched."""
    tracking = tracking_store.get_all_tracking()
    if not tracking:
        return
    applied = 0
    for job_url, row in tracking.items():
        local_job = db.get_job_by_url(job_url)
        if not local_job:
            continue
        fields = {}
        if row.get("status"):
            fields["status"] = row["status"]
        if row.get("date_applied"):
            fields["date_applied"] = row["date_applied"]
        if row.get("notes"):
            fields["notes"] = row["notes"]
        if fields:
            db.update_job(local_job["id"], **fields)
            applied += 1
    if applied:
        logger.info("Reconciled tracking state for %d job(s) from Supabase", applied)


def scrape_and_score(min_results=6, progress_cb=None):
    """Runs every scraper, scores and stores the results. Returns
    (inserted_count, run_log)."""
    jobs, run_log = scraper.run_daily_scrape(min_results=min_results, progress_cb=progress_cb)
    inserted = _store_jobs(jobs)
    if "Seed/Demo" not in run_log["sources"]:
        # Real sources delivered enough on their own this run - clear out
        # any leftover demo postings from earlier (e.g. the initial boot
        # seed) so they stop outranking real offers.
        db.delete_jobs_by_source("Seed/Demo")
    reconcile_tracking()
    return inserted, run_log


SCRAPE_HARD_TIMEOUT = 240  # seconds - see _run_scrape_task


def _run_scrape_task(task_id):
    """Runs scrape_and_score under a hard wall-clock timeout. Belt and
    braces on top of scraper.py's own per-source timeouts: a run has
    been observed taking far longer on a real host than any configured
    timeout should allow (network conditions outside this app's
    control), which would otherwise leave a task stuck in "running"
    forever - confusing for anyone polling /api/scrape/status. On
    timeout the abandoned background thread keeps running until it
    finishes on its own (harmless, just wasted work); the task itself
    is reported as failed immediately so the UI never hangs on it."""
    task = SCRAPE_TASKS[task_id]

    def progress_cb(source_name, index, total):
        task["progress"] = {"source": source_name, "index": index, "total": total}

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(scrape_and_score, progress_cb=progress_cb)
        inserted, run_log = future.result(timeout=SCRAPE_HARD_TIMEOUT)
        task.update(
            status="completed",
            finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            new_jobs=inserted,
            run_log=run_log,
        )
    except FutureTimeoutError:
        logger.error("Scraping task %s exceeded %ds - abandoning", task_id, SCRAPE_HARD_TIMEOUT)
        task.update(
            status="failed",
            finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            error=f"Timeout apres {SCRAPE_HARD_TIMEOUT}s (conditions reseau) - reessayez",
        )
    except Exception as e:
        logger.error("Scraping task %s failed: %s", task_id, e, exc_info=True)
        task.update(
            status="failed",
            finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            error=str(e),
        )
    finally:
        # wait=False: never block on a run we've already given up on.
        pool.shutdown(wait=False)


def _schedule_daily_retry(attempt):
    from datetime import datetime, timedelta
    retry_at = datetime.now() + timedelta(hours=1)
    _scheduler.add_job(
        _daily_scrape_job, "date", run_date=retry_at,
        kwargs={"attempt": attempt},
        id=f"daily_scrape_retry_{attempt}",
        replace_existing=True,
        misfire_grace_time=3600,
    )


def _daily_scrape_job(attempt=1):
    """Scheduled scrape with a retry fallback: if the run raises or finds
    nothing at all, try again an hour later, up to MAX_DAILY_RETRIES times
    (7h -> 8h -> 9h)."""
    try:
        inserted, run_log = scrape_and_score()
        logger.info("Daily scrape (attempt %d) inserted %d jobs", attempt, inserted)
        if inserted == 0 and attempt <= MAX_DAILY_RETRIES:
            logger.warning("Daily scrape found nothing, retrying in 1h (attempt %d)", attempt + 1)
            _schedule_daily_retry(attempt + 1)
    except Exception as e:
        logger.error("Daily scrape (attempt %d) failed: %s", attempt, e, exc_info=True)
        if attempt <= MAX_DAILY_RETRIES:
            _schedule_daily_retry(attempt + 1)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API - jobs
# ---------------------------------------------------------------------------
@app.route("/api/jobs/today")
def api_jobs_today():
    sector = request.args.getlist("sector") or None
    min_salary = request.args.get("min_salary", type=int)
    max_salary = request.args.get("max_salary", type=int)
    score_tier = request.args.get("score")  # top | good | all
    locations = request.args.getlist("location") or None
    status = request.args.get("status")
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    only_today = request.args.get("today_only", default="false") == "true"

    filters = dict(
        sector=sector,
        min_salary=min_salary,
        max_salary=max_salary,
        score_tier=None if score_tier in (None, "all") else score_tier,
        locations=locations,
        status=None if status in (None, "all") else status,
        limit=limit,
        offset=offset,
    )
    if only_today:
        filters["date_found"] = date.today().isoformat()

    jobs = db.get_jobs(**filters)
    total = db.count_jobs(**{k: v for k, v in filters.items() if k not in ("limit", "offset")})
    return jsonify({"jobs": jobs, "total": total})


@app.route("/api/jobs/<job_id>")
def api_job_detail(job_id):
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "not_found"}), 404
    return jsonify(job)


@app.route("/api/jobs/<job_id>/generate-cv-letter", methods=["POST"])
def api_generate_cv_letter(job_id):
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "not_found"}), 404

    cv_path = generate_cv(job)
    letter_path = generate_letter(job)

    db.update_job(job_id, cv_adapted_path=cv_path, lm_path=letter_path)

    return jsonify({
        "cv_path": cv_path,
        "letter_path": letter_path,
        "status": "generated",
    })


@app.route("/api/jobs/<job_id>/download-cv")
def api_download_cv(job_id):
    job = db.get_job(job_id)
    if not job or not job.get("cv_adapted_path") or not os.path.exists(job["cv_adapted_path"]):
        return jsonify({"error": "cv_not_found"}), 404
    return send_file(job["cv_adapted_path"], as_attachment=True)


@app.route("/api/jobs/<job_id>/download-letter")
def api_download_letter(job_id):
    job = db.get_job(job_id)
    if not job or not job.get("lm_path") or not os.path.exists(job["lm_path"]):
        return jsonify({"error": "letter_not_found"}), 404
    return send_file(job["lm_path"], as_attachment=True)


@app.route("/api/jobs/<job_id>/apply", methods=["POST"])
def api_apply(job_id):
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "not_found"}), 404
    body = request.get_json(silent=True) or {}
    status = body.get("status", "applied")
    applied_date = body.get("date", date.today().isoformat())
    db.update_job(job_id, status=status, date_applied=applied_date)
    tracking_store.upsert_tracking(job["job_url"], status=status, date_applied=applied_date)
    return jsonify({"success": True})


@app.route("/api/jobs/<job_id>/status", methods=["POST"])
def api_update_status(job_id):
    """Generic status update (e.g. interview, offer, rejected, archived)."""
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "not_found"}), 404
    body = request.get_json(silent=True) or {}
    fields = {}
    if "status" in body:
        fields["status"] = body["status"]
    if "notes" in body:
        fields["notes"] = body["notes"]
    db.update_job(job_id, **fields)
    tracking_store.upsert_tracking(job["job_url"], status=fields.get("status"), notes=fields.get("notes"))
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# API - stats & insights
# ---------------------------------------------------------------------------
@app.route("/api/stats/daily")
def api_stats_daily():
    return jsonify(db.get_daily_stats())


@app.route("/api/insights")
def api_insights():
    return jsonify(db.get_insights())


def _start_scrape_task():
    """Kicks off a scraping run in a background thread and returns its
    task_id immediately - shared by the manual refresh endpoint and the
    automatic boot-time refresh below."""
    task_id = str(uuid.uuid4())
    SCRAPE_TASKS[task_id] = {
        "status": "running",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "progress": None,
        "run_log": None,
        "new_jobs": None,
        "error": None,
    }
    thread = threading.Thread(target=_run_scrape_task, args=(task_id,), daemon=True)
    thread.start()
    return task_id


# ---------------------------------------------------------------------------
# API - manual refresh (async: kicks off scraping in the background and
# returns immediately, per the improvement spec's non-blocking requirement)
# ---------------------------------------------------------------------------
@app.route("/api/scrape/run", methods=["POST"])
def api_scrape_run():
    try:
        task_id = _start_scrape_task()
        return jsonify({
            "success": True,
            "status": "scraping_in_progress",
            "task_id": task_id,
            "message": "Scraping demarre - suivez /api/scrape/status/<task_id>",
        }), 202
    except Exception as e:
        logger.error("Failed to start refresh: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "Scraping failed to start", "details": str(e)}), 500


@app.route("/api/scrape/status/<task_id>")
def api_scrape_status(task_id):
    task = SCRAPE_TASKS.get(task_id)
    if not task:
        return jsonify({"error": "unknown_task"}), 404
    return jsonify({"task_id": task_id, **task})


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
_scheduler = None


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_daily_scrape_job, "cron", hour=7, minute=0, id="daily_scrape")
    _scheduler.start()
    return _scheduler


def create_app():
    ensure_dirs()
    db.init_db()
    seed_if_empty()
    return app


DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

create_app()
# Under Flask's debug reloader the module is imported twice (a watcher
# process, then the actual server child with WERKZEUG_RUN_MAIN=true).
# Only the process that will actually serve requests should start the
# background scheduler / boot-time refresh.
if not DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_scheduler()
    if db.has_only_demo_jobs():
        # Storage is ephemeral on hosts like Render's free tier: every
        # redeploy/restart wipes real data back down to the demo seed.
        # Kick off a real scrape in the background right away instead of
        # waiting for a manual refresh or the 7h cron.
        logger.info("Only demo postings on hand at boot - starting a background refresh")
        _start_scrape_task()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=DEBUG, host="0.0.0.0", port=port)
