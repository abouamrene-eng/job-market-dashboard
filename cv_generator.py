"""Renders Amine's real CV (per cv_identity_guide.py / templates/cv_template.html)
adapted to a job posting: the role variant (AMOA / PM / Aero) is auto-detected
from the posting's title+description, and the ATS-safe single-column layout
is used since these CVs are meant for job-board applications.

Primary path: Jinja2 -> HTML -> weasyprint -> PDF. weasyprint depends on
native libraries (Pango/Cairo) that may not be present on every deploy
target; if it fails to import or to render, we fall back to the older
reportlab-based generator (role-adaptive keyword bolding, 1-page budget) so
CV generation never breaks in production.
"""
import logging
import os
import re
import unicodedata
from datetime import date

from jinja2 import Environment, FileSystemLoader

import cv_identity_guide as guide
from config import EXPORT_DIR

logger = logging.getLogger("cv_generator")

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")
    return text or "Company"


def _variant_experiences(variant: str) -> list:
    return [exp for exp in guide.EXPERIENCES if exp["variant"] in (None, variant)]


def render_cv_html(job: dict, mode: str = "ats", variant: str = None) -> str:
    variant = variant or guide.detect_variant(job)
    template = _env.get_template("cv_template.html")
    return template.render(
        mode=mode,
        variant=variant,
        c=guide.CONTACT,
        v=guide.VARIANTS[variant],
        sidebar=guide.SIDEBAR,
        impact=guide.IMPACT,
        experiences=_variant_experiences(variant),
        formation=guide.FORMATION,
        projects_aero=guide.PROJECTS_AERO,
    )


def _variant_label(variant: str) -> str:
    return {"amoa": "AMOA", "pm": "Product_Owner", "aero": "Aero"}.get(variant, variant.upper())


def _cv_filename(job: dict, variant: str) -> str:
    month = date.today().strftime("%Y-%m")
    company = _slugify(job.get("company", "Company"))
    return f"CV_Amine_Bouamrene_{_variant_label(variant)}_{company}_{month}.pdf"


def generate_cv(job: dict, mode: str = "ats") -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    variant = guide.detect_variant(job)
    path = os.path.join(EXPORT_DIR, _cv_filename(job, variant))

    try:
        from weasyprint import HTML
        html = render_cv_html(job, mode=mode, variant=variant)
        HTML(string=html, base_url=TEMPLATE_DIR).write_pdf(path)
        return path
    except Exception as e:
        # Falling back silently would mean a broken weasyprint install goes
        # unnoticed forever - log the real cause so it shows up in the
        # deploy's logs instead of just "CV looks different than expected".
        logger.error("weasyprint failed, falling back to reportlab CV: %s", e, exc_info=True)
        return _generate_cv_legacy(job, path)


# ---------------------------------------------------------------------------
# Legacy fallback (reportlab) — used only if weasyprint is unavailable or
# fails to render (e.g. missing native Pango/Cairo libs on the host). Keeps
# the same role-detection so the fallback CV still targets the right variant,
# with inline bolding of the job's own keywords for ATS/human skimmability.
# ---------------------------------------------------------------------------
CV_KEYWORD_POOL = [
    "product owner", "amoa", "programme manager", "program manager",
    "agile coach", "scrum master", "product manager", "business analyst",
    "transformation", "safe", "scrum", "gmao", "change management",
    "conduite du changement", "vision produit", "user story", "backlog",
    "kpi", "reporting", "leadership", "data", "donnees", "etl",
    "aeronautique", "aéronautique", "defense", "défense", "agile",
]


def _bold_matches(text: str, blob: str) -> str:
    kws = sorted({k for k in CV_KEYWORD_POOL if k in blob}, key=len, reverse=True)
    if not kws:
        return text
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in kws) + r")\b", re.IGNORECASE)
    return pattern.sub(r"<b>\1</b>", text)


def _generate_cv_legacy(job: dict, path: str) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (HRFlowable, ListFlowable, ListItem, Paragraph,
                                     SimpleDocTemplate)

    NAVY = colors.HexColor("#150D49")
    ACCENT = colors.HexColor("#2B2270")

    blob = f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()
    variant = guide.detect_variant(job)
    v = guide.VARIANTS[variant]
    experiences = _variant_experiences(variant)

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=styles["Title"], textColor=NAVY, fontSize=20, spaceAfter=2)
    title_style = ParagraphStyle("RoleTitle", parent=styles["Normal"], textColor=ACCENT, fontSize=12, spaceAfter=10)
    contact_style = ParagraphStyle("Contact", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], textColor=NAVY, spaceBefore=12, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    exp_title_style = ParagraphStyle("ExpTitle", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#141414"), spaceBefore=8, fontName="Helvetica-Bold")
    exp_meta_style = ParagraphStyle("ExpMeta", parent=styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=4)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=18 * mm, bottomMargin=15 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)
    story = []

    story.append(Paragraph(guide.CONTACT["name"], name_style))
    story.append(Paragraph(v["headline"], title_style))
    story.append(Paragraph(
        f"{guide.CONTACT['email']} | {guide.CONTACT['phone']} | {guide.CONTACT['linkedin']} | {guide.CONTACT['city']}",
        contact_style,
    ))
    story.append(HRFlowable(width="100%", color=NAVY, thickness=1, spaceBefore=6, spaceAfter=8))

    story.append(Paragraph("Profil", section_style))
    story.append(Paragraph(_bold_matches(v["profile"], blob), body_style))

    story.append(Paragraph("Compétences", section_style))
    story.append(Paragraph(" | ".join(v["competences"]), body_style))

    story.append(Paragraph("Expérience professionnelle", section_style))
    for exp in experiences:
        story.append(Paragraph(f"{exp['title']} - {re.sub('<[^<]+?>', '', exp['company'])}", exp_title_style))
        story.append(Paragraph(f"{exp['date']} · {exp['location']}", exp_meta_style))
        for group in exp["groups"]:
            bullets = group["bullets"]
            story.append(ListFlowable(
                [ListItem(Paragraph(_bold_matches(b, blob), body_style)) for b in bullets],
                bulletType="bullet",
            ))

    story.append(Paragraph("Formation", section_style))
    for f in guide.FORMATION:
        story.append(Paragraph(f"<b>{f['title']}</b> ({f['date']}) - {f['company']}", body_style))

    story.append(Paragraph("Certifications", section_style))
    story.append(Paragraph(" | ".join(guide.SIDEBAR["certifications"]), body_style))

    story.append(Paragraph("Langues", section_style))
    story.append(Paragraph(" | ".join(guide.SIDEBAR["langues"]), body_style))

    doc.build(story)
    return path
