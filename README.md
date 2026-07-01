# ZPantry AI Service

AI Service la service Python/FastAPI doc lap cua ZPantry. Frontend khong goi truc tiep service nay. Backend la service duy nhat goi AI Service thong qua `IAIRecommendationClient`.

Muc tieu hien tai cua AI Service la cung cap mock deterministic de test flow tich hop. Chua goi model AI that, chua can API key OpenAI/Gemini.

## Base URL

Khi chay Docker compose root:

```text
http://localhost:8000
```

Trong Docker network, backend goi qua:

```text
http://ai-service:8000
```

## Response Format

Tat ca API tra ve wrapper thong nhat:

```json
{
  "success": true,
  "message": "ok",
  "data": {},
  "errors": null,
  "traceId": "",
  "timestamp": "2026-06-30T00:00:00Z"
}
```

## API Purpose

### GET `/ai/health`

Dung de healthcheck AI Service.

Backend/Docker compose dung endpoint nay de biet AI Service da san sang nhan request hay chua.

Response `data`:

```json
{
  "status": "healthy"
}
```

### POST `/ai/recommend-meals`

Dung de goi y mon an dua tren nguyen lieu user dang co va danh sach recipe ung vien do backend gui sang.

Luot xu ly hien tai:

- Backend lay pantry/user input.
- Backend lay candidate recipes trong database.
- Backend goi API nay.
- AI Service tinh diem mock bang overlap giua nguyen lieu user va nguyen lieu recipe.
- AI Service tra ve danh sach recipe da rank.
- Backend luu `MealRecommendation` va `MealRecommendationItem`.

Request chinh:

```json
{
  "userId": "guid",
  "inputIngredientText": "egg, tomato",
  "ingredients": [
    {
      "ingredientId": "guid",
      "name": "egg",
      "quantity": 2,
      "unit": "piece"
    }
  ],
  "candidateRecipes": [
    {
      "recipeId": "guid",
      "recipeName": "Omelette",
      "ingredientNames": ["egg", "tomato", "salt"],
      "instructionText": "Cook eggs with tomato."
    }
  ],
  "topK": 5
}
```

Response `data`:

```json
{
  "items": [
    {
      "recipeId": "guid",
      "recipeName": "Omelette",
      "matchScore": 0.667,
      "missingIngredientCount": 1,
      "missingIngredientNames": ["salt"],
      "reason": "Matched 2 of 3 required ingredients using mock overlap scoring.",
      "rank": 1
    }
  ]
}
```

### POST `/ai/suggest-missing-ingredients`

Dung de tinh danh sach nguyen lieu user con thieu cho mot recipe cu the.

Luot xu ly hien tai:

- Backend xac dinh recipe can check.
- Backend gui `requiredIngredients` cua recipe va `userIngredients` user dang co.
- AI Service normalize/tokenize text.
- AI Service tra ve cac nguyen lieu nam trong recipe nhung user chua co.

Request chinh:

```json
{
  "recipeId": "guid",
  "recipeName": "Omelette",
  "requiredIngredients": ["egg", "tomato", "salt"],
  "userIngredients": ["egg", "tomato"]
}
```

Response `data`:

```json
{
  "recipeId": "guid",
  "missingIngredients": ["salt"]
}
```

### POST `/ai/embed-ingredient`

Dung de sinh embedding vector cho Ingredient.

Backend goi API nay khi tao/cap nhat ingredient. Hien tai embedding la mock deterministic 1536 chieu sinh tu `ingredientId` va `normalizedName`. Sau nay co the thay bang provider that.

Request chinh:

```json
{
  "ingredientId": "guid",
  "name": "Egg",
  "normalizedName": "egg",
  "category": "protein"
}
```

Response `data`:

```json
{
  "ingredientId": "guid",
  "recipeId": null,
  "embedding": [0.1, 0.2],
  "dimension": 1536
}
```

### POST `/ai/embed-recipe`

Dung de sinh embedding vector cho Recipe.

Backend goi API nay khi tao/cap nhat recipe. Hien tai embedding la mock deterministic 1536 chieu sinh tu recipe id, ten mon, mo ta, nguyen lieu va instruction text.

Request chinh:

```json
{
  "recipeId": "guid",
  "name": "Omelette",
  "description": "Simple breakfast recipe",
  "ingredientNames": ["egg", "tomato", "salt"],
  "instructionText": "Cook eggs with tomato."
}
```

Response `data`:

```json
{
  "ingredientId": null,
  "recipeId": "guid",
  "embedding": [0.1, 0.2],
  "dimension": 1536
}
```

## Mock Logic Notes

Recommendation mock:

- Normalize text ve lowercase.
- Tach nguyen lieu theo dau phay, cham phay, gach cheo, pipe va newline.
- Tinh `matchScore = matchedIngredientCount / requiredIngredientCount`.
- Sap xep theo score cao hon truoc, so nguyen lieu thieu it hon truoc.

Embedding mock:

- Dung SHA-256 tren seed text.
- Lap digest thanh vector 1536 chieu.
- Ket qua deterministic, phu hop de test integration.

## TODO

- Thay mock embedding bang provider that.
- Them tu dien dong nghia nguyen lieu tieng Viet.
- Cai tien recipe ranking.
- Them logging middleware latency/error.
- Them test tu dong cho schema va endpoints.
