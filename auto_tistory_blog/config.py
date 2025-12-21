# config.py

# ===== 계정 =====
KAKAO_ID = "leehan2121@kakao.com"
KAKAO_PW = "fnzktm21@!"

# ===== URL =====
TISTORY_LOGIN_URL = "https://www.tistory.com/auth/login"
TISTORY_WRITE_URL = "https://ohmygodit.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F"

# ===== 발행 옵션 =====
DRAFT_ALERT_ACCEPT = False
VISIBILITY_ID = "open0"   # 비공개 고정

# ===== LLM 모드 =====
USE_LLM = True
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:3b"     # 네가 설치한 모델명과 동일해야 함
OLLAMA_MODEL = "llama3.2:3b"
LLM_TIMEOUT = 1200          # 20분 (처음엔 넉넉히)
LLM_NUM_PREDICT = 700       # 너무 길면 속도 느려짐
LLM_TEMPERATURE = 0.3       # 혼합언어/헛소리 줄이기
LLM_TOP_P = 0.9


# ===== Google News RSS (4개 주제) =====
GOOGLE_NEWS_REGION = "hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_LIMIT_PER_TOPIC = 1   # 각 주제당 1개씩만 발행(테스트 목적)

GOOGLE_NEWS_FEEDS = {
    # 최근 1일(when:1d)
    "politics": f"https://news.google.com/rss/search?q=%EC%A0%95%EC%B9%98%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "gossip":   f"https://news.google.com/rss/search?q=%EC%97%B4%EC%95%A0%20OR%20%EC%97%B0%EC%95%A0%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "kpop":     f"https://news.google.com/rss/search?q=KPOP%20OR%20%EC%BC%80%EC%9D%B4%ED%8C%9D%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "hot":      f"https://news.google.com/rss/search?q=%EC%9D%B4%EC%8A%88%20OR%20%EB%85%BC%EB%9E%80%20OR%20%EC%86%8D%EB%B3%B4%20when%3A1d&{GOOGLE_NEWS_REGION}",
}

# prompts.py의 카테고리 키와 맞춰야 함: politics/gossip/social
# hot, kpop은 gossip 또는 social로 매핑해서 사용
PROMPT_CATEGORY_MAP = {
    "politics": "politics",
    "gossip":   "gossip",
    "kpop":     "gossip",
    "hot":      "social",
}

# ===== (선택) RSS 원문(XML) 상단 출력 =====
DEBUG_PRINT_RSS_SOURCE = False

# === 이미지 생성/업로드 ===
ENABLE_IMAGE = True
SD_URL = "http://127.0.0.1:7860"
SD_WIDTH = 1024
SD_HEIGHT = 576
SD_STEPS = 25
SD_CFG_SCALE = 6.5


# === SD(A1111) 이미지 생성 ===
ENABLE_IMAGE = True
SD_URL = "http://localhost:7860"

# 빠른 기본값 (성공률 우선)
SD_WIDTH = 768
SD_HEIGHT = 512
SD_STEPS = 20
SD_CFG_SCALE = 7.0
SD_SAMPLER = "DPM++ 2M"
SD_TIMEOUT_SEC = 900
SD_OUT_DIR = "debug/images"

