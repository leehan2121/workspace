# tistory_image.py
import time
from pathlib import Path
from typing import List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def _switch_to_frame_chain(driver, chain: List[object]) -> None:
    """
    # 프레임 체인으로 이동한다
    # Switch(전환) to frame chain(프레임 체인)
    """
    driver.switch_to.default_content()
    for fr in chain:
        driver.switch_to.frame(fr)


def _find_file_input_anywhere(driver) -> Optional[Tuple[object, List[object]]]:
    """
    # 현재 문서 + 모든 iframe에서 input[type=file]을 찾는다
    # Find(찾기) input[type=file] across document(문서) and iframes(아이프레임)
    """
    driver.switch_to.default_content()

    # 1) default content
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if inputs:
        return inputs[0], []

    # 2) 1-depth iframes
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for fr in frames:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            inputs2 = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            if inputs2:
                return inputs2[0], [fr]
        except Exception:
            continue

    # 3) 2-depth nested iframes (가끔 에디터 내부가 중첩됨)
    # 3) 2-depth nested iframes(중첩) for editor variants(에디터 변형)
    driver.switch_to.default_content()
    frames1 = driver.find_elements(By.TAG_NAME, "iframe")
    for fr1 in frames1:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr1)
            frames2 = driver.find_elements(By.TAG_NAME, "iframe")
            for fr2 in frames2:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(fr1)
                    driver.switch_to.frame(fr2)
                    inputs3 = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    if inputs3:
                        return inputs3[0], [fr1, fr2]
                except Exception:
                    continue
        except Exception:
            continue

    driver.switch_to.default_content()
    return None


def _open_attach_menu_tinymce(driver, wait) -> bool:
    """
    # TinyMCE 상단 툴바의 '첨부' 메뉴를 연다
    # Open(열기) TinyMCE toolbar(툴바) attach menu(첨부 메뉴)
    """
    driver.switch_to.default_content()
    # 네가 준 DOM 스니펫 기준으로 '첨부' 버튼은 #mceu_0-open
    # Based on DOM snippet(스니펫), attach button(첨부 버튼) is #mceu_0-open
    try:
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#mceu_0-open")))
        btn.click()
        time.sleep(0.2)
        return True
    except Exception:
        return False


def _click_attach_submenu_photo(driver, wait) -> bool:
    """
    # 첨부 드롭다운에서 '사진' 항목을 클릭한다
    # Click(클릭) the 'Photo'(사진) item in the attach dropdown(첨부 드롭다운)
    """
    driver.switch_to.default_content()

    # 1) DOM에서 확정된 고정 id를 최우선으로 클릭
    # First(최우선), click stable id(안정적인 id) confirmed(확정) by DOM snippet(스니펫)
    try:
        el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#attach-image")))
        el.click()
        time.sleep(0.2)
        return True
    except Exception:
        pass

    # 2) 텍스트 기반 백업(사진/이미지)
    # Backup(백업) with text-based selectors(텍스트 기반 선택자)
    candidates = [
        (By.CSS_SELECTOR, "#attach-image-text"),  # 사진 텍스트 span
        (By.XPATH, "//*[@role='menuitem' and .//span[normalize-space()='사진']]"),
        (By.XPATH, "//*[self::div or self::span or self::button or self::a][contains(normalize-space(.), '사진')]"),
        (By.XPATH, "//*[self::div or self::span or self::button or self::a][contains(normalize-space(.), '이미지')]"),
        (By.CSS_SELECTOR, ".mce-i-image"),  # 아이콘 기반
    ]

    for by, sel in candidates:
        try:
            el = wait.until(EC.element_to_be_clickable((by, sel)))
            el.click()
            time.sleep(0.2)
            return True
        except Exception:
            continue

    return False



# tistory_image.py
import time
from typing import Optional, Tuple, List

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def _switch_to_frame_chain(driver, chain: List) -> None:
    """
    # 프레임 체인으로 이동한다
    # Switch(전환) to frame chain(프레임 체인)
    """
    driver.switch_to.default_content()
    for fr in chain:
        driver.switch_to.frame(fr)


def _find_file_input_anywhere(driver) -> Optional[Tuple[object, List]]:
    """
    # 현재 문서 + 모든 iframe에서 input[type=file] 탐색
    # Find(찾기) input[type=file] across document(문서) and iframes(아이프레임)
    """
    driver.switch_to.default_content()
    elems = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if elems:
        return elems[0], []

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for fr in frames:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            elems2 = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            if elems2:
                return elems2[0], [fr]
        except Exception:
            continue

    # 2-depth nested iframes
    driver.switch_to.default_content()
    frames1 = driver.find_elements(By.TAG_NAME, "iframe")
    for fr1 in frames1:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr1)
            frames2 = driver.find_elements(By.TAG_NAME, "iframe")
            for fr2 in frames2:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(fr1)
                    driver.switch_to.frame(fr2)
                    elems3 = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    if elems3:
                        return elems3[0], [fr1, fr2]
                except Exception:
                    continue
        except Exception:
            continue

    driver.switch_to.default_content()
    return None


def _open_attach_menu(driver, wait) -> bool:
    """
    # '첨부' 메뉴를 연다 (TinyMCE)
    # Open(열기) attach menu(첨부 메뉴) in TinyMCE(editor; 에디터)
    """
    try:
        driver.switch_to.default_content()
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#mceu_0-open")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.1)
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.2)
        return True
    except Exception:
        return False


def upload_and_insert_image(driver, wait, image_path: str, sleep_after_upload: float = 2.5) -> bool:
    """
    # OS 파일 선택창을 띄우지 않고 input[type=file]에 send_keys로 업로드한다
    # Upload(업로드) via send_keys(경로 주입) to input[type=file] without OS file dialog(운영체제 파일창)

    핵심:
    - '사진' 메뉴(#attach-image)를 클릭하면 OS 파일창이 뜰 수 있으니 클릭하지 않는다.
    - 대신 '첨부' 메뉴만 열고, 생성/노출된 input[type=file]을 찾아 경로를 주입한다.
    # Key idea(핵심 아이디어): avoid clicking(클릭 회피) photo menu, inject path to file input.
    """
    driver.switch_to.default_content()

    # 1) 첨부 메뉴만 연다 (사진 메뉴 클릭 금지)
    # Only open(열기) attach menu(첨부 메뉴); do NOT click photo menu(사진 메뉴)
    _open_attach_menu(driver, wait)

    # 2) input[type=file]이 동적으로 생길 수 있으니 짧게 폴링하며 탐색
    # Poll(반복 확인) for dynamically created(동적 생성) file input(파일 인풋)
    found = None
    for _ in range(20):
        found = _find_file_input_anywhere(driver)
        if found:
            break
        time.sleep(0.15)

    if not found:
        raise RuntimeError("E_TISTORY_FILE_INPUT_NOT_FOUND: input[type=file]을 찾지 못했습니다.")

    file_input, frame_chain = found

    # 3) 해당 프레임으로 이동 후 send_keys
    # Switch(전환) to frame then send_keys(경로 주입)
    if frame_chain:
        _switch_to_frame_chain(driver, frame_chain)
    else:
        driver.switch_to.default_content()

    try:
        # 일부 사이트는 hidden input이라 interactable 오류가 날 수 있어서 JS로 표시 시도
        # Some sites have hidden input(숨김 인풋) -> try JS to make it visible(보이게)
        driver.execute_script("arguments[0].style.display='block'; arguments[0].style.visibility='visible';", file_input)
        file_input.send_keys(image_path)
    except Exception as e:
        driver.switch_to.default_content()
        raise RuntimeError(f"E_TISTORY_FILE_INPUT_SENDKEYS_FAIL: {repr(e)}")

    driver.switch_to.default_content()

    # 4) 업로드 완료 대기
    # Wait(대기) for upload completion(업로드 완료)
    time.sleep(sleep_after_upload)

    return True
