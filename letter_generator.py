"""Generates a personalized 200-250 word cover letter (DOCX) for a job.

Structure: intro hook -> why this role (dynamic on job keywords) -> why
this company (dynamic on sector) -> closing/signature, in professional
French ("Cordialement", not "Best regards").
"""
import os
import re
import unicodedata

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from config import CANDIDATE, EXPORT_DIR

NAVY = RGBColor(0x1A, 0x36, 0x5D)

WHY_ROLE_RULES = [
    (["product owner"],
     "Votre recherche d'un Product Owner capable de piloter la vision produit et "
     "l'adoption utilisateur trouve une resonance directe avec mes 3 annees "
     "d'experience chez SNCF Gare & Connexions, ou j'ai porte cette responsabilite "
     "au quotidien."),
    (["amoa", "programme manager", "program manager"],
     "En tant que consultant AMOA, j'ai l'habitude d'orchestrer des changements "
     "complexes en coordonnant equipes MOA et MOE, ce qui correspond precisement "
     "aux enjeux de ce poste."),
    (["agile coach", "scrum master"],
     "Certifie Leading SAFe et practicien SCRUM depuis 3 ans, je suis a l'aise "
     "pour coacher des equipes produit et instaurer une culture agile durable, "
     "exactement ce que ce role requiert."),
    (["transformation"],
     "La transformation digitale que vous engagez necessite quelqu'un ayant deja "
     "affronte les enjeux reels du terrain : processus legacy, adoption par 7 000 "
     "utilisateurs et pilotage du changement a grande echelle."),
]
DEFAULT_WHY_ROLE = (
    "Mon parcours combine pilotage agile, gestion de programme et conduite du "
    "changement, des competences qui repondent directement aux enjeux de ce poste."
)

WHY_COMPANY_RULES = [
    (["conseil", "consulting"],
     "{company} represente pour moi un environnement ou piloter la transformation "
     "digitale de grands comptes devient le coeur du metier, avec la diversite de "
     "missions que je recherche."),
    (["tech", "saas", "software"],
     "Rejoindre {company} - un acteur tech en forte croissance - m'attire "
     "fortement : apres 3 ans en grande entreprise, j'aspire a des cycles de "
     "decision plus rapides et un impact produit plus direct."),
    (["industrie", "aeronautique", "aéronautique", "defense", "défense", "energie", "énergie"],
     "Ma formation d'ingenieur ENAC et mon experience GMAO/ferroviaire font de moi "
     "un candidat naturel pour {company}, ou rigueur technique et culture "
     "operationnelle sont essentielles."),
]
DEFAULT_WHY_COMPANY = (
    "{company} correspond parfaitement aux valeurs de rigueur et d'impact que je "
    "recherche pour la suite de mon parcours."
)


def _blob(job: dict) -> str:
    return f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")
    return text or "Company"


def _pick(rules, blob, default):
    for keywords, text in rules:
        if any(kw in blob for kw in keywords):
            return text
    return default


def build_letter_text(job: dict) -> dict:
    blob = _blob(job)
    company = job.get("company", "votre entreprise")
    job_title = job.get("job_title", "ce poste")

    intro = (
        f"En tant que Product Owner certifie (PSPO I, Leading SAFe) depuis 3 ans "
        f"chez SNCF Gare & Connexions, j'ai pilote la transformation digitale "
        f"d'une solution GMAO utilisee par 7 000 collaborateurs sur 3 000 gares. "
        f"Ingenieur ENAC de formation, votre opportunite de {job_title} chez "
        f"{company} m'interesse particulierement."
    )

    why_role = _pick(WHY_ROLE_RULES, blob, DEFAULT_WHY_ROLE)

    sector_blob = f"{job.get('sector', '')} {blob}"
    why_company = _pick(WHY_COMPANY_RULES, sector_blob, DEFAULT_WHY_COMPANY).format(company=company)

    closing = (
        "Je serais ravi de discuter de la maniere dont mon experience en pilotage "
        "produit, mon leadership AMOA/MOE et mes certifications agiles peuvent "
        "s'aligner avec vos enjeux strategiques. Je reste disponible pour un "
        "entretien a votre convenance."
    )

    return {"intro": intro, "why_role": why_role, "why_company": why_company, "closing": closing}


def generate_letter(job: dict) -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    parts = build_letter_text(job)
    company = job.get("company", "Company")

    filename = f"LM_{_slugify(company)}.docx"
    path = os.path.join(EXPORT_DIR, filename)

    doc = Document()

    header = doc.add_paragraph()
    run = header.add_run(CANDIDATE["name"])
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = NAVY
    header.add_run(f"\n{CANDIDATE['email']} | {CANDIDATE['phone']}")

    doc.add_paragraph()
    date_p = doc.add_paragraph()
    date_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    from datetime import date
    date_p.add_run(f"Paris, le {date.today().strftime('%d/%m/%Y')}")

    doc.add_paragraph()
    doc.add_paragraph(f"Objet : Candidature - {job.get('job_title', '')} chez {company}")
    doc.add_paragraph()

    doc.add_paragraph("Madame, Monsieur,")
    doc.add_paragraph()
    doc.add_paragraph(parts["intro"])
    doc.add_paragraph(parts["why_role"])
    doc.add_paragraph(parts["why_company"])
    doc.add_paragraph(parts["closing"])
    doc.add_paragraph()
    doc.add_paragraph("Cordialement,")
    doc.add_paragraph(CANDIDATE["name"])

    doc.save(path)
    return path
