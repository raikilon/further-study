"""Pagination strategies for catalog pages that hide later course cards."""

from dataclasses import dataclass
import json
from urllib.parse import urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .program_parser import ProgramParser
from .text_utils import is_same_institution, normalize_url

MAX_SUPSI_WIDGET_PAGES = 40


@dataclass
class PaginationBatch:
    programs: list
    detail_urls: list
    pages_loaded: int = 0
    issues: list = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class HtmlPaginationAdapter:
    """Recognize ordinary next-page links rendered in HTML."""

    NEXT_LABELS = {
        "next", "next page", "weiter", "suivant", "suivante", "successivo",
        "successiva", "prossimo",
    }
    LOAD_MORE_LABELS = {
        "load more", "show more", "see more", "more results", "mehr anzeigen",
        "mehr laden", "weitere laden", "voir plus", "afficher plus",
        "mostra di più", "mostra di piu", "carica altro", "visualizza altri",
    }
    LOAD_MORE_CLASS_MARKERS = (
        "load-more", "load_more", "more-results", "more_results", "show-more",
        "show_more", "pagination-more", "pagination_more",
    )
    NON_PAGINATION_CLASS_MARKERS = (
        "js-collapsed_text--toggle", "intro_text--description--toggle",
        "imd-custom-cards__show-more-bttn", "phzh-card-teaser-list__link",
    )

    def is_next_page_link(self, anchor):
        rel = anchor.get("rel", [])
        classes = anchor.get("class", [])
        aria_label = (anchor.get("aria-label") or "").strip().lower()
        text = " ".join(anchor.stripped_strings).strip().lower()
        href = (anchor.get("href") or "").strip()
        ancestors = [" ".join(parent.get("class", [])).lower() for parent in anchor.parents if getattr(parent, "get", None)]
        if href.startswith("#") or anchor.has_attr("data-slide") or any("carousel" in value or "slider" in value for value in ancestors):
            return False
        if isinstance(rel, str):
            rel = rel.split()
        return (
            "next" in [token.lower() for token in rel]
            or any(token.lower() in {"next", "pagination-next"} for token in classes)
            or aria_label in self.NEXT_LABELS
            or text in self.NEXT_LABELS
        )

    def is_page_number_link(self, anchor):
        classes = [value.lower() for value in anchor.get("class", [])]
        text = " ".join(anchor.stripped_strings).strip()
        ancestor_classes = [
            " ".join(parent.get("class", [])).lower()
            for parent in list(anchor.parents)[:4]
            if getattr(parent, "get", None)
        ]
        context_classes = classes + ancestor_classes
        in_pagination = any("pagination" in value or "pager" in value for value in context_classes)
        non_catalog_context = any(
            any(term in value for term in ("news", "event", "blog", "podcast"))
            for value in context_classes
        )
        return (
            in_pagination
            and not non_catalog_context
            and text.isdigit()
            and not (anchor.get("href") or "").strip().startswith("#")
        )

    def is_load_more_control(self, element):
        classes = " ".join(element.get("class", [])).lower()
        text = " ".join(element.stripped_strings).strip().lower()
        aria = (element.get("aria-label") or "").strip().lower()
        if any(marker in classes for marker in self.NON_PAGINATION_CLASS_MARKERS):
            return False
        if element.has_attr("data-slide"):
            return False
        if any(word in text for word in ("show less", "hide", "weniger anzeigen", "weniger laden")):
            return False

        if any(marker in classes for marker in self.LOAD_MORE_CLASS_MARKERS):
            return True
        if element.has_attr("aria-expanded") or element.has_attr("aria-controls"):
            return False
        if element.name != "button" or (text not in self.LOAD_MORE_LABELS and aria not in self.LOAD_MORE_LABELS):
            return False
        return self._has_listing_context(element)

    @staticmethod
    def _has_listing_context(element):
        listing_terms = ("pagination", "pager", "result", "catalog", "course", "program", "listing", "card-list", "teaser-list", "offers")
        for parent in list(element.parents)[:4]:
            classes = " ".join(parent.get("class", [])).lower()
            if any(term in classes for term in listing_terms):
                return True
        return False

    def followable_links(self, soup, page_url, domain):
        links = set()
        for anchor in soup.select("a[href]"):
            if not (self.is_next_page_link(anchor) or self.is_page_number_link(anchor) or self.is_load_more_control(anchor)):
                continue
            if (anchor.get("href") or "").strip().startswith("#"):
                continue
            href = normalize_url(anchor.get("href"), page_url)
            if href and href != normalize_url(page_url) and is_same_institution(href, domain):
                links.add(href)
        for button in soup.select("button[data-url], button[data-href], button[data-next-url]"):
            if not self.is_load_more_control(button):
                continue
            href = button.get("data-url") or button.get("data-href") or button.get("data-next-url")
            normalized = normalize_url(href, page_url)
            if normalized and is_same_institution(normalized, domain):
                links.add(normalized)
        return sorted(links)

    def inspect(self, soup, page_url):
        findings = {}
        for anchor in soup.select("a[href]"):
            if (anchor.get("href") or "").strip().startswith("#"):
                continue
            if self.is_load_more_control(anchor):
                kind = "load-more-link"
            elif self.is_next_page_link(anchor):
                kind = "next-link"
            elif self.is_page_number_link(anchor):
                kind = "numbered-page-link"
            else:
                continue
            href = normalize_url(anchor.get("href"), page_url)
            status = "followable" if href and href != normalize_url(page_url) else "adapter-required"
            findings[(kind, href or page_url)] = {"kind": kind, "url": href or page_url, "status": status}

        for button in soup.select("button"):
            if not self.is_load_more_control(button):
                continue
            href = button.get("data-url") or button.get("data-href") or button.get("data-next-url")
            normalized = normalize_url(href, page_url) if href else None
            kind = "load-more-button"
            status = "followable" if normalized else "adapter-required"
            findings[(kind, normalized or page_url)] = {"kind": kind, "url": normalized or page_url, "status": status}
        return list(findings.values())


class SupsiWidgetPaginationAdapter:
    """Follow SUPSI's public load-more widget pages and parse their course cards."""

    def __init__(self, parser=None):
        self.parser = parser or ProgramParser()

    def supports(self, provider, soup, page_url):
        host = (urlsplit(page_url).hostname or "").lower()
        return provider["domain"] == "supsi.ch" and host.endswith(".supsi.ch") and bool(soup.select("a.load-more-items"))

    def load_more(self, soup, page_url, provider, fetcher, max_pages):
        result = PaginationBatch(programs=[], detail_urls=[])
        widgets = self._widget_ids(soup)
        if not widgets or max_pages <= 0:
            return result
        max_pages = min(max_pages, MAX_SUPSI_WIDGET_PAGES)

        parsed_url = urlsplit(page_url)
        language = self._language(parsed_url.path)
        seen_card_urls = set()
        for widget_id in widgets:
            for page_number in range(1, max_pages + 1):
                api_url = self._api_url(parsed_url, language, widget_id, page_number)
                response, issue = fetcher.get(api_url)
                if response is None:
                    if issue:
                        result.issues.append("SUPSI catalog page {}: {}".format(page_number, issue))
                    break

                result.pages_loaded += 1
                page_soup = BeautifulSoup(response.content, "html.parser")
                cards = page_soup.select("div.corso")
                if not cards:
                    break
                new_cards = []
                for card in cards:
                    link = card.select_one('a[href*="course-details"]')
                    card_url = normalize_url(link.get("href"), api_url) if link else None
                    if card_url and card_url not in seen_card_urls:
                        seen_card_urls.add(card_url)
                        new_cards.append((card, link))
                if not new_cards:
                    # Some portals repeat the last page for out-of-range page numbers.
                    break
                for card, link in new_cards:
                    self._add_course_card(card, link, api_url, provider, result)
                if result.pages_loaded >= max_pages:
                    return result
        return result

    @staticmethod
    def _widget_ids(soup):
        widget_ids = []
        for button in soup.select("a.load-more-items"):
            widget = button.find_parent(attrs={"data-widget-id": True})
            widget_id = widget.get("data-widget-id") if widget else None
            if widget_id and widget_id not in widget_ids:
                widget_ids.append(widget_id)
        return widget_ids

    @staticmethod
    def _language(path):
        first_segment = next((segment for segment in path.split("/") if segment), "it")
        return first_segment if first_segment in {"de", "fr", "it", "en"} else "it"

    @staticmethod
    def _api_url(page_url, language, widget_id, page_number):
        query = urlencode({"moreelements": "id={};page={}".format(widget_id, page_number)})
        path = "/api/widgets/{}/{}".format(language, widget_id)
        return urlunsplit(("https", page_url.hostname, path, query, ""))

    def _add_course_card(self, card, link, page_url, provider, result):
        program = self.parser.parse_catalog_link(link, page_url, provider)
        if not program:
            return
        detail_url = normalize_url(program["sourceUrl"])
        if detail_url in result.detail_urls:
            return
        result.programs.append(program)
        result.detail_urls.append(detail_url)


class SearchResultsWidgetAdapter:
    """Handle the BFH-style JSON search widget used by several provider sites."""

    def __init__(self, parser=None):
        self.parser = parser or ProgramParser()

    def supports(self, soup, page_url):
        component = soup.select_one(".comp-search-results[data-url][data-state]")
        return bool(component and component.select_one(".more-results-button"))

    def load_more(self, soup, page_url, provider, fetcher, max_pages):
        result = PaginationBatch(programs=[], detail_urls=[])
        component = soup.select_one(".comp-search-results[data-url][data-state]")
        if not component or max_pages <= 0:
            return result

        endpoint = normalize_url(component.get("data-url"), page_url)
        try:
            state = json.loads(component.get("data-state", "{}"))
        except (TypeError, json.JSONDecodeError):
            result.issues.append("Search-results widget has invalid state JSON")
            return result
        if not endpoint or not isinstance(state, dict):
            result.issues.append("Search-results widget is missing its endpoint or state")
            return result

        offset = self._initial_offset(component, state)
        seen_urls = set()
        for _ in range(max_pages):
            payload = dict(state)
            payload["offset"] = offset
            response, issue = fetcher.post_json(endpoint, payload, referer=page_url)
            if response is None:
                if issue:
                    result.issues.append("Search-results pagination: {}".format(issue))
                break
            try:
                data = response.json()
            except ValueError:
                result.issues.append("Search-results pagination returned invalid JSON")
                break

            cards = BeautifulSoup(data.get("resultsGridHtml", ""), "html.parser").select(".search-result-item")
            if not cards:
                break
            result.pages_loaded += 1
            new_cards = 0
            for card in cards:
                link = card.select_one("a[href]")
                program = self.parser.parse_catalog_link(link, page_url, provider) if link else None
                if not program:
                    continue
                source_url = normalize_url(program["sourceUrl"])
                if not source_url or source_url in seen_urls:
                    continue
                seen_urls.add(source_url)
                new_cards += 1
                result.programs.append(program)
                result.detail_urls.append(source_url)

            offset += len(cards)
            if not data.get("moreResultsButton") or new_cards == 0:
                break
        return result

    @staticmethod
    def _initial_offset(component, state):
        try:
            state_count = int(state.get("count", 0))
            if state_count:
                return max(0, state_count)
        except (TypeError, ValueError):
            pass
        return len(component.select(".search-result-item"))
