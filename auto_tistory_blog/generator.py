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
    - 제어문자 제거
    - 공백 정리
    """
    if not text:
        return text

    text = re.sub(r"[\u3040-\u30FF]+", "", text)          # Japanese
    text = re.sub(r"[\u0100-\u024F]+", "", text)          # Latin ext
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)  # controls
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


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
    # 1) 빈 줄(\n\n) 기준
    paras_blank = [p.strip() for p in re.split(r"\n\s*\n", b) if p.strip()]

    # 2) 헤딩(##) 기준(빈 줄 안 넣는 모델 대응)
    parts_by_heading = []
    if "##" in b:
        chunks = re.split(r"(?m)^\s*##\s+", b)
        for ch in chunks:
            ch = ch.strip()
            if ch:
                parts_by_heading.append(ch)

    # 3) 줄바꿈만 있는 경우(빈 줄 없이 \n만)
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
    for pat in banned_patterns:
        if re.search(pat, combined):
            fail = _make_fail_preview_html(topic_tag, title, body, f"banned pattern matched: {pat}")
            raise RuntimeError(f"E_GUARD_BANNED_PATTERN: {pat} saved={fail}")

    brace_count = b.count("{") + b.count("}")
    if brace_count >= 8:
        fail = _make_fail_preview_html(topic_tag, title, body, f"suspicious JSON/braces count ({brace_count})")
        raise RuntimeError(f"E_GUARD_JSON_LEAK: saved={fail}")


def generate_post_with_ollama(
    category: str,
    article: dict,
    ollama_url: str,
    model: str,
    timeout: int = 600,
    topic_tag: str = "topic"
):
    import config

    # 출처 URL 정리
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

    # ===== 1차/2차 생성 =====
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

    src = article.get("source") or "출처"
    url = article.get("link") or ""
    if url:
        body = body.rstrip() + f"\n\n출처: {src} ({url})\n"

    if not title:
        title = (article.get("title") or "제목 없음").strip()
    if not body:
        raise RuntimeError(f"E_LLM_BODY_EMPTY({last_mode}): saved={last_raw_path}")

    rewrite_on_short = getattr(config, "LLM_REWRITE_ON_SHORT", True)
    rewrite_max_tries = getattr(config, "LLM_REWRITE_MAX_TRIES", 1)

    try:
        _validate_post_quality(title, body, topic_tag)
        return title, body

    except RuntimeError as e:
        msg = str(e)
        if not rewrite_on_short:
            raise

        if ("E_GUARD_BODY_SHORT" not in msg) and ("E_GUARD_PARA_FEW" not in msg):
            raise

        for k in range(rewrite_max_tries):
            min_body = getattr(config, "LLM_MIN_BODY_CHARS", 450)
            min_para = getattr(config, "LLM_MIN_PARAGRAPHS", 3)

            rewrite_prompt = (
                "Return ONLY a JSON object.\n"
                "Rewrite the draft into a longer Korean blog post.\n"
                f"- At least {min_para} paragraphs\n"
                f"- At least {min_body} characters\n"
                "- No HTML tags. Use blank lines between paragraphs.\n"
                "- Must include headings: ## 핵심 요약 / ## 내용 정리 / ## 의미와 관전 포인트 / ## 한 줄 결론\n"
                "JSON format: {\"title\":\"...\",\"body\":\"...\"}\n\n"
                f"DRAFT_TITLE:\n{title}\n\nDRAFT_BODY:\n{body}\n"
            )

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

            title2 = _clean_weird_lang((parsed2.get("title") or title).strip())
            body2 = _clean_weird_lang((parsed2.get("body") or "").strip())
            body2 = re.sub(r'^\|\s*\n', '', body2).strip()

            if url:
                body2 = body2.rstrip() + f"\n\n출처: {src} ({url})\n"

            if not body2:
                continue

            _validate_post_quality(title2, body2, topic_tag)
            return title2, body2

        raise
