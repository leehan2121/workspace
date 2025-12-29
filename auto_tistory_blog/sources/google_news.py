"""sources/google_news.py

RSS 수집기 (Google News + 일반 RSS/Atom 겸용)

이 파일은 여러 RSS 소스를 같은 방식으로 처리하기 위해,
XML 네임스페이스가 섞여 있어도 item/entry 를 찾아서 파싱하도록 만들어져 있다.

✅ 목표
- Google News RSS: <item> 기반
- TechRadar 등 일반 RSS: <item> 기반
- Atom: <entry> 기반

주의:
- feedparser 같은 외부 의존성을 추가하지 않고(ElementTree만 사용)
  'tag가 namespace를 포함'하는 경우에도 동작하도록 tag 끝부분으로 매칭한다.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import requests
import xml.etree.ElementTree as ET


DEFAULT_HEADERS = {
    # 구글 뉴스가 User-Agent 없으면 403/429를 주는 케이스가 있어서 최대한 "브라우저처럼".
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://news.google.com/",
}


def _local_name(tag: str) -> str:
    """{namespace}tag 형태에서 tag만 꺼낸다 / Extract localname."""
    if not tag:
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _find_child_text(parent: ET.Element, name: str) -> str:
    """Namespace 무시하고 child text 찾기 / Find child text ignoring namespace."""
    name = name.lower()
    for ch in list(parent):
        if _local_name(ch.tag).lower() == name:
            if ch.text:
                return ch.text.strip()
            # 일부 feed는 <link href="..."/> 처럼 attribute에 있음
            if name == "link":
                href = ch.get("href")
                if href:
                    return href.strip()
            return ""
    return ""


def _iter_by_localname(root: ET.Element, target: str):
    target = target.lower()
    for el in root.iter():
        if _local_name(el.tag).lower() == target:
            yield el


def _parse_rss_or_atom(xml_text: str) -> List[Dict]:
    """RSS/Atom XML을 파싱해서 공통 Dict 리스트로 반환."""
    root = ET.fromstring(xml_text)

    items: List[Dict] = []

    # 1) RSS: <item>
    rss_items = list(_iter_by_localname(root, "item"))
    if rss_items:
        for it in rss_items:
            title = _find_child_text(it, "title")
            link = _find_child_text(it, "link")
            # 일부 RSS는 <guid>에 url이 있기도 함
            if not link:
                link = _find_child_text(it, "guid")

            pub = _find_child_text(it, "pubDate")
            if not pub:
                pub = _find_child_text(it, "date")

            source = _find_child_text(it, "source")
            desc = _find_child_text(it, "description")
            if not desc:
                desc = _find_child_text(it, "summary")

            if title and link:
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "published": pub,
                        "source": source,
                        "description": desc,
                    }
                )
        return items

    # 2) Atom: <entry>
    atom_entries = list(_iter_by_localname(root, "entry"))
    for en in atom_entries:
        title = _find_child_text(en, "title")

        # Atom link는 <link href="..."/> 형태가 일반적
        link = ""
        for lk in list(en):
            if _local_name(lk.tag).lower() == "link":
                href = lk.get("href")
                if href:
                    link = href.strip()
                    break
                if lk.text:
                    link = lk.text.strip()
                    break

        pub = _find_child_text(en, "published") or _find_child_text(en, "updated")
        source = _find_child_text(en, "source")
        desc = _find_child_text(en, "summary") or _find_child_text(en, "content")

        if title and link:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "published": pub,
                    "source": source,
                    "description": desc,
                }
            )
    return items


def debug_print_rss_source(url: str, text: str, status_code: Optional[int] = None) -> None:
    """디버그용: RSS 원문 일부 출력"""
    head = (text or "")[:400].replace("\n", " ")
    sc = f" status={status_code}" if status_code is not None else ""
    print(f"[RSS][DEBUG]{sc} url={url} head={head}")


def fetch_google_news_rss(feed_url: str, max_items: int = 20, limit: int | None = None) -> List[Dict]:
    """RSS URL에서 아이템 가져오기.

    이름은 google_news 이지만, 지금 프로젝트에선 "모든 RSS"를 여기로 통일해서 부른다.
    """
    # Backward-compat: some callers use keyword argument `limit`.
    # 하위호환: 일부 호출부에서 keyword 인자 `limit`를 사용합니다.
    if limit is not None:
        max_items = limit

    if not feed_url or not str(feed_url).startswith("http"):
        return []

    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            r = requests.get(
                feed_url,
                headers=DEFAULT_HEADERS,
                timeout=15,
                allow_redirects=True,
            )

            # 200이 아니면 일단 디버깅 힌트 출력
            if r.status_code != 200:
                debug_print_rss_source(feed_url, r.text or "", status_code=r.status_code)
                # 403/429 같은 경우에는 잠깐 쉬고 재시도
                if r.status_code in (403, 429, 503):
                    time.sleep(1.0 + attempt * 1.2)
                    continue
                return []

            text = r.text or ""
            # 가끔 HTML(동의/차단 페이지)이 오면 item이 0개가 됨 → 디버그 출력
            if "<rss" not in text and "<feed" not in text:
                debug_print_rss_source(feed_url, text, status_code=r.status_code)
                return []

            try:
                items = _parse_rss_or_atom(text)
            except Exception as e:
                # XML 파싱 실패 시 원문 일부 저장/출력
                last_err = e
                debug_print_rss_source(feed_url, text, status_code=r.status_code)
                time.sleep(0.6 + attempt * 0.8)
                continue

            return items[: max(0, int(max_items))]

        except Exception as e:
            last_err = e
            time.sleep(0.6 + attempt * 0.8)

    # 최종 실패
    if last_err:
        print(f"[RSS][WARN] fetch failed: url={feed_url} err={last_err!r}")
    return []