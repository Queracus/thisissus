"""Import a recipe from a web page: schema.org Recipe JSON-LD (what most recipe sites publish) → editable draft.

Fetching is guarded: only http(s) and only public internet addresses, so the server can't be used to reach the home network.
"""
import asyncio
import html
import ipaddress
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 10
MAX_REDIRECTS = 3
FRACTIONS = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3", "⅛": "1/8"}
UNITS = {"g", "kg", "mg", "l", "dl", "ml", "cl", "cup", "cups", "tbsp", "tsp", "oz", "lb", "lbs", "pinch", "clove", "cloves",
         "žlica", "žlice", "žlici", "žlic", "žlička", "žličke", "žlički", "žličk", "skodelica", "skodelice", "skodelici",
         "ščep", "strok", "stroka", "stroki", "kos", "kosa", "kosi", "pest", "vrečka", "vrečke", "paket"}
NUMBER = re.compile(r"^\s*(?P<num>\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?)\s*(?P<rest>.*)$")  # longest forms first
DURATION = re.compile(r"^P(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?)?$")


class ImportBlocked(Exception):
    """The URL points somewhere we must not fetch (not http(s), or a private/loopback address)."""


# ---------- parsing (pure) ----------

class _JsonLd(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks, self._inside = [], False

    def handle_starttag(self, tag, attrs):
        self._inside = tag == "script" and dict(attrs).get("type", "").lower() == "application/ld+json"
        if self._inside:
            self.blocks.append("")

    def handle_endtag(self, tag):
        self._inside = False

    def handle_data(self, data):
        if self._inside:
            self.blocks[-1] += data


def _nodes(data):
    """Every JSON object in a JSON-LD document (lists and @graph flattened)."""
    if isinstance(data, list):
        for x in data:
            yield from _nodes(x)
    elif isinstance(data, dict):
        yield data
        yield from _nodes(data.get("@graph", []))


def _is_recipe(node: dict) -> bool:
    t = node.get("@type")
    return "Recipe" in (t if isinstance(t, list) else [t])


def _text(value) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(value)))).strip()


def iso_minutes(value) -> int | None:
    m = DURATION.match(str(value or "").strip())
    if not m or not any(m.groupdict().values()):
        return None
    d, h, mi, s = (int(m.group(k) or 0) for k in "dhms")
    return d * 1440 + h * 60 + mi + round(s / 60)


def _amount(text: str) -> float:
    total = 0.0
    for part in text.replace(",", ".").split():
        num, _, den = part.partition("/")
        total += float(num) / float(den) if den else float(num)
    return round(total, 3)


def parse_ingredient(text: str) -> dict:
    t = _text(text)
    for sym, frac in FRACTIONS.items():
        t = re.sub(rf"(\d)\s*{sym}", rf"\1 {frac}", t).replace(sym, frac)
    m = NUMBER.match(t)
    if not m:
        return {"amount": None, "unit": None, "item": t}
    rest = m.group("rest").split(" ", 1)
    unit = rest[0].rstrip(".").lower() if rest[0].rstrip(".").lower() in UNITS else None
    item = (rest[1] if len(rest) > 1 else "") if unit else m.group("rest")
    return {"amount": _amount(m.group("num")), "unit": unit, "item": item.strip() or t}


def _steps(value) -> list[str]:
    if isinstance(value, str):
        return [s for s in (_text(x) for x in re.split(r"\n+", value)) if s]
    if isinstance(value, list):
        return [s for v in value for s in _steps(v)]
    if isinstance(value, dict):
        if "itemListElement" in value:
            return _steps(value["itemListElement"])
        return _steps(value.get("text") or value.get("name") or "")
    return []


def _first_int(value) -> int | None:
    for v in value if isinstance(value, list) else [value]:
        if m := re.search(r"\d+", str(v)):
            return max(1, int(m.group()))
    return None


def _image(value, base_url: str) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get("url")
    return urljoin(base_url, value) if isinstance(value, str) and value else None


def parse_recipe_html(page: str, base_url: str) -> dict | None:
    parser = _JsonLd()
    parser.feed(page)
    for block in parser.blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        recipe = next((n for n in _nodes(data) if _is_recipe(n)), None)
        if not recipe or not recipe.get("name"):
            continue
        total = iso_minutes(recipe.get("totalTime"))
        parts = [iso_minutes(recipe.get(k)) for k in ("prepTime", "cookTime")]
        return {
            "title": _text(recipe["name"])[:120],
            "portions": _first_int(recipe.get("recipeYield")) or 2,
            "prep_minutes": total if total is not None else (sum(p for p in parts if p) or None),
            "ingredients": [parse_ingredient(i) for i in recipe.get("recipeIngredient") or [] if _text(i)],
            "steps": _steps(recipe.get("recipeInstructions")),
            "source_url": base_url,
            "image_url": _image(recipe.get("image"), base_url),
        }
    return None


# ---------- fetching (guarded) ----------

async def _check_public(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ImportBlocked(url)
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, parsed.port or 443)
    except OSError:
        raise ImportBlocked(url)
    if not infos or any(not ipaddress.ip_address(info[4][0].split("%")[0]).is_global for info in infos):
        raise ImportBlocked(url)


async def fetch_bytes(url: str, max_bytes: int = MAX_BYTES) -> bytes:
    """GET a public URL (every redirect re-checked), at most max_bytes."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": "Thisissus recipe import"}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await _check_public(url)
            async with client.stream("GET", url) as res:
                if res.is_redirect:
                    url = urljoin(url, res.headers["location"])
                    continue
                res.raise_for_status()
                body = b""
                async for chunk in res.aiter_bytes():
                    body += chunk
                    if len(body) > max_bytes:
                        raise httpx.HTTPError("too large")
                return body
    raise httpx.HTTPError("too many redirects")


async def fetch_html(url: str) -> str:
    return (await fetch_bytes(url)).decode("utf-8", errors="replace")
