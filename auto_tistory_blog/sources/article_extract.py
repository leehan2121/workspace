# sources/article_extract.py

"""기사 링크에서 본문 단서를 뽑아오는 가벼운 추출기.

한국어
- RSS는 제목/링크만 있는 경우가 많아, LLM 출력이 두루뭉술해지기 쉽습니다.
- meta description(메타 설명)과 일부 문단 텍스트를 추출해 LLM에게 제공합니다.

English
- RSS often contains only title/link, which makes LLM output generic.
- We extract meta description and a few paragraph texts to provide clues.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class ArticleHint:
    """LLM에 전달할 '기사 단서' 묶음.

    Article hints for LLM.
    """

    final_url: str
    og_title: str
    description: str
    excerpt: str


def _strip_tags(html: str) -> str:
    """HTML 태그 제거.

    Strip HTML tags.
    """
    if not html:
        return ""
    # script/style 제거
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<.*?>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


def _find_meta_content(html: str, *, prop: str = "", name: str = "") -> str:
    """og/meta 태그에서 content를 추출.

    Extract meta content from og/meta tags.
    """
    if not html:
        return ""

    if prop:
        m = re.search(
            rf'(?is)<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            html,
        )
        if m:
            return m.group(1).strip()

    if name:
        m = re.search(
            rf'(?is)<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            html,
        )
        if m:
            return m.group(1).strip()

    return ""


def fetch_article_hint(url: str, *, timeout_sec: int = 12, max_chars: int = 1600) -> Optional[ArticleHint]:
    """기사 링크에서 요약 단서를 추출.

    한국어
    - 목적: '정답' 본문을 뽑는 게 아니라, LLM이 재구성할 때 쓸 '재료'를 주는 것
    - 전략: 메타 설명 + 문단 텍스트 일부만 추출

    English
    - Goal: not to fully scrape the article, but to provide clues for rewriting
    - Strategy: meta description + a few paragraph texts
    """
    if not url:
        return None

    try:
        r = requests.get(url, timeout=timeout_sec, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        r.raise_for_status()
        html = r.text or ""
        final_url = r.url or url
    except Exception:
        return None

    og_title = _find_meta_content(html, prop="og:title")
    description = _find_meta_content(html, prop="og:description") or _find_meta_content(html, name="description")

    # 문단 후보: <p> 텍스트를 여러 개 모아서 하나의 excerpt로
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", html)
    cleaned = []
    for p in paras:
        t = _strip_tags(p)
        if not t:
            continue
        # 너무 짧은 문단 제거
        if len(t) < 25:
            continue
        cleaned.append(t)
        if sum(len(x) for x in cleaned) >= max_chars:
            break

    excerpt = " ".join(cleaned)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    excerpt = excerpt[:max_chars].rstrip()

    return ArticleHint(
        final_url=final_url,
        og_title=og_title[:180].strip(),
        description=description[:320].strip(),
        excerpt=excerpt,
    )
