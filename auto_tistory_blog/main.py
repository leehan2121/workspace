# main.py
from datetime import datetime

import config
from rss import fetch_rss_items
from tistory_bot import make_driver, login, write_post, publish_with_visibility
from utils import pause_forever


def build_body(items):
    lines = []
    lines.append(f"[자동 수집 뉴스] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['title']}")
        lines.append(it["link"])
        lines.append("")
    return "\n".join(lines)


def main():
    items = fetch_rss_items(config.RSS_URL, config.MAX_ITEMS)
    if not items:
        pause_forever(None, "RSS 수집 결과가 비어있음")

    title_text = f"[자동] 뉴스 모음 {datetime.now().strftime('%Y-%m-%d')}"
    body_text = build_body(items)

    driver, wait = make_driver()

    try:
        login(driver, wait, config.TISTORY_LOGIN_URL, config.KAKAO_ID, config.KAKAO_PW)

        write_post(
            driver, wait,
            config.TISTORY_WRITE_URL,
            config.DRAFT_ALERT_ACCEPT,
            title_text,
            body_text
        )

        publish_with_visibility(
            driver, wait,
            config.DRAFT_ALERT_ACCEPT,
            config.VISIBILITY_ID
        )

        pause_forever(driver, "작업 완료(브라우저 유지)")

    except Exception as e:
        pause_forever(driver, f"예외 발생: {repr(e)}")


if __name__ == "__main__":
    main()
