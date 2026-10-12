import unittest

from app.api.routes.pantry_import import ProviderOutputError, _validate_and_normalize


def food_payload():
    return {
        "imageType": "FOOD_IMAGE", "imageTypeConfidence": 0.9, "imageQuality": "GOOD",
        "reason": None, "warnings": [], "ingredients": [{
            "rawName": "Trứng gà", "canonicalHint": "trứng gà", "category": "DAIRY_EGG",
            "quantity": 6, "unit": "piece", "quantitySource": "COUNTED",
            "state": "FRESH", "confidence": 0.95,
        }],
    }


class PantryImportSchemaTest(unittest.TestCase):
    def test_accepts_closed_enum_food_payload(self):
        result = _validate_and_normalize(food_payload())
        self.assertEqual("FOOD_IMAGE", result["imageType"])
        self.assertEqual("Trứng gà", result["ingredients"][0]["rawName"])

    def test_unknown_requires_reason_and_has_no_ingredients(self):
        result = _validate_and_normalize({
            "imageType": "UNKNOWN", "imageTypeConfidence": 0.2, "imageQuality": "LOW",
            "reason": "BLURRY", "warnings": ["BLURRY"], "ingredients": [{"ignored": True}],
        })
        self.assertEqual([], result["ingredients"])

    def test_rejects_guessed_quantity_when_source_is_none(self):
        payload = food_payload()
        payload["ingredients"][0]["quantitySource"] = "NONE"
        with self.assertRaises(ProviderOutputError):
            _validate_and_normalize(payload)

    def test_rejects_unrecognised_enum(self):
        payload = food_payload()
        payload["ingredients"][0]["category"] = "PROTEIN"
        with self.assertRaises(ProviderOutputError):
            _validate_and_normalize(payload)

