"""Durable application-tracking storage via Supabase's REST API (PostgREST).
Verified end-to-end 2026-08-21 on a real France Travail posting: status
"applied" + a notes string, written through this module, survived a full
Render redeploy (local SQLite wipe -> boot-time auto-refresh -> the same
posting rediscovered and reconciled back to "applied" with its note).

Why this exists: the local SQLite database lives on Render's ephemeral
disk and is wiped on every redeploy/restart. The job listings themselves
self-heal (see app.py's boot-time auto-refresh), but a candidate's own
tracking data - which offers they applied to, when, with what notes -
can never be regenerated. That subset is mirrored here, in a free
Supabase Postgres project that survives redeploys.

Uses plain HTTP calls against Supabase's auto-generated REST API instead
of a Postgres client library, so no new dependency is needed - `requests`
is already required for scraping.

Table expected (create once via the Supabase SQL editor):

    create table job_tracking (
      job_url text primary key,
      status text not null default 'new',
      date_applied date,
      notes text,
      updated_at timestamptz not null default now()
    );

Configured via SUPABASE_URL and SUPABASE_SERVICE_KEY environment
variables. The service_role key is required (not the anon key) because
this table has no public-facing use and should not be reachable except
from this backend. Without both variables set, every function below is a
silent no-op (logged once) - the app keeps working exactly as before,
just without durable tracking.
"""
import logging
import os

import requests

logger = logging.getLogger("tracking_store")

TIMEOUT = 10
_warned_unconfigured = False


def _config():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    return url, key


def is_configured() -> bool:
    global _warned_unconfigured
    url, key = _config()
    if url and key:
        return True
    if not _warned_unconfigured:
        logger.info(
            "SUPABASE_URL/SUPABASE_SERVICE_KEY not set - application "
            "tracking (status/notes) will NOT survive a redeploy. See "
            "README.md for setup."
        )
        _warned_unconfigured = True
    return False


def _headers(key):
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def get_all_tracking() -> dict:
    """Returns {job_url: {status, date_applied, notes}} for every job ever
    tracked. Returns {} (never raises) if unconfigured or unreachable."""
    if not is_configured():
        return {}
    url, key = _config()
    try:
        resp = requests.get(
            f"{url}/rest/v1/job_tracking",
            headers=_headers(key),
            params={"select": "job_url,status,date_applied,notes"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return {row["job_url"]: row for row in resp.json()}
    except requests.RequestException as e:
        logger.error("Supabase: failed to fetch tracking data: %s", e)
        return {}
    except ValueError as e:
        logger.error("Supabase: invalid tracking response: %s", e)
        return {}


def upsert_tracking(job_url: str, status=None, date_applied=None, notes=None):
    """Writes through a tracking change. Best-effort: logs and returns on
    failure rather than raising, so a Supabase outage never breaks the
    apply/status-update flow the user is actively using."""
    if not is_configured() or not job_url:
        return
    url, key = _config()
    payload = {"job_url": job_url}
    if status is not None:
        payload["status"] = status
    if date_applied is not None:
        payload["date_applied"] = date_applied
    if notes is not None:
        payload["notes"] = notes

    try:
        resp = requests.post(
            f"{url}/rest/v1/job_tracking",
            headers={**_headers(key), "Prefer": "resolution=merge-duplicates,return=minimal"},
            params={"on_conflict": "job_url"},
            json=[payload],
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Supabase: failed to persist tracking for %s: %s", job_url, e)


def get_veille():
    """Returns the durably-stored market veille row (dict) or None if
    unconfigured, absent, or unreachable - same durability gap as job
    tracking: the local SQLite copy is wiped on every redeploy, so this is
    what survives. See reconcile_veille() in app.py for how it's restored."""
    if not is_configured():
        return None
    url, key = _config()
    try:
        resp = requests.get(
            f"{url}/rest/v1/market_veille",
            headers=_headers(key),
            params={"select": "*", "id": "eq.1"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else None
    except requests.RequestException as e:
        logger.error("Supabase: failed to fetch veille: %s", e)
        return None
    except ValueError as e:
        logger.error("Supabase: invalid veille response: %s", e)
        return None


def upsert_veille(fields: dict):
    """Writes through a market veille update. Best-effort, mirrors
    upsert_tracking's failure handling. `fields` uses the same keys as
    database.save_veille (target_min/target_max/summary/grille_json/
    targets_json/sources_json)."""
    if not is_configured() or not fields:
        return
    url, key = _config()
    payload = {"id": 1, **fields}
    try:
        resp = requests.post(
            f"{url}/rest/v1/market_veille",
            headers={**_headers(key), "Prefer": "resolution=merge-duplicates,return=minimal"},
            params={"on_conflict": "id"},
            json=[payload],
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Supabase: failed to persist veille: %s", e)
