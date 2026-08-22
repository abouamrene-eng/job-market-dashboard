"""Generates the honest, path-specific advantages/disadvantages/advice for
a job posting, for both Path A (Product/AMOA) and Path B (Sales Engineer).

Ground rule (per the dual-path brief): never dress up a bad fit. A sales
posting gets a blunt "not aligned" Path A analysis, and a pure product/AMOA
posting gets a blunt "wrong direction" Path B analysis - the whole point of
this feature is honest signal, not encouragement.
"""
from config import NOTABLE_COMPANIES, PATH_B_TARGET_COMPANIES


def _is_bigco(company: str) -> bool:
    company = (company or "").lower()
    return any(name in company for name in NOTABLE_COMPANIES["cac40_fortune500_gafam"])


def _fmt_k(amount) -> str:
    return f"{round(amount / 1000)}k€"


def generate_path_a_analysis(job: dict, path_a: dict, path_b: dict) -> dict:
    b = path_a["breakdown"]
    company = job.get("company", "cette entreprise")
    sector = (job.get("sector") or "").lower()
    salary_ref = job.get("salary_max") or job.get("salary_min") or 0

    not_a_product_role = b["role_match"] == 0 and path_b["breakdown"]["role_match"] > 0
    if not_a_product_role:
        return {
            "advantages": ["Pas d'avantage specifique - ce n'est pas un role produit/AMOA."],
            "disadvantages": [
                f"Role {job.get('job_title', '')} oriente vente/technique, pas strategie produit.",
                "Ne developpe pas les competences de pilotage produit dont tu as besoin pour founder.",
            ],
            "advice": "Wrong career path pour l'objectif produit/founder. A ignorer pour le Path A, "
                      "sauf si tu veux uniquement observer comment la vente fonctionne de l'exterieur.",
        }

    advantages = []
    disadvantages = []

    if "aeronautique" in sector or any(kw in job.get("job_description", "").lower() for kw in ["aeronautique", "aéronautique", "aerospace"]):
        advantages.append("Secteur aéronautique = expertise sectorielle directe (atout si tu montes un projet aero plus tard).")
    if b["equity"] >= 12:
        advantages.append("Equity significative - upside réel si l'entreprise scale.")
    elif b["equity"] == 5:
        advantages.append("Equity mentionnée (montant non précisé dans l'annonce) - à clarifier en entretien.")
    if b["salary"] >= 22:
        advantages.append(f"Salaire solide ({_fmt_k(salary_ref)}) pour le marché produit/AMOA.")
    if any("startup" in d or "scale-up" in d for d in b["bonus_detail"]):
        advantages.append("Culture scale-up - décisions rapides, périmètre large pour un profil junior-senior.")
    if _is_bigco(company):
        advantages.append(f"{company} = réseau grand compte, base de contacts utile pour un futur projet entrepreneurial.")
    if not advantages:
        advantages.append("Role produit/AMOA correct, sans signal fort particulier au-dela du fit de role.")

    if _is_bigco(company) and b["equity"] == 0:
        disadvantages.append("Grand groupe sans equity - potentiel de gain plafonné au salaire fixe.")
    if b["penalty"] < 0:
        disadvantages.extend(d.lstrip("-0123456789 ") for d in b["penalty_detail"])
    if _is_bigco(company):
        disadvantages.append("Bureaucratie possible (prise de décision lente) - se donner 2-3 ans max sur ce type de poste.")
    if b["salary"] <= 18:
        disadvantages.append(f"Salaire ({_fmt_k(salary_ref)}) en dessous de ta cible 90-110k€.")
    if not disadvantages:
        disadvantages.append("Aucun signal négatif fort détecté dans l'annonce.")

    score = path_a["score"]
    if score >= 75:
        advice = ("Excellent tremplin produit/AMOA. À candidater en priorité - utilise ce poste pour "
                   "construire l'expertise et le réseau qui serviront ton projet founder d'ici 2-3 ans.")
    elif score >= 55:
        advice = ("Bon fit produit, sans être exceptionnel. À considérer si le secteur ou l'équipe te "
                   "motive particulièrement, sinon continue à chercher mieux aligné.")
    else:
        advice = ("Fit produit faible sur ce poste. Ne pas prioriser pour le Path A - garde tes candidatures "
                   "pour des rôles plus alignés avec ton objectif founder.")

    return {"advantages": advantages, "disadvantages": disadvantages, "advice": advice}


def generate_path_b_analysis(job: dict, path_a: dict, path_b: dict) -> dict:
    b = path_b["breakdown"]
    company = job.get("company", "cette entreprise")

    not_a_sales_role = b["role_match"] == 0 and path_a["breakdown"]["role_match"] > 0
    if not_a_sales_role:
        return {
            "advantages": ["Pas d'avantage specifique - ce n'est pas un role sales engineer/solutions."],
            "disadvantages": [
                f"Role {job.get('job_title', '')} oriente produit/AMOA, pas vente/revenue.",
                "N'apprend rien sur le cycle de vente, le closing ou la relation client payante.",
            ],
            "advice": "Wrong direction pour explorer le sales path. Skip cette offre pour le Path B - "
                      "cherche plutôt des intitulés Sales Engineer / Solutions Architect / Solutions Engineer.",
        }

    advantages = []
    disadvantages = []

    tier_label = b["company_tier_label"]
    if tier_label == "High-growth SaaS":
        advantages.append(f"{company} = référence du secteur pour apprendre la vente technique (le meilleur \"bootcamp\" sales du marché).")
    elif tier_label == "Scaling SaaS":
        advantages.append(f"{company} = scale-up solide, bonne exposition au revenue sans le rythme extrême d'un tier 1.")
    elif tier_label == "Enterprise SaaS":
        advantages.append(f"{company} = vente enterprise structurée, utile pour apprendre les cycles longs et les gros comptes.")

    if b["variable_amount_detected"] and b["variable_amount_detected"] > 1:
        advantages.append(f"Variable détectée jusqu'à ~{_fmt_k(b['variable_amount_detected'])} - upside financier réel dès l'année 1.")
    elif b["variable"] > 0:
        advantages.append("Part variable mentionnée (montant non précisé) - à faire chiffrer en entretien.")
    if b["learning"] >= 8:
        advantages.append("Signaux de forte culture commerciale/croissance - bon environnement d'apprentissage.")
    if b["location"] == 10:
        advantages.append("Remote/Paris - compatible avec tes side projects.")
    if not advantages:
        advantages.append("Role sales engineer/solutions correct, sans signal fort particulier au-delà du fit de rôle.")

    disadvantages.append("Année 1 = position junior sur le volet vente, malgré ton expérience produit.")
    disadvantages.append("Rémunération variable = revenu moins prévisible qu'un poste produit à salaire fixe.")
    if b["penalty"] < 0:
        disadvantages.extend(d.lstrip("-0123456789 ") for d in b["penalty_detail"])
    if not tier_label:
        disadvantages.append("Entreprise hors des tiers SaaS identifiés - culture commerciale à vérifier en entretien.")

    score = path_b["score"]
    if score >= 75:
        advice = ("C'est LE type d'offre à prendre si tu veux sérieusement tester le sales engineering. "
                   "Attends-toi à stresser sur les quotas au début, mais l'apprentissage vaut le détour.")
    elif score >= 55:
        advice = ("Vaut le détour pour explorer le sales path, sans être la meilleure option du marché. "
                   "Compare avec d'autres offres tier 1 avant de te décider.")
    else:
        advice = ("Signal faible pour valider un pivot sales sur ce poste précis - cherche une offre "
                   "avec un tier d'entreprise et une part variable plus clairs avant de te lancer.")

    return {"advantages": advantages, "disadvantages": disadvantages, "advice": advice}


def generate_recommendation(path_a: dict, path_b: dict, threshold: int = 15) -> str:
    a, b_score = path_a["score"], path_b["score"]
    diff = a - b_score
    if abs(diff) <= threshold:
        return "Poste cross-fit : score proche sur les deux paths, utile pour explorer l'un ou l'autre."
    if diff > 0:
        return f"Path A clairement meilleur pour ce poste ({a} vs {b_score})."
    return f"Path B clairement meilleur pour ce poste ({b_score} vs {a})."
