"""Adapts Amine's CV to a given job posting and renders it as a PDF.

The headline title and highlighted achievements switch based on keywords
found in the job title/description (see ROLE_PROFILES below), experiences
are reordered by relevance to the posting, and a short summary paragraph
naturally works in a few of the posting's own keywords for ATS matching.
"""
import os
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, ListFlowable, ListItem, Paragraph,
                                 SimpleDocTemplate, Spacer)

from config import CANDIDATE, EXPORT_DIR

NAVY = colors.HexColor("#1a365d")
GREEN = colors.HexColor("#2f855a")

ROLE_PROFILES = [
    {
        "match": ["aeronautique", "aéronautique", "aerospace", "defense", "défense", "aviation"],
        "title": "Senior Product Owner | ENAC | Aerospace & Defense",
        "highlights": ["Diplome ingenieur ENAC", "Background technique avionique/securite",
                       "Experience GMAO en environnement safety-critical"],
    },
    {
        "match": ["product owner"],
        "title": "Senior Product Owner | SAFe & PSPO I Certified",
        "highlights": ["Delivery produit pour 7 000 utilisateurs", "Vision produit et user stories",
                       "Pilotage de l'adoption utilisateur"],
    },
    {
        "match": ["amoa", "programme manager", "program manager"],
        "title": "AMOA Consultant | Enterprise Programme Manager",
        "highlights": ["Management d'une equipe de 10 personnes", "Conduite du changement",
                       "Qualite et gouvernance de la donnee"],
    },
    {
        "match": ["agile coach", "scrum master"],
        "title": "Agile Coach | SAFe Practitioner",
        "highlights": ["Expertise SAFe a grande echelle", "Coaching d'equipes produit",
                       "Animation des ceremonies agiles"],
    },
    {
        "match": ["transformation"],
        "title": "Digital Transformation Consultant",
        "highlights": ["Implementation GMAO a l'echelle nationale", "Optimisation de processus",
                        "Formation et adoption utilisateur"],
    },
]
DEFAULT_PROFILE = {
    "title": CANDIDATE["title_default"],
    "highlights": ["Pilotage agile SAFe/SCRUM", "Management AMOA/MOE", "Conduite du changement"],
}


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")
    return text or "Company"


def _job_blob(job: dict) -> str:
    return f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()


def _pick_profile(job: dict) -> dict:
    blob = _job_blob(job)
    for profile in ROLE_PROFILES:
        if any(kw in blob for kw in profile["match"]):
            return profile
    return DEFAULT_PROFILE


def _rank_experiences(job: dict) -> list:
    blob = _job_blob(job)
    scored = []
    for exp in CANDIDATE["experiences"]:
        overlap = sum(1 for kw in exp["keywords"] if kw in blob)
        scored.append((overlap, exp))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [exp for _, exp in scored]


def _matched_keywords(job: dict, limit=3) -> list:
    blob = _job_blob(job)
    pool = [
        "product owner", "amoa", "agile", "safe", "scrum", "transformation",
        "gmao", "programme manager", "business analyst", "data",
    ]
    found = [kw for kw in pool if kw in blob]
    return found[:limit]


def generate_cv(job: dict) -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    profile = _pick_profile(job)
    ranked_experiences = _rank_experiences(job)
    keywords = _matched_keywords(job)

    filename = f"CV_Amine_{_slugify(job.get('company', 'Company'))}.pdf"
    path = os.path.join(EXPORT_DIR, filename)

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=styles["Title"], textColor=NAVY, fontSize=22, spaceAfter=2)
    title_style = ParagraphStyle("RoleTitle", parent=styles["Normal"], textColor=GREEN, fontSize=13, spaceAfter=10)
    contact_style = ParagraphStyle("Contact", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], textColor=NAVY, spaceBefore=12, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    exp_title_style = ParagraphStyle("ExpTitle", parent=styles["Normal"], fontSize=11, textColor=NAVY, spaceBefore=8, fontName="Helvetica-Bold")
    exp_meta_style = ParagraphStyle("ExpMeta", parent=styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=4)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=18 * mm, bottomMargin=15 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)
    story = []

    story.append(Paragraph(CANDIDATE["name"], name_style))
    story.append(Paragraph(profile["title"], title_style))
    story.append(Paragraph(
        f"{CANDIDATE['email']} | {CANDIDATE['phone']} | {CANDIDATE['age']} ans",
        contact_style,
    ))
    story.append(HRFlowable(width="100%", color=NAVY, thickness=1, spaceBefore=6, spaceAfter=8))

    summary = (
        f"Candidat pour le poste de {job.get('job_title', 'ce poste')} chez "
        f"{job.get('company', '')}. " +
        (f"Expertise directement alignee sur : {', '.join(keywords)}. " if keywords else "") +
        "Ingenieur ENAC avec 3 ans d'experience en pilotage produit et AMOA/MOE "
        "sur des programmes a fort volume d'utilisateurs."
    )
    story.append(Paragraph(summary, body_style))

    story.append(Paragraph("Points forts pour ce poste", section_style))
    story.append(ListFlowable(
        [ListItem(Paragraph(h, body_style)) for h in profile["highlights"]],
        bulletType="bullet",
    ))

    story.append(Paragraph("Experience professionnelle", section_style))
    for exp in ranked_experiences:
        story.append(Paragraph(f"{exp['title']} - {exp['company']}", exp_title_style))
        story.append(Paragraph(exp["duration"], exp_meta_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(h, body_style)) for h in exp["highlights"]],
            bulletType="bullet",
        ))

    story.append(Paragraph("Formation", section_style))
    for edu in CANDIDATE["education"]:
        story.append(Paragraph(f"<b>{edu['degree']}</b> ({edu['years']}) - {edu['detail']}", body_style))

    story.append(Paragraph("Certifications", section_style))
    story.append(Paragraph(" | ".join(CANDIDATE["certifications"]), body_style))

    story.append(Paragraph("Competences cles", section_style))
    story.append(Paragraph(" | ".join(CANDIDATE["key_skills"]), body_style))

    story.append(Paragraph("Competences techniques", section_style))
    for category, items in CANDIDATE["technical_skills"].items():
        story.append(Paragraph(f"<b>{category} :</b> {', '.join(items)}", body_style))

    story.append(Paragraph("Langues", section_style))
    story.append(Paragraph(
        " | ".join(f"{lang['name']} ({lang['level']})" for lang in CANDIDATE["languages"]),
        body_style,
    ))

    doc.build(story)
    return path
