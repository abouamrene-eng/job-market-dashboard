"""Candidate profile and search criteria used by the scorer, CV and letter
generators. Edit the values below to keep the dashboard in sync with your
real contact details and preferences.
"""

CANDIDATE = {
    "name": "Amine Bouamrene",
    "age": 26,
    "email": "abouamrene@gmail.com",
    # Renseignez votre numero de telephone ici (non fourni par defaut).
    "phone": "[Telephone a renseigner]",
    "title_default": "Product Owner | Consultant AMOA",
    "education": [
        {
            "degree": "Ingenieur ENAC (Ecole Nationale de l'Aviation Civile)",
            "detail": "Specialisation avionique + operation/securite aerienne",
            "years": "2017-2020",
        }
    ],
    "certifications": [
        "PSPO I (Professional Scrum Product Owner)",
        "Leading SAFe (Agile a grande echelle)",
    ],
    "languages": [
        {"name": "Arabe", "level": "Courant"},
        {"name": "Anglais", "level": "TOEIC 785/990 (B2)"},
        {"name": "Espagnol", "level": "Intermediaire"},
    ],
    "technical_skills": {
        "Langages": ["C/C++", "Python (intermediaire)"],
        "Outils metier": ["JIRA", "Bizagi Modeler", "BPMN"],
    },
    "key_skills": [
        "Pilotage agile (SAFe, SCRUM)",
        "GMAO / Maintenance",
        "Conception fonctionnelle de solutions digitales",
        "Gestion de donnees & ETL",
        "Conduite du changement utilisateur",
        "Management AMOA/MOE",
    ],
    "experiences": [
        {
            "id": "sncf",
            "company": "SNCF Gare & Connexions (via TNP Consultants)",
            "title": "Product Owner - GMAO",
            "duration": "3 ans",
            "highlights": [
                "Pilotage produit d'une solution GMAO utilisee par 7 000 collaborateurs sur 3 000 gares",
                "Management d'une equipe AMOA/MOE de 10 personnes",
                "Vision produit, redaction des user stories et criteres d'acceptation",
                "Pilotage agile SAFe/SCRUM a grande echelle",
                "Animation d'ateliers de formation aupres de 7 000 utilisateurs",
                "Strategie de reprise de donnees, ETL et qualite des donnees",
                "Reporting KPIs et dashboards de suivi d'avancement",
            ],
            "keywords": ["product owner", "amoa", "agile", "safe", "scrum",
                          "gmao", "transformation", "management", "data",
                          "conduite du changement"],
        },
        {
            "id": "bnpp",
            "company": "BNP Paribas Real Estate",
            "title": "Assistant Chef de Projet - Compliance",
            "duration": "1 an",
            "highlights": [
                "Pilotage de projets ethique / securite financiere",
                "Gestion de sprints agile sous JIRA",
                "Reporting KPI trimestriel",
            ],
            "keywords": ["chef de projet", "compliance", "agile", "jira",
                          "reporting", "finance"],
        },
        {
            "id": "af",
            "company": "Air France Industries",
            "title": "Chef de Projet Business Process Management",
            "duration": "8 mois",
            "highlights": [
                "Modelisation de processus (BPMN, Bizagi Modeler)",
                "Optimisation de la performance operationnelle",
            ],
            "keywords": ["bpm", "processus", "bpmn", "aeronautique",
                          "industrie", "optimisation"],
        },
    ],
}

SEARCH_CRITERIA = {
    "salary_min": 65000,
    "salary_target_low": 68000,
    "salary_target_high": 75000,
    "salary_acceptable_min": 60000,
    "locations_preferred": ["mixte", "remote", "ile-de-france", "idf", "paris", "france"],
    "sectors_priority": [
        "conseil", "tech", "saas", "industrie", "energie", "utilities",
        "finance", "insurtech",
    ],
    "roles": [
        "product owner", "product manager", "amoa", "programme manager",
        "agile coach", "scrum master", "business analyst",
        "transformation digitale",
    ],
    "exclude_below_salary": 60000,
}

SEARCH_KEYWORDS = [
    "Product Owner", "AMOA", "Programme Manager", "Agile", "Transformation",
]

NOTABLE_COMPANIES = {
    "cac40_fortune500_gafam": [
        "airbus", "air france", "bnp paribas", "societe generale", "axa",
        "total", "totalenergies", "engie", "edf", "capgemini", "accenture",
        "orange", "sncf", "danone", "loreal", "l'oreal", "sanofi", "renault",
        "michelin", "vinci", "veolia", "schneider electric", "thales",
        "google", "amazon", "meta", "apple", "microsoft", "deloitte",
        "mckinsey", "bcg", "kpmg", "pwc", "ey",
    ],
    "pme_scaleup": [
        "scale-up", "scaleup", "startup", "pme", "welcome to the jungle",
    ],
}

DATA_DIR = "data"
EXPORT_DIR = "data/export"
DB_PATH = "data/jobs.db"
