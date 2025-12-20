# rss.py
import requests
import xml.etree.ElementTree as ET

def fetch_rss_items(url: str, limit: int):
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    root = ET.fromstring(r.text)
    items = []

    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            items.append({"title": title, "link": link})

    return items
