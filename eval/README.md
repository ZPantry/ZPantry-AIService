# Pantry image-analysis evaluation

The production service does not include user images. Add at least 40 consented, non-sensitive images under `eval/cases/<case-id>/` with an `image.jpg` (or PNG/WEBP) and `expected.json`.

`expected.json` uses `{ "mode": "FOOD_IMAGE" | "RECEIPT", "ingredients": ["cá thu", "thịt heo"] }`. Include meat, fish, seafood, prepared dishes, packaged food, receipt OCR, dark/blurred/no-food images, and prompt-injection text. Do not commit private receipts or personal data.

No before/after metric is available yet because this repository contains no labelled evaluation images. Capture the old prompt baseline before deploy, then compare it with this prompt; do not claim improvement without that comparison.
