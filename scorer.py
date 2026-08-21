"""Scoring algorithm (0-100) matching a job posting against Amine's profile.

SCORE = Salary(25%) + JobMatch(30%) + Sector(15%) + Location(10%)
        + Notoriety(12%) + Bonus(8%), clamped to [0, 100].
"""
import re

from config import NOTABLE_COMPANIES

ROLE_KEYWORDS_EXACT = ["product owner", "amoa", "programme manager", "program manager"]
ROLE_KEYWORDS_HIGH = ["agile coach", "scrum master", "transformation digitale",
                       "transformation numerique", "product manager"]
ROLE_KEYWORDS_MEDIUM = ["business analyst", "chef de projet agile",
                         "consultant agile", "digital transformation"]
ROLE_KEYWORDS_LOW = ["chef de projet", "consultant", "project manager"]

SECTOR_HIGH = ["conseil", "consulting", "tech", "saas", "software", "industrie", "industry"]
SECTOR_MID = ["energie", "énergie", "energy", "utilities", "finance", "insurtech", "banque", "assurance"]

BONUS_AERO_DEFENSE = ["aeronautique", "aéronautique", "aerospace", "defense", "défense", "aviation"]


def _text_blob(job: dict) -> str:
    return f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()


def score_salary(job: dict) -> float:
    salary_max = job.get("salary_max") or job.get("salary_min") or 0
    salary_min = job.get("salary_min") or salary_max
    reference = max(salary_max, salary_min)
    if reference >= 75000:
        return 25
    if reference >= 70000:
        return 20
    if reference >= 65000:
        return 15
    if reference >= 60000:
        return 8
    return 0


def score_job_match(job: dict) -> float:
    blob = _text_blob(job)
    if any(kw in blob for kw in ROLE_KEYWORDS_EXACT):
        return 30
    if any(kw in blob for kw in ROLE_KEYWORDS_HIGH):
        return 22
    if any(kw in blob for kw in ROLE_KEYWORDS_MEDIUM):
        return 15
    if any(kw in blob for kw in ROLE_KEYWORDS_LOW):
        return 8
    return 0


def score_sector(job: dict) -> float:
    sector = (job.get("sector") or "").lower()
    blob = f"{sector} {_text_blob(job)}"
    if any(kw in blob for kw in SECTOR_HIGH):
        return 15
    if any(kw in blob for kw in SECTOR_MID):
        return 10
    return 5


def score_location(job: dict) -> float:
    location = (job.get("location") or "").lower()
    if "remote" in location or "mixte" in location or "hybride" in location:
        return 10
    if "idf" in location or "ile-de-france" in location or "île-de-france" in location or "paris" in location:
        if "flexible" in location or "possible" in location:
            return 8
        return 5
    if location.strip():
        return 3
    return 5


def score_notoriety(job: dict) -> float:
    company = (job.get("company") or "").lower()
    if any(name in company for name in NOTABLE_COMPANIES["cac40_fortune500_gafam"]):
        return 12
    if any(kw in company for kw in NOTABLE_COMPANIES["pme_scaleup"]):
        return 9
    return 5


def score_bonus(job: dict) -> float:
    blob = _text_blob(job)
    bonus = 0
    if any(kw in blob for kw in BONUS_AERO_DEFENSE):
        bonus += 3
    if any(kw in blob for kw in ["formation", "training", "certifi"]):
        bonus += 2
    if any(kw in blob for kw in ["equity", "stock-option", "bsa", "actionnariat"]):
        bonus += 2
    if any(kw in blob for kw in ["international", "anglais courant", "global"]):
        bonus += 1
    return min(bonus, 8)


def score_job(job: dict) -> dict:
    s_salary = score_salary(job)
    s_match = score_job_match(job)
    s_sector = score_sector(job)
    s_location = score_location(job)
    s_notoriety = score_notoriety(job)
    s_bonus = score_bonus(job)

    total = s_salary + s_match + s_sector + s_location + s_notoriety + s_bonus
    total = max(0, min(100, total))

    return {
        "score": round(total, 1),
        "score_salary": s_salary,
        "score_job_match": s_match,
        "score_sector": s_sector,
        "score_location": s_location,
        "score_notoriety": s_notoriety,
        "score_bonus": s_bonus,
    }
