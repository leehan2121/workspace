# llm_client.py
import requests

def ollama_generate(ollama_url: str, model: str, prompt: str, timeout: int = 600) -> str:
    """
    Ollama local API 호출 (비스트리밍)
    - timeout: read timeout을 충분히 크게
    - options: 너무 길게 생성해서 느려지는 걸 막기 위해 num_predict로 출력 길이 제한
    """
    endpoint = ollama_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            # 출력 토큰 길이 제한 (너무 길어져서 느려지는거 방지)
            "num_predict": 700,
            # 너무 오래 생각만 하는거 완화 (선택)
            "temperature": 0.7,
        }
    }

    # timeout을 (연결, 읽기) 튜플로 줘서 더 안정적으로
    r = requests.post(endpoint, json=payload, timeout=(15, timeout))
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()
