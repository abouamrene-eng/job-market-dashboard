"""Web scraping layer.

Each `scrape_<source>()` function returns a list of job dicts shaped like
the `jobs` table columns. Every scraper is wrapped in retry + error
handling so a single source going down (layout change, anti-bot wall,
timeout, rate limit) never takes the whole daily refresh down with it -
`run_daily_scrape()` moves on to the next source and keeps whatever the
others found.

PRIMARY SOURCE: France Travail (the official French public employment
service, formerly Pole Emploi) exposes a free, ToS-compliant search API
that aggregates real live postings from across the French market -
including many relayed from private job boards. This is the reliable,
high-volume source (see scrape_france_travail below); it needs a free
client_id/client_secret from https://francetravail.io/inscription set as
the FRANCE_TRAVAIL_CLIENT_ID / FRANCE_TRAVAIL_CLIENT_SECRET environment
variables. Without them it's skipped (logged once), not an error.

SECONDARY: LinkedIn, Indeed, Glassdoor and Welcome to the Jungle actively
block automated scraping and their Terms of Service restrict it. The
functions below are written defensively (short timeouts, retries, a real
User-Agent, best-effort parsing) but are expected to return few or zero
results in most environments - that is normal, not a bug: it's exactly
the "N/9 sources ok" case this module is built to degrade into gracefully.
When live sources under-deliver, `run_daily_scrape()` tops up the feed
with `generate_seed_jobs()` so the dashboard stays usable for demoing the
scoring/CV/letter flow - those demo postings link out to a live Google
search for the role instead of a dead URL.
"""
import logging
import os
import random
import re
import time
import unicodedata
import urllib.parse
import uuid
from datetime import date

import requests
from bs4 import BeautifulSoup

from config import SEARCH_KEYWORDS

logger = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 30       # seconds, per HTTP request
SOURCE_TIMEOUT_BUDGET = 120  # seconds, soft budget per source (see _within_budget)
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds: 2, 4, 8

ALLOWED_SOURCES = {
    "France Travail", "Indeed", "LinkedIn", "WTTJ", "Glassdoor", "Consulting.fr",
    "RegionsJob", "StepStone", "Talent.com", "Jooble", "Seed/Demo",
}


def _sleep_backoff(attempt):
    delay = BACKOFF_BASE ** attempt
    time.sleep(delay)


def _request_with_retry(url, params=None, max_retries=MAX_RETRIES):
    """GET with retry/backoff. Returns response text, or None if the
    source should be skipped (rate-limited past budget, server error,
    connection failure) - never raises."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        except requests.Timeout:
            logger.warning("timeout on %s (attempt %d/%d)", url, attempt, max_retries)
            if attempt < max_retries:
                _sleep_backoff(attempt)
            continue
        except requests.RequestException as e:
            logger.error("connection error on %s: %s", url, e)
            return None

        if resp.status_code == 200:
            return resp.text
        if resp.status_code in (403, 429):
            logger.warning("rate limited (%d) on %s (attempt %d/%d)",
                            resp.status_code, url, attempt, max_retries)
            if attempt < max_retries:
                _sleep_backoff(attempt)
            continue
        if resp.status_code in (404, 500, 502, 503):
            logger.warning("server error %d on %s - skipping source", resp.status_code, url)
            return None
        logger.warning("unexpected status %d on %s - skipping source", resp.status_code, url)
        return None

    logger.error("max retries exceeded for %s", url)
    return None


def _demo_search_url(job_title: str, company: str) -> str:
    """A real, working link for seed/demo postings (no official URL exists)
    instead of a dead placeholder - a live search for the role."""
    query = urllib.parse.quote_plus(f"{job_title} {company} offre d'emploi")
    return f"https://www.google.com/search?q={query}"


def _normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def validate_job(job: dict):
    """Returns (True, None) if the job is well-formed enough to store, or
    (False, reason) otherwise. A job without a usable URL is always
    rejected - the whole point of the "Voir l'offre" button is a live
    link, never a dead one."""
    title = (job.get("job_title") or "").strip()
    company = (job.get("company") or "").strip()
    url = (job.get("job_url") or "").strip()
    source = job.get("source")

    if len(title) < 5:
        return False, "job_title too short"
    if len(company) < 2:
        return False, "company too short"
    if not url:
        return False, "missing job_url"
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False, "invalid job_url"
    if source not in ALLOWED_SOURCES:
        return False, f"unknown source: {source}"

    salary_min, salary_max = job.get("salary_min"), job.get("salary_max")
    if salary_min is not None and salary_min <= 0:
        return False, "salary_min must be positive"
    if salary_max is not None and salary_max <= 0:
        return False, "salary_max must be positive"
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        return False, "salary_min > salary_max"

    return True, None


def _clean_job(job: dict) -> dict:
    """Fills in gaps that shouldn't cause a real posting to be rejected
    (a short scraped snippet, an overlong location string) instead of
    dropping otherwise-good data."""
    job["location"] = (job.get("location") or "France")[:100]
    if len(job.get("job_description") or "") < 50:
        job["job_description"] = (
            f"{job['job_title']} chez {job['company']}, {job['location']}. "
            f"Voir l'offre complete via le lien source ({job.get('source', 'source')})."
        )
    return job


FT_TOKEN_URL = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=/partenaire"
FT_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
FT_PAGE_SIZE = 50
FT_MAX_PAGES = 3  # up to 150 offers per keyword

_ft_token_cache = {"token": None, "expires_at": 0}
_ft_warned_missing_credentials = False


def _get_france_travail_token():
    """OAuth2 client-credentials flow, with the token cached until shortly
    before it expires. Returns None (logging once) if no credentials are
    configured - callers treat that as "source unavailable", not an error.
    """
    global _ft_warned_missing_credentials
    client_id = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID")
    client_secret = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET")
    if not client_id or not client_secret:
        if not _ft_warned_missing_credentials:
            logger.info(
                "France Travail: FRANCE_TRAVAIL_CLIENT_ID/SECRET not set - "
                "skipping this source (get free credentials at francetravail.io)"
            )
            _ft_warned_missing_credentials = True
        return None

    now = time.time()
    if _ft_token_cache["token"] and now < _ft_token_cache["expires_at"]:
        return _ft_token_cache["token"]

    try:
        resp = requests.post(
            FT_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        _ft_token_cache["token"] = data["access_token"]
        _ft_token_cache["expires_at"] = now + data.get("expires_in", 1000) - 60
        return _ft_token_cache["token"]
    except requests.RequestException as e:
        logger.error("France Travail: failed to obtain OAuth token: %s", e)
        return None
    except (KeyError, ValueError) as e:
        logger.error("France Travail: unexpected token response: %s", e)
        return None


def _parse_ft_salary(salaire):
    """France Travail returns salary as free text like 'Annuel de 45000.0
    Euros a 55000.0 Euros' or 'Mensuel de 3000.0 a 3500.0 Euros'. Extracts
    the numbers and normalizes to an annual figure; returns (None, None)
    if nothing usable is present."""
    if not salaire:
        return None, None
    libelle = (salaire.get("libelle") or "")
    if not libelle:
        return None, None

    numbers = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", libelle)]
    if not numbers:
        return None, None

    low = libelle.lower()
    multiplier = 1
    if "mensuel" in low:
        multiplier = 12
    elif "horaire" in low:
        multiplier = 1607  # duree legale annuelle de reference (35h/semaine)

    if len(numbers) == 1:
        lo = hi = round(numbers[0] * multiplier)
    else:
        lo, hi = sorted(numbers[:2])
        lo, hi = round(lo * multiplier), round(hi * multiplier)

    # Source data occasionally mislabels the period (e.g. an employer
    # enters an already-annual figure but the posting is tagged
    # "Mensuel", which would multiply it by 12 into a 6-figure absurdity).
    # A number outside a plausible French salary range is more likely a
    # mislabeled period than a real offer - drop it rather than store and
    # score against a figure we know is implausible.
    if hi > 300_000 or lo < 10_000:
        return None, None
    return lo, hi


def scrape_france_travail(keyword="Product Owner", limit=None):
    """Search live postings via the official France Travail API - the
    primary, reliable, high-volume source. Paginates up to FT_MAX_PAGES
    pages of FT_PAGE_SIZE results each."""
    token = _get_france_travail_token()
    if not token:
        return []

    jobs = []
    for page in range(FT_MAX_PAGES):
        start = page * FT_PAGE_SIZE
        end = start + FT_PAGE_SIZE - 1
        try:
            resp = requests.get(
                FT_SEARCH_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"motsCles": keyword, "range": f"{start}-{end}", "sort": 1},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.error("France Travail: request failed for %r page %d: %s", keyword, page, e)
            break

        if resp.status_code == 204:
            break  # no results at all
        if resp.status_code not in (200, 206):
            logger.warning("France Travail: status %d for %r page %d", resp.status_code, keyword, page)
            break

        try:
            results = resp.json().get("resultats", [])
        except ValueError:
            logger.error("France Travail: invalid JSON for %r page %d", keyword, page)
            break

        for offer in results:
            try:
                salary_min, salary_max = _parse_ft_salary(offer.get("salaire"))
                entreprise = ((offer.get("entreprise") or {}).get("nom")
                              or "Entreprise non precisee")
                lieu = (offer.get("lieuTravail") or {}).get("libelle") or "France"
                origine = offer.get("origineOffre") or {}
                job_url = origine.get("urlOrigine") or (
                    f"https://candidat.francetravail.fr/offres/recherche/detail/{offer.get('id', '')}"
                )
                jobs.append({
                    "id": str(uuid.uuid4()),
                    "date_found": date.today().isoformat(),
                    "job_title": offer.get("intitule", ""),
                    "company": entreprise,
                    "location": lieu,
                    "sector": offer.get("secteurActiviteLibelle") or "",
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "job_url": job_url,
                    "job_description": offer.get("description", ""),
                    "source": "France Travail",
                })
            except Exception as e:
                logger.warning("France Travail: failed to parse one offer: %s", e)

        if len(results) < FT_PAGE_SIZE:
            break  # last page reached
        time.sleep(0.3)

    return jobs


def scrape_indeed(keyword="Product Owner", location="France", limit=15):
    """Best-effort scrape of Indeed France search results (BeautifulSoup4)."""
    jobs = []
    html = _request_with_retry("https://fr.indeed.com/jobs", params={"q": keyword, "l": location})
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.job_seen_beacon") or soup.select("div.cardOutline")
        for card in cards[:limit]:
            try:
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
            except Exception as e:
                logger.warning("Indeed: failed to parse one card: %s", e)
    except Exception as e:
        logger.error("Indeed: parse error: %s", e)
    return jobs


def scrape_glassdoor(keyword="Product Owner", limit=15):
    """Best-effort scrape of Glassdoor FR search results (BeautifulSoup4)."""
    jobs = []
    html = _request_with_retry(
        "https://www.glassdoor.fr/Emploi/france-product-owner-emplois-SRCH_IL.0,6_IN86_KO7,20.htm"
    )
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("li.react-job-listing")
        for card in cards[:limit]:
            try:
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
            except Exception as e:
                logger.warning("Glassdoor: failed to parse one card: %s", e)
    except Exception as e:
        logger.error("Glassdoor: parse error: %s", e)
    return jobs


def scrape_consulting_fr(keyword="Product Owner", limit=10):
    """Best-effort scrape of Consulting.fr job listings (BeautifulSoup4)."""
    jobs = []
    html = _request_with_retry("https://www.consulting.fr/emploi")
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".job-item")
        for card in cards[:limit]:
            try:
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
            except Exception as e:
                logger.warning("Consulting.fr: failed to parse one card: %s", e)
    except Exception as e:
        logger.error("Consulting.fr: parse error: %s", e)
    return jobs


def scrape_regionsjob(keyword="Product Owner", limit=10):
    """Best-effort scrape of RegionsJob search results (BeautifulSoup4)."""
    jobs = []
    html = _request_with_retry("https://www.regionsjob.com/offres-emploi", params={"q": keyword})
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("article.card-offer") or soup.select(".offer-item")
        for card in cards[:limit]:
            try:
                title_el = card.find(["h2", "h3"])
                company_el = card.select_one(".company, .offer-company")
                link_el = card.find("a", href=True)
                if not (title_el and link_el):
                    continue
                href = link_el["href"]
                job_url = f"https://www.regionsjob.com{href}" if href.startswith("/") else href
                jobs.append({
                    "id": str(uuid.uuid4()),
                    "date_found": date.today().isoformat(),
                    "job_title": title_el.get_text(strip=True),
                    "company": company_el.get_text(strip=True) if company_el else "RegionsJob",
                    "location": "France",
                    "sector": "",
                    "salary_min": None,
                    "salary_max": None,
                    "job_url": job_url,
                    "job_description": "",
                    "source": "RegionsJob",
                })
            except Exception as e:
                logger.warning("RegionsJob: failed to parse one card: %s", e)
    except Exception as e:
        logger.error("RegionsJob: parse error: %s", e)
    return jobs


def scrape_stepstone(keyword="Product Owner", limit=10):
    """Best-effort scrape of StepStone France search results (BeautifulSoup4)."""
    jobs = []
    html = _request_with_retry("https://www.stepstone.fr/emplois", params={"ke": keyword})
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[data-testid='job-item']")
        for card in cards[:limit]:
            try:
                title_el = card.find(["h2", "h3"])
                company_el = card.select_one("[data-at='job-item-company-name']")
                link_el = card.find("a", href=True)
                if not (title_el and link_el):
                    continue
                href = link_el["href"]
                job_url = f"https://www.stepstone.fr{href}" if href.startswith("/") else href
                jobs.append({
                    "id": str(uuid.uuid4()),
                    "date_found": date.today().isoformat(),
                    "job_title": title_el.get_text(strip=True),
                    "company": company_el.get_text(strip=True) if company_el else "StepStone",
                    "location": "France",
                    "sector": "",
                    "salary_min": None,
                    "salary_max": None,
                    "job_url": job_url,
                    "job_description": "",
                    "source": "StepStone",
                })
            except Exception as e:
                logger.warning("StepStone: failed to parse one card: %s", e)
    except Exception as e:
        logger.error("StepStone: parse error: %s", e)
    return jobs


def scrape_talent(keyword="Product Owner", limit=10):
    """Best-effort scrape of Talent.com search results (BeautifulSoup4)."""
    jobs = []
    html = _request_with_retry("https://fr.talent.com/jobs", params={"k": keyword, "l": "France"})
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[data-testid='searchCardResults']")
        for card in cards[:limit]:
            try:
                title_el = card.find(["h2", "h3"])
                company_el = card.select_one(".company_names, .businessName")
                link_el = card.find("a", href=True)
                if not (title_el and link_el):
                    continue
                href = link_el["href"]
                job_url = f"https://fr.talent.com{href}" if href.startswith("/") else href
                jobs.append({
                    "id": str(uuid.uuid4()),
                    "date_found": date.today().isoformat(),
                    "job_title": title_el.get_text(strip=True),
                    "company": company_el.get_text(strip=True) if company_el else "Talent.com",
                    "location": "France",
                    "sector": "",
                    "salary_min": None,
                    "salary_max": None,
                    "job_url": job_url,
                    "job_description": "",
                    "source": "Talent.com",
                })
            except Exception as e:
                logger.warning("Talent.com: failed to parse one card: %s", e)
    except Exception as e:
        logger.error("Talent.com: parse error: %s", e)
    return jobs


def scrape_jooble(keyword="Product Owner", limit=10):
    """Best-effort scrape of Jooble (job aggregator) search results."""
    jobs = []
    html = _request_with_retry("https://fr.jooble.org/SearchResult", params={"ukw": keyword, "rgns": "France"})
    if not html:
        return jobs
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".vacancy")
        for card in cards[:limit]:
            try:
                title_el = card.find(["h2", "h3"])
                company_el = card.select_one(".company")
                link_el = card.find("a", href=True)
                if not (title_el and link_el):
                    continue
                jobs.append({
                    "id": str(uuid.uuid4()),
                    "date_found": date.today().isoformat(),
                    "job_title": title_el.get_text(strip=True),
                    "company": company_el.get_text(strip=True) if company_el else "Jooble",
                    "location": "France",
                    "sector": "",
                    "salary_min": None,
                    "salary_max": None,
                    "job_url": link_el["href"],
                    "job_description": "",
                    "source": "Jooble",
                })
            except Exception as e:
                logger.warning("Jooble: failed to parse one card: %s", e)
    except Exception as e:
        logger.error("Jooble: parse error: %s", e)
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
    scrape_france_travail,
    scrape_indeed,
    scrape_glassdoor,
    scrape_consulting_fr,
    scrape_regionsjob,
    scrape_stepstone,
    scrape_talent,
    scrape_jooble,
    scrape_linkedin,
    scrape_wttj,
]


# ---------------------------------------------------------------------------
# Seed / demo data - realistic French postings matching the search criteria.
# Used to top up the feed whenever live scraping returns too little (which,
# given anti-bot protections on the primary sources, is the common case).
# job_url points to a live Google search for the role so the "Voir
# l'offre" button always resolves to something real.
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
        job["job_url"] = _demo_search_url(job["job_title"], job["company"])
        jobs.append(job)
    return jobs


def run_daily_scrape(min_results=6, progress_cb=None):
    """Runs every source (with retry/backoff/error-handling), validates
    and deduplicates the results, tops up with seed data if needed, and
    returns (jobs, run_log). run_log mirrors the per-source counters the
    improvement spec asks for logged (found/duplicates/saved/errors) and
    is what the async refresh endpoint exposes as progress.

    progress_cb(source_name, index, total), if given, is called before
    each source runs - lets the caller (the async refresh endpoint) report
    "scraping en cours (3/9 sources)" back to the frontend.
    """
    run_log = {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {},
    }
    logger.info("Starting scraping run")

    seen_urls = set()
    seen_title_company = set()
    all_valid_jobs = []

    total_sources = len(SOURCES)
    for i, source_fn in enumerate(SOURCES, start=1):
        source_name = source_fn.__name__.replace("scrape_", "")
        if progress_cb:
            progress_cb(source_name, i, total_sources)

        found = duplicates = validated = rejected = 0
        error = None
        try:
            source_jobs = []
            source_started = time.time()
            for keyword in SEARCH_KEYWORDS:
                if time.time() - source_started > SOURCE_TIMEOUT_BUDGET:
                    logger.warning(
                        "%s: exceeded %ds budget, moving on with %d keyword(s) left",
                        source_name, SOURCE_TIMEOUT_BUDGET,
                        len(SEARCH_KEYWORDS) - SEARCH_KEYWORDS.index(keyword),
                    )
                    break
                source_jobs.extend(source_fn(keyword))
            found = len(source_jobs)

            for job in source_jobs:
                job = _clean_job(job)
                ok, reason = validate_job(job)
                if not ok:
                    rejected += 1
                    logger.info("rejected job from %s: %s", source_name, reason)
                    continue

                url_key = _normalize_url(job["job_url"])
                title_company_key = (job["job_title"].strip().lower(), job["company"].strip().lower())
                if url_key in seen_urls or title_company_key in seen_title_company:
                    duplicates += 1
                    continue

                seen_urls.add(url_key)
                seen_title_company.add(title_company_key)
                validated += 1
                all_valid_jobs.append(job)
        except Exception as e:
            error = str(e)
            logger.error("%s: unhandled error: %s", source_name, e, exc_info=True)

        run_log["sources"][source_name] = {
            "found": found, "duplicates": duplicates,
            "saved": validated, "rejected": rejected, "error": error,
        }
        logger.info("%s: %d found, %d duplicates, %d saved, %d rejected%s",
                     source_name, found, duplicates, validated, rejected,
                     f" - ERROR: {error}" if error else "")

        # Be polite to whichever source just answered before hitting the next one.
        time.sleep(random.uniform(1, 3))

    if len(all_valid_jobs) < min_results:
        needed = min_results - len(all_valid_jobs)
        seed_jobs = generate_seed_jobs(min(needed + 2, len(_SEED_TEMPLATES)))
        seed_kept = []
        for job in seed_jobs:
            job = _clean_job(job)
            ok, _ = validate_job(job)
            if not ok:
                continue
            url_key = _normalize_url(job["job_url"])
            title_company_key = (job["job_title"].strip().lower(), job["company"].strip().lower())
            if url_key in seen_urls or title_company_key in seen_title_company:
                continue
            seen_urls.add(url_key)
            seen_title_company.add(title_company_key)
            seed_kept.append(job)
        all_valid_jobs.extend(seed_kept)
        run_log["sources"]["Seed/Demo"] = {
            "found": len(seed_jobs), "duplicates": len(seed_jobs) - len(seed_kept),
            "saved": len(seed_kept), "rejected": 0, "error": None,
        }
        logger.info("Seed/Demo: topped up with %d demo postings", len(seed_kept))

    run_log["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    run_log["total_found"] = sum(s["found"] for s in run_log["sources"].values())
    run_log["total_duplicates"] = sum(s["duplicates"] for s in run_log["sources"].values())
    run_log["total_saved"] = sum(s["saved"] for s in run_log["sources"].values())
    logger.info("Total: %d found, %d duplicates, %d saved",
                 run_log["total_found"], run_log["total_duplicates"], run_log["total_saved"])

    return all_valid_jobs, run_log
