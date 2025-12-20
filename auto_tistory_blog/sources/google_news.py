# sources/google_news.py
import requests
import xml.etree.ElementTree as ET


def fetch_google_news_rss(feed_url: str, limit: int = 3):
    """
    Google News RSS(XML)에서 title/link/pubDate/source를 limit개까지 반환.
    """
    r = requests.get(feed_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    root = ET.fromstring(r.text)
    items = []

    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()

        # <source url="...">매체명</source>
        source_el = item.find("source")
        source_name = ""
        source_url = ""
        if source_el is not None:
            source_name = (source_el.text or "").strip()
            source_url = (source_el.get("url") or "").strip()

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "source": source_name,
                "source_url": source_url,
            })

    return items


def debug_print_rss_source(feed_url: str, lines: int = 30):
    """
    '페이지 소스' 확인용: RSS 원문(XML) 상단 일부를 출력.
    """
    r = requests.get(feed_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    text = r.text.splitlines()
    for i, line in enumerate(text[:lines], 1):
        print(f"{i:02d} {line}")
