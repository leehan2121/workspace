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


# ===== Category mapping (카테고리 매핑) =====
# NOTE: topic -> categoryId 매핑이 필요한 경우 main.py에서 topic을 category_id로 변환해서 넘기는 게 가장 안전.
#      (main.py converts topic to category_id and passes it to write_post.)
TISTORY_CATEGORY_ID_MAP = {
    "kpop": "1549319",
    "politics": "1549306",
    "economy": "1549307",
    "society": "1549308",
    "world": "1549309",         # 국제
    "it_science": "1549310",
    "culture_ent": "1549311",
    "sports": "1549312",
}

CATEGORY_NAME_MAP = {
    "1549319": "KPOP",
    "1549306": "정치",
    "1549307": "경제",
    "1549308": "사회",
    "1549309": "국제",
    "1549310": "IT·과학",
    "1549311": "문화·연예",
    "1549312": "스포츠",
}


def make_driver():
    """
    크롬 드라이버 생성 및 옵션 설정
    Create Chrome driver with options
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # webdriver-manager: 자동 설치/버전 매칭
    # Auto-install/match chromedriver via webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 20)
    return driver, wait


# ===== 카테고리 선택 유틸 (Category helpers) =====
def select_category_by_id(driver, wait, category_id: str, retry: int = 3) -> bool:
    """
    티스토리 카테고리 선택 (확정판)
    Final category selector for Tistory editor

    핵심:
    - category-btn 텍스트는 항상 '카테고리/더보기'라서 검증에 사용 불가
      category-btn text doesn't reflect selected value
    - 드롭다운을 다시 열어 활성 아이템의 category-id로 검증
      Verify by reopening dropdown and reading active item's category-id
    """
    cid = str(category_id).strip()
    if not cid or cid == "0":
        return True

    def open_dropdown():
        btn = wait.until(EC.element_to_be_clickable((By.ID, "category-btn")))
        driver.execute_script("arguments[0].click();", btn)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.btn-category [id^="category-item-"][category-id]')
            )
        )

    def close_dropdown():
        # 제목 입력창 클릭로 닫기(가장 안정)
        # Close dropdown by clicking title input (most stable)
        try:
            title_inp = driver.find_element(By.ID, "post-title-inp")
            driver.execute_script("arguments[0].click();", title_inp)
        except Exception:
            driver.execute_script("""
                const c = document.querySelector('#editorContainer');
                if (c) c.click();
            """)

    def click_item():
        # id 형태: category-item-1549306
        # item id format
        item = driver.find_element(By.CSS_SELECTOR, f'#category-item-{cid}[category-id="{cid}"]')
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", item)

        # 이벤트 시퀀스가 더 잘 먹히는 케이스가 있음
        # Dispatch event sequence for reliability
        driver.execute_script("""
            const el = arguments[0];
            ['mouseover','mousedown','mouseup','click'].forEach(type => {
              el.dispatchEvent(new MouseEvent(type, {bubbles:true, cancelable:true, view:window}));
            });
        """, item)

    def read_active_id_from_dropdown() -> str:
        # 드롭다운 내부에서 '활성/선택' 상태인 아이템의 category-id를 읽는다.
        # Read active/selected category-id from dropdown.
        js = r"""
        try {
          const root = document.querySelector('.btn-category') || document;
          const el =
            root.querySelector('[id^="category-item-"][category-id].mce-active') ||
            root.querySelector('[id^="category-item-"][category-id][aria-selected="true"]') ||
            root.querySelector('[id^="category-item-"][category-id].active') ||
            root.querySelector('[id^="category-item-"][category-id].mce-selected');

          if (!el) return '';
          let v = el.getAttribute('category-id') || el.getAttribute('data-category-id') || el.getAttribute('id') || '';
          if (!v) return '';
          v = String(v);
          // id 값이 'category-item-1549306'이면 숫자만 뽑는다.
          const m = v.match(/(\d{4,})$/);
          return m ? m[1] : v;
        } catch (e) {
          return '';
        }
        """
        return (driver.execute_script(js) or "").strip()

    last_seen = ""
    for _ in range(max(1, int(retry))):
        try:
            open_dropdown()
            click_item()
            close_dropdown()
            time.sleep(0.4)

            # 검증(Verification): 다시 열어서 active 항목 확인
            open_dropdown()
            active = read_active_id_from_dropdown()
            last_seen = active or last_seen
            close_dropdown()

            if active == cid:
                return True

            # 간헐적으로 DOM이 늦게 반영됨 → 잠깐 대기 후 재시도
            time.sleep(0.6)

        except Exception as e:
            # 드롭다운이 꼬인 경우를 대비해 닫고 재시도
            try:
                close_dropdown()
            except Exception:
                pass
            time.sleep(0.6)

    print(f"[WARN] 카테고리 선택 검증 실패: target={cid}, active={last_seen}")
    return False


def read_active_category_id() -> str:
    """
    현재 선택(활성)된 카테고리 ID를 최대한 안정적으로 읽어온다.
    - 실패 시 '0' 같은 값 대신 빈 문자열("" )을 반환해서 불필요한 경고 로그를 줄인다.
    """
    # 우선순위: aria-selected=true → .active → 선택된 텍스트 기반
    js = """
    try {
      // 1) 카테고리 목록이 렌더된 영역에서 aria-selected=true 찾기
      var selected = document.querySelector('[role="option"][aria-selected="true"]')
                  || document.querySelector('[role="option"].active')
                  || document.querySelector('.category-list [aria-selected="true"]')
                  || document.querySelector('.category-list .active');

      if (selected) {
        // data-id / value / id 등 후보
        var cid = selected.getAttribute('data-id')
               || selected.getAttribute('data-value')
               || selected.getAttribute('value')
               || selected.getAttribute('data-category-id')
               || selected.getAttribute('id');
        if (cid) return String(cid);
      }

      // 2) 카테고리 버튼(콤보박스)에 선택된 값이 표기되는 경우 텍스트를 반환(상위에서 매핑 가능)
      var btn = document.querySelector('#category-btn');
      if (btn) {
        var t = (btn.innerText || '').trim();
        if (t && t !== '카테고리') return t;
      }
    } catch (e) {}
    return "";
    """
    v = driver.execute_script(js)
    return "" if v in (None, 0, "0") else str(v)
def find_editor_iframe(driver):
    """
    모든 iframe을 순회하면서 '에디터 본문'으로 보이는 프레임 찾기
    Scan all iframes to find an editor frame
    """
    for _ in range(30):
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)

                # iframe 내부에서 body/contenteditable 존재 여부로 판별
                # Detect editor by body/contenteditable
                body = None
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                except Exception:
                    body = None

                if body:
                    aria = (body.get_attribute("aria-label") or "")
                    cls = (body.get_attribute("class") or "")
                    ce = (body.get_attribute("contenteditable") or "")

                    if ("글 내용 입력" in aria) or ("mce-content-body" in cls) or (ce.lower() == "true"):
                        driver.switch_to.default_content()
                        return frame

                # contenteditable div가 있으면 에디터로 간주
                # If contenteditable div exists, treat as editor
                ces = driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
                if ces:
                    driver.switch_to.default_content()
                    return frame

            except Exception:
                continue

        driver.switch_to.default_content()
        time.sleep(1)

    return None


def move_editor_caret_to_top(driver, wait) -> None:
    """
    본문 에디터 커서를 최상단으로 이동
    Move editor caret to top
    """
    iframe = None
    try:
        iframe = driver.find_element(By.ID, "editor-tistory_ifr")
    except Exception:
        iframe = find_editor_iframe(driver)

    if not iframe:
        return

    driver.switch_to.default_content()
    driver.switch_to.frame(iframe)

    driver.execute_script("""
        const doc = document;
        const body = doc.body;
        if (!body) return;

        const first = body.querySelector('p') || body.firstChild || body;
        const range = doc.createRange();

        try { range.setStart(first, 0); }
        catch (e) { range.setStart(body, 0); }

        range.collapse(true);
        const sel = doc.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        // focus
        if (body && body.focus) body.focus();
    """)

    driver.switch_to.default_content()


# ===== 입력 유틸 (Typing helpers) =====

def move_editor_caret_to_marker(driver, wait, marker: str) -> bool:
    """
    본문 에디터에서 marker 문자열 위치로 커서를 이동하고 marker를 삭제한다.
    Move caret to marker text in the editor and delete the marker text.

    반환값:
    - True: marker를 찾고 커서 이동 성공
    - False: marker를 찾지 못함
    """
    if not marker:
        return False

    iframe = find_editor_iframe(driver)
    if not iframe:
        return False

    try:
        driver.switch_to.frame(iframe)
        js = """
        const marker = arguments[0];
        function findTextNode(root) {
          const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
          let node;
          while ((node = walker.nextNode())) {
            const idx = node.nodeValue ? node.nodeValue.indexOf(marker) : -1;
            if (idx >= 0) {
              return { node, idx };
            }
          }
          return null;
        }
        const found = findTextNode(document.body);
        if (!found) return false;

        const range = document.createRange();
        range.setStart(found.node, found.idx);
        range.setEnd(found.node, found.idx + marker.length);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        // marker 문자열 삭제 -> 커서는 그 위치에 남음
        document.execCommand('delete');
        return true;
        """
        ok = bool(driver.execute_script(js, marker))
        return ok
    finally:
        driver.switch_to.default_content()

def _clear_and_type(el, text: str):
    """입력창 비우고 텍스트 입력 / Clear and type"""
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.BACKSPACE)
    el.send_keys(text)


def _try_input_body_via_iframe(driver, wait, body_text: str, draft_alert_accept: bool) -> bool:
    # 1) 알려진 iframe selector 후보들을 먼저 시도
    iframe_selectors = [
        "iframe[title='Rich Text Area']",
        "iframe[title*='Rich']",
        "iframe[title*='Text']",
        "iframe[title*='Area']",
        "iframe#tx_canvas_wysiwyg",
        "iframe.se2_inputarea",
        "iframe#editor-tistory_ifr",  # 티스토리
    ]

    for css in iframe_selectors:
        try:
            driver.switch_to.default_content()
            handle_any_alert(driver, accept=draft_alert_accept, timeout=1)

            wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, css)))
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
    frame = find_editor_iframe(driver)
    if frame:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)

            targets = []
            try:
                targets.append(driver.find_element(By.CSS_SELECTOR, "body"))
            except Exception:
                pass

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
    selectors = [
        "div.ProseMirror",
        "[contenteditable='true']",
        ".toastui-editor-contents",
    ]

    for css in selectors:
        try:
            driver.switch_to.default_content()
            handle_any_alert(driver, accept=draft_alert_accept, timeout=1)

            el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
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


# ===== 로그인 (Login) =====
def login(driver, wait, login_url, kakao_id, kakao_pw):
    """
    티스토리 → 카카오 로그인 자동 진입 및 계정 입력 시도
    Auto navigate to Kakao login and try credential input
    """
    driver.get(login_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # 티스토리 로그인 화면에서 카카오 버튼 클릭
    try:
        cur = driver.current_url or ""
        if "tistory.com/auth/login" in cur and "accounts.kakao.com" not in cur:
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn_login.link_kakao_id")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.2)
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
            time.sleep(1.0)
    except Exception:
        pass

    # 카카오 로그인 페이지 대기
    for _ in range(60):
        url = driver.current_url or ""
        print("URL:", url)
        if "accounts.kakao.com" in url:
            break
        time.sleep(0.5)

    # 카카오 계정 입력 시도
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
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

    # 티스토리로 돌아올 때까지 대기
    for _ in range(180):
        url = driver.current_url or ""
        print("URL:", url)
        if "tistory.com" in url and "accounts.kakao.com" not in url:
            return True
        time.sleep(1)

    raise RuntimeError("로그인 완료 안 됨 (Login did not complete)")


# ===== 발행 레이어 열기 (Open publish layer) =====
def click_done_to_open_publish_layer(driver, wait):
    """
    에디터 하단 '완료' 버튼 클릭 → 발행 레이어 열기
    Click Done button to open publish layer
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


# ===== 글쓰기 (Write post) =====
def write_post(
    driver,
    wait,
    write_url,
    draft_alert_accept,
    title_text,
    body_text,
    image_paths=None,
    require_image_upload=False,
    category_id=None,
    insert_image_at_top=True,
    context_image_path=None,
    context_marker=None
):
    """
    글쓰기 페이지에서 제목/본문/카테고리/이미지 입력 후 '완료'까지
    Fill title/body/category/images then click Done
    """
    driver.get(write_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    handle_any_alert(driver, accept=draft_alert_accept, timeout=2)

    # ===== 카테고리 선택 (Category) =====
    if category_id and str(category_id).strip() != "0":
        select_category_by_id(driver, wait, str(category_id).strip())

    # ===== 제목 입력 (Title) =====
    for _ in range(3):
        try:
            title = wait.until(EC.element_to_be_clickable((By.ID, "post-title-inp")))
            _clear_and_type(title, title_text)
            break
        except UnexpectedAlertPresentException:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=5)
    else:
        raise RuntimeError("제목 입력 실패 (Title input failed)")

    # ===== 본문 입력 (Body) =====
    ok = False
    for _ in range(3):
        try:
            ok = _try_input_body_via_iframe(driver, wait, body_text, draft_alert_accept)
            if ok:
                break
            ok = _try_input_body_via_contenteditable(driver, wait, body_text, draft_alert_accept)
            if ok:
                break
        except UnexpectedAlertPresentException:
            handle_any_alert(driver, accept=draft_alert_accept, timeout=5)
            continue

    if not ok:
        raise TimeoutException("본문 입력용 iframe/contenteditable 요소를 찾지 못함 (Cannot find editor input target)")


# ===== 이미지 최상단 삽입을 원하면: 본문 입력 후, 커서를 최상단으로 옮긴 뒤 넣는 게 가장 안정(본문 입력이 기존 내용을 지울 수 있음) =====
    if image_paths and insert_image_at_top:
        try:
            move_editor_caret_to_top(driver, wait)
        except Exception:
            pass

        for p in image_paths:
            print("p:=============",p)
            try:
                ok_img = upload_and_insert_image(driver, p, timeout=180, sleep_after_upload=2.5)
                if not ok_img:
                    if require_image_upload:
                        raise RuntimeError(f"이미지 업로드/삽입 실패: {p}")
                    print(f"[WARN] 이미지 업로드 실패 → 이미지 없이 진행: {p}")
            except Exception as e:
                if require_image_upload:
                    raise RuntimeError(f"이미지 업로드/삽입 예외: {p} / {repr(e)}")
                print(f"[WARN] 이미지 업로드 예외 → 이미지 없이 진행: {p} / {repr(e)}")

    

    

    # ===== 배경·맥락 이미지: 마커 위치에 삽입 =====
    if context_image_path and context_marker:
        try:
            ok_mark = move_editor_caret_to_marker(driver, wait, context_marker)
            if not ok_mark:
                print(f"[WARN] context marker not found -> skip context image (marker={context_marker})")
            else:
                ok_ctx = upload_and_insert_image(
                    driver,
                    context_image_path,
                    timeout=180,
                    sleep_after_upload=2.5
                )
                if not ok_ctx:
                    if require_image_upload:
                        raise RuntimeError(
                            f"배경·맥락 이미지 업로드/삽입 실패: {context_image_path}"
                        )
                    print(
                        f"[WARN] 배경·맥락 이미지 업로드 실패 → 이미지 없이 진행: {context_image_path}"
                    )
        except Exception as e:
            if require_image_upload:
                raise
            print(
                f"[WARN] 배경·맥락 이미지 업로드 예외 → 이미지 없이 진행: {context_image_path} / {e!r}"
            )

    # ===== 이미지가 있는데 '최상단'이 아니라면: 본문 입력 후 삽입 =====
    if image_paths and not insert_image_at_top:
        for p in image_paths:
            try:
                ok_img = upload_and_insert_image(driver, p, timeout=180, sleep_after_upload=2.5)
                if not ok_img:
                    if require_image_upload:
                        raise RuntimeError(f"이미지 업로드/삽입 실패: {p}")
                    print(f"[WARN] 이미지 업로드 실패 → 이미지 없이 진행: {p}")
            except Exception as e:
                if require_image_upload:
                    raise RuntimeError(f"이미지 업로드/삽입 예외: {p} / {repr(e)}")
                print(f"[WARN] 이미지 업로드 예외 → 이미지 없이 진행: {p} / {repr(e)}")

    # ===== 완료 클릭 -> 발행 레이어 열기 =====
    handle_any_alert(driver, accept=draft_alert_accept, timeout=1)
    ok_done = click_done_to_open_publish_layer(driver, wait)
    if not ok_done:
        raise RuntimeError("완료 버튼을 못 찾음 (Done button not found)")

    return True


def publish_with_visibility(driver, wait, draft_alert_accept, visibility_id):
    """
    발행 레이어에서 공개 범위 선택 후 발행
    Select visibility then publish
    """
    handle_any_alert(driver, accept=draft_alert_accept, timeout=2)

    # NOTE(KO): 티스토리 발행 레이어는 DOM/애니메이션 때문에
    #           element_to_be_clickable이 간헐적으로 TimeoutException을 유발한다.
    #           -> presence 대기 후 JS 클릭을 병행.
    # NOTE(EN): Publish layer can be flaky; use presence + JS click fallback.

    vid = (visibility_id or "").strip()
    if not vid:
        raise RuntimeError("VISIBILITY_ID가 비어있음")

    handle_any_alert(driver, accept=draft_alert_accept, timeout=2)

    # 1) presence 먼저
    try:
        el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, vid)))
    except TimeoutException:
        # radio가 늦게 렌더링되는 경우: publish-layer 내부에서 재탐색
        el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"input#{vid}[type='radio']"))
        )

    # 2) 클릭 시도(일반 클릭 -> JS 클릭)
    try:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, vid))).click()
    except Exception:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)

    print(f"✅ 공개설정 선택: {vid}")

    # 발행 버튼
    try:
        btn = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "publish-btn")))
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "publish-btn"))).click()
        except Exception:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            driver.execute_script("arguments[0].click();", btn)
    except Exception as e:
        raise TimeoutException(f"publish-btn 클릭 실패: {e!r}")

    print("✅ 발행 완료(publish-btn 클릭)")
    return True
