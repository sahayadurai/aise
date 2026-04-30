"""OpenRouter LLM client."""
from __future__ import annotations
import httpx, time
from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL


async def chat_completion(
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> dict:
    """
    Send a chat completion request to OpenRouter.
    Returns {content, model, usage, latency_s}.
    """
    api_key = (OPENROUTER_API_KEY or "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set. Please set it in your .env file.")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "RAG-Benchmark",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
    data = resp.json()
    latency = round(time.time() - t0, 2)

    content = ""
    if data.get("choices"):
        content = data["choices"][0].get("message", {}).get("content", "")

    return {
        "content": content,
        "model": data.get("model", model),
        "usage": data.get("usage", {}),
        "latency_s": latency,
    }
