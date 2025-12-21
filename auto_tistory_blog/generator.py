# generator.py
import json
import re
from pathlib import Path
from datetime import datetime
import requests

from prompts import build_prompt_json

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)


def _now_tag():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text if text is not None else "")


def _clean_weird_lang(text: str) -> str:
    """
    - 일본어(히라가나/가타카나) 제거
    - 라틴 확장 일부 제거
    - 한자(중국어/한자) 제거
    - 제어문자 제거
    - 공백 정리
    """
    if not text:
        return text

    text = re.sub(r"[\u3040-\u30FF]+", "", text)          # Japanese
    text = re.sub(r"[\u0100-\u024F]+", "", text)          # Latin ext (accented)
    text = re.sub(r"[\u4E00-\u9FFF]+", "", text)          # CJK ideographs (Hanja)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)  # controls
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _build_retry_prompt_kor(base_prompt: str, fail_reason: str) -> str:
    """가드 실패 시, 초안(draft)을 주지 않고 '처음부터 재생성'시키는 리트라이 프롬프트.

    Retry prompt that forces regeneration from scratch (no draft leakage).
    - leakage (유출): 이전 출력에 섞인 한자/잡문자가 다음 출력으로 전염되는 문제
    """
    return (
        base_prompt
        + "\n\n[추가 지시: 1차 출력이 규칙 위반으로 실패했다]\n"
        + f"- 실패 사유: {fail_reason}\n"
        + "- 위 사유를 반드시 해결하라.\n"
        + "- 특히 title/body에 한글 외 문자가 1개라도 섞이면 실패다.\n"
        + "- 본문 길이가 부족하면 각 섹션에 구체 사실/수치/배경을 추가해 확장하라.\n"
        + "- 결과는 반드시 JSON 1개만 출력하라.\n"
    )


def _extract_first_json_object(text: str):
    if not text:
        return None

    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = cleaned[start:end + 1].strip()
    candidate = candidate.replace('"body": |', '"body":')

    try:
        return json.loads(candidate)
    except Exception:
        return None


def _resolve_final_url(url: str) -> str:
    if not url:
        return url
    try:
        r = requests.get(url, allow_redirects=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        return r.url or url
    except Exception:
        return url


def _html_escape(s: str) -> str:
    if s is None:
        return ""
    return (s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def _make_fail_preview_html(topic_tag: str, title: str, body: str, reason: str) -> Path:
    p = DEBUG_DIR / f"fail_guard_{topic_tag}_{_now_tag()}.html"
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<title>FAIL GUARD PREVIEW</title>
<style>
  body{{font-family: Arial, sans-serif; margin:20px; line-height:1.5;}}
  .box{{padding:12px; border:1px solid #ddd; border-radius:10px; margin:12px 0;}}
  .reason{{background:#fff4f4; border-color:#ffcccc;}}
  pre{{white-space:pre-wrap; word-break:break-word;}}
</style>
</head>
<body>
<h2>LLM Guard 실패</h2>
<div class="box reason"><b>Reason:</b> {_html_escape(reason)}</div>

<div class="box">
  <h3>Title</h3>
  <pre>{_html_escape(title)}</pre>
</div>

<div class="box">
  <h3>Body</h3>
  <pre>{_html_escape(body)}</pre>
</div>
</body>
</html>"""
    _write_text(p, html)
    return p


def _contains_cjk_ideographs(text: str) -> bool:
    # 한자 영역(중국어/한자 포함 여부). 한국어-only 정책이면 걸러야 함
    return bool(re.search(r"[\u4E00-\u9FFF]", text or ""))


def _validate_post_quality(title: str, body: str, topic_tag: str):
    import config

    min_body_chars = getattr(config, "LLM_MIN_BODY_CHARS", 450)
    min_paragraphs = getattr(config, "LLM_MIN_PARAGRAPHS", 3)
    min_title_chars = getattr(config, "LLM_MIN_TITLE_CHARS", 8)
    max_title_chars = getattr(config, "LLM_MAX_TITLE_CHARS", 80)

    banned_patterns = getattr(config, "LLM_BANNED_PATTERNS", [
        r"```",
        r"(?i)\bassistant\s*:",
        r"(?i)\bsystem\s*:",
        r"(?i)\buser\s*:",
        r"(?i)\bas an ai\b",
        r"(?i)\bprompt\b",
        r"<think>",
        r"(?i)<br\s*/?>",   # ✅ HTML br 금지
        r"(?i)<p\s*>",
        r"(?i)</p\s*>",
        r"(?i)<div\s*>",
        r"(?i)</div\s*>",
    ])

    t = (title or "").strip()
    b = (body or "").strip()

    if len(t) < min_title_chars:
        fail = _make_fail_preview_html(topic_tag, title, body, f"title too short (<{min_title_chars})")
        raise RuntimeError(f"E_GUARD_TITLE_SHORT: saved={fail}")

    if len(t) > max_title_chars:
        fail = _make_fail_preview_html(topic_tag, title, body, f"title too long (>{max_title_chars})")
        raise RuntimeError(f"E_GUARD_TITLE_LONG: saved={fail}")

    if len(b) < min_body_chars:
        fail = _make_fail_preview_html(topic_tag, title, body, f"body too short (<{min_body_chars} chars)")
        raise RuntimeError(f"E_GUARD_BODY_SHORT: saved={fail}")

    # ===== 문단 카운트 강화 =====
    paras_blank = [p.strip() for p in re.split(r"\n\s*\n", b) if p.strip()]

    parts_by_heading = []
    if "##" in b:
        chunks = re.split(r"(?m)^\s*##\s+", b)
        for ch in chunks:
            ch = ch.strip()
            if ch:
                parts_by_heading.append(ch)

    lines = [ln.strip() for ln in b.split("\n") if ln.strip()]
    estimated_by_lines = []
    if len(lines) >= 10:
        step = 5
        for i in range(0, len(lines), step):
            block = "\n".join(lines[i:i + step]).strip()
            if block:
                estimated_by_lines.append(block)

    para_count = max(len(paras_blank), len(parts_by_heading), len(estimated_by_lines))

    if para_count < min_paragraphs:
        fail = _make_fail_preview_html(
            topic_tag, title, body,
            f"too few paragraphs (<{min_paragraphs}); counted={para_count} "
            f"(blank={len(paras_blank)}, heading={len(parts_by_heading)}, est={len(estimated_by_lines)})"
        )
        raise RuntimeError(f"E_GUARD_PARA_FEW: saved={fail}")

    combined = f"{t}\n{b}"

    # ✅ 한자 섞이면 실패 처리 (중국어/한자 출력 방지)
    if _contains_cjk_ideographs(combined):
        fail = _make_fail_preview_html(topic_tag, title, body, "contains CJK ideographs (Chinese characters)")
        raise RuntimeError(f"E_GUARD_LANG_CJK: saved={fail}")

    for pat in banned_patterns:
        if re.search(pat, combined):
            fail = _make_fail_preview_html(topic_tag, title, body, f"banned pattern matched: {pat}")
            raise RuntimeError(f"E_GUARD_BANNED_PATTERN: {pat} saved={fail}")

    brace_count = b.count("{") + b.count("}")
    if brace_count >= 8:
        fail = _make_fail_preview_html(topic_tag, title, body, f"suspicious JSON/braces count ({brace_count})")
        raise RuntimeError(f"E_GUARD_JSON_LEAK: saved={fail}")


def _fallback_title_from_article(article_title: str, max_len: int = 80) -> str:
    t = (article_title or "").strip()
    t = re.sub(r"\s+", " ", t)
    if len(t) > max_len:
        t = t[:max_len].rstrip()
    return t if t else "뉴스 요약"


def generate_post_with_ollama(
    category: str,
    article: dict,
    ollama_url: str,
    model: str,
    timeout: int = 600,
    topic_tag: str = "topic"
):
    import config

    if article.get("link"):
        article["link"] = _resolve_final_url(article["link"])

    endpoint = ollama_url.rstrip("/") + "/api/generate"

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["title", "body"]
    }

    base_prompt = build_prompt_json(category, article)
    _write_text(DEBUG_DIR / f"llm_prompt_{topic_tag}_{_now_tag()}.txt", base_prompt)

    base_options = {
        "temperature": getattr(config, "LLM_TEMPERATURE", 0.2),
        "top_p": getattr(config, "LLM_TOP_P", 0.9),
        "num_predict": getattr(config, "LLM_NUM_PREDICT", 1800),
    }

    max_retries = getattr(config, "LLM_MAX_RETRIES", 2)

    def call_ollama(prompt: str, *, fmt, options: dict, mode_tag: str):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": fmt,
            "options": options,
        }

        _write_text(
            DEBUG_DIR / f"llm_payload_{topic_tag}_{mode_tag}_{_now_tag()}.json",
            json.dumps(payload, ensure_ascii=False, indent=2)
        )

        r = requests.post(endpoint, json=payload, timeout=(10, timeout))
        r.raise_for_status()
        data = r.json()
        raw = data.get("response", "")

        raw_path = DEBUG_DIR / f"llm_raw_{topic_tag}_{mode_tag}_{_now_tag()}.txt"
        _write_text(raw_path, raw)

        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = _extract_first_json_object(raw)

        return parsed, raw_path

    last_raw_path = None
    last_mode = None

    parsed = None
    for attempt in range(1, max_retries + 1):
        if attempt == 1:
            mode = "schema"
            prompt = base_prompt
            options = dict(base_options)
            fmt = schema
        else:
            mode = "json_fallback"
            prompt = base_prompt + "\n\nIMPORTANT: Output ONLY valid JSON. No extra text."
            options = dict(base_options)
            options["temperature"] = 0
            options["num_predict"] = max(options.get("num_predict", 1800), 2000)
            fmt = "json"

        parsed, raw_path = call_ollama(prompt, fmt=fmt, options=options, mode_tag=mode)
        last_raw_path = raw_path
        last_mode = mode

        if isinstance(parsed, dict):
            break

    if not isinstance(parsed, dict):
        raise RuntimeError(f"E_LLM_PARSE_FAILED({last_mode}): response not JSON. saved={last_raw_path}")

    title = _clean_weird_lang((parsed.get("title") or "").strip())
    body = _clean_weird_lang((parsed.get("body") or "").strip())
    body = re.sub(r'^\|\s*\n', '', body).strip()

    # ✅ 출처 링크는 자동화 파이프라인에서 중요한 메타데이터
    # Source link (metadata): helpful for attribution and transparency
    src = article.get("source") or "출처"
    url = article.get("link") or ""
    append_src_url = getattr(config, "APPEND_SOURCE_URL", True)
    if append_src_url and url:
        body = body.rstrip() + f"\n\n출처: {src} ({url})\n"

    # ✅ title이 비거나 너무 짧으면 기사 제목으로 1차 보정
    if not title or len(title.strip()) < getattr(config, "LLM_MIN_TITLE_CHARS", 8):
        title = _fallback_title_from_article(article.get("title", ""), getattr(config, "LLM_MAX_TITLE_CHARS", 80))

    if not body:
        raise RuntimeError(f"E_LLM_BODY_EMPTY({last_mode}): saved={last_raw_path}")

    rewrite_on_short = getattr(config, "LLM_REWRITE_ON_SHORT", True)
    rewrite_max_tries = getattr(config, "LLM_REWRITE_MAX_TRIES", 2)

    # 1) 일단 검증
    try:
        _validate_post_quality(title, body, topic_tag)
        return title, body

    except RuntimeError as e:
        msg = str(e)
        if not rewrite_on_short:
            raise

        # ✅ title 관련 실패면 기사 제목으로 보정하고 재검증
        if "E_GUARD_TITLE_SHORT" in msg or "E_GUARD_TITLE_LONG" in msg:
            title = _fallback_title_from_article(article.get("title", ""), getattr(config, "LLM_MAX_TITLE_CHARS", 80))
            _validate_post_quality(title, body, topic_tag)
            return title, body

        # ✅ 언어/본문/문단 실패면 rewrite
        allowed = (
            ("E_GUARD_BODY_SHORT" in msg) or
            ("E_GUARD_PARA_FEW" in msg) or
            ("E_GUARD_LANG_CJK" in msg)
        )
        if not allowed:
            raise

        # ✅ rewrite는 '초안'을 주면 오염(한자/잡문자)이 전염되기 쉬움
        # ✅ 그래서 실패 사유만 주고, base_prompt로 처음부터 재생성한다.
        for k in range(rewrite_max_tries):
            rewrite_prompt = _build_retry_prompt_kor(base_prompt, msg)

            options2 = {
                "temperature": 0,
                "top_p": 0.9,
                "num_predict": max(getattr(config, "LLM_REWRITE_NUM_PREDICT", 2200),
                                   getattr(config, "LLM_NUM_PREDICT", 1800)),
            }

            parsed2, raw2_path = call_ollama(
                rewrite_prompt,
                fmt="json",
                options=options2,
                mode_tag=f"rewrite{k+1}"
            )

            if not isinstance(parsed2, dict):
                continue

            title2 = _clean_weird_lang((parsed2.get("title") or "").strip())
            body2 = _clean_weird_lang((parsed2.get("body") or "").strip())
            body2 = re.sub(r'^\|\s*\n', '', body2).strip()

            if append_src_url and url:
                body2 = body2.rstrip() + f"\n\n출처: {src} ({url})\n"

            if not title2 or len(title2) < getattr(config, "LLM_MIN_TITLE_CHARS", 8):
                title2 = _fallback_title_from_article(article.get("title", ""), getattr(config, "LLM_MAX_TITLE_CHARS", 80))

            if not body2:
                continue

            _validate_post_quality(title2, body2, topic_tag)
            return title2, body2

        raise
