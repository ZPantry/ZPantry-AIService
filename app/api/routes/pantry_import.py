"""Gemini pantry-image analysis with mode-specific prompts and validated output."""
import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import re
import time
from io import BytesIO
from collections import OrderedDict
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas.common_schema import ApiResponse

router = APIRouter()
log = logging.getLogger("uvicorn.error")
MAX_BYTES = 10 * 1024 * 1024
MAX_IMAGE_EDGE = int(os.getenv("GEMINI_MAX_IMAGE_EDGE", "1536"))
SUPPORTED_TYPES = {"FOOD_IMAGE", "RECEIPT"}
REASONS = {"BLURRY", "TOO_DARK", "NO_FOOD", "NOT_SUPPORTED", "UNCERTAIN"}
CATEGORIES = {"MEAT", "SEAFOOD", "VEGETABLE", "FRUIT", "DAIRY_EGG", "GRAIN_STARCH", "SPICE_SAUCE", "OIL_FAT", "BEVERAGE", "SNACK_SWEET", "OTHER_FOOD"}
STATES = {"FRESH", "FROZEN", "COOKED", "DRIED", "CANNED", "PROCESSED", "UNKNOWN"}
UNITS = {"g", "kg", "ml", "l", "piece", "pack", "bottle", "can", "bunch"}
QUANTITY_SOURCES = {"PRINTED", "COUNTED", "NONE"}
GARBAGE_RECEIPT = re.compile(r"\b(tổng|cộng|vat|giảm\s*giá|khuyến\s*mãi|túi|phí|thuế|discount|total|tax|bag|fee)\b", re.IGNORECASE)
PROMPT_DIR = Path(__file__).resolve().parents[3] / "prompts"

SCHEMA = {"type": "OBJECT", "properties": {
    "reason": {"type": "STRING", "enum": sorted(REASONS), "nullable": True},
    "ingredients": {"type": "ARRAY", "maxItems": 40, "items": {"type": "OBJECT", "properties": {
        "rawName": {"type": "STRING", "description": "Vietnamese UTF-8 food name; never use English."},
        "canonicalHint": {"type": "STRING", "description": "Lowercase generic Vietnamese UTF-8 food name; never use English, brands, sizes, packaging, or preparation details."},
        "category": {"type": "STRING", "enum": sorted(CATEGORIES)},
        "state": {"type": "STRING", "enum": sorted(STATES)},
        "quantity": {"type": "NUMBER", "nullable": True},
        "unit": {"type": "STRING", "enum": sorted(UNITS), "nullable": True},
        "quantitySource": {"type": "STRING", "enum": sorted(QUANTITY_SOURCES)},
        "confidence": {"type": "NUMBER"},
    }, "required": ["rawName", "canonicalHint", "category", "quantitySource", "confidence"]}},
}, "required": ["ingredients"]}
_cache: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
_failures: dict[str, tuple[int, float]] = {}
_semaphore: asyncio.Semaphore | None = None
_limit = 0


class Unavailable(Exception):
    pass


class InvalidOutput(Exception):
    pass


def prompt_for(expected_type: str) -> str:
    try:
        name = "receipt.txt" if expected_type == "RECEIPT" else "food_image.txt"
        return (PROMPT_DIR / name).read_text(encoding="utf-8")
    except OSError as exception:
        raise RuntimeError("Image-analysis prompt is unavailable") from exception


def _csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


def config() -> tuple[tuple[str, ...], str | None, int, int, int, int, str, str]:
    return (_csv("GEMINI_MODELS", "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite"),
            os.getenv("GEMINI_HARD_MODEL", "").strip() or None,
            int(os.getenv("GEMINI_TIMEOUT_MS", "25000")), int(os.getenv("GEMINI_MAX_CONCURRENCY", "5")),
            int(os.getenv("GEMINI_QUEUE_TIMEOUT_MS", "3000")), int(os.getenv("GEMINI_CACHE_TTL_SECONDS", "600")),
            os.getenv("GEMINI_THINKING_LEVEL", "low").strip().lower(),
            os.getenv("GEMINI_MEDIA_RESOLUTION", "MEDIA_RESOLUTION_HIGH").strip().upper())


@router.post("/analyze-receipt", response_model=ApiResponse[dict], deprecated=True)
async def receipt(image: UploadFile = File(...)) -> ApiResponse[dict]:
    return ApiResponse(success=True, message="ok", data={"items": (await analyze(image, "RECEIPT"))["ingredients"]}, errors=None)


@router.post("/recognize-food-image", response_model=ApiResponse[dict], deprecated=True)
async def food(image: UploadFile = File(...)) -> ApiResponse[dict]:
    return ApiResponse(success=True, message="ok", data={"items": (await analyze(image, "FOOD_IMAGE"))["ingredients"]}, errors=None)


@router.post("/analyze-image", response_model=ApiResponse[dict])
async def unified(image: UploadFile = File(...), expected_type: str | None = Form(None, alias="expectedType")) -> ApiResponse[dict]:
    # AUTO remains tolerated for old clients; actual image handling defaults to food photos.
    mode = expected_type.strip().upper() if expected_type else "FOOD_IMAGE"
    if mode not in SUPPORTED_TYPES:
        log.warning("gemini_call event=unsupported_expected_type expectedType=%s fallback=FOOD_IMAGE", mode)
        mode = "FOOD_IMAGE"
    return ApiResponse(success=True, message="ok", data=await analyze(image, mode), errors=None)


async def analyze(image: UploadFile, expected: str) -> dict[str, Any]:
    if expected not in SUPPORTED_TYPES:
        raise HTTPException(400, "expectedType must be FOOD_IMAGE or RECEIPT.")
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Only JPEG, PNG, and WEBP images are supported.")
    content = await image.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, "Image must not exceed 10 MB.")
    content, mime = resize_for_gemini(content, image.content_type)
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise _error("AI_UNAVAILABLE", "Image analysis provider is not configured.")
    models, hard_model, timeout, concurrency, queue, ttl, thinking, resolution = config()
    cache_key = hashlib.sha256(content).hexdigest() + ":" + expected
    now = time.monotonic(); cached = _cache.get(cache_key)
    if cached and cached[0] > now:
        log.info("gemini_call event=cache_hit imageBytes=%d expectedType=%s itemCount=%d", len(content), expected, len(cached[1]["ingredients"]))
        return cached[1]
    global _semaphore, _limit
    if _semaphore is None or _limit != concurrency:
        _semaphore, _limit = asyncio.Semaphore(concurrency), concurrency
    try:
        await asyncio.wait_for(_semaphore.acquire(), queue / 1000)
    except TimeoutError:
        raise _error("AI_UNAVAILABLE", "Image analysis provider is busy.")
    try:
        result, used_model = await _call_models(models, content, mime, expected, key, timeout, thinking, resolution)
        if hard_model and hard_model not in models and _needs_hard_model(result):
            try:
                harder = await call_with_retry(hard_model, content, image.content_type, expected, key, timeout, thinking, resolution)
                if _score(harder) > _score(result): result, used_model = harder, hard_model
            except (Unavailable, InvalidOutput):
                log.warning("gemini_call event=hard_model_failed model=%s expectedType=%s", hard_model, expected)
        _cache[cache_key] = (now + ttl, result)
        while len(_cache) > 100: _cache.popitem(last=False)
        log.info("gemini_call event=success modelUsed=%s expectedType=%s itemCount=%d", used_model, expected, len(result["ingredients"]))
        return result
    except InvalidOutput:
        raise _error("AI_INVALID_OUTPUT", "AI returned invalid analysis output.")
    except Unavailable:
        raise _error("AI_UNAVAILABLE", "Image analysis provider is temporarily unavailable.")
    finally:
        _semaphore.release()


def resize_for_gemini(content: bytes, mime: str) -> tuple[bytes, str]:
    """Bounds provider input while preserving orientation; invalid image bytes remain validation errors."""
    try:
        with Image.open(BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source)
            if max(image.size) <= MAX_IMAGE_EDGE:
                return content, mime
            image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
            output = BytesIO()
            if image.mode in {"RGBA", "LA"}:
                image.save(output, format="PNG", optimize=True)
                return output.getvalue(), "image/png"
            image.convert("RGB").save(output, format="JPEG", quality=88, optimize=True)
            return output.getvalue(), "image/jpeg"
    except (UnidentifiedImageError, OSError) as exception:
        raise HTTPException(400, "Image content is invalid.") from exception


async def _call_models(models: tuple[str, ...], content: bytes, mime: str, expected: str, key: str, timeout: int, thinking: str, resolution: str) -> tuple[dict[str, Any], str]:
    for model in models:
        count, open_until = _failures.get(model, (0, 0))
        if open_until > time.monotonic():
            log.warning("gemini_call event=circuit_open model=%s", model); continue
        try:
            result = await call_with_retry(model, content, mime, expected, key, timeout, thinking, resolution)
            _failures.pop(model, None)
            return result, model
        except InvalidOutput:
            raise
        except Unavailable:
            _failures[model] = (count + 1, time.monotonic() + 30 if count + 1 >= 5 else 0)
    raise Unavailable()


async def call_with_retry(model: str, content: bytes, mime: str, expected: str, key: str, timeout: int, thinking: str, resolution: str) -> dict[str, Any]:
    for attempt in range(1, 4):
        start = time.monotonic(); status = None; detail = ""; retry_after = 0.0
        try:
            return await call(model, content, mime, expected, key, timeout, thinking, resolution)
        except InvalidOutput:
            detail = "invalid_output"; retryable = attempt < 2
        except httpx.HTTPStatusError as exception:
            status = exception.response.status_code; detail = exception.response.text[:300].replace("\n", " ")
            retry_after = _retry_after(exception.response.headers.get("retry-after")); retryable = status in {429, 500, 503, 504}
        except (httpx.TimeoutException, httpx.NetworkError) as exception:
            detail = type(exception).__name__; retryable = True
        finally:
            log.info("gemini_call model=%s attempt=%d httpStatus=%s error=%s latencyMs=%d imageBytes=%d expectedType=%s", model, attempt, status, detail, int((time.monotonic() - start) * 1000), len(content), expected)
        if not retryable or attempt == 3: break
        await asyncio.sleep(min(5, retry_after or .5 * (2 ** (attempt - 1)) + random.uniform(0, .25)))
    if detail == "invalid_output": raise InvalidOutput()
    raise Unavailable()


async def call(model: str, content: bytes, mime: str, expected: str, key: str, timeout: int, thinking: str, resolution: str) -> dict[str, Any]:
    optional = {"thinkingConfig": {"thinkingLevel": thinking}, "mediaResolution": resolution}
    strict_schema = True
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout / 1000, connect=5)) as client:
        response = await client.post(url, json=_payload(content, mime, expected, optional))
        if response.status_code == 400:
            log.warning("gemini_call event=optional_config_rejected model=%s", model)
            response = await client.post(url, json=_payload(content, mime, expected, {}))
        if response.status_code == 400:
            # Some Gemini model revisions reject a strict responseSchema although JSON mode is supported.
            # Keep extraction available and enforce the same schema in normalize() after the response.
            log.warning("gemini_call event=response_schema_rejected model=%s fallback=json_mode", model)
            response = await client.post(url, json=_payload(content, mime, expected, {}, strict_schema=False))
            strict_schema = False
    response.raise_for_status()
    try:
        return normalize(json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"]), expected, lenient=not strict_schema)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exception:
        raise InvalidOutput() from exception


def _payload(content: bytes, mime: str, expected: str, optional: dict[str, Any], strict_schema: bool = True) -> dict[str, Any]:
    generation = {"responseMimeType": "application/json", "maxOutputTokens": 4096, **optional}
    if strict_schema:
        generation["responseSchema"] = SCHEMA
    prompt = prompt_for(expected)
    if not strict_schema:
        # This is only used if the provider rejects responseSchema. It preserves the contract without
        # repeating the full enum table in the normal prompt.
        prompt += "\nReturn only a JSON object: {\"reason\": null or a reason code, \"ingredients\": [{\"rawName\": string, \"canonicalHint\": string, \"quantity\": number or null, \"unit\": string or null}]}. Never return prose or markdown."
    return {"systemInstruction": {"parts": [{"text": prompt}]}, "contents": [{"parts": [{"inline_data": {"mime_type": mime, "data": base64.b64encode(content).decode()}}]}], "generationConfig": generation}


def normalize(value: object, expected: str, lenient: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("ingredients"), list): raise ValueError()
    reason = value.get("reason")
    if reason is not None and reason not in REASONS: raise ValueError()
    merged: dict[tuple[str, str | None], dict[str, Any]] = {}
    for row in value["ingredients"]:
        item = _normalize_item(row, expected, lenient)
        if item is None: continue
        key = (item["canonicalHint"], item["unit"])
        if key not in merged or item["confidence"] > merged[key]["confidence"]: merged[key] = item
    rows = list(merged.values())[:40]
    if not rows and reason is None: raise ValueError()
    return {"imageType": expected, "ingredients": rows, "warnings": [], "reason": reason}


def _normalize_item(row: object, expected: str, lenient: bool) -> dict[str, Any] | None:
    if not isinstance(row, dict) or not isinstance(row.get("rawName"), str) or not row["rawName"].strip(): raise ValueError()
    raw_name = row["rawName"].strip()
    if expected == "RECEIPT" and GARBAGE_RECEIPT.search(raw_name): return None
    hint = _canonical_hint(row.get("canonicalHint") or raw_name)
    category, source = row.get("category"), row.get("quantitySource")
    if lenient and category not in CATEGORIES: category = "OTHER_FOOD"
    if lenient and source not in QUANTITY_SOURCES: source = "COUNTED" if isinstance(row.get("quantity"), (int, float)) else "NONE"
    if category not in CATEGORIES or source not in QUANTITY_SOURCES: raise ValueError()
    state = row.get("state", "UNKNOWN")
    if lenient and state not in STATES: state = "UNKNOWN"
    if state not in STATES: raise ValueError()
    unit = row.get("unit")
    if lenient and unit not in UNITS: unit = None
    if unit is not None and unit not in UNITS: raise ValueError()
    quantity = row.get("quantity")
    if not isinstance(quantity, (int, float)) or isinstance(quantity, bool) or quantity <= 0: quantity = None
    if source == "NONE": quantity = None
    confidence = row.get("confidence")
    if lenient and (not isinstance(confidence, (int, float)) or isinstance(confidence, bool)): confidence = .5
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool): raise ValueError()
    flags = (["LOW_CONFIDENCE"] if float(confidence) < .6 else [])
    if (expected == "FOOD_IMAGE" and source == "PRINTED") or (expected == "RECEIPT" and source == "COUNTED"): flags.append("ANOMALY")
    if source == "NONE": flags.append("NO_QUANTITY")
    return {"rawName": raw_name, "canonicalHint": hint, "category": category, "state": state, "quantity": quantity, "unit": unit, "quantitySource": source, "confidence": float(confidence), "flags": flags, "food": True}


def _canonical_hint(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\sđĐ]", " ", value.strip().lower())).strip()


def _needs_hard_model(result: dict[str, Any]) -> bool:
    rows = result["ingredients"]
    return bool(rows) and (len(rows) <= 2 or sum(row["confidence"] for row in rows) / len(rows) < .5)


def _score(result: dict[str, Any]) -> tuple[int, float]:
    rows = result["ingredients"]
    return len(rows), sum(row["confidence"] for row in rows) / len(rows) if rows else 0.0


def _error(code: str, message: str) -> HTTPException:
    return HTTPException(503, detail={"code": code, "message": message, "retryable": True})


def _retry_after(value: str | None) -> float:
    try: return min(10, max(0, float(value or 0)))
    except ValueError: return 0
