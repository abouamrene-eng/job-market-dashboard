"""Single scoring rubric (0-100) matching a job posting against Amine's
aeronautique + Product/AMOA search, per the V5 brief. Replaces the earlier
dual Path A/B scoring - there is exactly one score, one breakdown, and one
salary estimate per job now.

SCORE = Role(30%) + Sector(25%, aeronautique tops it) + Company(20%) +
        Salary(20%) + Location(5%) + Bonus(up to +10: ENAC/aero/equity)
"""
from config import AERO_COMPANIES, AERO_COMPANIES_OTHER, ENAC_KEYWORDS, NOTABLE_COMPANIES

ROLE_SCORES = [
    (["product manager"], 30),
    (["amoa"], 30),
    (["product owner"], 28),
    (["programme manager", "program manager"], 28),
    (["agile coach", "scrum master", "transformation digitale",
      "transformation numerique", "business analyst"], 15),
]

SECTOR_SCORES = [
    (["aeronautique", "aéronautique", "aerospace", "aviation", "defense", "défense"], 25),
    (["fintech"], 15),
    (["supply chain", "logistique", "logistics"], 12),
    (["tech", "saas", "software", "logiciel", "numerique", "numérique"], 10),
    (["conseil", "consulting"], 8),
]

LOCATION_REMOTE_100 = ["remote", "télétravail", "teletravail", "full remote", "100% remote"]
LOCATION_HYBRIDE = ["hybride", "hybrid", "mixte"]
LOCATION_PARIS = ["paris", "ile-de-france", "île-de-france", "idf"]
LOCATION_TOULOUSE = ["toulouse"]

EQUITY_KEYWORDS = ["equity", "actions gratuites", "bspce", "stock-options", "stock options"]


def _text_blob(job: dict) -> str:
    return f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()


def _tiered(blob: str, tiers: list) -> int:
    for keywords, points in tiers:
        if any(kw in blob for kw in keywords):
            return points
    return 0


def detect_is_aeronautique(job: dict) -> bool:
    company = (job.get("company") or "").lower()
    if any(name in company for name in AERO_COMPANIES) or any(name in company for name in AERO_COMPANIES_OTHER):
        return True
    blob = f"{(job.get('sector') or '').lower()} {_text_blob(job)}"
    return any(kw in blob for kw in SECTOR_SCORES[0][0])


def detect_enac_mentioned(job: dict) -> bool:
    blob = _text_blob(job)
    return any(kw in blob for kw in ENAC_KEYWORDS)


def detect_company_type(job: dict) -> str:
    company = (job.get("company") or "").lower()
    if (any(name in company for name in AERO_COMPANIES)
            or any(name in company for name in AERO_COMPANIES_OTHER)
            or any(name in company for name in NOTABLE_COMPANIES["cac40_fortune500_gafam"])):
        return "BigCo"
    blob = f"{company} {_text_blob(job)}"
    if "scale-up" in blob or "scaleup" in blob:
        return "Scale-up"
    if "startup" in blob or "start-up" in blob:
        return "Startup"
    return "Autre"


def score_role(job: dict) -> float:
    return _tiered(_text_blob(job), ROLE_SCORES)


def score_sector(job: dict) -> float:
    blob = f"{(job.get('sector') or '').lower()} {_text_blob(job)}"
    return _tiered(blob, SECTOR_SCORES)


def score_company(job: dict) -> float:
    company = (job.get("company") or "").lower()
    for name, points in AERO_COMPANIES.items():
        if name in company:
            return points
    if any(name in company for name in AERO_COMPANIES_OTHER):
        return 17
    if any(name in company for name in NOTABLE_COMPANIES["cac40_fortune500_gafam"]):
        return 15
    company_type = detect_company_type(job)
    if company_type == "Scale-up":
        return 12
    if company_type == "Startup":
        return 10
    return 8


def score_salary(job: dict) -> float:
    reference = job.get("salary_max") or job.get("salary_min") or 0
    if reference >= 110000:
        return 20
    if reference >= 100000:
        return 18
    if reference >= 90000:
        return 15
    if reference >= 85000:
        return 10
    if reference >= 75000:
        return 5
    return 0


def score_location(job: dict) -> float:
    location = (job.get("location") or "").lower()
    if any(kw in location for kw in LOCATION_REMOTE_100):
        return 5
    if any(kw in location for kw in LOCATION_HYBRIDE):
        return 4
    if any(kw in location for kw in LOCATION_PARIS) or any(kw in location for kw in LOCATION_TOULOUSE):
        return 3
    return 0


def score_bonus(job: dict) -> float:
    bonus = 0
    if detect_enac_mentioned(job):
        bonus += 5
    if detect_is_aeronautique(job):
        bonus += 5
    if any(kw in _text_blob(job) for kw in EQUITY_KEYWORDS):
        bonus += 3
    return min(bonus, 10)


def score_job(job: dict) -> dict:
    s_role = score_role(job)
    s_sector = score_sector(job)
    s_company = score_company(job)
    s_salary = score_salary(job)
    s_location = score_location(job)
    s_bonus = score_bonus(job)

    total = s_role + s_sector + s_company + s_salary + s_location + s_bonus
    total = max(0, min(100, round(total, 1)))

    return {
        "score": total,
        # Field names kept from the pre-V5 schema (score_job_match/score_sector/
        # score_notoriety/score_salary/score_location/score_bonus) so the DB
        # columns and the existing "Détail du score" UI don't need renaming -
        # only what feeds each field changed.
        "score_job_match": s_role,
        "score_sector": s_sector,
        "score_notoriety": s_company,
        "score_salary": s_salary,
        "score_location": s_location,
        "score_bonus": s_bonus,
        "is_aeronautique": detect_is_aeronautique(job),
        "enac_mentioned": detect_enac_mentioned(job),
        "company_type": detect_company_type(job),
    }


def estimate_salary(job: dict = None) -> dict:
    """Amine's personalized 'what you can actually ask for' range - based on
    HIS profile (ENAC, 3 years Product/AMOA @ SNCF, aero specialism), not a
    generic average of scraped postings. Nudged up for aeronautique-fit and
    BigCo postings, which pay better on his specific background."""
    base = 60000
    reasons = ["Diplôme ENAC (+5 000 €)", "3 ans d'expérience Product/AMOA (+15 000 €)",
               "Expérience GMAO à grande échelle (+10 000 €)"]
    base += 5000 + 15000 + 10000

    is_aero = bool(job) and detect_is_aeronautique(job)
    if is_aero:
        base += 10000
        reasons.append("Spécialiste aéronautique (+10 000 €)")

    is_bigco = bool(job) and detect_company_type(job) == "BigCo"
    if is_bigco:
        base += 15000
        reasons.append("Grille grand groupe (+15 000 €)")

    return {
        "min": base - 5000,
        "max": base + 5000,
        "reasons": reasons,
    }
