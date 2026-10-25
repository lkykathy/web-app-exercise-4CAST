from hashlib import sha256
from itertools import product 
from db.src.clothing_db import search_clothing, get_warmth_range
from db.src.tagging import CATEGORY_TO_MAIN

HOME_OCCASIONS = ("casual", "smart-casual", "formal", "cocktail")
SHOES_FOR_OCCASION = {
    "casual": {"sneakers", "boots", "heels", "flats", "sandals", "loafers"},
    "smart-casual": {"sneakers", "boots", "heels", "flats", "loafers"},
    "formal": {"heels", "flats", "loafers"},
    "cocktail": {"heels", "flats", "loafers", "boots"}
}


def _occasion_labels(item):
    labels = item.get("occasion", item.get("occasion", [])) or []
    return {labels} if isinstance(labels, str) else set(labels)


def _weather_vals(weather):
    temp = weather.get("feels_like_fahrenheit")
    if temp is None:
        temp = weather.get("temperature_fahrenheit", weather.get("temp"))
    unit = weather.get("unit", "F").upper()
    target_low, target_high = get_warmth_range(temp, unit=unit)
    celsius = (temp - 32) * 5 / 9 if unit == "F" else temp
    return (target_low + target_high) / 2, celsius


def _outfit_record(parts, occasion, score):
    ids = [str(item["_id"]) for _, item in parts]
    signature = occasion + "|" + "|".join(ids)
    return {
        "id": sha256(signature.encode()).hexdigest()[:16],
        "occasion": occasion,
        "score": round(score, 2),
        "item_ids": ids,
        "parts":[{"role": role, "item": item} for role, item in parts],
        "reasoning": f"A {occasion.replace('-', ' ')} look selected for the current weather."
    }


def build_outfits(candidates, *, weather, occasion, limit=5, refresh=0):
    ideal_warmth, celsius = _weather_vals(weather)
    groups = {name: [] for name in ("tops", "bottoms", "one-piece", "shoes", "outerwear")}
    for item in candidates:
        if item.get("is_available") is False:
            continue
        main = item.get("main_category") or CATEGORY_TO_MAIN.get(item.get("category"))
        if main not in groups:
            continue
        labels = _occasion_labels(item)
        if main in {"tops", "bottoms", "one-piece"} and labels and occasion not in labels:
            continue
        if main in {"shoes", "outerwear"} and labels and occasion not in labels:
            continue
        if main == "shoes" and item.get("category") not in SHOES_FOR_OCCASION[occasion]:
            continue
        groups[main].append(item)

    print("\nFiltered clothing groups:")
    for category, items in groups.items():
        print(category, ":", [item.get("name") for item in items])

    if not groups["shoes"]:
        return []

    outerwear_items = groups["outerwear"][:3] if celsius < 20 else []
    outerwear_options = [None] + outerwear_items
    looks = []

    def append_look(parts):
        core = [item for role, item in parts if role in ("top", "bottom", "one_piece")]
        score = -sum(abs(item.get("warmth_level", 3) - ideal_warmth) for item in core)
        if celsius < 13 and any(role == "outerwear" for role, _ in parts):
            score += 2
        if celsius >= 13 and any(role == "outerwear" for role, _ in parts):
            score -= 1
        if any(item.get("is_favorite") for _, item in parts):
            score += 0.25
        looks.append(_outfit_record(parts, occasion, score))

    # top + bottom + shoes (+ outerwear)
    for top, bottom, shoes, outerwear_item in product(
        groups["tops"][:10],
        groups["bottoms"][:10],
        groups["shoes"][:6],
        outerwear_options
    ):
        parts = [("top", top), ("bottom", bottom), ("shoes", shoes)]
        if outerwear_item is not None:
            parts.append(("outerwear", outerwear_item))
        append_look(parts)
    # one-piece + shoes (+ outerwear)
    for one_piece, shoes, outerwear_item in product(
        groups["one-piece"][:10],
        groups["shoes"][:6],
        outerwear_options
    ):
        parts = [("one_piece", one_piece), ("shoes", shoes)]
        if outerwear_item is not None:
            parts.append(("outerwear", outerwear_item))
        append_look(parts)
    looks.sort(key=lambda look: (-look["score"], look["id"]))
    if not looks:
        return []
    position = refresh % len(looks)
    return (looks[position:] + looks[:position])[:limit]


def get_featured_outfits(weather, *, refresh_by_occasion=None):
    candidates = search_clothing(available=True, limit=None)
    refresh_by_occasion = refresh_by_occasion or {}
    return {
        occasion: (looks[0] if looks else None)
        for occasion in HOME_OCCASIONS
        for looks in [build_outfits(
            candidates,
            weather=weather,
            occasion=occasion,
            limit=1,
            refresh=refresh_by_occasion.get(occasion, 0)
        )]
    }


def get_outfits_for_weather(weather, *, occasion="casual", limit=5, refresh=0):
    candidates = search_clothing(available=True, limit=None)
    return build_outfits(
        candidates,
        weather=weather,
        occasion=occasion,
        limit=limit, 
        refresh=refresh
    )