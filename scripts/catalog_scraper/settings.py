"""Scraper configuration and classification vocabularies."""

import re
from pathlib import Path

DIRECTORY_URL = "https://www.swissuniversities.ch/en/topics/studying/accredited-swiss-higher-education-institutions"

OUTPUT_PATH = Path("public/data/programs.json")

REPORT_PATH = Path("public/data/scrape-report.json")

PROVIDER_START_PAGES = {
    # SUPSI's public catalog paginates results through its course widget API.
    "supsi.ch": ("https://formazionecontinua.supsi.ch/it/catalogocorsi",),
}

USER_AGENT = "FurtherStudyCHCatalogBot/1.0 (+respectful educational program index)"

REQUEST_TIMEOUT = 8

REQUEST_DELAY_SECONDS = 0.25

MAX_PAGES_PER_PROVIDER = 100

MAX_WORKERS = 16

MAX_SITEMAP_LOCATIONS = 1200

MAX_CANDIDATE_LINKS = 450

SKIP_ROOTS = {
    "swissuniversities.ch", "akkreditierungsrat.ch", "fedlex.admin.ch",
    "linkedin.com", "facebook.com", "instagram.com", "youtube.com",
    "x.com", "twitter.com", "tiktok.com", "wikipedia.org", "wa.me", "t.me",
    "xing.com", "bsky.app", "he-arc.ch",
}

# Canonical hosts confirmed with curl when the directory URL redirects to an
# unrelated host, has a broken certificate, or is no longer the institution's
# current website.
PROVIDER_DOMAIN_ALIASES = {
    "ecav.ch": ("edhea.ch",),
    "eesp.ch": ("hetsl.ch",),
    "sfivet.swiss": ("sfuvet.swiss",),
    "unisi.ch": ("usi.ch",),
    "unizh.ch": ("uzh.ch",),
}

PROVIDER_HOMEPAGE_OVERRIDES = {
    "cesarritzcolleges.edu": "https://www.cesarritzcolleges.edu/en/",
    "ecav.ch": "https://edhea.ch/",
    "eesp.ch": "https://www.hetsl.ch/",
    "hepl.ch": "https://www.hepl.ch/accueil.html",
    "phbern.ch": "https://www.phbern.ch/",
    "phsg.ch": "https://www.phsg.ch/de",
    "sfivet.swiss": "https://www.sfuvet.swiss/",
    "unisi.ch": "https://www.usi.ch/it",
    "unizh.ch": "https://www.uzh.ch/en.html",
}

# These sites fail on the bare host but work when their verified www host is
# retained. URL normalization normally removes www to avoid duplicate URLs.
PRESERVE_WWW_DOMAINS = {
    "cesarritzcolleges.edu", "hepl.ch", "hetsl.ch", "phbern.ch", "phsg.ch",
}

PROVIDER_NAME_OVERRIDES = {
    "epfl.ch": "EPFL",
    "ethz.ch": "ETH Zurich",
    "unibas.ch": "University of Basel",
    "unibe.ch": "University of Bern (UniBE)",
    "unifr.ch": "University of Fribourg",
    "unige.ch": "University of Geneva (UNIGE)",
    "unil.ch": "University of Lausanne (UNIL)",
    "unilu.ch": "University of Lucerne",
    "unine.ch": "University of Neuchâtel",
    "unisg.ch": "University of St. Gallen (HSG)",
    "unisi.ch": "Università della Svizzera italiana (USI)",
    "unizh.ch": "University of Zurich (UZH)",
    "uzh.ch": "University of Zurich (UZH)",
    "bfh.ch": "Bern University of Applied Sciences (BFH)",
    "fhnw.ch": "University of Applied Sciences and Arts Northwestern Switzerland (FHNW)",
    "hslu.ch": "Lucerne University of Applied Sciences and Arts (HSLU)",
    "ost.ch": "Eastern Switzerland University of Applied Sciences (OST)",
    "supsi.ch": "University of Applied Sciences and Arts of Southern Switzerland (SUPSI)",
    "kalaidos-fh.ch": "Kalaidos University of Applied Sciences",
    "hevs.ch": "HES-SO Valais-Wallis",
    "hesge.ch": "HES-SO Genève",
    "hefr.ch": "HES-SO Fribourg",
    "zhdk.ch": "Zurich University of the Arts (ZHdK)",
    "zhaw.ch": "Zurich University of Applied Sciences (ZHAW)",
    "fh-hwz.ch": "Hochschule für Wirtschaft Zürich (HWZ)",
    "hwz.ch": "Hochschule für Wirtschaft Zürich (HWZ)",
    "phlu.ch": "Pädagogische Hochschule Luzern (PH Luzern)",
    "phzh.ch": "Pädagogische Hochschule Zürich (PH Zürich)",
    "phgr.ch": "Pädagogische Hochschule Graubünden (PHGR)",
    "phsz.ch": "Pädagogische Hochschule Schwyz (PHSZ)",
    "phsg.ch": "Pädagogische Hochschule St. Gallen (PHSG)",
    "phsh.ch": "Pädagogische Hochschule Schaffhausen (PHSH)",
    "hfh.ch": "Interkantonale Hochschule für Heilpädagogik (HfH)",
    "phtg.ch": "Pädagogische Hochschule Thurgau (PHTG)",
    "accademiadimitri.ch": "Accademia Teatro Dimitri (SUPSI)",
}

CONTINUING_TERMS = (
    "continuing-education", "continuing_education", "continuing education",
    "further-education", "further education", "lifelong-learning", "lifelong learning",
    "weiterbildung", "formation-continue", "formation continue", "formationcontinue",
    "formazione-continua", "formazione continua", "formation-professionnelle",
    "executive-education", "executive education", "formation-continuee",
)

CATALOG_TERMS = (
    "catalog", "catalogue", "catalogo", "course-list", "course-listing", "all-courses",
    "cours", "kurse", "angebote", "offres", "offerta", "programmes", "programme",
)

OVERVIEW_TITLE_TERMS = (
    "continuing education", "further education", "lifelong learning", "weiterbildung",
    "formation continue", "formation continuee", "formazione continua", "course catalogue",
    "course catalog", "catalogue des cours", "catalogo corsi", "all programs", "all courses",
    "offre de formation", "unsere angebote", "program overview", "programmübersicht", "mba, mas, das",
    "mas + emba", "mas/cas/das", "cas (unterteilung)", "cas certificate of advanced studies", "cas - certificate of advanced studies",
)

SUBPAGE_TITLE_TERMS = (
    "admission", "registration", "inscription", "formulaire", "anmeldung", "application form", "interesse",
    "ausbildungsziel", "eignung", "zulassung", "studiendaten", "calendar", "calendrier",
    "eligibility", "requirements", "course dates", "program dates", "study data", "objectives",
    "objectifs", "admission requirements", "registration form", "registration deadline",
    "termine", "terminplan", "stundenplan", "dates", "flyer", "brochure", "download",
    "dossier", "contact", "kontakt", "navigation", "startseite", "diplomfeier", "rückschau",
    "info-anlass", "infoabend", "infoveranstaltung", "webinar", "open day", "faqs", "frequently asked questions",
    "ausführungsbestimmungen", "studienordnung", "studienplan", "règlement", "reglement", "pdf herunterladen",
    "direkt zum seitenanfang", "sprunglinks", "impressum", "datenschutz",
    "module", "modul", "overview", "überblick", "course structure", "program structure", "programme structure",
    "infoanlass", "infoabend", "infoveranstaltung", "info event", "infosession",
)

LANGUAGE_PATTERNS = {
    "de": re.compile(r"\b(deutsch|german|allemand|tedesco)\b", re.I),
    "fr": re.compile(r"\b(français|francais|french|français|francese)\b", re.I),
    "it": re.compile(r"\b(italiano|italian|italien|italienisch)\b", re.I),
    "en": re.compile(r"\b(english|anglais|englisch|inglese)\b", re.I),
}

MONTHS = {
    "jan": 1, "january": 1, "januar": 1, "janvier": 1, "gennaio": 1,
    "feb": 2, "february": 2, "februar": 2, "février": 2, "fevrier": 2, "febbraio": 2,
    "mar": 3, "march": 3, "märz": 3, "maerz": 3, "mars": 3, "marzo": 3,
    "apr": 4, "april": 4, "avril": 4, "aprile": 4,
    "may": 5, "mai": 5, "maggio": 5,
    "jun": 6, "june": 6, "juni": 6, "juin": 6, "giugno": 6,
    "jul": 7, "july": 7, "juli": 7, "juillet": 7, "luglio": 7,
    "aug": 8, "august": 8, "août": 8, "aout": 8, "agosto": 8,
    "sep": 9, "sept": 9, "september": 9, "septembre": 9, "settembre": 9,
    "oct": 10, "october": 10, "oktober": 10, "octobre": 10, "ottobre": 10,
    "nov": 11, "november": 11, "novembre": 11,
    "dec": 12, "december": 12, "dezember": 12, "décembre": 12, "decembre": 12, "dicembre": 12,
}

SUBJECT_KEYWORDS = {
    "ai-data": ("data science", "data analytics", "machine learning", "artificial intelligence", "\bai\b", "cyber", "digital*", "informatik", "computer science", "numérique", "informatique", "digitale", "informatica"),
    "business-leadership": ("management", "leadership", "business", "finance", "project", "organisation", "wirtschaft", "führung", "strategie", "gestion", "impresa"),
    "health-life-sciences": ("health", "medical", "medicine", "life science", "pharma", "biotech", "nursing", "gesundheit", "medizin", "santé", "médecine", "salute", "sanità"),
    "arts-society": ("arts", "design", "culture", "education", "social work", "music", "theatre", "kunst", "bildung", "sozial", "artificial", "artistic", "teatro", "arti"),
    "sustainability": ("sustainab*", "environment", "climate", "energy", "esg", "nachhalt*", "umwelt", "durable", "environnement", "développement durable", "sviluppo sostenibile", "ambiente"),
}

FIELD_LABELS = {
    "language": re.compile(r"^(language|teaching language|language of instruction|instruction language|unterrichtssprache|langue(?:s)? d['’]enseignement|langue d'instruction|lingua d['’]insegnamento|lingua di insegnamento)$", re.I),
    "location": re.compile(r"^(location|study location|place|lieu|lieu de formation|standort|studienort|ort|luogo|sede)$", re.I),
    "duration": re.compile(r"^(duration|length|dauer|durée|durata)$", re.I),
    "format": re.compile(r"^(format|study format|mode|mode of study|delivery|delivery mode|erogazione|modalità(?: di erogazione)?|modalita(?: di erogazione)?|modalité(?:s)?|studienform|durchführungsform)$", re.I),
    "fee": re.compile(r"^(cost|costs|tuition|tuition fee|fee|fees|price|prix|coût|cout|kosten|kurskosten|costo|costi|tasse)$", re.I),
    "start": re.compile(r"^(next start|start date|start|begin|beginn|startdatum|date de début|début|date de demarrage|data inizio|inizio|nächste durchführung|nächster start|prochaine session|next session)$", re.I),
}
