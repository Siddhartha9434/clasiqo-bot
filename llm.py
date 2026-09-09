"""
LLM wrapper with two free backends:

  - "groq"   -> Groq's free-tier hosted API (https://console.groq.com). This is
                what makes the pipeline work with your laptop OFF, since it's a
                cloud call, not something running on your machine. Free tier,
                no credit card required at signup, generous request quota.
  - "ollama" -> local Ollama instance (free, but only works while your machine
                is on and `ollama serve` is running). Handy for testing locally.

Backend is chosen automatically:
  - If a GROQ_API_KEY environment variable is set -> use Groq.
  - Otherwise -> fall back to local Ollama.

This means: run locally with just Ollama installed (no key needed), but the
GitHub Actions workflow (which has no way to run Ollama persistently) sets
GROQ_API_KEY as a repo secret and automatically uses Groq instead - fully
automatic, fully cloud-based, $0 cost either way.
"""
import json
import os
import time
import requests

from config import OLLAMA_MODEL, OLLAMA_HOST, GROQ_MODEL

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

BACKEND = "groq" if GROQ_API_KEY else "ollama"


def _groq_chat(prompt: str, system: str = None, json_mode: bool = False,
               temperature: float = 0.7, max_retries: int = 4) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                # Free-tier rate limit - back off and retry rather than fail the run
                wait = int(resp.headers.get("retry-after", 5)) + attempt * 3
                print(f"[llm] Groq rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Groq request failed after {max_retries} attempts: {last_err}")


def _ollama_chat(prompt: str, system: str = None, json_mode: bool = False,
                  temperature: float = 0.7) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    if json_mode:
        payload["format"] = "json"

    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()


def generate(prompt: str, system: str = None, json_mode: bool = False, temperature: float = 0.7) -> str:
    if BACKEND == "groq":
        return _groq_chat(prompt, system=system, json_mode=json_mode, temperature=temperature)
    return _ollama_chat(prompt, system=system, json_mode=json_mode, temperature=temperature)


def generate_json(prompt: str, system: str = None, temperature: float = 0.3) -> dict:
    raw = generate(prompt, system=system, json_mode=True, temperature=temperature)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Model occasionally wraps JSON in text/fences despite format=json; try to salvage
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not parse JSON from model output: {raw[:300]}")


if __name__ == "__main__":
    print(f"[llm] backend = {BACKEND}")
    print(generate("Say hello in one short sentence."))
