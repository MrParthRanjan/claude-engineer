"""SCMP Daily Reader — RSS Fetching & Article Extraction"""

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from .config import CONFIG


@dataclass
class Article:
    title: str
    link: str
    description: str
    category: str
    published: str
    full_text: Optional[str] = None
    ai_summary: Optional[str] = None
    crux: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Article":
        return cls(**d)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SCMPDailyReader/1.0; +https://github.com)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/rss+xml",
}


def _clean_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def _parse_rss_date(date_str: str) -> str:
    """Try common RSS date formats, return formatted string."""
    if not date_str:
        return ""
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%d %b %Y, %I:%M %p")
        except ValueError:
            continue
    return date_str[:20]  # fallback: raw string truncated


def _fetch_article_text(url: str) -> Optional[str]:
    """Attempt to scrape visible article body. Returns None on paywall/error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=CONFIG.request_timeout)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        for sel in ["div.article-body", "div[class*='article-body']", "article"]:
            el = soup.select_one(sel)
            if el:
                text = re.sub(r"\s+", " ", el.get_text(separator=" ")).strip()
                if len(text) > 200:
                    return text[:3000]
        return None
    except Exception as exc:
        logger.debug(f"Article fetch failed for {url}: {exc}")
        return None


def _parse_feed(xml_text: str, category: str) -> List[Article]:
    """Parse raw RSS/Atom XML and return Article list."""
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    articles = []
    try:
        root = ET.fromstring(xml_text)
        # RSS 2.0
        items = root.findall(".//item")
        if not items:
            # Atom
            items = root.findall(".//atom:entry", ns)

        for entry in items[: CONFIG.articles_per_category]:
            def g(tag: str) -> str:
                el = entry.find(tag)
                if el is None:
                    el = entry.find(f"atom:{tag}", ns)
                return (el.text or "").strip() if el is not None else ""

            title = g("title")
            link_el = entry.find("link")
            if link_el is not None:
                link = link_el.text or link_el.get("href", "")
            else:
                link = ""
            link = link.strip()

            desc = _clean_html(g("description") or g("summary"))
            pub = _parse_rss_date(g("pubDate") or g("published") or g("updated"))

            if title:
                articles.append(
                    Article(
                        title=title,
                        link=link,
                        description=desc,
                        category=category,
                        published=pub,
                    )
                )
    except ET.ParseError as exc:
        logger.warning(f"XML parse error for {category}: {exc}")
    return articles


def fetch_category(category: str, url: str, fallback_url: Optional[str] = None) -> List[Article]:
    logger.info(f"Fetching {category}...")
    for attempt_url in filter(None, [url, fallback_url]):
        try:
            resp = requests.get(attempt_url, headers=HEADERS, timeout=CONFIG.request_timeout)
            if resp.status_code == 200:
                articles = _parse_feed(resp.text, category)
                if articles:
                    return articles
            else:
                logger.debug(f"{category}: HTTP {resp.status_code} on {attempt_url}")
        except Exception as exc:
            logger.debug(f"{category}: request error on {attempt_url}: {exc}")
    logger.warning(f"All sources failed for {category}")
    return []


def fetch_all_categories() -> Dict[str, List[Article]]:
    result: Dict[str, List[Article]] = {}
    for cat in CONFIG.feeds:
        primary  = CONFIG.feeds.get(cat)
        fallback = CONFIG.fallback_feeds.get(cat)
        articles = fetch_category(cat, primary, fallback)
        if articles:
            result[cat] = articles
        time.sleep(0.5)
    return result


# ──────────────────────────────────────────────
# Cache — one JSON file per calendar day
# ──────────────────────────────────────────────

def _cache_key() -> str:
    return date.today().isoformat()


def load_cache() -> Optional[Dict[str, List[Article]]]:
    try:
        with open(CONFIG.cache_file) as f:
            raw = json.load(f)
        if raw.get("date") != _cache_key():
            return None
        result = {}
        for cat, items in raw.get("categories", {}).items():
            result[cat] = [Article.from_dict(a) for a in items]
        return result
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def save_cache(data: Dict[str, List[Article]]) -> None:
    payload = {
        "date": _cache_key(),
        "categories": {
            cat: [a.to_dict() for a in articles]
            for cat, articles in data.items()
        },
    }
    with open(CONFIG.cache_file, "w") as f:
        json.dump(payload, f, indent=2)


def get_articles(force_refresh: bool = False) -> Dict[str, List[Article]]:
    if not force_refresh:
        cached = load_cache()
        if cached:
            logger.info("Loaded today's digest from cache.")
            return cached
    data = fetch_all_categories()
    save_cache(data)
    return data
