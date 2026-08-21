"""Flask backend for Amine's Job Market Dashboard."""
import os
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request, send_file, render_template
from flask_cors import CORS

import database as db
import scraper
from cv_generator import generate_cv
from letter_generator import generate_letter
from scorer import score_job
from config import DATA_DIR, EXPORT_DIR

app = Flask(__name__)
CORS(app)


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)


def scrape_and_score(min_results=6):
    """Runs the scrapers, scores every new job, and stores it."""
    jobs = scraper.run_daily_scrape(min_results=min_results)
    inserted = 0
    for job in jobs:
        job.update(score_job(job))
        job_id = db.upsert_job(job)
        if job_id:
            inserted += 1
    return inserted


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


# ---------------------------------------------------------------------------
# API - manual refresh (triggers the scraper on demand)
# ---------------------------------------------------------------------------
@app.route("/api/scrape/run", methods=["POST"])
def api_scrape_run():
    inserted = scrape_and_score()
    return jsonify({"success": True, "new_jobs": inserted})


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
def start_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(scrape_and_score, "cron", hour=7, minute=0, id="daily_scrape")
    scheduler.start()
    return scheduler


def create_app():
    ensure_dirs()
    db.init_db()
    if db.count_jobs() == 0:
        scrape_and_score()
    return app


DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

create_app()
# Under Flask's debug reloader the module is imported twice (a watcher
# process, then the actual server child with WERKZEUG_RUN_MAIN=true).
# Only the process that will actually serve requests should start the
# background scheduler.
if not DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_scheduler()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=DEBUG, host="0.0.0.0", port=port)
