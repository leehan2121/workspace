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
    # 티스토리 글쓰기 화면에서 OS 파일창 없이 이미지 업로드/삽입
    # Upload/insert image without OS file dialog by using file input send_keys()

    핵심 포인트:
    - iframe(editor-tistory_ifr)은 "본문 편집" 영역이다. 업로드 input은 iframe 밖에 있다.
    - 업로드 input은 id="openFile" 로 존재한다.
    # Key point: editor iframe is for content(editing), file input lives in top-level DOM.
    """

    driver.switch_to.default_content()

    # 1) 첨부 메뉴 열기(선택)
    # Attach menu open(optional). Some UI flows require this, but file input exists anyway.
    try:
        btn_attach = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#mceu_0-open")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_attach)
        time.sleep(0.1)
        try:
            btn_attach.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_attach)
        time.sleep(0.2)
    except Exception:
        # 첨부 버튼 못 찾아도 계속 진행 (openFile이 있으면 업로드 가능)
        # Continue if attach button not found (upload still possible via #openFile).
        pass

    # 2) 업로드 input 찾기: #openFile (iframe 밖)
    # Find upload input: #openFile (outside iframe).
    file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#openFile[type='file']")))

    # 3) hidden/투명 요소라도 send_keys는 되는 편이라 그대로 시도,
    #    막히면 JS로 visibility만 보정
    # Try send_keys even if hidden/transparent; if blocked, adjust visibility via JS.
    try:
        file_input.send_keys(image_path)
    except Exception:
        driver.execute_script(
            "arguments[0].style.display='block';"
            "arguments[0].style.visibility='visible';"
            "arguments[0].style.opacity='1';",
            file_input
        )
        file_input.send_keys(image_path)

    # 4) 업로드/삽입 반영 대기
    # Wait for upload/render to complete.
    time.sleep(sleep_after_upload)

    return True