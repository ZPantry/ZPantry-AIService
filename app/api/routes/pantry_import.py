import base64, json, os
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.schemas.common_schema import ApiResponse

router = APIRouter()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_BYTES = 10 * 1024 * 1024
PROMPTS = {"receipt": "Extract food/ingredient lines. Return JSON only with an items array. Each item must have rawName, quantity, unit, price, confidence, and food. Mark non-food items food:false. Never invent a quantity.", "food": "Recognize visible food ingredients. Return JSON only with an items array. Each item must have rawName, quantity, unit, confidence, and food. Use null if quantity is uncertain; never guess 1."}

@router.post("/analyze-receipt", response_model=ApiResponse[dict])
async def analyze_receipt(image: UploadFile = File(...)) -> ApiResponse[dict]: return ApiResponse(success=True, message="ok", data=await _analyze(image, "receipt"), errors=None)
@router.post("/recognize-food-image", response_model=ApiResponse[dict])
async def recognize_food_image(image: UploadFile = File(...)) -> ApiResponse[dict]: return ApiResponse(success=True, message="ok", data=await _analyze(image, "food"), errors=None)

async def _analyze(image: UploadFile, mode: str) -> dict:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}: raise HTTPException(400, "Only JPEG, PNG, and WEBP images are supported.")
    content = await image.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES: raise HTTPException(413, "Image must not exceed 10 MB.")
    key = os.getenv("GEMINI_API_KEY")
    if not key: raise HTTPException(503, "Image analysis provider is not configured.")
    payload = {"contents":[{"parts":[{"text":PROMPTS[mode]},{"inline_data":{"mime_type":image.content_type,"data":base64.b64encode(content).decode()}}]}],"generationConfig":{"responseMimeType":"application/json","temperature":0}}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client: response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}", json=payload)
        response.raise_for_status(); parsed = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        return _normalize_provider_payload(parsed)
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError): raise HTTPException(503, "Image analysis provider is unavailable.")

def _normalize_provider_payload(parsed: object) -> dict:
    """Accept harmless provider shape variations and emit the one backend contract."""
    if isinstance(parsed, list):
        source_items = parsed
    elif isinstance(parsed, dict):
        source_items = parsed.get("items", parsed.get("ingredients"))
    else:
        source_items = None
    if not isinstance(source_items, list):
        raise ValueError("invalid provider response")
    items = []
    for item in source_items:
        if not isinstance(item, dict):
            continue
        raw_name = next((item.get(key) for key in ("rawName", "name", "item", "productName", "product")
                         if isinstance(item.get(key), str) and item.get(key).strip()), None)
        if raw_name is None:
            continue
        items.append({
            "rawName": raw_name.strip(),
            "quantity": item.get("quantity", item.get("qty", item.get("amount"))),
            "unit": item.get("unit"),
            "price": item.get("price", item.get("unitPrice")),
            "confidence": item.get("confidence"),
            "food": item.get("food", True),
        })
    return {"items": items}
