# tistory_bot.py
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager

from utils import pause_forever, handle_any_alert


def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 30)
    return driver, wait


def login(driver, wait, tistory_login_url, kakao_id, kakao_pw):
    driver.get(tistory_login_url)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn_login.link_kakao_id"))).click()

    try:
        wait.until(EC.presence_of_element_located((By.ID, "loginId--1")))
        driver.find_element(By.ID, "loginId--1").clear()
        driver.find_element(By.ID, "loginId--1").send_keys(kakao_id)

        driver.find_element(By.ID, "password--2").clear()
        driver.find_element(By.ID, "password--2").send_keys(kakao_pw)
        driver.find_element(By.ID, "password--2").send_keys(Keys.ENTER)
    except Exception:
        pass  # 수동 로그인 허용

    # 2초마다 URL 로그 (수동 개입 가능)
    for _ in range(120):
        print("URL:", driver.current_url)
        if "tistory.com" in driver.current_url and "accounts.kakao.com" not in driver.current_url:
            return True
        time.sleep(2)

    pause_forever(driver, "로그인 완료 안 됨")
    return False


def find_editor_iframe(driver):
    for _ in range(30):
        for frame in driver.find_elements(By.TAG_NAME, "iframe"):
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                aria = body.get_attribute("aria-label") or ""
                cls = body.get_attribute("class") or ""
                if "글 내용 입력" in aria or "mce-content-body" in cls:
                    driver.switch_to.default_content()
                    return frame
            except Exception:
                pass
        driver.switch_to.default_content()
        time.sleep(1)
    return None


def click_done_to_open_publish_layer(driver, wait):
    """
    에디터 하단 '완료' -> 발행 레이어 열기
    1) id=publish-layer-btn
    2) 텍스트=완료 버튼
    """
    try:
        btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.ID, "publish-layer-btn")))
        btn.click()
        print("✅ 완료 버튼 클릭(id=publish-layer-btn)")
        return True
    except Exception:
        pass

    xpath = "//button[normalize-space()='완료']"
    btns = driver.find_elements(By.XPATH, xpath)
    for b in btns:
        try:
            if b.is_displayed() and b.is_enabled():
                b.click()
                print("✅ 완료 버튼 클릭(텍스트 매칭)")
                return True
        except Exception:
            continue

    return False


def write_post(driver, wait, write_url, draft_alert_accept, title_text, body_text):
    # 글쓰기 진입
    driver.get(write_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # 임시저장 alert 처리
    handle_any_alert(driver, accept=draft_alert_accept, timeout=5)

    # 제목 입력 (확정: post-title-inp)
    for _ in range(3):
        try:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=1)
            title_el = wait.until(EC.element_to_be_clickable((By.ID, "post-title-inp")))
            title_el.click()
            title_el.clear()
            title_el.send_keys(title_text)
            break
        except UnexpectedAlertPresentException:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=5)
    else:
        pause_forever(driver, "제목 입력 실패(alert 반복)")

    # 본문 입력 (확정: iframe)
    for _ in range(3):
        try:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=1)
            iframe = find_editor_iframe(driver)
            if not iframe:
                pause_forever(driver, "에디터 iframe 못 찾음")

            driver.switch_to.frame(iframe)
            body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            body.click()
            body.send_keys(Keys.CONTROL, "a")
            body.send_keys(Keys.BACKSPACE)
            body.send_keys(body_text)
            driver.switch_to.default_content()
            break
        except UnexpectedAlertPresentException:
            driver.switch_to.default_content()
            handle_any_alert(driver, accept=draft_alert_accept, timeout=5)
    else:
        pause_forever(driver, "본문 입력 실패(alert 반복)")

    # 완료 클릭 -> 발행 레이어 열기
    handle_any_alert(driver, accept=draft_alert_accept, timeout=1)
    ok = click_done_to_open_publish_layer(driver, wait)
    if not ok:
        pause_forever(driver, "완료 버튼을 못 찾음(완료 버튼 DOM 확인 필요)")

    return True


def publish_with_visibility(driver, wait, draft_alert_accept, visibility_id):
    # 발행 레이어에서 비공개(open0)/공개(open20)/보호(open15) 선택
    handle_any_alert(driver, accept=draft_alert_accept, timeout=2)

    wait.until(EC.element_to_be_clickable((By.ID, visibility_id))).click()
    print(f"✅ 공개설정 선택: {visibility_id}")

    # 공개 발행 버튼 (확정)
    wait.until(EC.element_to_be_clickable((By.ID, "publish-btn"))).click()
    print("✅ 발행 완료(publish-btn 클릭)")
    return True
