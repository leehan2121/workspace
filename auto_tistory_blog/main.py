# main.py
import config

from sources.google_news import fetch_google_news_rss, debug_print_rss_source
from generator import generate_post_with_ollama
from tistory_bot import make_driver, login, write_post, publish_with_visibility
from utils import pause_forever

import traceback
from pathlib import Path
from datetime import datetime

# =========================
# 로그 유틸
# =========================

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

def run_step(driver, name, fn):
    log_step(name)
    try:
        return fn()
    except Exception as e:
        log_err(f"{name} 실패: {repr(e)}")
        log_err(traceback.format_exc())
        debug_dump(driver, f"fail_{name.replace(' ', '_')}")
        raise

# =========================
# 메인
# =========================

def main():
    log_step("프로그램 시작")

    # RSS 소스 디버그 모드
    if getattr(config, "DEBUG_PRINT_RSS_SOURCE", False):
        log_warn("DEBUG_PRINT_RSS_SOURCE=True → RSS 소스만 출력하고 종료")
        for key, url in config.GOOGLE_NEWS_FEEDS.items():
            print("\n==============================")
            print("TOPIC:", key)
            print("URL:", url)
            debug_print_rss_source(url, lines=30)
        return

    # 드라이버 생성
    log_step("make_driver() 호출 직전")
    driver, wait = make_driver()
    log_step("make_driver() 리턴 직후")

    try:
        # 로그인
        run_step(
            driver,
            "로그인 시작",
            lambda: login(
                driver,
                wait,
                config.TISTORY_LOGIN_URL,
                config.KAKAO_ID,
                config.KAKAO_PW
            )
        )

        # 주제별 글 작성
        for topic_key, feed_url in config.GOOGLE_NEWS_FEEDS.items():
            log_info(f"===== TOPIC START: {topic_key} =====")

            items = run_step(
                driver,
                f"RSS 수집 ({topic_key})",
                lambda: fetch_google_news_rss(
                    feed_url,
                    limit=config.GOOGLE_NEWS_LIMIT_PER_TOPIC
                )
            )

            if not items:
                log_warn(f"{topic_key}: RSS 결과 없음")
                continue

            article = items[0]
            log_info(f"{topic_key}: 기사 제목 = {article.get('title')}")

            prompt_category = config.PROMPT_CATEGORY_MAP.get(topic_key, "social")

            title_text, body_text = run_step(
                driver,
                f"LLM 글 생성 ({topic_key})",
                lambda: generate_post_with_ollama(
                    category=prompt_category,
                    article={
                        "title": article["title"],
                        "link": article["link"],
                        "source": article.get("source", ""),
                        "lead": "",
                        "excerpt": "",
                    },
                    ollama_url=config.OLLAMA_URL,
                    model=config.OLLAMA_MODEL,
                    timeout=config.LLM_TIMEOUT
                )
            )

            log_info(f"{topic_key}: 생성된 제목 = {title_text[:120]}")
            log_info(f"{topic_key}: 본문 미리보기 = {body_text[:200].replace(chr(10), ' ')} ...")

            run_step(
                driver,
                f"글쓰기 입력 ({topic_key})",
                lambda: write_post(
                    driver,
                    wait,
                    config.TISTORY_WRITE_URL,
                    config.DRAFT_ALERT_ACCEPT,
                    title_text,
                    body_text
                )
            )

            run_step(
                driver,
                f"발행 처리 ({topic_key})",
                lambda: publish_with_visibility(
                    driver,
                    wait,
                    config.DRAFT_ALERT_ACCEPT,
                    config.VISIBILITY_ID
                )
            )

            log_info(f"✅ 완료: {topic_key} 1건 발행")

        log_step("전체 작업 완료")
        pause_forever(driver, "전체 작업 완료(브라우저 유지)")

    except Exception as e:
        debug_dump(driver, "last_exception")
        pause_forever(driver, f"예외 발생: {repr(e)}")


if __name__ == "__main__":
    main()
