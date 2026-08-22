"""Dual career-path scoring: Path A (Product/AMOA - secure, founder
potential) vs Path B (Sales Engineer/Solutions Architect - higher ceiling,
variable comp). Independent from scorer.py's single `score` field (which
stays as-is and keeps driving the existing feed/sort/stats) - these are
additive fields for the V3 path-comparison features.

Both scores are heuristic and best-effort, same spirit as the rest of this
codebase's keyword-based scoring: real postings rarely state equity or
variable-comp numbers explicitly, so those signals are extracted from
free text with conservative fallbacks (0 points, never guessed-positive).
"""
import re

from config import PATH_B_TARGET_COMPANIES

# ---------------------------------------------------------------------------
# Path A - Product / AMOA
# ---------------------------------------------------------------------------
PATH_A_ROLE_TIERS = [
    (["product manager", "product owner"], 30),
    (["amoa", "programme manager", "program manager", "transformation manager",
      "transformation digitale", "chef de projet transformation"], 30),
    (["innovation lead", "responsable innovation", "innovation manager"], 20),
    (["strategy", "stratégie", "strategie"], 15),
]
PATH_A_SECTOR_TIERS = [
    (["aeronautique", "aéronautique", "aerospace", "aviation"], 20),
    (["fintech"], 18),
    (["supply chain", "logistique", "logistics"], 17),
    (["tech", "saas", "software", "logiciel", "numerique", "numérique"], 15),
]
PATH_A_SALARY_TIERS = [(110000, 25), (100000, 24), (90000, 22), (85000, 18)]
PATH_A_EQUITY_TIERS = [(0.5, 15), (0.3, 12), (0.0, 5)]  # last tier = "mentioned, no %"
PATH_A_LOCATION_PARIS_REMOTE = ["paris", "remote", "télétravail", "teletravail", "full remote"]
PATH_A_LOCATION_EU = ["europe", "eu", "hybride", "hybrid"]

STARTUP_KEYWORDS = ["scale-up", "scaleup", "startup", "hypercroissance", "forte croissance"]
AERO_KEYWORDS = ["aeronautique", "aéronautique", "aerospace", "defense", "défense", "aviation"]
LEGACY_PENALTY_KEYWORDS = ["legacy", "maintenance corrective", "systeme historique", "système historique"]
LOW_AUTONOMY_KEYWORDS = ["peu d'autonomie", "reporting hierarchique strict", "forte hierarchie"]

# ---------------------------------------------------------------------------
# Path B - Sales Engineer / Solutions Architect
# ---------------------------------------------------------------------------
PATH_B_ROLE_TIERS = [
    (["sales engineer", "ingenieur avant-vente", "ingénieur avant-vente"], 35),
    (["solutions architect", "solution architect"], 35),
    (["solutions engineer", "solution engineer"], 30),
    (["business development engineer", "technical account manager",
      "technical business development", "technical sales", "solutions consultant"], 30),
]
PATH_B_VARIABLE_TIERS = [(40000, 25), (30000, 22), (20000, 18), (1, 10)]
PATH_B_LEARNING_STRONG = ["forte croissance", "hypercroissance", "scale-up", "scaleup",
                           "culture commerciale", "sales culture"]
COMMISSION_ONLY_KEYWORDS = ["commission uniquement", "100% commission", "sans salaire fixe",
                             "sans fixe", "1099", "independant pur", "indépendant pur"]
UNREALISTIC_QUOTA_KEYWORDS = ["quota agressif", "objectifs irrealistes", "objectifs irréalistes"]


def _blob(job: dict) -> str:
    return f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()


def _tiered(blob: str, tiers: list) -> int:
    for keywords, points in tiers:
        if any(kw in blob for kw in keywords):
            return points
    return 0


def _company_matches(company: str, names: list) -> bool:
    company = (company or "").lower()
    return any(name in company for name in names)


def _location_points(location: str) -> int:
    location = (location or "").lower()
    if any(kw in location for kw in PATH_A_LOCATION_PARIS_REMOTE):
        return 10
    if any(kw in location for kw in PATH_A_LOCATION_EU):
        return 7
    return 0


def _extract_equity_pct(blob: str):
    """Best-effort: looks for an explicit percentage near an equity keyword
    first ('0.5% equity', '0,3 % actions'); falls back to a bare equity
    mention (BSPCE, stock-options, actionnariat) with no number found."""
    pct_match = re.search(r"(\d+(?:[.,]\d+)?)\s*%\s*(?:d'|de\s+)?(?:equity|actions|capital|bspce)", blob)
    if pct_match:
        return float(pct_match.group(1).replace(",", "."))
    if re.search(r"\bequity\b|bspce|stock-?options?|actionnariat|actions gratuites", blob):
        return 0.0  # mentioned but no % found - lands in the "<0.3%" tier
    return None


def _extract_variable_comp(blob: str):
    """Best-effort: looks for an explicit amount near a variable-comp
    keyword ('30k-50k variable', 'OTE 130k', 'variable de 20 000€')."""
    amount_match = re.search(
        r"(\d{2,3})\s*k?\s*(?:€|k€)?\s*(?:-|a|à)\s*(\d{2,3})\s*k?\s*(?:€|k€)?\s*(?:de\s+)?variable",
        blob,
    )
    if amount_match:
        return int(amount_match.group(2)) * 1000
    single_match = re.search(r"variable\s*(?:de\s+)?(?:jusqu'?[aà]\s*)?(\d{2,3})\s*k", blob)
    if single_match:
        return int(single_match.group(1)) * 1000
    if re.search(r"\bote\b|\bcommission\b|\bprime[s]? sur objectifs?\b|part variable", blob):
        return 1  # mentioned, amount unknown - lands in the ">0" tier
    return None


def score_path_a(job: dict) -> dict:
    blob = _blob(job)
    company = job.get("company", "")

    role = _tiered(blob, PATH_A_ROLE_TIERS)
    sector = _tiered(f"{(job.get('sector') or '').lower()} {blob}", PATH_A_SECTOR_TIERS)

    salary_ref = job.get("salary_max") or job.get("salary_min") or 0
    salary = 0
    for threshold, points in PATH_A_SALARY_TIERS:
        if salary_ref >= threshold:
            salary = points
            break

    equity_pct = _extract_equity_pct(blob)
    equity = 0
    if equity_pct is not None:
        for threshold, points in PATH_A_EQUITY_TIERS:
            if equity_pct >= threshold:
                equity = points
                break

    location = _location_points(job.get("location", ""))

    bonus = 0
    bonus_detail = []
    if _company_matches(company, STARTUP_KEYWORDS) or any(kw in blob for kw in STARTUP_KEYWORDS):
        bonus += 5
        bonus_detail.append("+5 startup/scale-up")
    bonus += 5  # ENAC - candidate trait, always applies to the product/AMOA path
    bonus_detail.append("+5 ENAC")
    if any(kw in blob for kw in AERO_KEYWORDS):
        bonus += 3
        bonus_detail.append("+3 aéronautique")

    penalty = 0
    penalty_detail = []
    if any(kw in blob for kw in LEGACY_PENALTY_KEYWORDS):
        penalty -= 10
        penalty_detail.append("-10 systeme legacy")
    if any(kw in blob for kw in LOW_AUTONOMY_KEYWORDS):
        penalty -= 5
        penalty_detail.append("-5 peu d'autonomie")

    total = role + sector + salary + equity + location + bonus + penalty
    total = max(0, min(100, round(total)))

    return {
        "score": total,
        "breakdown": {
            "role_match": role, "role_match_max": 30,
            "sector": sector, "sector_max": 20,
            "salary": salary, "salary_max": 25,
            "equity": equity, "equity_max": 15,
            "location": location, "location_max": 10,
            "bonus": bonus, "bonus_detail": bonus_detail,
            "penalty": penalty, "penalty_detail": penalty_detail,
        },
    }


def score_path_b(job: dict) -> dict:
    blob = _blob(job)
    company = job.get("company", "")

    role = _tiered(blob, PATH_B_ROLE_TIERS)

    variable_amount = _extract_variable_comp(blob)
    variable = 0
    if variable_amount is not None:
        for threshold, points in PATH_B_VARIABLE_TIERS:
            if variable_amount >= threshold:
                variable = points
                break

    company_tier = 0
    company_tier_label = None
    if _company_matches(company, PATH_B_TARGET_COMPANIES["tier1_high_growth_saas"]):
        company_tier, company_tier_label = 20, "High-growth SaaS"
    elif _company_matches(company, PATH_B_TARGET_COMPANIES["tier2_scaling_saas"]):
        company_tier, company_tier_label = 18, "Scaling SaaS"
    elif _company_matches(company, PATH_B_TARGET_COMPANIES["tier3_enterprise_saas"]):
        company_tier, company_tier_label = 15, "Enterprise SaaS"
    elif any(kw in blob for kw in ["saas", "tech", "logiciel", "software"]):
        company_tier, company_tier_label = 10, "Other tech"

    location = _location_points(job.get("location", ""))

    learning = 3  # weak signal by default
    if company_tier_label == "High-growth SaaS":
        learning = 10
    elif any(kw in blob for kw in PATH_B_LEARNING_STRONG):
        learning = 8

    penalty = 0
    penalty_detail = []
    if any(kw in blob for kw in COMMISSION_ONLY_KEYWORDS):
        penalty -= 10
        penalty_detail.append("-10 commission pure (pas de fixe)")
    if any(kw in blob for kw in UNREALISTIC_QUOTA_KEYWORDS):
        penalty -= 10
        penalty_detail.append("-10 quota irrealiste")

    total = role + variable + company_tier + location + learning + penalty
    total = max(0, min(100, round(total)))

    return {
        "score": total,
        "breakdown": {
            "role_match": role, "role_match_max": 35,
            "variable": variable, "variable_max": 25, "variable_amount_detected": variable_amount,
            "company_tier": company_tier, "company_tier_max": 20, "company_tier_label": company_tier_label,
            "location": location, "location_max": 10,
            "learning": learning, "learning_max": 10,
            "penalty": penalty, "penalty_detail": penalty_detail,
        },
    }


def determine_primary_path(path_a_score: int, path_b_score: int, threshold: int = 15) -> str:
    """'A' or 'B' if one path clearly fits better, 'both' if within
    `threshold` points of each other (genuinely cross-fit posting)."""
    if abs(path_a_score - path_b_score) <= threshold:
        return "both"
    return "A" if path_a_score > path_b_score else "B"
