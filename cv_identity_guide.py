"""Design tokens + real CV content, extracted from Amine's two source CVs
(CV_Amine_Bouamrene.pdf and CV_-_Amine_Bouamrene.pptx) and normalized per
CV_IDENTITY_GUIDE.md / CV_STYLE_RECOMMENDATIONS.txt.

This is the single source of truth for cv_generator.py: colors/fonts/spacing
tokens for the HTML/CSS template, and the content itself (header, sidebar
blocks, experiences, formation, projects) for each of the three role
variants (amoa / pm / aero). Per the identity guide's rule #8: the factual
content never changes across variants, only the order, headline, pitch and
which bullets/sections get promoted.
"""

COLORS = {
    "primary": "#150D49",
    "accent": "#2B2270",
    "highlight": "#95C11E",
    "heading": "#141414",
    "text": "#3F3F3F",
    "text_muted": "#656565",
    "bg": "#FFFFFF",
    "surface": "#F4F4F7",
    "rule": "#E2E2EA",
    "sidebar_fg": "#FFFFFF",
}

FONTS = {
    "body": "'Lato', 'Open Sans', 'Segoe UI', Arial, sans-serif",
    "headers": "'Space Grotesk', 'Lato', 'Segoe UI', Arial, sans-serif",
}

CONTACT = {
    "name": "Amine Bouamrene",
    "email": "mohamed.bouamrene.2017@alumni.enac.fr",
    "phone": "06 65 46 70 56",
    "linkedin": "linkedin.com/in/aminebouamrene",
    "city": "Paris, France",
}

# ---------------------------------------------------------------------------
# Role-detection keywords -> variant. Order matters: first match wins.
# ---------------------------------------------------------------------------
VARIANT_KEYWORDS = [
    ("aero", ["aeronautique", "aéronautique", "aerospace", "aviation", "avionique",
              "defense", "défense", "enac", "mbse", "mro", "surete aeroportuaire",
              "sûreté aéroportuaire", "etops"]),
    ("pm", ["product owner", "product manager", "backlog", "roadmap",
            "user stories", "user story", "sprint", "discovery"]),
    ("amoa", ["amoa", "programme manager", "program manager", "moe",
              "conduite du changement", "cadrage", "bpm", "business process",
              "transformation"]),
]
DEFAULT_VARIANT = "amoa"


def detect_variant(job: dict) -> str:
    blob = f"{job.get('job_title', '')} {job.get('job_description', '')}".lower()
    for variant, keywords in VARIANT_KEYWORDS:
        if any(kw in blob for kw in keywords):
            return variant
    return DEFAULT_VARIANT


# ---------------------------------------------------------------------------
# Per-variant header / profile / competences (identity guide section 8)
# ---------------------------------------------------------------------------
VARIANTS = {
    "amoa": {
        "headline": "Consultant AMOA | Chef de projet Transformation | Certifié SAFe",
        "profile": (
            "Consultant AMOA, 3 ans de pilotage de programme de transformation SI en "
            "environnement agile à l'échelle : cadrage, conduite du changement, gestion "
            "des risques et coordination AMOA/MOE (10 personnes)."
        ),
        "competences": [
            "Pilotage de projet Agile (SAFe & Scrum)",
            "Cadrage et conduite du changement",
            "Modélisation de processus (BPMN, Bizagi)",
            "Gestion des risques et du planning",
            "Mise en place et optimisation des processus",
            "Reprise et qualité de données",
            "Animation d'ateliers métiers",
        ],
        "show_impact": False,
    },
    "pm": {
        "headline": "Product Owner | Product Manager | PSPO I & Leading SAFe",
        "profile": (
            "Product Owner, 3 ans de déploiement agile d'une solution GMAO pour 7 000 "
            "utilisateurs sur 3 000 sites. Vision produit, arbitrage du besoin métier, "
            "élaboration des User Stories et pilotage du delivery en environnement SAFe."
        ),
        "competences": [
            "Vision et roadmap produit",
            "Gestion et priorisation du backlog",
            "User Stories et critères d'acceptation",
            "Agile at scale (SAFe, Scrum)",
            "Pilotage d'équipe AMOA/MOE",
            "KPI et adoption utilisateurs",
            "Discovery et cadrage de solutions",
        ],
        "show_impact": True,
    },
    "aero": {
        "headline": "Ingénieur ENAC | Ingénieur systèmes & avionique | Gestion de projet",
        "profile": (
            "Ingénieur ENAC spécialisé avionique et opérations aériennes, avec 3 ans "
            "d'expérience en conception fonctionnelle et pilotage de projets SI "
            "industriels (ferroviaire, aéronautique)."
        ),
        "competences": [
            "Opérations aériennes",
            "Conformité et sûreté aéroportuaire",
            "Optimisation et modélisation (Matlab/Simulink, CPLEX, Python)",
            "Maintenance et GMAO",
            "Gestion de projet Agile",
            "Amélioration de la performance opérationnelle",
        ],
        "show_impact": False,
        "formation_first": True,
    },
}

SIDEBAR = {
    "secteurs": ["Ferroviaire", "Aéronautique", "Conformité réglementaire"],
    "outils": ["JIRA · Confluence", "Bizagi Modeler (BPMN)", "Matlab/Simulink · Python · C/C++"],
    "outils_aero": "CORE (MBSE) · Winpep · JetPlanner",
    "certifications": ["PSPO I (Scrum.org)", "Leading SAFe", "Sûreté aéroportuaire"],
    "langues": [
        "Français — langue maternelle",
        "Arabe — courant",
        "Anglais — TOEIC 785/990",
        "Espagnol — intermédiaire",
    ],
}

IMPACT = [
    {"n": "7 000", "label": "utilisateurs"},
    {"n": "3 000", "label": "gares équipées"},
    {"n": "10", "label": "personnes pilotées"},
]

# ---------------------------------------------------------------------------
# Experience — real content, identical across variants (order/emphasis only
# changes via the template, not the facts themselves).
# ---------------------------------------------------------------------------
EXPERIENCES = [
    {
        "title": "Product Owner — Outil GMAO (3 000 gares ; 7 000 utilisateurs)",
        "date": "09/2022 – aujourd'hui",
        "company": "TNP Consultants pour SNCF Gares &amp; Connexions",
        "location": "Paris, France · 3 ans",
        "groups": [
            {
                "sub": "Gestion de projet",
                "bullets": [
                    "Pilotage et management AMOA et MOE (10 personnes)",
                    "Arbitrage des besoins métiers et responsabilité de la vision produit",
                    "Pilotage de la conception : élaboration des User Stories, animation des revues "
                    "fonctionnelles, définition des critères d'acceptation et exécution des tests d'acceptation",
                    "Gestion du planning et des risques projet",
                    "Reporting, suivi d'avancement des actions et communication",
                    "Animation d'ateliers de formation auprès des utilisateurs",
                ],
            },
            {
                "sub": "Appui à la gestion de la reprise de données",
                "bullets": [
                    "Définition de la stratégie de reprise de données",
                    "Mise en qualité continue des données mises à disposition de l'outil",
                ],
            },
        ],
        "tools": "<b>Méthode :</b> SAFe, Scrum — <b>Outils :</b> JIRA, Confluence",
        "variant": None,
    },
    {
        "title": "Assistant chef de projet — Compliance",
        "date": "09/2021 – 08/2022",
        "company": "BNP Paribas Real Estate",
        "location": "Paris, France · 1 an",
        "groups": [
            {
                "sub": None,
                "bullets": [
                    "Pilotage de projets d'éthique professionnelle et de sécurité financière",
                    "Planification et animation de comités",
                    "Collecte, validation et priorisation des besoins métier",
                    "Planification des sprints dans un schéma agile et suivi des développements (JIRA)",
                    "Reporting trimestriel (KPI) et présentation des chiffres et graphiques clés",
                    "Création et diffusion de newsletters trimestrielles sur l'avancement des projets",
                ],
            },
        ],
        "tools": None,
        "variant": None,
    },
    {
        "title": "Chef de projet — Business Process Management",
        "date": "03/2020 – 11/2020",
        "company": "DRH Pilotes - Air France",
        "location": "Roissy Charles de Gaulle, France · 8 mois",
        "groups": [
            {
                "sub": None,
                "bullets": [
                    "Modélisation des processus métier au sein du service",
                    "Optimisation des méthodes et outils des processus, amélioration de la performance opérationnelle",
                    "Étude de cadrage pour la mise en place d'un SI et l'adoption d'une méthode agile",
                ],
            },
        ],
        "tools": "<b>Méthode :</b> RUP — <b>Logiciel :</b> Bizagi Modeler — <b>Notion :</b> BPMN",
        "variant": None,
    },
    {
        "title": "Ground Operations Intern",
        "date": "06/2019 – 08/2019",
        "company": "Openskies - Level",
        "location": "Rungis/Orly, France",
        "groups": [
            {
                "sub": None,
                "bullets": [
                    "Mise à jour du manuel d'opérations",
                    "Suivi et optimisation des performances à l'escale",
                    "Réalisation de check-lists pour les contrôles terrain",
                ],
            },
        ],
        "tools": None,
        "variant": "aero",
    },
    {
        "title": "Stagiaire — pôle Maintenance Repair Overhaul",
        "date": "07/2018 – 08/2018",
        "company": "Air France Industries",
        "location": "Blagnac, France",
        "groups": [
            {
                "sub": None,
                "bullets": [
                    "Immersion en équipe de techniciens de maintenance sur A318/A319/A320/A321",
                ],
            },
        ],
        "tools": None,
        "variant": "aero",
    },
]

FORMATION = [
    {
        "title": "Diplôme d'ingénieur — spécialisation avionique",
        "date": "2017 – 2020",
        "company": "École Nationale de l'Aviation Civile (ENAC)",
        "location": "Toulouse, France",
        "bullets": [
            "Spécialisation avionique, opérations et sécurité aérienne",
            "Projets d'étude : rénovation du cockpit d'un A320 (Airbus, Collins Aerospace) ; "
            "spécification du module Lateral Guidance d'un FMS",
        ],
    },
    {
        "title": "Classes préparatoires aux Grandes Écoles — MPSI/MP",
        "date": "2014 – 2017",
        "company": "Lycée Marcelin Berthelot",
        "location": "Saint-Maur-des-Fossés, France",
        "bullets": [],
    },
    {
        "title": "Baccalauréat scientifique — spécialité Mathématiques, mention bien",
        "date": "2013 – 2014",
        "company": "Lycée international Alexandre Dumas",
        "location": "Alger, Algérie",
        "bullets": [],
    },
]

PROJECTS_AERO = [
    {
        "title": "ENAC Automatic Flight System — spécifications fonctionnelles",
        "date": "09/2019 – 01/2020",
        "company": "ENAC",
        "location": "Toulouse, France",
        "bullets": [
            "Spécifications fonctionnelles détaillées du module Lateral Guidance",
            "Exigences détaillées pour toutes les interfaces du système",
        ],
        "tools": "<b>Notion :</b> Model Based System Engineering — <b>Logiciel :</b> CORE",
    },
    {
        "title": "Refonte du cockpit A320 — systèmes de communication",
        "date": "02/2019 – 05/2019",
        "company": "ENAC",
        "location": "Toulouse, France",
        "bullets": [
            "Réalisation d'un plan de développement, de validation, de vérification et d'intégration",
            "Gestion de projet : planification, répartition des ressources, conduite du changement, "
            "gestion des risques",
        ],
        "tools": None,
    },
    {
        "title": "Projet RTM-MLE — ouverture d'une ligne Rotterdam-Malé",
        "date": "09/2018 – 01/2019",
        "company": "ENAC",
        "location": "Toulouse, France",
        "bullets": [
            "Choix de la route et étude du segment ETOPS",
            "Détermination des temps de vol et des charges marchandes",
            "Étude des procédures de réduction de consommation de carburant",
        ],
        "tools": "<b>Logiciels :</b> Winpep, JetPlanner",
    },
]
