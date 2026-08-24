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

Le profil candidat (`CANDIDATE` dans `config.py`, et son identite visuelle
dans `cv_identity_guide.py` pour le CV genere) est deja rempli avec les
vraies coordonnees d'Amine.

## Generation du CV : weasyprint

`cv_generator.py` rend `templates/cv_template.html` (contenu dans
`cv_identity_guide.py`, extrait des deux CV sources reels d'Amine - palette
indigo `#150D49`, Lato/Space Grotesk) en PDF via
[weasyprint](https://weasyprint.org/), qui depend de bibliotheques systeme
natives (Pango, Cairo, GDK-Pixbuf) non installees par defaut sur tous les
hebergeurs Python "buildpack" comme Render. Si l'import ou le rendu
weasyprint echoue au runtime (bibliotheques absentes), le generateur
bascule automatiquement sur l'ancien rendu reportlab (memes variantes de
role AMOA/PM/Aero, mise en page plus simple) - la generation de CV ne casse
jamais, meme si weasyprint ne peut pas tourner sur l'environnement de
deploiement. Si vous voyez le CV "ancienne version" en sortie sur Render,
installez les paquets systeme requis par weasyprint (voir leur doc
d'installation) ou passez a un deploiement Docker.

Le CV est genere en mode ATS (une colonne, sans photo, texte selectionnable)
par defaut puisque c'est le canal principal de cette appli (candidatures sur
job boards) ; le mode "design" (2 colonnes, sidebar indigo, pour un envoi
direct a un recruteur) est disponible via `cv_generator.generate_cv(job,
mode="design")`.

## Securite : proteger l'acces

L'application sert des donnees personnelles (email, telephone dans les CV
generes) et peut declencher du scraping - elle ne doit jamais rester
accessible publiquement sans protection. Definissez :

```bash
export DASHBOARD_USER="amine"          # optionnel, "amine" par defaut
export DASHBOARD_PASSWORD="..."        # obligatoire pour activer la protection
```

Sur Render : Dashboard -> votre service -> Environment -> Add Environment
Variable. Le navigateur demandera alors identifiant/mot de passe (HTTP
Basic Auth) a la premiere visite. **Sans `DASHBOARD_PASSWORD` defini,
l'application tourne sans aucune protection** - pratique en local, jamais
souhaitable en production.

## Persistance du suivi de candidature (Supabase)

Le cache d'offres (`data/jobs.db`) vit sur un disque ephemere en
production (voir "Hebergement" plus bas) et est regenere automatiquement
apres chaque redeploiement. Mais le *suivi* (quelles offres ont ete
marquees "candidate", avec quelles notes) ne peut pas etre regenere - il
est donc mirrore dans un projet Supabase (Postgres) gratuit qui, lui,
survit aux redeploiements.

1. Creez un projet gratuit sur https://supabase.com
2. Dans l'editeur SQL du projet, executez :
   ```sql
   create table job_tracking (
     job_url text primary key,
     status text not null default 'new',
     date_applied date,
     notes text,
     updated_at timestamptz not null default now()
   );
   ```
3. Dans Project Settings -> API, recuperez l'**URL du projet** et la cle
   **`service_role`** (pas la cle `anon` - `service_role` est necessaire
   car cette table n'a pas vocation a etre appelee depuis un navigateur)
4. Definissez les variables d'environnement (jamais dans le code) :
   ```bash
   export SUPABASE_URL="https://xxxxx.supabase.co"
   export SUPABASE_SERVICE_KEY="..."
   ```
   Les noms doivent correspondre exactement (`SUPABASE_URL`,
   `SUPABASE_SERVICE_KEY`) - une variable mal nommee ou une valeur avec des
   guillemets/espaces colles par erreur echoue silencieusement (le suivi
   continue de fonctionner localement mais ne persiste plus, sans erreur
   visible). Pour verifier que c'est bien pris en compte : marquez une offre
   "candidate", puis controlez que la table `job_tracking` dans Supabase a
   bien une nouvelle ligne.

Sans ces identifiants, le suivi fonctionne normalement mais uniquement
tant que le processus tourne - il repart a zero au prochain redeploiement
(comportement d'avant cette fonctionnalite, logue une fois, jamais une
erreur).

La meme table Supabase (memes identifiants) mirrore aussi la synthese de
veille marche (section "Veille marche" du dashboard) - sans quoi elle
serait, elle aussi, effacee a chaque redeploiement. Executez en plus dans
l'editeur SQL Supabase :
```sql
create table market_veille (
  id integer primary key,
  target_min integer,
  target_max integer,
  summary text,
  grille_json text,
  targets_json text,
  sources_json text,
  updated_at timestamptz not null default now()
);
```

## A savoir sur le scraping

**Sources principales : deux API officielles, executees automatiquement
chaque jour.** Ce sont de vraies API (gratuites, conformes aux CGU), pas du
scraping - la difference compte : un site web peut bloquer un robot qui lit
sa page HTML en douce, mais pas un appel a une API qu'il expose lui-meme
pour ca.

1. **France Travail** (ex Pole Emploi) - la source a plus fort volume.
   - Creez un compte gratuit sur https://francetravail.io/inscription
   - Dans "Mes applications" -> "Creer une application", cochez l'API
     **"Offres d'emploi v2"**
   - Recuperez le `client_id` et le `client_secret` generes :
     ```bash
     export FRANCE_TRAVAIL_CLIENT_ID="..."
     export FRANCE_TRAVAIL_CLIENT_SECRET="..."
     ```

2. **Adzuna** - un agregateur international, complementaire (couvre aussi
   des offres et sites que France Travail ne remonte pas).
   - Creez un compte gratuit sur https://developer.adzuna.com/ (1000
     appels/mois sur le tier gratuit, largement suffisant pour un scrape
     quotidien)
   - Recuperez l'`app_id` et l'`app_key` generes :
     ```bash
     export ADZUNA_APP_ID="..."
     export ADZUNA_APP_KEY="..."
     ```

Sur Render : Dashboard -> votre service -> Environment -> Add Environment
Variable (jamais dans le code ni commite dans git). Sans ces identifiants,
la source correspondante est simplement ignoree (loguee une fois, pas une
erreur) - le dashboard continue de fonctionner avec les sources restantes.

**Sources secondaires : scraping best-effort, desactivees par defaut.**
LinkedIn, Indeed, Glassdoor et Welcome to the Jungle bloquent activement le
scraping automatise et leurs CGU le restreignent. `scraper.py` contient des
tentatives best-effort (BeautifulSoup4, avec retry/backoff) pour Indeed,
Glassdoor, Consulting.fr, RegionsJob, StepStone, Talent.com et Jooble, plus
des stubs LinkedIn/WTTJ - mais elles ne tournent jamais automatiquement
(`run_daily_scrape(include_secondary=True)` n'est appele nulle part) : elles
avaient sature le CPU du plan gratuit Render en tournant en parallele pour
un gain quasi nul, la plupart des requetes etant bloquees. Conservees dans
le code au cas ou un futur setup (proxy, Selenium) les rendrait viables.

**Aucun repli demo.** Sans aucune source configuree, le Flux reste
honnetement vide plutot que rempli d'offres fictives - voir le widget de
statut par source affiche dans l'etat vide du dashboard.

## Fonctionnalites

- Feed quotidien d'offres, trie par score de compatibilite (0-100)
- Scoring : salaire (25%), correspondance du poste (30%), secteur (15%),
  localisation (10%), notoriete de l'entreprise (12%), bonus (8%)
- Filtres : secteur, salaire, score, localisation, statut de candidature
- Generation en un clic d'un CV PDF fidele a l'identite visuelle reelle
  d'Amine (indigo `#150D49`, Lato/Space Grotesk, layout A4), decline en 3
  variantes de role (AMOA / Product Owner / Aeronautique) auto-detectees
  a partir des mots-cles de l'offre, rendu en version ATS une colonne -
  et d'une lettre de motivation DOCX personnalisee (accroche, pourquoi ce
  role, pourquoi cette entreprise)
- Suivi de candidature (new / applied / interview / offer / rejected)
- Stats du jour et market insights (salaire moyen par secteur, entreprises
  qui recrutent le plus, tendance des offres sur 14 jours)
- Rafraichissement manuel via le bouton "Refresh", scraping automatique
  quotidien a 7h (APScheduler), et rafraichissement automatique au demarrage
  si la base ne contient que des offres de demo (utile sur un hebergement
  au stockage ephemere comme le plan gratuit Render, ou chaque redeploiement
  reinitialise la base - voir `has_only_demo_jobs()` dans `database.py`)

## Structure

```
job-market-dashboard/
├── app.py                 # Flask backend + routes API
├── scraper.py              # Scraping multi-source + fallback seed data
├── scorer.py               # Algorithme de scoring
├── cv_generator.py         # Rendu CV PDF : Jinja2 -> HTML -> weasyprint
├── cv_identity_guide.py     # Design tokens + contenu reel du CV, par variante de role
├── letter_generator.py     # Generation lettre DOCX (python-docx)
├── database.py             # SQLite (schema + CRUD)
├── config.py                # Profil candidat + criteres de recherche
├── requirements.txt
├── templates/{index.html,cv_template.html}
├── static/{css,js}/
└── data/                    # jobs.db + export/ (auto-crees, gitignore)
```
