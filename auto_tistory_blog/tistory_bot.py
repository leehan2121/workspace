# tistory_bot.py
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    TimeoutException,
)
from webdriver_manager.chrome import ChromeDriverManager

from tistory_image import upload_and_insert_image
from utils import handle_any_alert


def make_driver():
    # 크롬 드라이버 생성 및 옵션 설정
    # Create(생성) a Chrome(크롬) driver(드라이버) with options(옵션)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 기본 대기(명시적 대기용)
    # Default(기본) explicit wait(명시적 대기)
    wait = WebDriverWait(driver, 20)
    return driver, wait




def login(driver, wait, login_url, kakao_id, kakao_pw):
    """
    # 티스토리 → 카카오 로그인까지 자동 진입하고 계정 입력을 시도한다
    # Auto(자동) navigate(이동) from Tistory login to Kakao login, then try(시도) credential input(자격증명 입력; credential(자격증명))
    """
    # 1) 티스토리 로그인 페이지 이동
    # Go(이동) to Tistory login page(티스토리 로그인 페이지)
    driver.get(login_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # 2) 티스토리 로그인 화면에서 '카카오계정으로 로그인' 버튼 클릭
    # Click(클릭) "Login with Kakao"(카카오계정으로 로그인) button(버튼) on Tistory login page
    try:
        cur = driver.current_url or ""
        if "tistory.com/auth/login" in cur and "accounts.kakao.com" not in cur:
            # ✅ 네가 준 DOM 기준: a.btn_login.link_kakao_id 가 정답
            # ✅ DOM-based(돔 기반) stable selector(안정 선택자): a.btn_login.link_kakao_id
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn_login.link_kakao_id")))

            # 보이는 상태로 스크롤
            # Scroll(스크롤) into view(보이는 위치) to avoid overlay(오버레이) issues(문제)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.2)

            # 일반 클릭 시도
            # Try(시도) normal click(일반 클릭)
            try:
                btn.click()
            except Exception:
                # 클릭이 막히면 JS 클릭으로 강제
                # If blocked(막힘), force click(강제 클릭) via JavaScript(JS; 자바스크립트)
                driver.execute_script("arguments[0].click();", btn)

            # 리다이렉트 대기
            # Wait(대기) for redirect(리다이렉트)
            time.sleep(1.0)

    except Exception:
        # 여기서 실패해도 수동 로그인 가능하도록 진행
        # Even if fail(실패), allow(허용) manual login(수동 로그인)
        pass

    # 3) 카카오 로그인 페이지로 넘어왔는지 확인
    # Ensure(확인) we reached Kakao login page(카카오 로그인 페이지)
    for _ in range(60):
        url = driver.current_url or ""
        print("URL:", url)
        if "accounts.kakao.com" in url:
            break
        time.sleep(0.5)

    # 4) 카카오 아이디/비번 입력 시도 (실패 시 수동 입력 허용)
    # Try(시도) filling Kakao id/pw(아이디/비번); allow(허용) manual input(수동 입력) on failure
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # 입력창 셀렉터는 변형이 있어 후보를 여러 개 둠
        # Input selectors(입력 선택자) may vary(변형), so try multiple candidates(후보)
        id_el = None
        pw_el = None

        for sel in [
            (By.NAME, "loginId"),
            (By.CSS_SELECTOR, "input[name='loginId']"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]:
            try:
                id_el = driver.find_element(*sel)
                if id_el:
                    break
            except Exception:
                continue

        for sel in [
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]:
            try:
                pw_el = driver.find_element(*sel)
                if pw_el:
                    break
            except Exception:
                continue

        if id_el and pw_el:
            id_el.clear()
            id_el.send_keys(kakao_id)
            pw_el.clear()
            pw_el.send_keys(kakao_pw)
            pw_el.send_keys(Keys.ENTER)

    except Exception:
        pass

    # 5) 티스토리로 돌아올 때까지 대기 (수동 로그인도 여기서 흡수)
    # Wait(대기) until redirected back(되돌아옴) to Tistory after login(로그인)
    for _ in range(180):
        url = driver.current_url or ""
        print("URL:", url)
        if "tistory.com" in url and "accounts.kakao.com" not in url:
            return True
        time.sleep(1)

    raise RuntimeError("로그인 완료 안 됨 (Login did not complete(완료되지 않음))")



def find_editor_iframe(driver):
    # 모든 iframe을 순회하면서 '에디터 본문'으로 보이는 프레임 찾기
    # Scan(스캔) all iframes(아이프레임들) to find editor(에디터) frame(프레임)
    for _ in range(30):
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)

                # iframe 내부에서 body/contenteditable 존재 여부로 판별
                # Detect(판별) by checking body(바디) / contenteditable(편집가능) element(요소)
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                except Exception:
                    body = None

                if body:
                    aria = (body.get_attribute("aria-label") or "")
                    cls = (body.get_attribute("class") or "")
                    ce = (body.get_attribute("contenteditable") or "")

                    # 대표적인 에디터 흔적(aria/class/contenteditable)
                    # Common(흔한) editor signals(신호)
                    if ("글 내용 입력" in aria) or ("mce-content-body" in cls) or (ce.lower() == "true"):
                        driver.switch_to.default_content()
                        return frame

                # body가 아니더라도 contenteditable div가 있으면 에디터로 간주
                # If contenteditable div exists(존재), treat as editor(에디터로 간주)
                ces = driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
                if ces:
                    driver.switch_to.default_content()
                    return frame

            except Exception:
                continue

        driver.switch_to.default_content()
        time.sleep(1)

    return None


def _clear_and_type(el, text: str):
    # 입력창 비우고 텍스트 입력
    # Clear(비우기) and type(입력) text(텍스트)
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.BACKSPACE)
    el.send_keys(text)


def _try_input_body_via_iframe(driver, wait, body_text: str, draft_alert_accept: bool) -> bool:
    # 1) 알려진 iframe selector 후보들을 먼저 시도
    # First(먼저), try known(알려진) iframe selectors(선택자 후보들)
    iframe_selectors = [
        "iframe[title='Rich Text Area']",
        "iframe[title*='Rich']",
        "iframe[title*='Text']",
        "iframe[title*='Area']",
        "iframe#tx_canvas_wysiwyg",        # 구형 에디터 케이스
        "iframe.se2_inputarea",            # 스마트에디터 류 케이스
    ]

    for css in iframe_selectors:
        try:
            driver.switch_to.default_content()
            handle_any_alert(driver, accept=draft_alert_accept, timeout=1)

            wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, css)))
            # iframe 안에서는 body에 입력되는 경우가 많음
            # Inside iframe(아이프레임 내부), typing into body(바디 입력) often works(잘 동작)
            body = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            _clear_and_type(body, body_text)

            driver.switch_to.default_content()
            return True
        except TimeoutException:
            driver.switch_to.default_content()
            continue
        except UnexpectedAlertPresentException:
            driver.switch_to.default_content()
            handle_any_alert(driver, accept=draft_alert_accept, timeout=3)
            continue
        except Exception:
            driver.switch_to.default_content()
            continue

    # 2) selector 후보가 실패하면 iframe 자동 탐색
    # If selectors(선택자) fail(실패), auto-detect(자동 탐지) iframe
    frame = find_editor_iframe(driver)
    if frame:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)

            # iframe 내에서 가능한 입력 타겟 후보
            # Candidate(후보) input targets(입력 대상) inside iframe
            targets = []
            try:
                targets.append(driver.find_element(By.CSS_SELECTOR, "body"))
            except Exception:
                pass

            # ProseMirror/ToastUI 계열
            # ProseMirror(프로즈미러) / ToastUI(토스트UI) editors
            targets.extend(driver.find_elements(By.CSS_SELECTOR, "div.ProseMirror"))
            targets.extend(driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']"))

            for t in targets:
                try:
                    if t.is_displayed() and t.is_enabled():
                        _clear_and_type(t, body_text)
                        driver.switch_to.default_content()
                        return True
                except Exception:
                    continue

            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()

    return False


def _try_input_body_via_contenteditable(driver, wait, body_text: str, draft_alert_accept: bool) -> bool:
    # iframe가 없을 때: contenteditable div(예: ProseMirror) 직접 입력
    # When no iframe(아이프레임 없음): type into contenteditable(편집가능) div directly(직접)
    selectors = [
        "div.ProseMirror",                 # ToastUI/ProseMirror
        "[contenteditable='true']",        # 일반 contenteditable
        ".toastui-editor-contents",        # ToastUI contents
    ]

    for css in selectors:
        try:
            driver.switch_to.default_content()
            handle_any_alert(driver, accept=draft_alert_accept, timeout=1)

            el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
            # 클릭/포커스 후 입력
            # Focus(포커스) then type(입력)
            _clear_and_type(el, body_text)
            return True
        except TimeoutException:
            continue
        except UnexpectedAlertPresentException:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=3)
            continue
        except Exception:
            continue

    return False


def click_done_to_open_publish_layer(driver, wait):
    """
    에디터 하단 '완료' 버튼 클릭 → 발행 레이어 열기
    Open(열기) publish layer(발행 레이어) by clicking Done(완료) button(버튼)

    1) id=publish-layer-btn 우선 시도
    First(먼저) try by id(아이디)

    2) 텍스트=완료 버튼 fallback
    Fallback(대체) by text(텍스트) match(매칭)
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


def write_post(driver, wait, write_url, draft_alert_accept, title_text, body_text, image_paths=None, require_image_upload=False):
    # 글쓰기 페이지 진입
    # Open(열기) new post page(새 글 페이지)
    driver.get(write_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # 임시저장 alert 처리
    # Handle(처리) draft alert(임시저장 알림)
    handle_any_alert(driver, accept=draft_alert_accept, timeout=2)

    # ===== 제목 입력 =====
    # Type(입력) title(제목)
    for _ in range(3):
        try:
            title = wait.until(EC.element_to_be_clickable((By.ID, "post-title-inp")))
            _clear_and_type(title, title_text)
            break
        except UnexpectedAlertPresentException:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=5)
    else:
        raise RuntimeError("제목 입력 실패 (Title input failed(실패))")

    # ===== 본문 입력 =====
    # Type(입력) body(본문) with iframe(아이프레임) + fallback(대체) strategy(전략)
    ok = False
    for _ in range(3):
        try:
            # 1) iframe 기반 입력 시도
            # Try(시도) iframe-based(아이프레임 기반) input
            ok = _try_input_body_via_iframe(driver, wait, body_text, draft_alert_accept)
            if ok:
                break

            # 2) contenteditable(div) 직접 입력 시도
            # Try direct(직접) contenteditable(편집가능) input
            ok = _try_input_body_via_contenteditable(driver, wait, body_text, draft_alert_accept)
            if ok:
                break

        except UnexpectedAlertPresentException:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=5)
            continue

    if not ok:
        # 여기까지 오면 에디터 구조가 완전히 달라진 것
        # If we reach here(여기까지 오면), editor DOM(에디터 DOM) likely changed(변경됨)
        raise TimeoutException("본문 입력용 iframe/contenteditable 요소를 찾지 못함 (Cannot find editor input target(입력 대상))")

    # ===== 이미지 업로드/삽입 (완료 버튼 누르기 전에!) =====
    # Upload(업로드) and insert(삽입) images before clicking Done(완료)
    if image_paths:
        for p in image_paths:
            try:
                ok_img = upload_and_insert_image(driver, wait, p, sleep_after_upload=2.5)
                if not ok_img:
                    # 이미지 업로드에 실패해도 글은 계속 진행할지 결정한다
                    # Decide(결정) whether to continue publishing(발행 계속) when image upload(이미지 업로드) fails(실패)
                    if require_image_upload:
                        raise RuntimeError(f"이미지 업로드/삽입 실패: {p}")
                    else:
                        print(f"[WARN] 이미지 업로드 실패 → 이미지 없이 진행: {p}")
            except Exception as e:
                # 이미지 업로드 예외도 치명 여부를 옵션으로 제어한다
                # Control(제어) fatality(치명 여부) of upload exception(업로드 예외) via option(옵션)
                if require_image_upload:
                    raise RuntimeError(f"이미지 업로드/삽입 예외: {p} / {repr(e)}")
                else:
                    print(f"[WARN] 이미지 업로드 예외 → 이미지 없이 진행: {p} / {repr(e)}")
# ===== 완료 클릭 -> 발행 레이어 열기 =====
    # Click Done(완료) to open publish layer(발행 레이어)
    handle_any_alert(driver, accept=draft_alert_accept, timeout=1)
    ok_done = click_done_to_open_publish_layer(driver, wait)
    if not ok_done:
        raise RuntimeError("완료 버튼을 못 찾음 (Done button not found(찾지 못함))")

    return True


def publish_with_visibility(driver, wait, draft_alert_accept, visibility_id):
    # 발행 레이어에서 비공개(open0)/공개(open20)/보호(open15) 선택
    # Select visibility(공개 설정) on publish layer(발행 레이어)
    handle_any_alert(driver, accept=draft_alert_accept, timeout=2)

    wait.until(EC.element_to_be_clickable((By.ID, visibility_id))).click()
    print(f"✅ 공개설정 선택: {visibility_id}")

    # 공개 발행 버튼 (확정)
    # Click publish button(발행 버튼) to confirm(확정)
    wait.until(EC.element_to_be_clickable((By.ID, "publish-btn"))).click()
    print("✅ 발행 완료(publish-btn 클릭)")
    return True
