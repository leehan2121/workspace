# rss_sources_loader.py
# -*- coding: utf-8 -*-
"""Load/merge RSS sources from a CSV file.

CSV format (header required):
publisher,title,categories,url

- categories: pipe-separated (e.g., "tech|science") or "_all_"
- This module merges the URLs into config.EXTRA_RSS_FEEDS_GLOBAL / BY_TOPIC.

이 모듈은 CSV로 관리하는 RSS 목록을 읽어서 config의 EXTRA_RSS_* 목록에 병합합니다.
"""

from __future__ import annotations

import csv
import os
from typing import Dict, List, Tuple

import config

# Map CSV category tokens -> internal topic keys.
# CSV 카테고리 토큰 -> 내부 topic 키 매핑
CATEGORY_TOKEN_MAP = {
    "politics": "politics",
    "economy": "economy",
    "society": "society",
    "culture": "culture_ent",
    "entertainment": "culture_ent",
    "sports": "sports",
    "international": "world",
    "world": "world",
    "tech": "it_science",
    "science": "it_science",
    "it": "it_science",
    "column": "opinion",
    "opinion": "opinion",
    "health": "health",
    "women": "women",
    "people": "people",
    "cartoon": "cartoon",
}

def _split_categories(raw: str) -> List[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    return [c.strip() for c in raw.split("|") if c.strip()]

def load_rss_sources_csv(path: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """Return (global_urls, by_topic_urls) from a CSV file."""
    if not os.path.exists(path):
        return [], {}

    global_urls: List[str] = []
    by_topic: Dict[str, List[str]] = {}

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            cats = (row.get("categories") or "").strip()
            if not url:
                continue

            if cats == "_all_":
                global_urls.append(url)
                continue

            tokens = _split_categories(cats)
            if not tokens:
                global_urls.append(url)
                continue

            mapped_any = False
            for t in tokens:
                topic = CATEGORY_TOKEN_MAP.get(t, None)
                if not topic:
                    continue
                by_topic.setdefault(topic, []).append(url)
                mapped_any = True

            if not mapped_any:
                # Unknown category token: treat as global fallback
                global_urls.append(url)

    # Dedup while preserving order
    def dedup(seq: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    global_urls = dedup(global_urls)
    by_topic = {k: dedup(v) for k, v in by_topic.items()}
    return global_urls, by_topic

def merge_rss_sources_from_csv(path: str) -> None:
    """Merge CSV sources into config.EXTRA_RSS_* in-place."""
    global_urls, by_topic = load_rss_sources_csv(path)

    # Merge into global
    if global_urls:
        config.EXTRA_RSS_FEEDS_GLOBAL = list(dict.fromkeys(config.EXTRA_RSS_FEEDS_GLOBAL + global_urls))

    # Merge into per-topic
    for topic, urls in by_topic.items():
        if not urls:
            continue
        cur = config.EXTRA_RSS_FEEDS_BY_TOPIC.get(topic, [])
        config.EXTRA_RSS_FEEDS_BY_TOPIC[topic] = list(dict.fromkeys(cur + urls))
