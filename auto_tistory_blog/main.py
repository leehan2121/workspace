# main.py
import config
from rss_sources_loader import merge_rss_sources_from_csv
import traceback
import json
import time
import threading
import os

from sources.google_news import fetch_google_news_rss

# debug_print_rss_source는 선택(optional)입니다.
# debug_print_rss_source is optional.
try:
    from sources.google_news import debug_print_rss_source  # type: ignore
except Exception:
    def debug_print_rss_source(*args, **kwargs):
        return None

from sources.article_extract import fetch_article_hint
from generator import generate_post_with_ollama
from tistory_bot import make_driver, login, write_post, publish_with_visibility , TISTORY_CATEGORY_ID_MAP
from utils import pause_forever
from image_pipeline import build_sd_prompt, build_sd_prompt_for_section

from pathlib import Path
from datetime import datetime

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

LOG_FILE = DEBUG_DIR / "run.log"

def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write(line: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_step(msg):
    line = f"[{_ts()}][STEP] {msg}"
    print(line, flush=True)
    _write(line)


def log_info(msg):
    line = f"[{_ts()}][INFO] {msg}"
    print(line, flush=True)
    _write(line)


def log_warn(msg):
    line = f"[{_ts()}][WARN] {msg}"
    print(line, flush=True)
    _write(line)


def log_err(msg):
    line = f"[{_ts()}][ERROR] {msg}"
    print(line, flush=True)
    _write(line)


def debug_dump(driver, tag="last"):
    if driver is None:
        return
    try:
        driver.save_screenshot(str(DEBUG_DIR / f"{tag}.png"))
    except Exception:
        pass
    try:
        with open(DEBUG_DIR / f"{tag}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception:
        pass


def dump_json(tag: str, data: dict):
    try:
        p = DEBUG_DIR / f"{tag}.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _safe_driver_state(driver):
    try:
        url = driver.current_url if driver else ""
    except Exception:
        url = ""
    try:
        title = driver.title if driver else ""
    except Exception:
        title = ""
    return url, title


def start_heartbeat(driver, step_name: str, interval_sec: int = 10):
    stop_event = threading.Event()
    started = time.time()

    def _loop():
        tick = 0
        while not stop_event.is_set():
            time.sleep(interval_sec)
            if stop_event.is_set():
                break
            tick += 1
            elapsed = int(time.time() - started)
            url, title = _safe_driver_state(driver)
            log_info(
                f"[HB] step='{step_name}' elapsed={elapsed}s tick={tick} url={url} title={title}"
            )

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return stop_event



# ===== RSS helpers (EXTRA first, multi-RSS support) =====
def _is_http_url(s: str) -> bool:
    return isinstance(s, str) and s.strip().lower().startswith(("http://", "https://"))

def _normalize_extra_global_feeds(extra):
    """EXTRA_RSS_FEEDS_GLOBAL을 어떤 형태로 주더라도 URL 리스트로 정규화.
    Normalize EXTRA_RSS_FEEDS_GLOBAL to list[str] of URLs.

    허용 형태:
    - list/tuple/set[str]
    - str
    - dict[str, str|list[str]]  (topic_key -> urls)
    """
    if not extra:
        return []

    urls = []
    if isinstance(extra, dict):
        for _k, v in extra.items():
            if not v:
                continue
            if isinstance(v, (list, tuple, set)):
                urls.extend([x for x in v if isinstance(x, str)])
            elif isinstance(v, str):
                urls.append(v)
    elif isinstance(extra, (list, tuple, set)):
        urls.extend([x for x in extra if isinstance(x, str)])
    elif isinstance(extra, str):
        urls.append(extra)

    # scheme 있는 URL만 통과
    return [u.strip() for u in urls if _is_http_url(u)]

def _iter_topic_sources(config):
    """(source_name, topic_key, url_list) 순으로 yield.
    Yield (source_name, topic_key, url_list) in priority order.

    요구사항:
    - EXTRA_RSS_FEEDS_BY_TOPIC 기준: topic(카테고리)당 1번만 순회
    - topic 안에서는 RSS URL(피드)당 1번씩 yield (PUBLISH_COUNT는 '피드당' 적용)
    """
    # 1) CSV/설정에서 topic별로 분리된 RSS feeds (권장)
    by_topic = getattr(config, "EXTRA_RSS_FEEDS_BY_TOPIC", {}) or {}
    if isinstance(by_topic, dict) and by_topic:
        for topic_key, urls in by_topic.items():
            if not urls:
                continue
            # url은 피드당 1회 실행되도록 개별 yield
            _env = os.getenv('PUBLISH_COUNT', '').strip()
            _per = int(_env) if _env.isdigit() else 1
            if _per < 1: _per = 1
            for u in list(dict.fromkeys([x.strip() for x in urls if isinstance(x, str) and x.strip()])):
                for _k in range(_per):
                    yield ("EXTRA_RSS_FEEDS_BY_TOPIC", str(topic_key), [u])
        return  # ✅ by_topic이 있으면 다른 소스는 돌리지 않음 (RSS only 모드)

    # 2) Global extra feeds (fallback)
    extra = getattr(config, "EXTRA_RSS_FEEDS_GLOBAL", None)
    if isinstance(extra, dict):
        for topic_key, v in extra.items():
            urls = _normalize_extra_global_feeds({topic_key: v})
            if urls:
                for u in urls:
                    yield ("EXTRA_RSS_FEEDS_GLOBAL", str(topic_key), [u])
    else:
        urls = _normalize_extra_global_feeds(extra)
        if urls:
            default_topic = getattr(config, "EXTRA_RSS_DEFAULT_TOPIC", "it_science")
            for u in urls:
                yield ("EXTRA_RSS_FEEDS_GLOBAL", str(default_topic), [u])

    # 3) Google News feeds (legacy)
    feeds = getattr(config, "GOOGLE_NEWS_FEEDS", {}) or {}
    if isinstance(feeds, dict):
        for topic_key, url in feeds.items():
            if isinstance(url, str) and url.strip():
                yield ("GOOGLE_NEWS_FEEDS", str(topic_key), [url.strip()])

def _fetch_rss_items_for_urls(urls, fetch_limit: int):
    """여러 RSS URL을 합쳐서 items 반환."""
    all_items = []
    for url in urls:
        try:
            debug_print_rss_source(url)
        except Exception:
            pass
        try:
            # NOTE: sources.google_news.fetch_google_news_rss() signature is
            # (feed_url, max_items=20). Older calls used `limit`.
            all_items.extend(fetch_google_news_rss(url, max_items=fetch_limit))
        except Exception as e:
            log_warn(f"RSS fetch failed: {url} / {e!r}")
    return all_items

def run_step(driver, name, fn, heartbeat_sec: int | None = None):
    log_step(name)

    hb_stop = None
    if heartbeat_sec and heartbeat_sec > 0:
        hb_stop = start_heartbeat(driver, name, heartbeat_sec)

    try:
        return fn()
    except Exception as e:
        log_err(f"{name} 실패: {repr(e)}")
        log_err(traceback.format_exc())
        debug_dump(driver, f"fail_{name.replace(' ', '_')}")
        raise
    finally:
        if hb_stop:
            hb_stop.set()


def main():
    log_step("프로그램 시작")

    # ===== Load domestic RSS sources from CSV (optional) =====
    # rss_sources.csv의 카테고리별 URL을 config.EXTRA_RSS_*에 병합합니다.
    try:
        if getattr(config, 'USE_RSS_SOURCES_CSV', False):
            merge_rss_sources_from_csv(config.RSS_SOURCES_CSV_PATH)
    except Exception as e:
        log_warn(f"RSS_SOURCES_CSV 로드 실패: {e}")

    if getattr(config, "DEBUG_PRINT_RSS_SOURCE", False):
        log_warn("DEBUG_PRINT_RSS_SOURCE=True → RSS 소스만 출력하고 종료")
        for key, url in config.GOOGLE_NEWS_FEEDS.items():
            print("\n==============================")
            print("TOPIC:", key)
            print("URL:", url)
            debug_print_rss_source(url, lines=30)
        return

    log_step("make_driver() 호출 직전")
    driver, wait = make_driver()
    log_step("make_driver() 리턴 직후")

    # ===== 발행 건수 제한(테스트/운영 공용) =====
    # Publish(발행) count(건수) limit(제한) for test(테스트) and run(운영).
    # - 환경변수 PUBLISH_COUNT가 있으면 최우선 사용.
    # - If env var(환경변수) PUBLISH_COUNT exists(존재), it wins(우선).
    # - 없으면 config.PUBLISH_TOTAL_COUNT(있을 때만) 사용.
    # - Else use config.PUBLISH_TOTAL_COUNT if present(존재 시).
    # - 0 또는 미설정이면 제한 없음.
    # - 0 or unset means no limit(제한 없음).
    # - 환경변수 PUBLISH_COUNT는 '피드(RSS URL)당 발행 개수'로 사용합니다.
    # - Env var PUBLISH_COUNT is treated as 'posts per RSS feed'.
    _env_cnt = os.getenv('PUBLISH_COUNT', '').strip()
    publish_per_feed = int(_env_cnt) if _env_cnt.isdigit() else int(getattr(config, 'PUBLISH_PER_FEED', 1) or 1)
    if publish_per_feed < 1:
        publish_per_feed = 1

    stop_all = False

    try:
        run_step(
            driver,
            "로그인 시작",
            lambda: login(
                driver,
                wait,
                config.TISTORY_LOGIN_URL,
                config.KAKAO_ID,
                config.KAKAO_PW
            ),
            heartbeat_sec=10
        )

        for source_name, topic_key, feed_urls in _iter_topic_sources(config):
            if stop_all:
                break

            log_info(f"===== TOPIC START: {topic_key} ({source_name}) =====")
            # topic_key 기준으로 카테고리ID 결정 (config 매핑 우선)
            category_id = config.TISTORY_CATEGORY_ID_MAP.get(topic_key) or TISTORY_CATEGORY_ID_MAP.get(topic_key, "0")

            # NOTE: 이 토픽은 RSS URL이 여러 개일 수 있음
            # NOTE(EN): A topic can have multiple RSS URLs.
            def _fetch_items_from_urls(urls: list) -> list:
                merged = []
                seen = set()

                for u in (urls or []):
                    if not u:
                        continue
                    u = str(u).strip()
                    if not (u.startswith("http://") or u.startswith("https://")):
                        # topic_key 같은 값이 섞이면 스킵
                        continue

                    part = fetch_google_news_rss(
                        u,
                        max_items=getattr(
                            config,
                            "GOOGLE_NEWS_FETCH_LIMIT_PER_TOPIC",
                            config.GOOGLE_NEWS_LIMIT_PER_TOPIC,
                        ),
                    )

                    for it in (part or []):
                        # link 기준으로 중복 제거
                        # it is a dict in our pipeline.
                        link = (it.get("link") or "").strip()
                        k = link or (it.get("title") or "").strip()
                        if not k or k in seen:
                            continue
                        seen.add(k)
                        merged.append(it)

                return merged

            items = run_step(
                driver,
                f"RSS 수집 ({topic_key})",
                lambda urls=feed_urls: _fetch_items_from_urls(urls),
                heartbeat_sec=None
            )

            if not items:
                log_warn(f"{topic_key}: RSS 결과 없음")
                continue

            max_article_tries = getattr(config, "ARTICLE_MAX_TRIES_PER_TOPIC", 2)
            if max_article_tries < 1:
                max_article_tries = 1

            chosen_article = None

            # ✅ 여러 기사 중에서 "LLM 통과하는" 기사를 고른다 (최대 N개 시도)
            for ai, article in enumerate(items[:max_article_tries], start=1):
                log_info(f"{topic_key}: 후보 기사[{ai}/{max_article_tries}] = {article.get('title')}")
                dump_json(
                    tag=f"raw_article_{topic_key}_{ai}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    data=article
                )

                prompt_category = config.PROMPT_CATEGORY_MAP.get(topic_key, "social")

                try:
                    # ✅ 기사 단서 추출(메타 설명 + 일부 문단)
                    # Article hints (meta description + paragraph snippets)
                    hint = None
                    if getattr(config, "ENABLE_ARTICLE_HINT", True):
                        hint = fetch_article_hint(article.get("link", ""), timeout_sec=getattr(config, "ARTICLE_HINT_TIMEOUT_SEC", 12))

                    title_text, body_text = run_step(
                        driver,
                        f"LLM 글 생성 ({topic_key}) [article {ai}]",
                        lambda a=article: generate_post_with_ollama(
                            category=prompt_category,
                            article={
                                "title": a["title"],
                                "link": a["link"],
                                "source": a.get("source", ""),
                                "date": a.get("pubDate", "") or "",
                                # LLM 재구성 재료 (clues)
                                "lead": (hint.description if hint else ""),
                                "excerpt": (hint.excerpt if hint else ""),
                            },
                            ollama_url=config.OLLAMA_URL,
                            model=config.OLLAMA_MODEL,
                            timeout=config.LLM_TIMEOUT,
                            topic_tag=f"{topic_key}_a{ai}",
                        ),
                        heartbeat_sec=10
                    )

                    chosen_article = {
                        "article": article,
                        "title_text": title_text,
                        "body_text": body_text,
                        "index": ai,
                    }
                    break

                except RuntimeError as e:
                    msg = str(e)
                    # ✅ 가드/파싱 실패면 다음 기사로 넘어감
                    if msg.startswith("E_GUARD_") or msg.startswith("E_LLM_"):
                        log_warn(f"{topic_key}: 기사[{ai}] LLM 실패 → 다음 기사 시도 ({msg})")
                        continue
                    raise

            if not chosen_article:
                log_warn(f"{topic_key}: {max_article_tries}개 기사 시도했지만 LLM 통과 실패 → 토픽 스킵")
                continue

            article = chosen_article["article"]
            title_text = chosen_article["title_text"]
            body_text = chosen_article["body_text"]
            chosen_idx = chosen_article["index"]

            log_info(f"{topic_key}: ✅ 선택된 기사 = [{chosen_idx}] {article.get('title')}")

            if not title_text.strip() or not body_text.strip():
                log_warn(f"{topic_key}: title/body 비어있음 → 스킵")
                continue

            # (1) 본문이 JSON처럼 보이면 파싱 실패 가능성 높음
            if body_text.strip().startswith("{") and ("\"body\"" in body_text[:300] or "\"title\"" in body_text[:300]):
                log_warn(f"{topic_key}: 본문이 JSON처럼 보임 → 스킵(파싱 실패 가능성)")
                dump_json(
                    tag=f"bad_body_jsonlike_{topic_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    data={"title": title_text, "body_preview": body_text[:2000]}
                )
                continue

            # (2) 프롬프트 규칙이 그대로 섞여나오면 실패로 간주
            bad_markers = ["역할:", "목표:", "출력 공통 규칙", "공통 글 구조", "BASE_PROMPT", "너는 뉴스 편집자다"]
            if any(m in body_text for m in bad_markers):
                log_warn(f"{topic_key}: 본문에 프롬프트 흔적 감지 → 스킵")
                dump_json(
                    tag=f"bad_body_promptleak_{topic_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    data={"title": title_text, "body_preview": body_text[:2000]}
                )
                continue

            log_info(f"{topic_key}: 생성된 제목 = {title_text[:120]}")
            log_info(f"{topic_key}: 본문 미리보기 = {body_text[:200].replace(chr(10), ' ')} ...")

            # ===== 이미지 생성 (상단 2 + 본문 1) =====
            # 원하는 최종 레이아웃:
            #   [이미지(제목)]
            #   [이미지(요약)]
            #   요약 ...
            #   [이미지(본문)]  <- 본문 마커(§§BODY_IMG§§) 위치에 삽입
            #   본문 ...
            image_paths_top = []
            body_image_path = None

            # 섹션 텍스트 추출 (요약/본문 2단원 전제)
            BODY_MARKER = "§§BODY_IMG§§"

            def _extract_section(text: str, start_kw: str, end_kw=None) -> str:
                if not text:
                    return ""
                t = text
                si = t.find(start_kw)
                if si < 0:
                    return ""
                si = si + len(start_kw)
                t2 = t[si:]
                if end_kw:
                    ei = t2.find(end_kw)
                    if ei >= 0:
                        t2 = t2[:ei]
                # 마커/여백 제거
                t2 = t2.replace(BODY_MARKER, " ")
                return t2.strip()

            summary_text_for_image = _extract_section(body_text, "요약", "본문")
            body_text_for_image = _extract_section(body_text, "본문", None)

            # fallback: 섹션 텍스트가 비면 이미지 프롬프트가 약해져 생성 실패가 늘어남
            # If section text is empty, SD prompt becomes too weak and generation may fail.
            if not (summary_text_for_image or "").strip():
                summary_text_for_image = title_text
            if not (body_text_for_image or "").strip():
                body_text_for_image = (title_text + "\n" + summary_text_for_image).strip()

            if getattr(config, "ENABLE_IMAGE", False):
                # (1) 대표 이미지
                try:
                    cover_path = run_step(
                        driver,
                        f"SD 이미지 생성(대표) ({topic_key})",
                        lambda: build_sd_prompt(topic_key, title_text),
                        heartbeat_sec=10
                    )
                    if cover_path:
                        image_paths_top.append(cover_path)
                    else:
                        log_warn(f"{topic_key}: SD 대표 이미지 생성 실패(빈 경로) → 대표 이미지 없이 진행")
                except Exception as e:
                    log_warn(f"{topic_key}: SD 대표 이미지 생성 예외 → 대표 이미지 없이 진행 ({repr(e)})")

                # (2) 요약 이미지 (상단: 요약 위)
                try:
                    summary_path = run_step(
                        driver,
                        f"SD 이미지 생성(요약) ({topic_key})",
                        lambda: build_sd_prompt_for_section(topic_key, title_text, summary_text_for_image, kind="summary"),
                        heartbeat_sec=10
                    )
                    if summary_path:
                        image_paths_top.append(summary_path)
                    else:
                        log_warn(f"{topic_key}: SD 요약 이미지 생성 실패(빈 경로) → 요약 이미지 없이 진행")
                except Exception as e:
                    log_warn(f"{topic_key}: SD 요약 이미지 생성 예외 → 요약 이미지 없이 진행 ({repr(e)})")

                # (3) 본문 이미지 (마커 위치)
                try:
                    ctx_path = run_step(
                        driver,
                        f"SD 이미지 생성(본문) ({topic_key})",
                        lambda: build_sd_prompt_for_section(topic_key, title_text, body_text_for_image, kind="body"),
                        heartbeat_sec=10
                    )
                    if ctx_path:
                        body_image_path = ctx_path
                    else:
                        log_warn(f"{topic_key}: SD 본문 이미지 생성 실패(빈 경로) → 본문 이미지 없이 진행")
                except Exception as e:
                    log_warn(f"{topic_key}: SD 본문 이미지 생성 예외 → 본문 이미지 없이 진행 ({repr(e)})")

            # write_post()에는 상단 이미지 2장만 전달 (제목/요약)
            image_paths = image_paths_top

# ===== 글쓰기 입력 =====
            run_step(
                driver,
                f"글쓰기 입력 ({topic_key})",
                lambda: write_post(
                    driver,
                    wait,
                    config.TISTORY_WRITE_URL,
                    config.DRAFT_ALERT_ACCEPT,
                    title_text,
                    body_text,
                    image_paths=image_paths,
                    context_image_path=body_image_path,
                    context_marker="§§BODY_IMG§§",
                    require_image_upload=config.REQUIRE_IMAGE_UPLOAD,
                    category_id= category_id,
                    insert_image_at_top=config.INSERT_IMAGE_AT_TOP
                ),
                heartbeat_sec=10
            )

            run_step(
                driver,
                f"발행 처리 ({topic_key})",
                lambda: publish_with_visibility(
                    driver,
                    wait,
                    config.DRAFT_ALERT_ACCEPT,
                    config.VISIBILITY_ID
                ),
                heartbeat_sec=10
            )

            log_info(f"✅ 완료: {topic_key} 1건 발행")

        log_step("전체 작업 완료")
        pause_forever(driver, "전체 작업 완료(브라우저 유지)")

    except Exception as e:
        debug_dump(driver, "last_exception")
        pause_forever(driver, f"예외 발생: {repr(e)}")


if __name__ == "__main__":
    main()
