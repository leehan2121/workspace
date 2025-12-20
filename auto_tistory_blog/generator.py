# generator.py
import json
import re
import requests
from pathlib import Path
from datetime import datetime

from prompts import build_prompt_json

DEBUG_DIR = Path("debug")
RAW_DIR = DEBUG_DIR / "llm_raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def _ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _save_raw(topic_tag: str, stage: str, text: str):
    """
    stage 예: prompt, response, parsed_json
    """
    safe = re.sub(r"[^a-zA-Z0-9_\-()가-힣]", "_", topic_tag)[:80]
    p = RAW_DIR / f"{_ts()}__{safe}__{stage}.txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write(text or "")

def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("LLM 응답이 비어있음")

    t = text.strip()

    m = re.search(r"```json\s*(\{.*?\})\s*```", t, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return json.loads(m.group(1))

    m = re.search(r"```\s*(\{.*?\})\s*```", t, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))

    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = t[start:end + 1].strip()
        return json.loads(candidate)

    raise ValueError("LLM 응답에서 JSON을 추출하지 못함")

def _fallback_parse_text(raw: str, article_title: str) -> tuple[str, str]:
    """
    JSON 파싱 실패 시 텍스트에서 title/body 복구.
    BUT 첫 줄이 '{' 같은 경우는 title로 쓰지 말고 기사 제목을 사용.
    """
    if not raw:
        return (article_title or "(제목 없음)", "(본문 없음)")

    text = raw.strip()

    # 마커 기반
    if "[TITLE]" in text and "[BODY]" in text:
        try:
            part_title = text.split("[TITLE]", 1)[1].split("[BODY]", 1)[0].strip()
            part_body = text.split("[BODY]", 1)[1].strip()
            tline = part_title.splitlines()[0].strip() if part_title else ""
            title = tline if tline and not tline.startswith("{") else (article_title or "(제목 없음)")
            body = part_body if part_body else text
            return (title, body)
        except Exception:
            pass

    # 첫 줄/나머지
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return (article_title or "(제목 없음)", text)

    first = lines[0]
    # ✅ '{' 같은 쓰레기 타이틀 방지
    if first == "{" or first.startswith("{") or first.startswith("```") or first.lower().startswith("json"):
        title = article_title or "(제목 없음)"
        body = text
        return (title, body)

    title = first[:80]
    body = "\n".join(lines[1:]).strip()
    if not body:
        body = text

    return (title, body)

def generate_post_with_ollama(category, article, ollama_url, model, timeout=60, topic_tag=""):
    """
    - prompt/response 원본 저장 (재현/분석 가능)
    - JSON 파싱 실패 시 fallback
    - '{' 제목 방지
    """
    article_title = (article.get("title") or "").strip()
    topic_tag = topic_tag or category or "topic"

    prompt = build_prompt_json(category, article)
    _save_raw(topic_tag, "prompt", prompt)

    url = ollama_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    r = requests.post(url, json=payload, timeout=(10, timeout))
    r.raise_for_status()

    data = r.json()
    raw = (data.get("response") or "").strip()
    _save_raw(topic_tag, "response", raw)

    # 1) JSON 우선
    try:
        obj = _extract_json(raw)
        _save_raw(topic_tag, "parsed_json", json.dumps(obj, ensure_ascii=False, indent=2))

        title = (obj.get("title") or "").strip()
        body = (obj.get("body") or "").strip()

        # ✅ 타이틀이 '{' 같은 값이면 기사 제목으로 교체
        if not title or title == "{" or title.startswith("{"):
            title = article_title or "(제목 없음)"

        if not body:
            raise ValueError("JSON body 비어있음")

        return title, body

    except Exception as e:
        # 2) fallback
        title, body = _fallback_parse_text(raw, article_title)
        if not body or len(body) < 50:
            body = raw or body
        return title, body
