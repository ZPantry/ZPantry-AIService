import re
import unicodedata


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def tokenize_ingredient_text(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        normalized = normalize_text(value)
        if not normalized:
            continue

        for token in re.split(r"[,;|/\n]+", normalized):
            cleaned = token.strip()
            if cleaned:
                tokens.add(cleaned)

    return tokens
