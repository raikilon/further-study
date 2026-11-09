"""Small, dependency-light helpers shared by scraper modules."""

import hashlib
import json
import re
import unicodedata
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit

from .settings import LANGUAGE_PATTERNS, MONTHS, PRESERVE_WWW_DOMAINS, PROVIDER_DOMAIN_ALIASES, SUBJECT_KEYWORDS

def clean_text(value):
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()

def root_domain(host):
    host = (host or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) < 2:
        return host
    if host.endswith(".admin.ch") and len(parts) >= 3:
        return ".".join(parts[-3:])
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "ac", "edu", "gov", "net"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])

def normalize_url(url, base=None):
    if base:
        url = urljoin(base, url)
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    scheme = "https"
    host = parsed.hostname.lower()
    if host.startswith("www.") and host[4:] not in PRESERVE_WWW_DOMAINS:
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((scheme, host, path, urlencode(query, doseq=True), ""))

def is_same_institution(url, domain):
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    allowed_domains = (domain, *PROVIDER_DOMAIN_ALIASES.get(domain, ()))
    return any(host == allowed or host.endswith("." + allowed) for allowed in allowed_domains)

def parse_date(value):
    value = clean_text(value)
    match = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", value)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            pass
    match = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b", value)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat()
        except ValueError:
            pass
    month_pattern = "|".join(sorted((re.escape(month) for month in MONTHS), key=len, reverse=True))
    patterns = [
        re.compile(r"\b(\d{1,2})\.?\s+(" + month_pattern + r")\.?\s+(20\d{2})\b", re.I),
        re.compile(r"\b(" + month_pattern + r")\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(20\d{2})\b", re.I),
    ]
    for index, pattern in enumerate(patterns):
        match = pattern.search(value)
        if not match:
            continue
        if index == 0:
            day, month_name, year = int(match.group(1)), match.group(2).lower(), int(match.group(3))
        else:
            month_name, day, year = match.group(1).lower(), int(match.group(2)), int(match.group(3))
        try:
            return date(year, MONTHS[month_name], day).isoformat()
        except (KeyError, ValueError):
            continue
    return None

def start_label(value):
    value = clean_text(value)
    if not value:
        return None
    year = re.search(r"\b20\d{2}\b", value)
    if not year:
        return None
    season = re.search(r"(spring|summer|autumn|fall|winter|frühling|fruehling|sommer|herbst|hiver|printemps|automne|estate|inverno|primavera|autunno)\s+(?:semester\s+)?20\d{2}|20\d{2}\s+(spring|summer|autumn|fall|winter|frühling|fruehling|sommer|herbst|hiver|printemps|automne|estate|inverno|primavera|autunno)", value, re.I)
    if season:
        return clean_text(season.group(0))
    return year.group(0)

def extract_languages(value):
    found = [code for code, pattern in LANGUAGE_PATTERNS.items() if pattern.search(value or "")]
    return found

def detect_subject(title, summary, full_text):
    for candidate in (title, summary, full_text):
        normalized = clean_text(candidate).lower()
        scores = {}
        for subject, keywords in SUBJECT_KEYWORDS.items():
            scores[subject] = sum(1 for keyword in keywords if term_matches(keyword, normalized))
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
    return "other"

def term_matches(keyword, text):
    if "\\b" in keyword:
        return bool(re.search(keyword, text, re.I))
    if keyword.endswith("*"):
        return bool(re.search(r"\b" + re.escape(keyword[:-1]) + r"\w*", text, re.I))
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text, re.I))

def extract_ects(text):
    match = re.search(r"\b(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:ECTS(?:[- ]?credits?)?|crédits? ECTS|crediti ECTS)\b", text, re.I)
    if not match:
        match = re.search(r"\bECTS\s*[:\-]?\s*(\d{1,3}(?:[.,]\d{1,2})?)\b", text, re.I)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", "."))
        return value if value > 0 else None
    except ValueError:
        return None

def extract_fee(text, fee_field=""):
    context = fee_field or ""
    if not context:
        for match in re.finditer(r"\b(?:costs?|tuition|fees?|price|prix|coût|cout|kosten|costo|costi)\b", text, re.I):
            context = text[match.start():match.start() + 180]
            if re.search(r"(?:CHF|Fr\.?|SFr\.?)\s*[\d]", context, re.I) or re.search(r"[\d][\d\s'’.,]*\s*CHF", context, re.I):
                break
    amount = re.search(r"(?:CHF|Fr\.?|SFr\.?)\s*([0-9][0-9\s'’.,]{0,18})", context, re.I)
    if not amount:
        amount = re.search(r"([0-9][0-9\s'’.,]{0,18})\s*CHF\b", context, re.I)
    if not amount:
        return None
    raw = amount.group(1).strip()
    raw = re.sub(r"[.,](?:-|\d{1,2})$", "", raw)
    digits = re.sub(r"\D", "", raw)
    try:
        return int(digits) if digits else None
    except ValueError:
        return None

def extract_format(value, full_text):
    text = (value or "") + " " + full_text[:6000]
    lowered = text.lower()
    online = any(word in lowered for word in ("online", "remote", "distance learning", "à distance", "distanciel", "fernunterricht", "a distanza"))
    onsite = any(word in lowered for word in ("in person", "on-site", "on campus", "présentiel", "presentiel", "vor ort", "präsenz", "in presenza"))
    if "hybrid" in lowered or "blended" in lowered or (online and onsite):
        return "hybrid"
    if online:
        return "online"
    if onsite:
        return "in-person"
    if value and any(word in lowered for word in ("to be confirmed", "à définir", "da definire")):
        return "varies"
    return None

def source_key(url):
    return normalize_url(url) or url

def program_identity(program):
    source = urlsplit(program.get("sourceUrl", ""))
    domain = program.get("providerDomain") or root_domain(source.hostname or "")
    normalized_title = unicodedata.normalize("NFKD", program.get("title", ""))
    normalized_title = normalized_title.encode("ascii", "ignore").decode("ascii").lower()
    normalized_title = re.sub(r"[^a-z0-9]+", " ", normalized_title).strip()
    return domain, normalized_title

def read_existing(path):
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)

def program_quality(program):
    score = 1 if program.get("confidence") == "high" else 0
    score += sum(program.get(field) not in (None, "", []) for field in ("languages", "duration", "ects", "priceCHF", "nextStart", "city"))
    score += 1 if len(program.get("summary", "")) > 80 else 0
    return score
