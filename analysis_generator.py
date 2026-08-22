"""Generates the advantages/disadvantages/advice for a job posting against
Amine's single aeronautique + Product/AMOA search (V5 - replaces the
earlier dual Path A/B analysis, which is gone along with the comparison
and career-advisor views).
"""
from config import NOTABLE_COMPANIES


def _is_bigco(company: str) -> bool:
    company = (company or "").lower()
    return any(name in company for name in NOTABLE_COMPANIES["cac40_fortune500_gafam"])


def _fmt_k(amount) -> str:
    return f"{round(amount / 1000)}k€"


def generate_analysis(job: dict, score_result: dict) -> dict:
    company = job.get("company", "cette entreprise")
    salary_ref = job.get("salary_max") or job.get("salary_min") or 0

    advantages = []
    disadvantages = []

    if score_result["is_aeronautique"]:
        advantages.append(f"{company} = secteur aéronautique, ta cible prioritaire et ton domaine d'expertise (ENAC).")
    if score_result["enac_mentioned"]:
        advantages.append("L'annonce mentionne l'ENAC ou une formation équivalente - signal fort que ton profil est recherché.")
    if score_result["score_salary"] >= 15:
        advantages.append(f"Salaire affiché ({_fmt_k(salary_ref)}) proche de ta cible réelle (95-110k€).")
    if score_result["company_type"] == "BigCo":
        advantages.append(f"{company} = grand groupe, réseau et référence solides pour la suite de ton parcours.")
    elif score_result["company_type"] == "Scale-up":
        advantages.append("Scale-up - décisions rapides, périmètre large pour un profil junior-senior.")
    if score_result["score_job_match"] >= 28:
        advantages.append("Intitulé de poste très proche de ton expérience (Product Owner / AMOA).")
    if not advantages:
        advantages.append("Aucun signal fort particulier au-delà du fit de rôle de base.")

    if score_result["score_salary"] <= 5:
        disadvantages.append(f"Salaire affiché ({_fmt_k(salary_ref)}) nettement en dessous de ta cible (95-110k€).")
    if not score_result["is_aeronautique"]:
        disadvantages.append("Hors secteur aéronautique - moins directement utile pour ton positionnement de spécialiste.")
    if score_result["company_type"] == "BigCo":
        disadvantages.append("Grand groupe - bureaucratie et décisions lentes possibles, se donner 2-3 ans max sur ce type de poste.")
    if score_result["score_job_match"] == 0:
        disadvantages.append("Intitulé de poste éloigné de Product/AMOA - vérifier le contenu réel de la mission avant de candidater.")
    if not disadvantages:
        disadvantages.append("Aucun signal négatif fort détecté dans l'annonce.")

    score = score_result["score"]
    if score >= 75:
        advice = (f"Excellent fit. À candidater en priorité - {company} coche l'essentiel de tes critères "
                   f"(rôle, {'secteur aéronautique, ' if score_result['is_aeronautique'] else ''}salaire).")
    elif score >= 55:
        advice = ("Bon fit sans être exceptionnel. À considérer, surtout si le secteur ou l'équipe te "
                   "motive particulièrement - sinon continue à chercher mieux aligné.")
    else:
        advice = ("Fit faible sur ce poste. Ne pas prioriser - garde tes candidatures pour des rôles "
                   "plus alignés avec ta cible aéronautique et salariale.")

    return {"advantages": advantages, "disadvantages": disadvantages, "advice": advice}
