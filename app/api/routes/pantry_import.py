import base64, json, os
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.schemas.common_schema import ApiResponse

router = APIRouter()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_BYTES = 10 * 1024 * 1024
PROMPTS = {"receipt": "Extract food/ingredient lines. Return JSON only: {items:[{rawName:string,quantity:number|null,unit:string|null,price:number|null,confidence:number|null,food:boolean}]}. Mark non-food food:false. Never invent quantity.", "food": "Recognize visible food ingredients. Return JSON only: {items:[{rawName:string,quantity:number|null,unit:string|null,confidence:number|null,food:boolean}]}. Use null if quantity is uncertain; never guess 1."}

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
        if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list): raise ValueError("invalid provider response")
        return parsed
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError): raise HTTPException(503, "Image analysis provider is unavailable.")
