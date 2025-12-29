# tistory_image.py
import os
import time
from pathlib import Path
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait


def _ts() -> str:
    """
    # 로그용 타임스탬프 문자열을 만든다.
    # Build(만들기) timestamp(타임스탬프) string for logs(로그).
    """
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _log(level: str, msg: str) -> None:
    """
    # 업로드 로직 디버깅을 위해 로그를 남긴다.
    # Log(로그) messages for debugging(디버깅) upload flow(업로드 흐름).
    """
    print(f"[{_ts()}][IMG][{level}] {msg}")


def _safe_send_keys(driver, by, selector, value, *, retries: int = 3):
    """
    # 요소를 찾아 send_keys를 안전하게 수행한다(재시도 포함).
    # Safely(안전하게) send keys(키 입력) with retries(재시도).
    """
    last_err: Optional[Exception] = None
    for n in range(1, retries + 1):
        try:
            el = driver.find_element(by, selector)
            el.send_keys(value)
            return el
        except Exception as e:
            last_err = e
            _log("WARN", f"send_keys retry({n}/{retries}) fail: {by} {selector} err={e!r}")
            time.sleep(0.3)
    raise last_err  # type: ignore[misc]


def _find_windows_file_dialog_hwnd() -> Optional[int]:
    """
    # Windows 네이티브 파일 선택창(hwnd)을 찾는다(pywin32가 있을 때만).
    # Find(찾기) Windows native file dialog hwnd(핸들) when pywin32 is available(가능할 때).

    메모:
    - 일반 파일 열기 대화상자 클래스(class; 클래스)는 보통 '#32770' 이다.
    """
    try:
        import win32gui  # pip install pywin32

        hwnd = win32gui.FindWindow("#32770", None)
        return int(hwnd) if hwnd else None
    except Exception:
        return None


def _close_native_file_dialog() -> bool:
    """
    # Windows 파일 선택창(네이티브)을 '브라우저를 닫지 않고' 안전하게 닫는다.
    # Close(닫기) Windows native file dialog(파일창) safely(안전하게) without closing Chrome(크롬 닫기 없이).

    ⚠️ 중요:
    - Alt+F4는 활성 창을 닫는다.
    - 파일창이 아니라 Chrome이 활성화돼 있으면 브라우저가 닫혀 Selenium 세션이 끊긴다.
    - So we DO NOT use Alt+F4(Alt+F4 사용 금지) by default(기본).

    전략:
    1) ESC 여러 번 (pyautogui)
    2) (옵션) pywin32가 있으면 '#32770' 창을 WM_CLOSE로 닫기(브라우저에 안전)
    """
    try:
        import pyautogui  # pip install pyautogui

        time.sleep(0.4)  # dialog focus wait

        for _ in range(4):
            pyautogui.press("esc")
            time.sleep(0.15)

        hwnd = _find_windows_file_dialog_hwnd()
        if hwnd:
            try:
                import win32gui
                import win32con
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.2)
                _log("INFO", f"native file dialog WM_CLOSE sent hwnd={hwnd}")
            except Exception as e:
                _log("WARN", f"WM_CLOSE failed: {e!r}")

        _log("INFO", "native file dialog close attempt: ESC x4 (+WM_CLOSE if possible)")
        return True
    except Exception as e:
        _log("WARN", f"native file dialog close skipped/failed: {e!r}")
        return False


# (호환성) 예전 이름을 쓰는 코드가 있을 수 있어서 alias(별칭) 제공
# Compatibility(호환): provide alias name for old callers(예전 호출자).
_close_native_file_dialog_esc = _close_native_file_dialog
_close_native_file_dialog = _close_native_file_dialog


def _open_attach_menu(driver, wait: WebDriverWait) -> bool:
    """
    # TinyMCE 상단 툴바의 '첨부' 메뉴를 연다.
    # Open(열기) attach menu(첨부 메뉴) in TinyMCE(toolbar; 툴바).

    고정 셀렉터:
    - #mceu_0-open
    """
    try:
        driver.switch_to.default_content()
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#mceu_0-open")))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.2)
        _log("INFO", "attach menu opened (#mceu_0-open clicked)")
        return True
    except Exception as e:
        _log("WARN", f"attach menu open failed: {e!r}")
        return False


def _click_attach_photo(driver, wait: WebDriverWait) -> bool:
    """
    # 첨부 드롭다운에서 '사진'을 클릭해 #openFile 생성/활성화를 트리거한다.
    # Click(클릭) Photo(사진) to trigger(트리거) #openFile creation(생성).

    고정 셀렉터:
    - #attach-image
    """
    try:
        driver.switch_to.default_content()
        photo = wait.until(EC.element_to_be_clickable((By.ID, "attach-image")))
        driver.execute_script("arguments[0].click();", photo)
        time.sleep(0.2)
        _log("INFO", "photo clicked (#attach-image) -> should create #openFile")
        return True
    except Exception as e:
        _log("WARN", f"photo click failed: {e!r}")
        return False


def _get_attachment_cnt(driver) -> int:
    """
    # window.Config.attachmentRawData.length 값을 가져온다.
    # Get(가져오기) window.Config.attachmentRawData.length.
    """
    try:
        cnt = driver.execute_script(
            "return (window.Config && window.Config.attachmentRawData) ? window.Config.attachmentRawData.length : 0;"
        )
        return int(cnt or 0)
    except Exception:
        return 0


def upload_and_insert_image(driver, image_path: str, timeout: int = 60, sleep_after_upload: float = 1.0) -> bool:
    """
    # 티스토리 글쓰기(/manage/newpost)에서 이미지를 업로드(첨부)하고 반영을 확인한다.
    # Upload(업로드) an image(이미지) on Tistory newpost editor(글쓰기) and verify(검증) it.

    고정 순서(베이스라인):
    1) 첨부(#mceu_0-open) → 2) 사진(#attach-image) → 3) 파일창 닫기(OS ESC)
    4) #openFile presence 대기 → 5) send_keys(image_path) → 6) attachmentRawData 증가 대기
    """
    if not image_path:
        _log("WARN", "image_path is empty -> skip")
        return False

    if isinstance(image_path, Path):
        image_path = str(image_path)
    image_path = os.path.abspath(image_path)

    if not os.path.exists(image_path):
        _log("ERROR", f"image not found: {image_path}")
        raise FileNotFoundError(image_path)

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    wait = WebDriverWait(driver, timeout)

    before_cnt = _get_attachment_cnt(driver)
    _log("INFO", f"before attachmentRawData.length = {before_cnt}")

    _open_attach_menu(driver, wait)
    _click_attach_photo(driver, wait)

    # 🔥 변경 핵심: Alt+F4 제거(브라우저 닫힘 방지) + WM_CLOSE 옵션
    _close_native_file_dialog()

    driver.switch_to.default_content()
    _log("INFO", "waiting #openFile presence...")
    wait.until(EC.presence_of_element_located((By.ID, "openFile")))
    _log("INFO", "#openFile present")

    selectors = [
        (By.ID, "openFile"),
        (By.CSS_SELECTOR, "input#openFile[type='file']"),
        (By.CSS_SELECTOR, "input[type='file']#openFile"),
        (By.CSS_SELECTOR, "input[type='file']"),
    ]

    ok = False
    last_err: Optional[Exception] = None

    for by, sel in selectors:
        try:
            _log("INFO", f"send_keys try selector: {by} {sel}")
            _safe_send_keys(driver, by, sel, image_path)
            ok = True
            _log("INFO", f"send_keys OK: {sel}")
            break
        except Exception as e:
            last_err = e
            _log("WARN", f"send_keys failed: {sel} err={e!r}")

    if not ok:
        _log("ERROR", f"send_keys all failed last_err={last_err!r}")
        raise TimeoutException("file input send_keys failed")

    _log("INFO", "waiting attachmentRawData.length increase...")

    def _uploaded(_drv):
        cnt = _get_attachment_cnt(_drv)
        return cnt > before_cnt

    wait.until(_uploaded)

    after_cnt = _get_attachment_cnt(driver)
    _log("INFO", f"after attachmentRawData.length = {after_cnt} (uploaded)")

    if sleep_after_upload:
        time.sleep(sleep_after_upload)

    return True
