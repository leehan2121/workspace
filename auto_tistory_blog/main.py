# main.py
import config
import traceback
import json
import time
import threading

from sources.google_news import fetch_google_news_rss, debug_print_rss_source
from generator import generate_post_with_ollama
from tistory_bot import make_driver, login, write_post, publish_with_visibility
from utils import pause_forever
from image_pipeline import build_sd_prompt

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

def dump_json(tag: str, data: dict):
    try:
        p = DEBUG_DIR / f"{tag}.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# =========================
# 진행률(Heartbeat) 모니터
# =========================

def _safe_driver_state(driver):
    """
    Selenium이 뻗었거나 page_source가 무거운 상황을 피하려고,
    url/title만 최대한 가볍게 뽑는다.
    """
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
    """
    특정 step이 오래 걸릴 때:
    - "지금 응답 대기 중인지"
    - "어느 페이지에서 걸렸는지"
    를 주기적으로 run.log에 남긴다.
    """
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
        # 로그인 (가끔 인증/리디렉션에서 멈출 수 있어서 HB 켬)
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

        # 주제별 글 작성
        for topic_key, feed_url in config.GOOGLE_NEWS_FEEDS.items():
            log_info(f"===== TOPIC START: {topic_key} =====")

            items = run_step(
                driver,
                f"RSS 수집 ({topic_key})",
                lambda: fetch_google_news_rss(
                    feed_url,
                    limit=config.GOOGLE_NEWS_LIMIT_PER_TOPIC
                ),
                heartbeat_sec=None
            )

            if not items:
                log_warn(f"{topic_key}: RSS 결과 없음")
                continue

            article = items[0]
            log_info(f"{topic_key}: 기사 제목 = {article.get('title')}")

            # 가공 전 데이터 저장(근거 파일)
            dump_json(
                tag=f"raw_article_{topic_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                data=article
            )

            prompt_category = config.PROMPT_CATEGORY_MAP.get(topic_key, "social")

            # ✅ 여기서 오래 걸릴 수 있으니 HB 켬 (10초마다 경과시간 출력)
            title_text, body_text = run_step(
                driver,
                f"LLM 글 생성 ({topic_key})",
                lambda: generate_post_with_ollama(
                    category=prompt_category,
                    article={
                        "title": article["title"],
                        "link": article["link"],
                        "source": article.get("source", ""),
                        "lead": article.get("lead", "") or "",
                        "excerpt": article.get("excerpt", "") or "",
                    },
                    ollama_url=config.OLLAMA_URL,
                    model=config.OLLAMA_MODEL,
                    timeout=config.LLM_TIMEOUT,
                    topic_tag=topic_key,          # ✅ 디버그 파일명용
                ),
                heartbeat_sec=10
            )

            # 방어: JSON/프롬프트가 그대로 올라가는 상황 차단
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

            # (2) 프롬프트 규칙이 그대로 섞여나오면(“역할:”, “출력 규칙:”) 실패로 간주
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

            
# ===== ✅ 커버 이미지 생성 =====
            image_paths = []
            if getattr(config, "ENABLE_IMAGE", False):
                def _make_img():
                    img = build_sd_prompt(topic_key, title_text)
                    if not img:
                        raise RuntimeError("E_IMAGE_EMPTY_PATH")
                    return img

                img_path = run_step(
                    driver,
                    f"SD 이미지 생성 ({topic_key})",
                    _make_img,
                    heartbeat_sec=10
                )
                image_paths = [img_path]

            # ===== 글쓰기 입력(이미지 포함) =====
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
                    image_paths=image_paths
                ),
                heartbeat_sec=10
            )


            # 발행 처리도 팝업/레이어 대기에서 멈출 수 있어 HB 켬
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
