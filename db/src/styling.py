from hashlib import sha256
from itertools import combinations, product
from db.src.clothing_db import search_clothing, get_weather_suit, get_warmth_range
from db.src.tagging import CATEGORY_TO_MAIN, COLOR_WHEEL as COMMON_COLOR_WHEEL

COLOR_WHEEL = {
    **COMMON_COLOR_WHEEL,
    "red": 1, "red-orange": 2, "orange": 3, "yellow-orange": 4,
    "yellow": 5, "yellow-green": 6, "green": 7, "blue-green": 8,
    "blue": 9, "blue-violet": 10, "violet": 11, "red-violet": 12,
}
QUIZ_WEIGHT = 0.20
MOOD_RULES = {
    'confident': {'colors': {'red', 'burgundy', 'black', 'navy'}, 'categories': {'blazer', 'dress-shirt', 'button-up-shirt', 'trousers', 'slacks', 'heels', 'loafers'}},
    'soft': {'colors': {'pink', 'cream', 'peach', 'lavender', 'white'}, 'categories': {'blouse', 'cardigan', 'sweater', 'skirt', 'flats'}},
    'creative': {'colors': {'purple', 'magenta', 'orange', 'yellow', 'turquoise'}, 'categories': {'crop-top', 'bodysuit', 'skirt', 'jacket', 'boots'}},
    'grounded': {'colors': {'brown', 'beige', 'tan', 'olive', 'green'}, 'categories': {'t-shirt', 'sweater', 'jeans', 'trousers', 'boots', 'loafers'}},
}
PALETTE_RULES = {
    'warm & fiery': {'colors': {'red', 'red-orange', 'orange', 'yellow-orange', 'yellow', 'coral', 'burgundy', 'gold'}},
    'cool & striking': {'colors': {'blue', 'blue-green', 'blue-violet', 'violet', 'navy', 'teal', 'turquoise', 'purple', 'silver'}},
    'earthy & natural': {'colors': {'brown', 'beige', 'tan', 'olive', 'green', 'cream'}},
    'soft & dreamlike': {'colors': {'pink', 'peach', 'lavender', 'mint', 'cream', 'white'}, 'lightness': {'light'}},
    'dark & minimal': {'colors': {'black', 'gray', 'navy', 'brown'}, 'lightness': {'dark'}},
    'playful & eclectic': {'colors': {'red', 'red-violet', 'pink', 'orange', 'yellow', 'lime', 'turquoise', 'purple', 'magenta'}},
}
STYLE_RULES = {
    'minimalist': {'occasions': {'casual', 'smart-casual', 'business-casual'}, 'accessories': {'watch', 'belt', 'bag'}, 'layers': {'blazer', 'coat', 'vest'}},
    'romantic': {'occasions': {'cocktail', 'formal', 'special-occasion'}, 'accessories': {'jewelry', 'scarf', 'bag'}, 'layers': {'cardigan', 'trench-coat'}},
    'streetwear': {'occasions': {'casual', 'loungewear'}, 'accessories': {'cap', 'hat', 'sunglasses', 'bag'}, 'layers': {'jacket', 'vest'}},
    'classic': {'occasions': {'smart-casual', 'business-casual', 'business-formal', 'formal'}, 'accessories': {'watch', 'belt', 'tie', 'scarf'}, 'layers': {'blazer', 'trench-coat', 'coat'}},
}
ENERGY_RULES = {
    'bold & powerful': {'colors': {'red', 'black', 'burgundy', 'purple', 'magenta'}, 'materials': {'leather', 'velvet', 'denim'}},
    'effortless & relaxed': {'colors': {'beige', 'cream', 'tan', 'blue', 'gray'}, 'materials': {'cotton', 'linen', 'knit', 'denim'}},
    'elegant & refined': {'colors': {'black', 'white', 'cream', 'navy', 'burgundy'}, 'materials': {'silk', 'satin', 'cashmere', 'wool'}},
    'fun & expressive': {'colors': {'pink', 'yellow', 'orange', 'lime', 'turquoise', 'magenta'}, 'materials': {'chiffon', 'lace', 'velvet', 'satin'}},
}


def _position(item):
    return item.get("color_wheel_pos", COLOR_WHEEL.get("color"))


def color_distance(a, b):
    return min(abs(a - b), 12 - abs(a - b))


def score_color(parts):
    items = [item for _, item in parts]
    positions = [_position(item) for item in items]
    hues = set(p for p in positions if p is not None)
    neutral_count = sum(p is None and item.get("color") in 
                        {"black", "white", "gray", "beige", "cream", "brown", "tan", "silver"}
                        for p, item in zip(positions, items))
    rec = []
    if ((len(hues) == 1 and neutral_count == 0) or len({i.get("color") for i in items}) == 1) and len({(i.get("color_lightness"), i.get("color_temp")) for i in items}) > 1:
        rec.append((35, "monochromatic"))
    if len(hues) >= 2:
        distance = [color_distance(a,b) for a,b in combinations(hues, 2)]
        if max(distance) <= 2:
            rec.append((30, "analogous"))
        if len(hues) == 2 and distance == [6]:
            rec.append((30, "complementary"))
    by_role = dict(parts)
    top = by_role["top"]
    bottom = by_role["bottom"]

    def family(item):
        return _position(item) if _position(item) is not None else item.get("color")

    repeated = any(family(top) == family(by_role[role]) for role in ("shoes", "accessory"))
    if repeated and family(top) != family(bottom):
        if len(hues) <= 2 or all(color_distance(a,b) <= 2 for a,b in combinations(hues, 2)):
            rec.append((30, "sandwiched"))
    if neutral_count >= 2 and len(hues) == 1:
        rec.append((25, "neutral + accent"))
    if not hues and neutral_count == len(items):
        rec.append((20, "neutral palette"))
    if not rec:
        return (15, "mixed palette") if len(hues) <= 3 and neutral_count >= 2 else (5, "no recognized harmony")
    score, label = max(rec)
    return min(35, score + (2 if len(rec) > 1 else 0)), label


def _weather_args(weather):
    temp = weather.get("temperature_fahrenheit")
    feels = weather.get("feels_like_fahrenheit")
    unit = "F"
    if temp is None:
        temp = weather.get("temp")
        feels = weather.get("feels_like", temp)
        unit = weather.get("unit", "F").upper()
    return dict(temp=temp, unit=unit, feels_like=feels,
                humidity=weather.get("humidity"),
                is_raining=weather.get("is_raining", False),
                is_snowing=weather.get("is_snowing", False),
                wind_mph=weather.get("wind_mph", 0),
                gust_mph=weather.get("gust_mph"))


def _quiz_rules(answers):
    if answers is None:
        return None
    tables = {'mood': MOOD_RULES, 'palette': PALETTE_RULES,
              'style': STYLE_RULES, 'energy': ENERGY_RULES}
    rules = {}
    for key, table in tables.items():
        value = ' '.join(str(answers.get(key, '')).strip().lower().split())
        rules[key] = table[value]
    return rules


def score_quiz(parts, rules):
    items = [item for _, item in parts]
    def fraction(values):
        return sum(values) / len(values) if values else 0
    def color_match(rule):
        checks = [fraction([item.get('color') in rule['colors'] for item in items])]
        if 'lightness' in rule:
            checks.append(fraction([item.get('color_lightness') in rule['lightness'] for item in items]))
        return sum(checks) / len(checks)
    mood = (color_match(rules['mood']) + fraction([
        item.get('category') in rules['mood']['categories'] for item in items
    ])) / 2
    palette = color_match(rules['palette'])
    accessories = [item for role, item in parts if role == 'accessory']
    layers = [item for role, item in parts if role == 'outerwear']
    style_checks = [fraction([item.get('category') in rules['style']['accessories'] for item in accessories])]
    if layers:
        style_checks.append(fraction([item.get('category') in rules['style']['layers'] for item in layers]))
    def occasion_match(item):
        labels = item.get('occasion') or []
        if isinstance(labels, str):
            labels = [labels]
        return bool(set(labels) & rules['style']['occasions'])
    style_checks.append(fraction([occasion_match(item) for item in items]))
    style = sum(style_checks) / len(style_checks)
    energy = (color_match(rules['energy']) + fraction([bool(set(item.get('material') or []) & rules['energy']['materials']) for item in items])) / 2
    breakdown = {key: round(value * 25, 2) for key, value in
                 [('mood', mood), ('palette', palette), ('style', style), ('energy', energy)]}
    return round(sum(breakdown.values()), 2), breakdown


def build_outfits(candidates, *, weather, limit=5, quiz_answers=None):
    rules = _quiz_rules(quiz_answers)
    args = _weather_args(weather)
    effective = args["feels_like"] if args["feels_like"] is not None else args["temp"]
    low, high = get_warmth_range(effective, unit=args["unit"])
    ideal = (low+high) / 2
    groups = {key: [] for key in {"tops", "bottoms", "shoes", "outerwear", "accessories"}}
    item_weather_scores = {}
    for item in candidates:
        main = item.get("main_category") or CATEGORY_TO_MAIN.get(item.get("category"))
        if main not in groups or item.get("is_available") is False:
            continue
        suit = get_weather_suit(item, **args)
        item_weather_scores[str(item["_id"])] = suit["score"]
        groups[main].append(item)
    pool = {}
    for top, bottom, shoes, accessory, outerwear in product(
        groups["tops"], groups["bottoms"], groups["shoes"], groups["accessories"], [None] + groups["outerwear"]):
        parts = [("top", top), ("bottom", bottom), ("shoes", shoes), ("accessory", accessory)]
        if outerwear is not None:
            parts.append(("outerwear", outerwear))
        ids = [str(item["_id"]) for _, item in parts]
        signature = tuple(sorted(ids))
        color_score, relationship = score_color(parts)
        dev = [abs(item["warmth_level"] - ideal) for _, item in parts]
        look_weather_score = max(0, min(35, 35-6 * sum(dev) / len(parts) + sum(weather_score[i] for i in ids) / len(ids)))
        mismatch_penalty = min(25, sum(max(0, d - 1) * 5 for d in dev))
        look_id = sha256(("|".join(signature)).encode()).hexdigest()[:16]
        pool[signature] = dict(id=look_id, item_ids=ids, items=[dict(color=r, item=i) for r,i in parts],
                               relationship=relationship, score_breakdown=dict(weather=round(look_weather_score, 2),
                                                                               color=color_score,
                                                                               weather_penalty=mismatch_penalty,
                                                                               completeness=15))
        if rules is not None:
            quiz_score, quiz_breakdown = score_quiz(parts, rules)
            pool[signature].update(quiz_score=quiz_score, quiz_breakdown=quiz_breakdown)
    selected = []
    while pool and len(selected) < limit:
        for look in pool.values():
            overlaps = [len(set(look["item_ids"]) & set(old["item_ids"])) /
                        len(set(look["item_ids"]) | set(old["item_ids"])) for old in selected]
            overlap = max(overlaps, default=0)
            palette = {entry["item"]["color"] for entry in look["items"]}
            same_palette = any(palette == {entry["item"]["color"] for entry in old["items"]} for old in selected)
            same_style = any(look["relationship"] == old["relationship"] for old in selected)
            variety = max(0, 15 * (1 - overlap) - (3 if same_palette else 0) - (2 if same_style else 0))
            duplicate_penalty = 10 if overlap >= 0.75 else 5 if overlap >= 0.5 else 0
            breakdown  = look["score_breakdown"]
            breakdown.update(variety=round(variety, 2), similarity_penalty=duplicate_penalty)
            look["score"] = round(max(0, min(100, breakdown["weather"] + breakdown["color"] + 15 + 
                                             breakdown["variety"] - breakdown["penalty"] - duplicate_penalty)), 2)
            look["reasoning"] = f"{look['relationship'].capitalize()}; weather suitable; includes an accessory."
            look["ranking_score"] = round((1 - QUIZ_WEIGHT) * look["score"] + QUIZ_WEIGHT * look["quiz_score"], 2) if rules is not None else look["score"]
        winner = min(pool.values(), key=lambda look: (-look["ranking_score"], look["id"]))
        selected.append(winner)
        del pool[tuple(sorted(winner["item_ids"]))]
    return sorted(selected, key=lambda look: (-look["ranking_score"], look["id"]))


def get_outfits(weather, *, limit=5, quiz_answers=None):
    return build_outfits(search_clothing(available=True, limit=None),
                        weather=weather, limit=limit, quiz_answers=quiz_answers)
                                                                 
