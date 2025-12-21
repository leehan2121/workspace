# llm_client.py
import requests

def ollama_generate(ollama_url: str, model: str, prompt: str, timeout: int = 600) -> str:
    endpoint = ollama_url.rstrip("/") + "/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,

        # ✅ JSON 출력 강제 (Ollama 지원)
        "format": "json",

        "options": {
            "num_predict": 900,
            "temperature": 0.2,
            "top_p": 0.9,
            "repeat_penalty": 1.1,

            # ✅ 프롬프트/입력 블록 재출력 방지용 stop
            "stop": [
                "\n[입력]",
                "\n\n[입력]",
                "\n[출력 형식]",
                "\n\n[출력 형식]",
            ],
        },
    }

    r = requests.post(endpoint, json=payload, timeout=(15, timeout))
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()
