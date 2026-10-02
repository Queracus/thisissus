"""Pure kitchen helpers."""


def _round(x: float) -> float | int:
    """Readable amounts: ≥10 → whole numbers, ≥1 → one decimal, below 1 → two decimals."""
    if x >= 10:
        return round(x)
    return round(x, 1) if x >= 1 else round(x, 2)


def scale(ingredients: list[dict], from_portions: float, to_portions: float) -> list[dict]:
    """Ingredients for to_portions; amounts without a number ("salt to taste") stay as they are."""
    factor = to_portions / from_portions
    return [{**i, "amount": None if i["amount"] is None else _round(i["amount"] * factor)} for i in ingredients]
