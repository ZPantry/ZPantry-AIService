import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.api.routes.pantry_import import _needs_hard_model, _payload, call_with_retry, config, normalize, prompt_for


def food_payload():
    return {"reason": None, "ingredients": [{
        "rawName": "Cá thu kho", "canonicalHint": "Cá thu", "category": "SEAFOOD",
        "state": "COOKED", "quantity": 2, "unit": "piece", "quantitySource": "COUNTED", "confidence": .95,
    }]}


class PantryImportSchemaTest(unittest.TestCase):
    def test_selects_a_separate_prompt_for_each_mode(self):
        self.assertIn("fish", prompt_for("FOOD_IMAGE"))
        self.assertIn("Vietnamese UTF-8", prompt_for("FOOD_IMAGE"))
        self.assertIn("Never return English names", prompt_for("FOOD_IMAGE"))
        self.assertIn("receipt", prompt_for("RECEIPT").lower())

    def test_food_schema_requires_vietnamese_name_descriptions(self):
        payload = _payload(b"image", "image/png", "FOOD_IMAGE", {})
        fields = payload["generationConfig"]["responseSchema"]["properties"]["ingredients"]["items"]["properties"]
        self.assertIn("Vietnamese", fields["rawName"]["description"])
        self.assertIn("Vietnamese", fields["canonicalHint"]["description"])

    def test_gemini_three_thinking_level_uses_the_rest_api_spelling(self):
        self.assertEqual("low", config()[-2])

    def test_server_assigns_image_type_and_preserves_food_metadata(self):
        result = normalize(food_payload(), "FOOD_IMAGE")
        self.assertEqual("FOOD_IMAGE", result["imageType"])
        self.assertEqual("cá thu", result["ingredients"][0]["canonicalHint"])
        self.assertEqual("COOKED", result["ingredients"][0]["state"])

    def test_quantity_is_removed_when_model_did_not_see_or_read_it(self):
        payload = food_payload(); payload["ingredients"][0].update(quantity=4, quantitySource="NONE")
        result = normalize(payload, "FOOD_IMAGE")
        self.assertIsNone(result["ingredients"][0]["quantity"])
        self.assertIn("NO_QUANTITY", result["ingredients"][0]["flags"])

    def test_duplicate_items_are_merged_and_receipt_noise_is_removed(self):
        payload = food_payload(); payload["ingredients"].append({**payload["ingredients"][0], "confidence": .5})
        payload["ingredients"].append({"rawName": "TỔNG CỘNG", "canonicalHint": "tổng cộng", "category": "OTHER_FOOD", "state": "UNKNOWN", "quantity": None, "unit": None, "quantitySource": "NONE", "confidence": .9})
        self.assertEqual(1, len(normalize(payload, "RECEIPT")["ingredients"]))

    def test_low_confidence_and_wrong_quantity_source_are_flagged_not_dropped(self):
        payload = food_payload(); payload["ingredients"][0].update(confidence=.4, quantitySource="PRINTED")
        result = normalize(payload, "FOOD_IMAGE")
        self.assertEqual({"LOW_CONFIDENCE", "ANOMALY"}, set(result["ingredients"][0]["flags"]))

    def test_empty_result_requires_a_reason(self):
        with self.assertRaises(ValueError): normalize({"ingredients": []}, "FOOD_IMAGE")
        self.assertEqual([], normalize({"reason": "BLURRY", "ingredients": []}, "FOOD_IMAGE")["ingredients"])

    def test_json_mode_fallback_normalizes_missing_optional_provider_fields(self):
        result = normalize({"ingredients": [{"rawName": "cá", "canonicalHint": "cá"}]}, "FOOD_IMAGE", lenient=True)
        self.assertEqual("OTHER_FOOD", result["ingredients"][0]["category"])
        self.assertIn("LOW_CONFIDENCE", result["ingredients"][0]["flags"])

    def test_json_mode_fallback_includes_a_machine_readable_output_contract(self):
        prompt = _payload(b"image", "image/png", "FOOD_IMAGE", {}, strict_schema=False)["systemInstruction"]["parts"][0]["text"]
        self.assertIn("Return only a JSON object", prompt)

    def test_hard_model_is_used_for_a_small_result(self):
        self.assertTrue(_needs_hard_model(normalize(food_payload(), "FOOD_IMAGE")))

    def test_transient_503_retries_and_keeps_a_valid_result(self):
        response = httpx.Response(503, request=httpx.Request("POST", "https://example.test"))
        with patch("app.api.routes.pantry_import.call", new=AsyncMock(side_effect=[httpx.HTTPStatusError("busy", request=response.request, response=response), normalize(food_payload(), "FOOD_IMAGE")])):
            result = asyncio.run(call_with_retry("model", b"image", "image/png", "FOOD_IMAGE", "key", 1000, "LOW", "MEDIA_RESOLUTION_HIGH"))
        self.assertEqual("FOOD_IMAGE", result["imageType"])
