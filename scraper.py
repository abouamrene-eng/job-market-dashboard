"""Web scraping layer.

Each `scrape_<source>()` function returns a list of job dicts shaped like
the `jobs` table columns. Every scraper is wrapped in a try/except so that
a single source going down (layout change, anti-bot wall, timeout) never
takes the whole daily refresh down with it.

IMPORTANT: LinkedIn, Indeed, Glassdoor and Welcome to the Jungle actively
block automated scraping and their Terms of Service restrict it. The
functions below are written defensively (short timeouts, real User-Agent,
best-effort parsing) but are expected to return few or zero results in
most environments - that is normal, not a bug. When a live source returns
nothing, `run_daily_scrape()` tops up the feed with `generate_seed_jobs()`
so the dashboard is always usable for demoing the scoring/CV/letter flow.
For a production deployment, replace these with official job-board APIs
(e.g. France Travail / Pole Emploi API, LinkedIn Talent API) which are
reliable and ToS-compliant.
"""
import random
import re
import uuid
from datetime import date

import requests
from bs4 import BeautifulSoup

from config import SEARCH_KEYWORDS

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT = 8


def _safe_get(url, params=None):
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def scrape_indeed(keyword="Product Owner", location="France", limit=15):
    """Best-effort scrape of Indeed France search results (BeautifulSoup4)."""
    jobs = []
    html = _safe_get(
        "https://fr.indeed.com/jobs",
        params={"q": keyword, "l": location},
    )
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.job_seen_beacon") or soup.select("div.cardOutline")
        for card in cards[:limit]:
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("span.companyName")
            location_el = card.select_one("div.companyLocation")
            snippet_el = card.select_one("div.job-snippet")
            link_el = card.select_one("a")
            if not (title_el and company_el and link_el):
                continue
            href = link_el.get("href", "")
            job_url = f"https://fr.indeed.com{href}" if href.startswith("/") else href
            jobs.append({
                "id": str(uuid.uuid4()),
                "date_found": date.today().isoformat(),
                "job_title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True),
                "location": location_el.get_text(strip=True) if location_el else location,
                "sector": "",
                "salary_min": None,
                "salary_max": None,
                "job_url": job_url,
                "job_description": snippet_el.get_text(strip=True) if snippet_el else "",
                "source": "Indeed",
            })
    except Exception:
        return jobs
    return jobs


def scrape_glassdoor(keyword="Product Owner", limit=15):
    """Best-effort scrape of Glassdoor FR search results (BeautifulSoup4)."""
    jobs = []
    html = _safe_get(
        "https://www.glassdoor.fr/Emploi/france-product-owner-emplois-SRCH_IL.0,6_IN86_KO7,20.htm"
    )
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("li.react-job-listing")
        for card in cards[:limit]:
            title_el = card.select_one("a.jobLink")
            company_el = card.select_one(".jobEmpolyerName, .employerName")
            if not (title_el and company_el):
                continue
            href = title_el.get("href", "")
            job_url = f"https://www.glassdoor.fr{href}" if href.startswith("/") else href
            jobs.append({
                "id": str(uuid.uuid4()),
                "date_found": date.today().isoformat(),
                "job_title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True),
                "location": "France",
                "sector": "",
                "salary_min": None,
                "salary_max": None,
                "job_url": job_url,
                "job_description": "",
                "source": "Glassdoor",
            })
    except Exception:
        return jobs
    return jobs


def scrape_consulting_fr(limit=10):
    """Best-effort scrape of Consulting.fr job listings (BeautifulSoup4)."""
    jobs = []
    html = _safe_get("https://www.consulting.fr/emploi")
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("article") or soup.select(".job-item")
        for card in cards[:limit]:
            title_el = card.find(["h2", "h3"])
            link_el = card.find("a", href=True)
            if not (title_el and link_el):
                continue
            jobs.append({
                "id": str(uuid.uuid4()),
                "date_found": date.today().isoformat(),
                "job_title": title_el.get_text(strip=True),
                "company": "Consulting.fr",
                "location": "France",
                "sector": "Conseil",
                "salary_min": None,
                "salary_max": None,
                "job_url": link_el["href"],
                "job_description": "",
                "source": "Consulting.fr",
            })
    except Exception:
        return jobs
    return jobs


def scrape_linkedin(keyword="Product Owner", limit=15):
    """LinkedIn Jobs requires an authenticated Selenium session and is
    outside the scope of a best-effort static scraper. This stub keeps the
    interface consistent with the other sources; wire up a Selenium driver
    with your own LinkedIn session cookie if you need this source.
    """
    return []


def scrape_wttj(keyword="Product Owner", limit=15):
    """Welcome to the Jungle renders listings client-side (JS); a static
    request cannot see them. Same note as scrape_linkedin: plug in Selenium
    if you need this source live.
    """
    return []


SOURCES = [
    scrape_indeed,
    scrape_glassdoor,
    scrape_consulting_fr,
    scrape_linkedin,
    scrape_wttj,
]


# ---------------------------------------------------------------------------
# Seed / demo data - realistic French postings matching the search criteria.
# Used to top up the feed whenever live scraping returns too little (which,
# given anti-bot protections on the primary sources, is the common case).
# ---------------------------------------------------------------------------
_SEED_TEMPLATES = [
    {
        "job_title": "Product Owner - Transformation Digitale",
        "company": "Capgemini",
        "location": "Paris / Remote (mixte)",
        "sector": "Conseil",
        "salary_min": 68000, "salary_max": 78000,
        "job_description": (
            "Nous recherchons un Product Owner certifie PSPO pour piloter la "
            "vision produit d'une plateforme utilisee par des milliers "
            "d'utilisateurs. Vous animerez les ceremonies agiles SAFe/SCRUM, "
            "redigerez les user stories et piloterez la conduite du "
            "changement aupres des utilisateurs finaux."
        ),
    },
    {
        "job_title": "AMOA Consultant - Programme SAFe",
        "company": "Accenture",
        "location": "Ile-de-France (3j bureau)",
        "sector": "Conseil",
        "salary_min": 66000, "salary_max": 74000,
        "job_description": (
            "En tant qu'AMOA Consultant, vous piloterez un programme de "
            "transformation multi-equipes en environnement SAFe. Management "
            "d'une equipe AMOA/MOE, gestion de la donnee, reporting KPI."
        ),
    },
    {
        "job_title": "Senior Product Manager - SaaS B2B",
        "company": "Alan",
        "location": "Remote",
        "sector": "Tech",
        "salary_min": 70000, "salary_max": 85000,
        "job_description": (
            "Scale-up en forte croissance recherche un Product Manager pour "
            "porter la roadmap d'un produit SaaS B2B. Environnement agile, "
            "cycles courts, equity attractive."
        ),
    },
    {
        "job_title": "Agile Coach - SAFe Practitioner",
        "company": "Societe Generale",
        "location": "Paris (hybride)",
        "sector": "Finance",
        "salary_min": 65000, "salary_max": 72000,
        "job_description": (
            "Nous recherchons un Agile Coach experimente SAFe pour coacher "
            "plusieurs equipes produit, animer les ceremonies et accompagner "
            "la conduite du changement dans un contexte bancaire."
        ),
    },
    {
        "job_title": "Programme Manager - Transformation Industrielle",
        "company": "Thales",
        "location": "Toulouse / Remote partiel",
        "sector": "Industrie",
        "salary_min": 69000, "salary_max": 80000,
        "job_description": (
            "Poste de Programme Manager pour piloter la transformation "
            "digitale d'un site industriel aeronautique et defense. Un "
            "diplome ingenieur (ENAC apprecie) et une premiere experience "
            "GMAO sont un plus."
        ),
    },
    {
        "job_title": "Business Analyst - Insurtech",
        "company": "Alan Health",
        "location": "Remote",
        "sector": "Insurtech",
        "salary_min": 62000, "salary_max": 70000,
        "job_description": (
            "Business Analyst pour accompagner une equipe produit agile sur "
            "des sujets de donnees et reporting KPI dans une insurtech en "
            "croissance internationale."
        ),
    },
    {
        "job_title": "Product Owner GMAO / Maintenance",
        "company": "Veolia",
        "location": "Ile-de-France",
        "sector": "Energie",
        "salary_min": 64000, "salary_max": 71000,
        "job_description": (
            "Product Owner pour une solution GMAO deployee a l'echelle "
            "nationale. Vision produit, formation des utilisateurs, "
            "pilotage agile SCRUM."
        ),
    },
    {
        "job_title": "Consultant Transformation Digitale",
        "company": "McKinsey & Company",
        "location": "Paris",
        "sector": "Conseil",
        "salary_min": 72000, "salary_max": 90000,
        "job_description": (
            "Consultant pour accompagner de grands comptes CAC40 dans leur "
            "transformation digitale et agile a l'echelle internationale."
        ),
    },
]


def generate_seed_jobs(n=8):
    jobs = []
    today = date.today().isoformat()
    for tmpl in random.sample(_SEED_TEMPLATES, min(n, len(_SEED_TEMPLATES))):
        job = dict(tmpl)
        job["id"] = str(uuid.uuid4())
        job["date_found"] = today
        job["source"] = "Seed/Demo"
        job["job_url"] = f"https://example-jobs.local/{uuid.uuid4()}"
        jobs.append(job)
    return jobs


def run_daily_scrape(min_results=6):
    """Run every source, return the combined job list. Tops up with seed
    data when live scraping under-delivers (expected given anti-bot
    protections on most job boards)."""
    all_jobs = []
    for keyword in SEARCH_KEYWORDS:
        for source_fn in SOURCES:
            try:
                all_jobs.extend(source_fn(keyword))
            except Exception:
                continue

    if len(all_jobs) < min_results:
        all_jobs.extend(generate_seed_jobs(min_results))

    # Deduplicate by job_url within this batch.
    seen = set()
    deduped = []
    for job in all_jobs:
        if job["job_url"] in seen:
            continue
        seen.add(job["job_url"])
        deduped.append(job)
    return deduped
