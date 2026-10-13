"""Prepare a repeatable labelled-image evaluation inventory without touching user uploads."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "results" / "inventory.csv"


def main() -> None:
    cases = sorted((ROOT / "cases").glob("*/expected.json"))
    if not cases:
        raise SystemExit("No labelled cases found. See eval/README.md before evaluating prompts.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for expected_path in cases:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        image = next((path for path in expected_path.parent.iterdir()
                      if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}), None)
        rows.append({"case": expected_path.parent.name, "mode": expected.get("mode", ""),
                     "expectedCount": len(expected.get("ingredients", [])), "hasImage": bool(image)})
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case", "mode", "expectedCount", "hasImage"])
        writer.writeheader(); writer.writerows(rows)
    print(f"Prepared {len(rows)} labelled cases in {OUT}")


if __name__ == "__main__":
    main()
