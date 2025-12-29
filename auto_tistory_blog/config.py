# config.py
import os  # <-- 필수

# ===== 계정 =====
KAKAO_ID = "leehan2121@kakao.com"
KAKAO_PW = "fnzktm21@!"

# ===== URL =====
TISTORY_LOGIN_URL = "https://www.tistory.com/auth/login"
TISTORY_WRITE_URL = "https://ohmygodit.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F"

# ===== 발행 옵션 =====
DRAFT_ALERT_ACCEPT = False
# 공개 설정 라디오 ID
# open20: 공개, open15: 공개(보호), open0: 비공개
VISIBILITY_ID = "open0"  # 공개

# ===== 이미지 옵션 =====
REQUIRE_IMAGE_UPLOAD = False  # 이미지 실패 시 글 발행을 계속할지 여부

# ===== LLM 모드 =====
USE_LLM = True
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:3b"  # 중복 제거
LLM_TIMEOUT = 1200

LLM_TEMPERATURE = 0.2
LLM_TOP_P = 0.9
LLM_NUM_PREDICT = 2800
LLM_MAX_RETRIES = 2

LLM_MIN_BODY_CHARS = 1000
LLM_MIN_PARAGRAPHS = 4
LLM_REWRITE_ON_SHORT = True
LLM_REWRITE_MAX_TRIES = 1
LLM_REWRITE_NUM_PREDICT = 2200

# ===== Google News RSS =====
GOOGLE_NEWS_REGION = "hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_LIMIT_PER_TOPIC = int(os.getenv("GOOGLE_NEWS_LIMIT_PER_TOPIC", "3"))
GOOGLE_NEWS_FETCH_LIMIT_PER_TOPIC = 25
ARTICLE_MAX_TRIES_PER_TOPIC = 5

GOOGLE_NEWS_FEEDS = {
    "politics": f"https://news.google.com/rss/search?q=%EC%A0%95%EC%B9%98%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "gossip":   f"https://news.google.com/rss/search?q=%EC%97%B4%EC%95%A0%20OR%20%EC%97%B0%EC%95%A0%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "kpop":     f"https://news.google.com/rss/search?q=KPOP%20OR%20%EC%BC%80%EC%9D%B4%ED%8C%9D%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "hot":      f"https://news.google.com/rss/search?q=%EC%9D%B4%EC%8A%88%20OR%20%EB%85%BC%EB%9E%80%20OR%20%EC%86%8D%EB%B3%B4%20when%3A1d&{GOOGLE_NEWS_REGION}",
}

PROMPT_CATEGORY_MAP = {
    "politics": "politics",
    "gossip":   "gossip",
    "kpop":     "gossip",
    "hot":      "social",
}

DEBUG_PRINT_RSS_SOURCE = False

ENABLE_ARTICLE_HINT = True
ARTICLE_HINT_TIMEOUT_SEC = 12

APPEND_SOURCE_URL = True

# === SD(A1111) 이미지 생성/업로드 ===
ENABLE_IMAGE = True
SD_URL = "http://127.0.0.1:7860"
SD_WIDTH = 768
SD_HEIGHT = 512
SD_STEPS = 18
SD_CFG_SCALE = 7.0
SD_SAMPLER = None
SD_TIMEOUT_SEC = 900
SD_OUT_DIR = "debug/images"

TISTORY_CATEGORY_ID_MAP = {
    "kpop": "1549319",
    "politics": "1549306",
    "economy": "1549307",
    "society": "1549308",
    "international": "1549309",
    "it_science": "1549310",
    "culture_ent": "1549311",
    "sports": "1549312",
    "gossip": "1549311",
    "hot": "1549308",
}

INSERT_IMAGE_AT_TOP = True

# ===== RSS sources CSV =====
USE_RSS_SOURCES_CSV = os.getenv("USE_RSS_SOURCES_CSV", "1") == "1"
RSS_SOURCES_CSV_PATH = os.getenv("RSS_SOURCES_CSV_PATH", "rss_sources.csv")

# 토픽별로 추가하고 싶은 RSS 목록(선택).
EXTRA_RSS_FEEDS_GLOBAL = [
    "https://www.techradar.com/feeds.xml",
]
EXTRA_RSS_DEFAULT_TOPIC = "it_science"
EXTRA_RSS_FEEDS_BY_TOPIC = {}

# ===== Pre-LLM hint guard =====
HINT_MIN_TOTAL_CHARS = 450
HINT_MIN_EXCERPT_CHARS = 120
STRIP_ENGLISH_TOKENS = os.getenv("STRIP_ENGLISH_TOKENS", "1") == "1"


# ===== Auto-generated override: RSS only (Newsis + YonhapNewsTV) =====
GOOGLE_NEWS_FEEDS = {}
EXTRA_RSS_FEEDS_GLOBAL = []
# EXTRA_RSS_FEEDS_BY_TOPIC will be filled by rss_sources.csv loader
