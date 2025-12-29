# sources/rss_generic.py
"""Generic RSS/Atom fetcher.

한국어 설명:
- Google News 전용 파서(sources/google_news.py) 말고, 일반 RSS/Atom(예: TechRadar)도 읽기 위한 모듈.
- item/entry에서 title/link/summary(또는 description)를 최대한 안전하게 뽑아낸다.

English note:
- A small generic RSS/Atom parser (no feedparser dependency).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import requests


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    if not s:
        return ""
    s = _TAG_RE.sub(" ", s)
    return " ".join(s.split()).strip()


def fetch_generic_rss(feed_url: str, limit: int = 10):
    """Fetch generic RSS or Atom.

    Returns list of dicts with: title, link, pubDate, description, source.
    """
    r = requests.get(feed_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    text = r.text
    root = ET.fromstring(text)

    # Atom uses namespaces; ElementTree requires explicit namespace handling.
    # We'll match tags by suffix (e.g., '{...}entry' endswith 'entry').
    def _endswith(tag: str, suffix: str) -> bool:
        return tag.lower().endswith(suffix)

    items = []

    # RSS: channel/item
    rss_items = [el for el in root.iter() if _endswith(el.tag, "item")]
    if rss_items:
        for it in rss_items[:limit]:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub_date = (it.findtext("pubDate") or it.findtext("date") or "").strip()
            desc = (it.findtext("description") or it.findtext("summary") or "").strip()
            desc = _strip_html(desc)
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "pubDate": pub_date,
                    "description": desc,
                    "source": "",
                    "source_url": feed_url,
                })
        return items

    # Atom: entry
    atom_entries = [el for el in root.iter() if _endswith(el.tag, "entry")]
    for ent in atom_entries[:limit]:
        title = (ent.findtext("title") or "").strip()

        # Atom link is in <link href="..." />
        link = ""
        for lk in list(ent):
            if _endswith(lk.tag, "link"):
                href = (lk.get("href") or "").strip()
                rel = (lk.get("rel") or "").strip()
                if href and (not rel or rel == "alternate"):
                    link = href
                    break
        if not link:
            link = (ent.findtext("link") or "").strip()

        pub_date = (ent.findtext("updated") or ent.findtext("published") or "").strip()
        desc = (ent.findtext("summary") or ent.findtext("content") or "").strip()
        desc = _strip_html(desc)

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "description": desc,
                "source": "",
                "source_url": feed_url,
            })

    return items
