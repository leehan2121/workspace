# main.py
import config
import traceback
import json
import time
import threading

from sources.google_news import fetch_google_news_rss, debug_print_rss_source
from sources.article_extract import fetch_article_hint
from generator import generate_post_with_ollama
from tistory_bot import make_driver, login, write_post, publish_with_visibility
from utils import pause_forever
from image_pipeline import build_sd_prompt

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

        for topic_key, feed_url in config.GOOGLE_NEWS_FEEDS.items():
            log_info(f"===== TOPIC START: {topic_key} =====")

            items = run_step(
                driver,
                f"RSS 수집 ({topic_key})",
                lambda: fetch_google_news_rss(
                    feed_url,
                    limit=getattr(config, "GOOGLE_NEWS_FETCH_LIMIT_PER_TOPIC", config.GOOGLE_NEWS_LIMIT_PER_TOPIC)
                ),
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

            # ===== 커버 이미지 생성 =====
            image_paths = []
            if getattr(config, "ENABLE_IMAGE", False):
                try:
                    img_path = run_step(
                        driver,
                        f"SD 이미지 생성 ({topic_key})",
                        lambda: build_sd_prompt(topic_key, title_text),
                        heartbeat_sec=10
                    )
                    if img_path:
                        image_paths = [img_path]
                    else:
                        log_warn(f"{topic_key}: SD 이미지 생성 실패(빈 경로) → 이미지 없이 진행")
                        image_paths = []
                except Exception as e:
                    log_warn(f"{topic_key}: SD 이미지 생성 예외 → 이미지 없이 진행 ({repr(e)})")
                    image_paths = []

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
                    require_image_upload=config.REQUIRE_IMAGE_UPLOAD
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
