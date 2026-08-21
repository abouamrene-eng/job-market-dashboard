"""Adapts Amine's CV to a given job posting and renders it as a 1-page PDF.

The headline title, executive summary and highlighted achievements switch
based on keywords found in the job title/description (see ROLE_PROFILES
below); experiences are reordered by relevance and their bullet points are
trimmed so the most relevant one keeps the most detail while older/less
relevant roles stay compact - the whole document is built to fit one page.
Matched job keywords are bolded inline for ATS/human skimmability.
"""
import os
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate

from config import CANDIDATE, EXPORT_DIR

NAVY = colors.HexColor("#1a365d")
GREY = colors.HexColor("#555555")

# Reportlab's built-in fonts don't include Calibri/Arial TTFs; Helvetica is
# the closest built-in metric-compatible substitute for Arial.
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

ROLE_PROFILES = [
    {
        "match": ["aeronautique", "aéronautique", "aerospace", "defense", "défense", "aviation"],
        "title": "Senior Product Owner | ENAC | Aerospace & Defense",
        "summary": (
            "Ingenieur ENAC avec 3 ans d'experience en pilotage de solutions digitales "
            "complexes (7 000 utilisateurs). Background technique unique en systemes "
            "critiques (avionique, C/C++) combine a une expertise Product Management et "
            "transformation agile (SAFe, PSPO I) - une combinaison rare pour piloter des "
            "initiatives digitales dans un secteur exigeant en surete de fonctionnement."
        ),
    },
    {
        "match": ["product owner"],
        "title": "Senior Product Owner | SAFe & PSPO I Certified",
        "summary": (
            "Product Owner avec 3 ans d'experience en pilotage de solutions digitales "
            "complexes a l'echelle entreprise (7 000 utilisateurs, 3 000 sites). Expert en "
            "vision produit, redaction de user stories et pilotage agile SAFe/SCRUM. "
            "Certifie PSPO I. Ingenieur ENAC avec background technique (C/C++, Python)."
        ),
    },
    {
        "match": ["amoa", "programme manager", "program manager"],
        "title": "AMOA Consultant | Enterprise Programme Manager",
        "summary": (
            "Consultant AMOA avec 3 ans d'experience en pilotage de programmes complexes "
            "et management d'equipe AMOA/MOE (10 personnes). Expert en conduite du "
            "changement, gouvernance de la donnee et arbitrage entre besoins metiers et "
            "contraintes techniques. Certifie SAFe. Ingenieur ENAC."
        ),
    },
    {
        "match": ["agile coach", "scrum master"],
        "title": "Agile Coach | SAFe Practitioner",
        "summary": (
            "Praticien agile certifie Leading SAFe avec 3 ans d'experience en pilotage de "
            "ceremonies SCRUM/SAFe a l'echelle et management d'equipe. Expertise en coaching "
            "d'equipes produit, amelioration de la maturite agile et synchronisation de "
            "programmes (PI planning, ART). Ingenieur ENAC."
        ),
    },
    {
        "match": ["transformation"],
        "title": "Digital Transformation Consultant",
        "summary": (
            "Consultant en transformation digitale avec 3 ans d'experience en pilotage "
            "d'une solution GMAO deployee a l'echelle nationale (7 000 utilisateurs). Expert "
            "en conduite du changement, optimisation de processus et gestion de la donnee. "
            "Certifie SAFe & PSPO I. Ingenieur ENAC."
        ),
    },
]
DEFAULT_PROFILE = {
    "title": CANDIDATE["title_default"],
    "summary": CANDIDATE["profile_summary_default"],
}

CV_KEYWORD_POOL = [
    "product owner", "amoa", "programme manager", "program manager",
    "agile coach", "scrum master", "product manager", "business analyst",
    "transformation", "safe", "scrum", "gmao", "change management",
    "conduite du changement", "vision produit", "user story", "backlog",
    "kpi", "reporting", "leadership", "data", "donnees", "etl",
    "aeronautique", "aéronautique", "defense", "défense", "agile",
]


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")
    return text or "Company"


def _job_blob(job: dict) -> str:
    return f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()


def _matched_keywords(blob: str) -> list:
    return [kw for kw in CV_KEYWORD_POOL if kw in blob]


def _bold_matches(text: str, keywords: list) -> str:
    kws = sorted({k for k in keywords if k}, key=len, reverse=True)
    if not kws:
        return text
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in kws) + r")\b", re.IGNORECASE)
    return pattern.sub(r"<b>\1</b>", text)


def _pick_profile(blob: str) -> dict:
    for profile in ROLE_PROFILES:
        if any(kw in blob for kw in profile["match"]):
            return profile
    return DEFAULT_PROFILE


def _rank_experiences(blob: str) -> list:
    scored = []
    for exp in CANDIDATE["experiences"]:
        overlap = sum(1 for kw in exp["keywords"] if kw in blob)
        scored.append((overlap, exp))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [exp for _, exp in scored]


def _select_bullets(exp: dict, blob: str, max_bullets: int) -> list:
    scored = []
    for i, bullet in enumerate(exp["highlights"]):
        score = sum(1 for kw in CV_KEYWORD_POOL if kw in blob and kw in bullet.lower())
        scored.append((score, i, bullet))
    scored.sort(key=lambda item: (-item[0], item[1]))
    kept = sorted(scored[:max_bullets], key=lambda item: item[1])
    return [b for _, _, b in kept]


def generate_cv(job: dict) -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    blob = _job_blob(job)
    profile = _pick_profile(blob)
    matched_keywords = _matched_keywords(blob)
    ranked_experiences = _rank_experiences(blob)
    bullet_budget = [5, 3, 2]  # most relevant experience keeps more detail

    filename = f"CV_Amine_{_slugify(job.get('company', 'Company'))}.pdf"
    path = os.path.join(EXPORT_DIR, filename)

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=styles["Normal"], fontName=FONT_BOLD,
                                 fontSize=17, textColor=NAVY, leading=20)
    title_style = ParagraphStyle("RoleTitle", parent=styles["Normal"], fontName=FONT_BOLD,
                                  fontSize=10.5, textColor=colors.HexColor("#2f855a"), leading=13)
    contact_line_style = ParagraphStyle("ContactLine", parent=styles["Normal"], fontName=FONT,
                                         fontSize=8.5, textColor=GREY, spaceAfter=3)
    section_style = ParagraphStyle("Section", parent=styles["Normal"], fontName=FONT_BOLD,
                                    fontSize=9.5, textColor=NAVY, spaceBefore=7, spaceAfter=3)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName=FONT,
                                 fontSize=9, leading=11.5)
    bullet_style = ParagraphStyle("Bullet", parent=body_style, leftIndent=10, spaceAfter=1.5)
    exp_title_style = ParagraphStyle("ExpTitle", parent=styles["Normal"], fontName=FONT_BOLD,
                                      fontSize=9.5, textColor=NAVY, spaceBefore=5)
    exp_meta_style = ParagraphStyle("ExpMeta", parent=styles["Normal"], fontName=FONT,
                                     fontSize=8, textColor=GREY, spaceAfter=2)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7)
        canvas.setFillColor(GREY)
        canvas.drawCentredString(A4[0] / 2, 0.4 * inch, "Page 1 of 1")
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.7 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    story = []

    story.append(Paragraph(CANDIDATE["name"], name_style))
    story.append(Paragraph(profile["title"], title_style))
    story.append(Paragraph(
        f"{CANDIDATE['email']} | {CANDIDATE['phone']} | {CANDIDATE['linkedin']}",
        contact_line_style,
    ))
    story.append(HRFlowable(width="100%", color=NAVY, thickness=1.1, spaceAfter=4))

    story.append(Paragraph("PROFIL EXECUTIF", section_style))
    story.append(Paragraph(_bold_matches(profile["summary"], matched_keywords), body_style))

    story.append(Paragraph("EXPERIENCE PROFESSIONNELLE", section_style))
    for i, exp in enumerate(ranked_experiences):
        budget = bullet_budget[i] if i < len(bullet_budget) else 2
        bullets = _select_bullets(exp, blob, budget)
        context = f" - {exp['context']}" if exp.get("context") else ""
        story.append(Paragraph(f"{exp['title']} - {exp['company']}", exp_title_style))
        story.append(Paragraph(f"{exp['duration']}{context}", exp_meta_style))
        for b in bullets:
            story.append(Paragraph(f"&bull; {_bold_matches(b, matched_keywords)}", bullet_style))

    story.append(Paragraph("COMPETENCES", section_style))
    matched_categories = set()
    for cat, items in CANDIDATE["skill_categories"].items():
        items_blob = " ".join(items).lower()
        if any(kw in items_blob and kw in blob for kw in CV_KEYWORD_POOL):
            matched_categories.add(cat)
    ordered_categories = sorted(
        CANDIDATE["skill_categories"].items(),
        key=lambda pair: pair[0] not in matched_categories,
    )
    for cat, items in ordered_categories:
        story.append(Paragraph(f"<b>{cat} :</b> {', '.join(items)}", body_style))
    story.append(Paragraph(f"<b>Savoir-etre :</b> {', '.join(CANDIDATE['soft_skills'])}", body_style))

    story.append(Paragraph("FORMATION & CERTIFICATIONS", section_style))
    for edu in CANDIDATE["education"]:
        story.append(Paragraph(
            f"<b>{edu['degree']}</b> ({edu['years']}) - {edu['detail']}. {edu['note']}.",
            body_style,
        ))
    cert_line = " | ".join(f"{c['name']} ({c['issuer']})" for c in CANDIDATE["certifications"])
    story.append(Paragraph(f"<b>Certifications :</b> {cert_line}", body_style))

    story.append(Paragraph("LANGUES", section_style))
    story.append(Paragraph(
        " | ".join(f"{lang['name']} ({lang['level']})" for lang in CANDIDATE["languages"]),
        body_style,
    ))

    story.append(Paragraph("POINTS FORTS", section_style))
    for point in CANDIDATE["differentiators"][:5]:
        story.append(Paragraph(f"&bull; {point}", bullet_style))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return path
