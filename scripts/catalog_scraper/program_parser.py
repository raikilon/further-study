"""Extracts CAS/MAS records from program pages and catalog links."""

import hashlib
import re
from datetime import date
from urllib.parse import parse_qs, unquote, urlsplit

from bs4 import BeautifulSoup

from .settings import CATALOG_TERMS, CONTINUING_TERMS, FIELD_LABELS, LANGUAGE_PATTERNS, OVERVIEW_TITLE_TERMS, PROVIDER_NAME_OVERRIDES, SUBJECT_KEYWORDS, SUBPAGE_TITLE_TERMS
from .text_utils import clean_text, detect_subject, extract_ects, extract_fee, extract_format, extract_languages, is_same_institution, normalize_url, parse_date, root_domain, start_label, term_matches

def path_has_credential(value):
    for segment in unquote(value.lower()).split("/"):
        segment = segment.strip(" .")
        # Match a credential directory or course slug, not umbrella paths such as
        # /mba-mas-das/ where unrelated pages inherit the word MAS.
        if segment == "mas" or segment.startswith(("mas-", "mas_")):
            return "MAS"
        if segment == "cas" or segment.startswith(("cas-", "cas_")):
            return "CAS"
    return None

def is_program_detail_path(path, credential):
    segments = [segment for segment in unquote(path.lower()).replace("_", "-").split("/") if segment]
    key = credential.lower()
    for position, segment in enumerate(segments):
        if segment == key:
            remainder = segments[position + 1:]
            if len(remainder) == 1:
                return True
            return len(remainder) == 2 and remainder[-1] in {"index.html", "index.htm", "index.php", "index_eng.html", "index_ger.html", "index_fr.html", "index_it.html"}
        if segment.startswith(key + "-"):
            remainder = segments[position + 1:]
            if not remainder:
                return True
            return len(remainder) == 1 and remainder[-1] in {"index.html", "index.htm", "index.php", "index_eng.html", "index_ger.html", "index_fr.html", "index_it.html"}
    return False

def is_specific_program_path(path):
    segments = [segment for segment in unquote(path.lower()).split("/") if segment]
    if len(segments) < 3:
        return False
    last = segments[-1]
    if last in {"cas", "mas", "das", "mba", "weiterbildung", "formation-continue", "continuing-education", "catalog", "catalogue", "index", "index.html"}:
        return False
    return True


def is_course_detail_url(url):
    parsed = urlsplit(url)
    identifiers = parse_qs(parsed.query).get("id", [])
    return parsed.path.rstrip("/").endswith("/course-details") and bool(identifiers)

def is_non_program_url(path):
    normalized = path.lower()
    if re.search(r"(^|[-_/])(?:infoveranstaltung|infoanlass|infoabend|infoevent|infosession)(?:[-_/]|$)", normalized):
        return True
    return any(term in normalized for term in (
        "/news/", "/actualites/", "/actualite/", "/presse/", "/press/", "/stories/",
        "/newsroom/", "/communiques/", "/mitteilungen/", "/imoniteur", "/enrollments",
        "/registration", "/register", "/application-form", "/application_form", "/interesse",
        "/agenda/", "/events/", "/event/", "/veranstaltungen/", "/veranstaltung/", "/case-study/", "/case-studies/",
        "/infoveranstaltung", "/info-anlass", "/infoabend", "/infoevent", "/webinar/", "/alumni/", "/alumni-",
        "/online-anmeldung", "/anmeldung/",
    )) or path.lower().endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".webp", ".svg"))

def is_non_program_record(program):
    title = clean_text(program.get("title", "")).lower()
    url = urlsplit(program.get("sourceUrl", ""))
    path = url.path.lower()
    if is_non_program_url(path):
        return True
    if any(term in title for term in OVERVIEW_TITLE_TERMS) or any(term in title for term in SUBPAGE_TITLE_TERMS):
        return True
    if re.fullmatch(r"cas\s*[-–:]\s*swiss tcm uni", title) or is_generic_award_title(title):
        return True
    if program.get("confidence") == "medium" and not is_program_detail_path(path, program.get("credential", "")):
        return True
    if program.get("confidence") == "low" and not is_program_detail_path(path, program.get("credential", "")) and not is_specific_program_path(path):
        return True
    return False

def is_generic_link_title(title, provider_name=""):
    normalized = clean_text(title).lower().strip(" -|·")
    if normalized in {"home", "homepage", "startseite", "portal", "the manufacture", "la manufacture", "de deutsch", "fr français", "en english", "it italiano", "deutsch", "français", "english", "italiano", "directly to page top", "direkt zum hauptinhalt", "go to top"}:
        return True
    if parse_date(normalized) and not re.search(r"\b(?:CAS|MAS)\b", title, re.I):
        return True
    if provider_name:
        title_words = set(re.findall(r"[a-z0-9]+", normalized)) - {"the", "a", "an", "home", "startseite"}
        provider_words = set(re.findall(r"[a-z0-9]+", clean_text(provider_name).lower()))
        if title_words and title_words.issubset(provider_words):
            return True
    return False


def is_generic_award_title(title):
    normalized = clean_text(title).lower().strip(" -|·")
    pattern = r"(?:cas\s*[-:]?\s*certificate of advanced studies|certificate of advanced studies(?:\s*\(cas\))?|cas\s+weiterbildungen|mas\s+master of advanced studies|master of advanced studies(?:\s*\(mas\))?)"
    return bool(re.fullmatch(pattern, normalized))

def candidate_score(url, anchor_text=""):
    value = (url + " " + anchor_text).lower().replace("_", "-")
    if urlsplit(url).path.lower().endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".webp", ".svg")):
        return 0
    score = 0
    if path_has_credential(urlsplit(url).path) or re.search(r"\b(?:CAS|MAS)\b|Certificate of Advanced Studies|Master of Advanced Studies", url + " " + anchor_text, re.I):
        score += 12
    if any(term in value for term in CONTINUING_TERMS):
        score += 6
    if any(term in value for term in CATALOG_TERMS):
        score += 2
    return score

def find_labeled_value(soup, field):
    label_re = FIELD_LABELS[field]
    for row in soup.select("tr"):
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"], recursive=False)]
        if len(cells) >= 2 and label_re.match(cells[0].rstrip(":")):
            return cells[1]
    for term in soup.find_all(["dt", "strong", "b", "h4", "h5"]):
        label = clean_text(term.get_text(" ", strip=True)).rstrip(":")
        if label_re.match(label):
            sibling = term.find_next(["dd", "td", "p", "span"])
            if sibling:
                value = clean_text(sibling.get_text(" ", strip=True))
                if value and not label_re.match(value.rstrip(":")):
                    return value
    for line in soup.stripped_strings:
        text = clean_text(line)
        match = re.match(r"^([^:：]{2,50})\s*[:：]\s*(.{1,180})$", text)
        if match and label_re.match(match.group(1).strip()):
            return clean_text(match.group(2))
    return ""

def canonical_source(soup, page_url):
    link = soup.find("link", rel=lambda value: value and "canonical" in value)
    if link and link.get("href"):
        canonical = normalize_url(link.get("href"), page_url)
        if canonical and is_same_institution(canonical, root_domain(urlsplit(page_url).hostname)):
            return canonical
    return normalize_url(page_url) or page_url

def provider_name_from_page(soup, current_name, is_homepage=False):
    if not is_homepage:
        return current_name
    if current_name in PROVIDER_NAME_OVERRIDES.values():
        return current_name
    site_name = soup.find("meta", attrs={"property": "og:site_name"})
    title = soup.find("title")
    candidate = clean_text(site_name.get("content", "") if site_name else (title.get_text(" ", strip=True) if is_homepage and title else ""))
    candidate = re.split(r"\s+[|–—]\s+", candidate, maxsplit=1)[0].strip()
    candidate = re.sub(r"^(home|homepage|accueil|startseite)\s*[:–—-]\s*", "", candidate, flags=re.I).strip()
    if len(candidate) < 3 or len(candidate) > 100:
        return current_name
    if candidate.lower() in {"home", "homepage", "startseite", "weiterbildung", "continuing education", "formation continue"}:
        return current_name
    return candidate

class ProgramParser:
    """Parse one program page or one course card from an official provider site."""

    @staticmethod
    def provider_name(soup, current_name, is_homepage=False):
        return provider_name_from_page(soup, current_name, is_homepage)

    @staticmethod
    def parse_page(soup, page_url, provider):
        content = ProgramParser._page_content(soup)
        title = ProgramParser._page_title(soup, content)
        if not title:
            return None

        path = urlsplit(page_url).path.lower().replace("_", "-")
        text = clean_text(content.get_text(" ", strip=True))
        credential = ProgramParser._page_credential(title, path, text)
        if not credential or ProgramParser._is_overview(title, content, text):
            return None

        summary = ProgramParser._summary(soup, content, credential, provider["name"])
        facts = ProgramParser._facts(content, text)
        return ProgramParser._build_program(soup, title, summary, page_url, provider, credential, facts)

    @staticmethod
    def _page_content(soup):
        return soup.find("main") or soup.find("article") or soup.body or soup

    @staticmethod
    def _page_title(soup, content):
        heading = content.find("h1") or soup.find("h1")
        if heading:
            return clean_text(heading.get_text(" ", strip=True))
        title_tag = soup.find("title")
        return clean_text(title_tag.get_text(" ", strip=True) if title_tag else "")

    @staticmethod
    def _page_credential(title, path, text):
        if re.search(r"Master of Advanced Studies|Maîtrise universitaire d'études avancées|Master di Advanced Studies", title, re.I):
            return "MAS"
        if re.search(r"Certificate of Advanced Studies|certificat (?:de formation continue|d'études avancées)|certificato di studi avanzati", title, re.I):
            return "CAS"

        title_mas = bool(re.search(r"\bMAS\b", title, re.I))
        title_cas = bool(re.search(r"\bCAS\b", title, re.I))
        path_credential = path_has_credential(path)
        page_mentions_award = bool(re.search(r"\b(?:CAS|MAS)\b|Certificate of Advanced Studies|Master of Advanced Studies", text, re.I))
        has_award_label = bool(re.search(
            r"(?:degree\s*/\s*certificate|degree awarded|title/qualification|qualification|titel\s*/\s*abschluss|abschluss|titre délivré|diplôme|titolo rilasciato).{0,220}(?:\bCAS\b|\bMAS\b|Certificate of Advanced Studies|Master of Advanced Studies|certificat de formation continue|certificato di studi avanzati)",
            text,
            re.I,
        ))

        if path_credential and page_mentions_award and is_program_detail_path(path, path_credential):
            return path_credential
        if has_award_label and title_mas:
            return "MAS"
        if has_award_label and title_cas:
            return "CAS"
        return None

    @staticmethod
    def _is_overview(title, content, text):
        normalized_title = title.lower().strip(" -|·")
        if any(term in normalized_title for term in OVERVIEW_TITLE_TERMS + SUBPAGE_TITLE_TERMS):
            return True
        if is_generic_award_title(title):
            return True
        if is_generic_link_title(title):
            return True
        if any(term in normalized_title for term in ("all continuing education", "all programs", "all programmes", "course catalogue", "course catalog", "catalogue des cours", "catalogo corsi", "weiterbildungsangebote")):
            return True
        if len(title) < 7 or len(title) > 180:
            return True
        return len(content.select("a[href]")) > 250 and len(re.findall(r"\b(?:CAS|MAS)\b", text, re.I)) > 10

    @staticmethod
    def _summary(soup, content, credential, provider_name):
        meta = soup.find("meta", attrs={"name": re.compile(r"description", re.I)}) or soup.find("meta", attrs={"property": "og:description"})
        description = clean_text(meta.get("content", "")) if meta else ""
        if len(description) < 35:
            description_headings = {"descrizione", "description", "about the program", "about the programme", "presentazione", "presentazione del corso"}
            for heading in content.find_all(["h2", "h3", "h4"]):
                if clean_text(heading.get_text(" ", strip=True)).lower() not in description_headings:
                    continue
                paragraph = heading.find_next("p")
                candidate = clean_text(paragraph.get_text(" ", strip=True)) if paragraph else ""
                if len(candidate) >= 55:
                    description = candidate
                    break
        if len(description) < 35:
            for paragraph in content.find_all(["p", "li"]):
                candidate = clean_text(paragraph.get_text(" ", strip=True))
                lowered = candidate.lower()
                is_notice = any(phrase in lowered for phrase in ("inizia domani", "inizia oggi", "starts tomorrow", "starts today", "course starts tomorrow"))
                if len(candidate) >= 55 and not is_notice and not lowered.startswith(("apply", "register", "home", "menu")):
                    description = candidate
                    break
        if description:
            return description[:420].rstrip()
        return "{} continuing-education program offered by {}.".format(credential, provider_name)

    @staticmethod
    def _facts(content, text):
        language_value = find_labeled_value(content, "language")
        location = find_labeled_value(content, "location")
        duration = find_labeled_value(content, "duration")
        format_value = find_labeled_value(content, "format")
        fee_value = find_labeled_value(content, "fee")
        start_value = find_labeled_value(content, "start")
        start_date = parse_date(start_value)
        if start_date and start_date < date.today().isoformat():
            start_date = None
            start_value = "Next cohort not announced"
        return {
            "city": location or "Not listed",
            "languages": extract_languages(language_value),
            "duration": duration or None,
            "format": extract_format(format_value, location),
            "ects": extract_ects(text),
            "priceCHF": extract_fee(text, fee_value),
            "priceNote": "From" if re.search(r"\b(from|ab|dès|à partir de|da)\b", fee_value, re.I) else None,
            "nextStart": start_date,
            "nextStartLabel": None if start_date else start_label(start_value),
        }

    @staticmethod
    def _tags(title, summary):
        tags = []
        searchable = (title + " " + summary).lower()
        for keywords in SUBJECT_KEYWORDS.values():
            for keyword in keywords:
                if term_matches(keyword, searchable):
                    tag = keyword.replace("\\b", "").replace("*", "").strip()
                    if tag and tag not in tags:
                        tags.append(tag)
                    break
        return tags[:8]

    @staticmethod
    def _build_program(soup, title, summary, page_url, provider, credential, facts):
        source_url = canonical_source(soup, page_url)
        stable = hashlib.sha1((provider["domain"] + "|" + source_url).encode("utf-8")).hexdigest()[:10]
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:64] or "program"
        return {
            "id": "{}-{}".format(slug, stable),
            "title": title,
            "credential": credential,
            "provider": provider["name"],
            "providerDomain": provider["domain"],
            **facts,
            "subject": detect_subject(title, summary, ""),
            "summary": summary,
            "tags": ProgramParser._tags(title, summary),
            "sourceUrl": source_url,
            "verifiedAt": date.today().isoformat(),
            "confidence": "high" if re.search(r"\b(?:CAS|MAS)\b|Certificate of Advanced Studies|Master of Advanced Studies", title, re.I) else "medium",
            "catalogStatus": "active",
        }

    @staticmethod
    def parse_catalog_link(anchor, page_url, provider):
        details = ProgramParser._link_details(anchor, page_url, provider)
        if details is None:
            return None
        title, source_url, credential = details
        card = ProgramParser._course_card(anchor)
        card_text = clean_text(card.get_text(" ", strip=True)) if card else ""
        summary = ProgramParser._card_summary(anchor, title, credential, provider["name"])
        facts = ProgramParser._facts(card, card_text) if card else {}
        stable = hashlib.sha1((provider["domain"] + "|" + source_url).encode("utf-8")).hexdigest()[:10]
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:64] or "program"
        return {
            "id": "{}-{}".format(slug, stable),
            "title": title,
            "credential": credential,
            "provider": provider["name"],
            "providerDomain": provider["domain"],
            "city": facts.get("city", "Not listed"),
            "languages": facts.get("languages", []),
            "subject": detect_subject(title, summary, ""),
            "format": facts.get("format"),
            "duration": facts.get("duration"),
            "ects": facts.get("ects"),
            "priceCHF": facts.get("priceCHF"),
            "priceNote": facts.get("priceNote"),
            "nextStart": facts.get("nextStart"),
            "nextStartLabel": facts.get("nextStartLabel"),
            "summary": summary,
            "tags": ProgramParser._tags(title, summary),
            "sourceUrl": source_url,
            "verifiedAt": date.today().isoformat(),
            "confidence": "low",
            "catalogStatus": "active",
        }

    @staticmethod
    def _link_details(anchor, page_url, provider):
        title = ProgramParser._link_title(anchor)
        if len(title) < 8 or len(title) > 180:
            return None
        source_url = normalize_url(anchor.get("href"), page_url)
        if not source_url or not is_same_institution(source_url, provider["domain"]):
            return None
        source_path = urlsplit(source_url).path.lower()
        if is_non_program_url(source_path) or (urlsplit(source_url).hostname or "").lower().startswith("pdf."):
            return None

        credential = ProgramParser._link_credential(title, source_url)
        if not credential or ProgramParser._is_link_title_excluded(title, source_url, credential, provider["name"]):
            return None
        return title, source_url, credential

    @staticmethod
    def _link_title(anchor):
        card = ProgramParser._course_card(anchor)
        heading = card.find(["h3", "h2"]) if card else None
        if heading:
            return clean_text(heading.get_text(" ", strip=True))
        return clean_text(anchor.get_text(" ", strip=True) or anchor.get("title") or anchor.get("aria-label"))

    @staticmethod
    def _course_card(anchor):
        sup_course = anchor.find_parent("div", class_="corso")
        if sup_course:
            return sup_course
        for parent in anchor.parents:
            if "search-result-item" in parent.get("class", []):
                return parent
        return None

    @staticmethod
    def _link_credential(title, source_url):
        if re.search(r"Master of Advanced Studies|Maîtrise universitaire d'études avancées|Master di Advanced Studies|\bMAS\b", title, re.I):
            return "MAS"
        if re.search(r"Certificate of Advanced Studies|certificat (?:de formation continue|d'études avancées)|certificato di studi avanzati|\bCAS\b", title, re.I):
            return "CAS"
        if is_course_detail_url(source_url):
            query = urlsplit(source_url).query
            query_credential = re.search(r"(?:^|[-_=])(?P<credential>CAS|MAS)(?:[-_=&]|$)", query, re.I)
            if query_credential:
                return query_credential.group("credential").upper()
            return None
        source_path = urlsplit(source_url).path
        path_credential = path_has_credential(source_path)
        return path_credential if path_credential and is_program_detail_path(source_path, path_credential) else None

    @staticmethod
    def _is_link_title_excluded(title, source_url, credential, provider_name):
        source_path = urlsplit(source_url).path
        normalized = title.lower().strip(" -|·")
        if any(term in normalized for term in OVERVIEW_TITLE_TERMS + SUBPAGE_TITLE_TERMS):
            return True
        if is_generic_award_title(title):
            return True
        if is_generic_link_title(title, provider_name):
            return True
        if not is_course_detail_url(source_url) and not is_program_detail_path(source_path, credential) and not is_specific_program_path(source_path):
            return True
        return False

    @staticmethod
    def _card_summary(anchor, title, credential, provider_name):
        parent = anchor
        for _ in range(4):
            parent = parent.parent
            if not parent:
                break
            context = clean_text(parent.get_text(" ", strip=True))
            if len(context) < 70 or len(context) > 900:
                continue
            if len(parent.select("a[href]")) <= 1 and len(re.findall(r"\b(?:CAS|MAS)\b", context, re.I)) <= 1:
                context = clean_text(context.replace(title, "", 1))
                if len(context) >= 45:
                    return context[:360].rstrip()
        return "{} continuing-education program offered by {}. Open the official page for details.".format(credential, provider_name)
