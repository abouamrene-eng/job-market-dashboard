# Job Market Dashboard - Amine Bouamrene

Application web pour suivre quotidiennement les offres d'emploi du marche
francais (Product Owner / AMOA / Agile / Transformation), les scorer par
rapport au profil d'Amine Bouamrene, et generer automatiquement un CV et
une lettre de motivation adaptes a chaque offre.

## Installation

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

L'application demarre sur http://localhost:5000. La base SQLite
(`data/jobs.db`) et le dossier d'export (`data/export/`) sont crees
automatiquement au premier lancement, avec quelques offres de demonstration
si la base est vide.

## Avant de l'utiliser pour de vrai

Ouvrez `config.py` et completez `CANDIDATE["phone"]` avec votre numero de
telephone (l'email est deja pre-rempli avec `abouamrene@gmail.com`).

## A savoir sur le scraping

**Source principale : l'API France Travail.** C'est la source fiable et a
fort volume - une API officielle, gratuite et conforme aux CGU (contrairement
au scraping), qui agrege de vraies offres du marche francais. Pour l'activer :

1. Creez un compte gratuit sur https://francetravail.io/inscription
2. Dans "Mes applications" -> "Creer une application", cochez l'API
   **"Offres d'emploi v2"**
3. Recuperez le `client_id` et le `client_secret` generes, et definissez-les
   comme variables d'environnement :
   ```bash
   export FRANCE_TRAVAIL_CLIENT_ID="..."
   export FRANCE_TRAVAIL_CLIENT_SECRET="..."
   ```
   Sur Render : Dashboard -> votre service -> Environment -> Add Environment
   Variable (jamais dans le code ni commite dans git).

Sans ces identifiants, cette source est simplement ignoree (logue une fois,
pas une erreur) et le dashboard retombe sur les sources secondaires.

**Sources secondaires : scraping best-effort.** LinkedIn, Indeed, Glassdoor
et Welcome to la Jungle bloquent activement le scraping automatise et leurs
CGU le restreignent. `scraper.py` essaie tout de meme des requetes
best-effort (BeautifulSoup4, avec retry/backoff) sur Indeed, Glassdoor,
Consulting.fr, RegionsJob, StepStone, Talent.com et Jooble, avec des
scrapers LinkedIn/WTTJ laisses en stub (a completer avec une session
Selenium authentifiee si besoin). Il est normal que la plupart de ces
sources secondaires renvoient 0 resultat la plupart du temps.

**Repli demo.** Quand ni France Travail ni le scraping secondaire ne
remontent assez de resultats, le dashboard complete le flux avec des offres
de demonstration realistes (`generate_seed_jobs`) dont le lien "Voir
l'offre" pointe vers une recherche Google reelle - pour que le scoring, la
generation de CV/LM et le tracking restent utilisables meme sans aucune
source live configuree.

## Fonctionnalites

- Feed quotidien d'offres, trie par score de compatibilite (0-100)
- Scoring : salaire (25%), correspondance du poste (30%), secteur (15%),
  localisation (10%), notoriete de l'entreprise (12%), bonus (8%)
- Filtres : secteur, salaire, score, localisation, statut de candidature
- Generation en un clic d'un CV PDF adapte au role (titre et highlights
  qui changent selon les mots-cles de l'offre) et d'une lettre de
  motivation DOCX personnalisee (accroche, pourquoi ce role, pourquoi
  cette entreprise)
- Suivi de candidature (new / applied / interview / offer / rejected)
- Stats du jour et market insights (salaire moyen par secteur, entreprises
  qui recrutent le plus, tendance des offres sur 14 jours)
- Rafraichissement manuel via le bouton "Refresh", et scraping automatique
  quotidien a 7h (APScheduler)

## Structure

```
job-market-dashboard/
├── app.py                 # Flask backend + routes API
├── scraper.py              # Scraping multi-source + fallback seed data
├── scorer.py               # Algorithme de scoring
├── cv_generator.py         # Generation CV PDF (reportlab)
├── letter_generator.py     # Generation lettre DOCX (python-docx)
├── database.py             # SQLite (schema + CRUD)
├── config.py                # Profil candidat + criteres de recherche
├── requirements.txt
├── templates/index.html
├── static/{css,js}/
└── data/                    # jobs.db + export/ (auto-crees, gitignore)
```
