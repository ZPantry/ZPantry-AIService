"""Safe Gemini connectivity check; reads GEMINI_API_KEY and GEMINI_MODELS from the environment."""
import os
import sys
import httpx

key = os.getenv("GEMINI_API_KEY")
models = [m.strip() for m in os.getenv("GEMINI_MODELS", os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")).split(",") if m.strip()]
if not key:
    print("GEMINI_API_KEY is not configured", file=sys.stderr)
    raise SystemExit(2)
for model in models:
    response = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}", json={"contents":[{"parts":[{"text":"hello"}]}]}, timeout=15)
    print(f"model={model} httpStatus={response.status_code}")
    if 200 <= response.status_code < 300:
        raise SystemExit(0)
raise SystemExit(1)
