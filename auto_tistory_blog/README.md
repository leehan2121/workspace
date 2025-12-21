auto_tistory_blog/
 ├─ main.py                 (수정)
 ├─ config.py               (수정)
 ├─ prompts.py              (그대로)
 ├─ generator.py            (그대로)
 ├─ llm_client.py           (그대로)
 ├─ rss.py                  (그대로)
 ├─ tistory_bot.py          (그대로)
 ├─ utils.py                (그대로)
 └─ sources/
     ├─ __init__.py         (신규)
     └─ google_news.py      (신규)

Ollama는 로컬 PC에서 대형 언어 모델(LLM)을 실행하게 해주는 런타임/서버다.

인터넷 없이도 동작하며, API 서버(http://127.0.0.1:11434) 를 띄워서 파이썬·노드·VS Code 터미널에서 호출 가능하다.

VS Code 터미널에서 설치/실행 가능하다. (Windows/macOS/Linux 지원)

winget install Ollama.Ollama
where.exe ollama
>> ollama --version

ollama pull llama3.2:3b


# 실행 명령어 terminal
# webui-user.bat --api
& "C:\stable-diffusion-webui\webui-user.bat" --api --listen --port 7860
git --version 
# 없으면 👉 https://git-scm.com/download/win

# 원하는 위치에서 실행 (예: C:)
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git

# 👉 링크: https://huggingface.co/Lykon/DreamShaper
Files and versions -> DreamShaper_8_pruned.safetensors 
# 다운된 파일을 이동
C:\stable-diffusion-webui\models\Stable-diffusion\
