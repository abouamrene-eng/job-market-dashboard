"""Candidate profile and search criteria used by the scorer, CV and letter
generators. Edit the values below to keep the dashboard in sync with your
real contact details, credentials and preferences.

A few fields below are placeholders or use relative durations instead of
absolute dates - double check them (LINKEDIN_URL, certifications,
education "projects") before sending a real application.
"""

LINKEDIN_URL = "linkedin.com/in/aminebouamrene"

CANDIDATE = {
    "name": "Amine Bouamrene",
    "age": 26,
    "email": "abouamrene@gmail.com",
    "phone": "06 65 46 70 56",
    "linkedin": LINKEDIN_URL,
    "current_salary": 56000,
    "current_company": "TNP Consultants (mission SNCF Gares & Connexions)",
    "title_default": "Product Owner | AMOA Consultant | SAFe & PSPO I Certified",
    "profile_summary_default": (
        "Product Owner avec 3 ans d'experience en pilotage de solutions digitales "
        "complexes a l'echelle entreprise (7 000 utilisateurs). Expert en "
        "transformation agile (SAFe, SCRUM), gestion de la donnee et conduite du "
        "changement utilisateur. Ingenieur ENAC - formation d'elite avec "
        "background technique (C/C++, Python)."
    ),
    "education": [
        {
            "degree": "Diplome d'ingenieur - ENAC (Ecole Nationale de l'Aviation Civile)",
            "years": "2017-2020",
            "detail": "Specialisations : avionique, operation/securite aerienne",
            "note": ("Formation technique unique : C/C++, ingenierie systeme, "
                      "theorie des systemes aeronautiques"),
        }
    ],
    "certifications": [
        {"name": "PSPO I (Professional Scrum Product Owner)", "issuer": "Scrum.org"},
        {"name": "Leading SAFe", "issuer": "Scaled Agile"},
    ],
    "languages": [
        {"name": "Francais", "level": "Natif"},
        {"name": "Anglais", "level": "TOEIC 785/990 (B2)"},
        {"name": "Arabe", "level": "Courant"},
        {"name": "Espagnol", "level": "Intermediaire"},
    ],
    "skill_categories": {
        "Pilotage agile": [
            "SAFe (Leading SAFe)", "PSPO I", "Scrum Master",
            "Program/Product Management", "Planning incremental & release planning",
            "Backlog management", "Ceremonies agiles (daily, sprint review, retro)",
        ],
        "Product management": [
            "Vision produit & strategie", "Redaction de user stories",
            "Criteres d'acceptation", "Gestion des besoins",
            "Priorisation & refinement du backlog", "Gestion des parties prenantes",
        ],
        "Donnees & qualite": [
            "Strategie de reprise de donnees", "Conception & validation ETL",
            "Assurance qualite des donnees", "Gouvernance des donnees",
            "GMAO / systemes de maintenance",
        ],
        "Conduite du changement": [
            "Change management", "Strategies d'adoption utilisateur",
            "Conception & animation de formations", "Communication aupres des parties prenantes",
        ],
        "Outils metier": ["JIRA", "Bizagi Modeler (BPMN)", "Confluence", "Excel avance"],
        "Langages de programmation": ["C/C++ (intermediaire)", "Python (intermediaire)"],
    },
    "soft_skills": [
        "Leadership & management d'equipe", "Alignement transverse",
        "Communication orale et ecrite (FR/EN)", "Resolution de problemes",
        "Negociation & influence", "Adaptabilite",
    ],
    "differentiators": [
        "Formation ENAC : ecole d'ingenieur d'elite, reconnaissance internationale",
        "3 ans de delivery a grande echelle (7 000+ utilisateurs)",
        "Double certification SAFe & PSPO I : methodologie agile eprouvee a l'echelle entreprise",
        "Background technique rare (C/C++, systemes critiques aeronautiques)",
        "Experience multi-secteurs : aeronautique, ferroviaire, finance",
        "Multilingue (FR/EN/AR) : atout pour les organisations internationales",
    ],
    "experiences": [
        {
            "id": "sncf",
            "company": "SNCF Gare & Connexions",
            "context": "via TNP Consultants (cabinet de conseil), Paris / Ile-de-France",
            "title": "Product Owner - GMAO",
            "duration": "3 ans",
            "highlights": [
                "Pilotage de la conception et de la livraison d'une solution GMAO pour 3 000 gares, 7 000 utilisateurs quotidiens",
                "Management d'une equipe AMOA/MOE de 10 personnes (arbitrage besoins metiers vs contraintes techniques)",
                "Vision produit, redaction des user stories et criteres d'acceptation",
                "Pilotage agile SAFe/SCRUM a grande echelle (PI planning, refinement, releases)",
                "Conduite du changement : animation de plus de 50 ateliers de formation utilisateur",
                "Strategie de reprise de donnees (ETL), qualite et gouvernance des donnees pour 7 000 utilisateurs",
                "Reporting KPIs et dashboards de suivi d'avancement, escalade des risques",
            ],
            "keywords": ["product owner", "amoa", "agile", "safe", "scrum",
                          "gmao", "transformation", "management", "data",
                          "conduite du changement", "vision produit",
                          "user story", "backlog"],
        },
        {
            "id": "bnpp",
            "company": "BNP Paribas Real Estate",
            "context": "Paris / Ile-de-France",
            "title": "Assistant Chef de Projet - Compliance",
            "duration": "1 an",
            "highlights": [
                "Pilotage de projets ethique professionnelle et securite financiere",
                "Gestion de sprints agile sous JIRA (ceremonies SCRUM)",
                "Reporting KPI trimestriel et communication aupres des parties prenantes",
            ],
            "keywords": ["chef de projet", "compliance", "agile", "jira",
                          "reporting", "finance", "scrum"],
        },
        {
            "id": "af",
            "company": "Air France Industries",
            "context": "France",
            "title": "Chef de Projet Business Process Management",
            "duration": "8 mois",
            "highlights": [
                "Modelisation de processus metier (BPMN, Bizagi Modeler)",
                "Etude d'optimisation des methodes et outils operationnels",
                "Amelioration de la performance (cadrage SI, adoption agile)",
            ],
            "keywords": ["bpm", "processus", "bpmn", "aeronautique",
                          "industrie", "optimisation"],
        },
    ],
}

SEARCH_CRITERIA = {
    # What Amine can realistically ask for given his real profile (ENAC +
    # 3 years Product/AMOA + large-scale GMAO delivery) - grounded in the
    # August 2026 market veille (Externatic grille "confirme" 3-6 ans IDF:
    # 53-63k EUR, cross-referenced against 16 real postings), not a generic
    # algorithmic guess. See scorer.estimate_salary().
    "salary_target_min": 58000,
    "salary_target_max": 65000,
    "locations_preferred": ["mixte", "remote", "ile-de-france", "idf", "paris",
                              "toulouse", "france"],
    "sectors_priority": [
        "aeronautique", "conseil", "tech", "saas", "industrie", "energie",
        "utilities", "finance", "insurtech",
    ],
    "roles": [
        "product owner", "product manager", "amoa", "programme manager",
        "agile coach", "scrum master", "business analyst",
        "transformation digitale",
    ],
    # Floor beneath which a posting isn't worth surfacing at all - below the
    # grille's "jeune diplome" tier (38-43k), not the old, unrealistically
    # high 60k cut that would have silently rejected genuinely good
    # "confirme" offers found in the veille (e.g. Storm Group 45-55k).
    "exclude_below_salary": 45000,
}

SEARCH_KEYWORDS = [
    "Product Owner", "AMOA", "Programme Manager", "Agile", "Transformation",
]

# ---------------------------------------------------------------------------
# Aeronautique focus (V5): the dashboard's default lens. AERO_COMPANIES
# feeds both the scoring bonus (scorer.py) and the "is_aeronautique" /
# "company_type" flags stored per job. ENAC_KEYWORDS flags postings that
# call out ENAC (or an ENAC-adjacent formation) as a plus - a strong signal
# this employer values Amine's exact background.
# ---------------------------------------------------------------------------
AERO_COMPANIES = {
    # Exact scoring per company (spec's own priority order).
    "airbus": 20,
    "thales": 20,
    "safran": 19,
    "dassault": 18,
    "dassault aviation": 18,
    "dassault systemes": 18,
    "dassault systèmes": 18,
}
AERO_COMPANIES_OTHER = [
    # Recognized aero/defense employers without an individually-tuned
    # score - fall back to the "Autre BigCo aero" bonus tier.
    "ariane group", "arianegroup", "thales alenia space", "zodiac aerospace",
    "safran aircraft engines", "joby", "joby aviation", "lilium", "embraer",
    "boeing", "collins aerospace", "liebherr aerospace", "latecoere",
    "latécoère", "stelia", "figeac aero", "figeac aéro", "daher",
    "air france", "air france industries", "aeroport", "aéroport", "adp",
    "onera", "cnes",
]
ENAC_KEYWORDS = ["enac", "ecole nationale de l'aviation civile",
                  "école nationale de l'aviation civile"]

# Maps each sector filter checkbox to the keywords it should match against
# (sector + title + description). Real postings (e.g. France Travail's
# secteurActiviteLibelle) use much more granular/varied wording than the
# 6 checkboxes, so an exact match on `sector` alone would miss almost
# everything - this is a fuzzy, best-effort grouping instead.
SECTOR_FILTER_KEYWORDS = {
    "Conseil": ["conseil", "consulting"],
    "Tech": ["tech", "informatique", "logiciel", "digital", "numerique",
              "numérique", "software", "saas", "programmation", "editeur"],
    "Industrie": ["industrie", "industriel", "ingenierie", "ingénierie",
                   "manufactur", "aeronautique", "aéronautique", "production"],
    "Energie": ["energie", "énergie", "utilities", "environnement"],
    "Finance": ["finance", "banque", "bancaire", "financier"],
    "Insurtech": ["assurance", "insurtech", "mutuelle"],
}

# Maps each role filter checkbox to the keywords it should match against
# job_title - mirrors SECTOR_FILTER_KEYWORDS's fuzzy-grouping approach.
ROLE_FILTER_KEYWORDS = {
    "Product Manager": ["product manager"],
    "Product Owner": ["product owner"],
    "AMOA": ["amoa"],
    "Programme Manager": ["programme manager", "program manager"],
}

NOTABLE_COMPANIES = {
    "cac40_fortune500_gafam": [
        "airbus", "air france", "bnp paribas", "societe generale", "axa",
        "total", "totalenergies", "engie", "edf", "capgemini", "accenture",
        "orange", "sncf", "danone", "loreal", "l'oreal", "sanofi", "renault",
        "michelin", "vinci", "veolia", "schneider electric", "thales", "safran",
        "google", "amazon", "meta", "apple", "microsoft", "deloitte",
        "mckinsey", "bcg", "kpmg", "pwc", "ey",
    ],
    "pme_scaleup": [
        "scale-up", "scaleup", "startup", "pme", "welcome to the jungle",
    ],
}

# Used by letter_generator to pick a company-specific "why this company"
# paragraph. Extend freely - unmatched companies fall back to a
# sector-based paragraph.
COMPANY_ARCHETYPES = {
    "conseil": ["capgemini", "accenture", "deloitte", "mckinsey", "bcg",
                "kpmg", "pwc", "ey", "consulting"],
    "tech_scaleup": ["alan", "doctolib", "qonto", "back market", "swile",
                      "scale-up", "scaleup", "startup", "saas"],
    "aero_defense": ["thales", "safran", "airbus", "dassault", "air france",
                       "aeronautique", "aéronautique", "defense", "défense"],
    "energie_utilities": ["edf", "engie", "totalenergies", "veolia",
                            "energie", "énergie", "utilities"],
}

DATA_DIR = "data"
EXPORT_DIR = "data/export"
DB_PATH = "data/jobs.db"
