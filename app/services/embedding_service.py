from hashlib import sha256


def build_embedding(seed_text: str, dimension: int = 1536) -> list[float]:
    digest = sha256(seed_text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dimension:
        for byte in digest:
            values.append(round(byte / 255.0, 6))
            if len(values) == dimension:
                break
    return values

