import re
import math 
from .database import db
from .db_helpers import now_utc, to_object_id, clean_text, text_list, warmth, page_limit
from .tagging import refresh_derived, CATEGORY_TO_MAIN, HOME_OCCASIONS, normalize_category, normalize_materials, normalize_occasions

CREATE_FIELDS = {"image_url", "color", "warmth_level","brand", "category", "material",
                 "occasion", "name", "is_favorite", "is_available", "source"}
EDIT_FIELDS = CREATE_FIELDS - {"source"}
SOURCES = ("camera", "photo-library", "search", "manual")


def _user_fields(data, *, partial=False):
    allowed = EDIT_FIELDS if partial else CREATE_FIELDS
    data = {key: value for key, value in data.items() if key in allowed}
    result = {}
    for field in ("image_url", "color", "brand", "name"):
        if field in data:
            result[field] = clean_text(data[field], field,
                            optional=field in {"brand", "name"},
                            lower=field == "color")
    if "category" in data:
        result["category"] = normalize_category(data["category"])
    if "material" in data:
        result["material"] = normalize_materials(data["material"])
    if "occasion" in data or "occasions" in data:
        result["occasion"] = normalize_occasions(data.get("occasions", data.get("occasion")))
    if "warmth_level" in data:
        result["warmth_level"] = warmth(data["warmth_level"])
    for field in ("is_favorite", "is_available"):
        if field in data:
            result[field] = data[field]
    if "source" in data:
        result["source"] = data["source"]
    return result


def add_clothing(clothing):
    data = _user_fields(clothing)
    for field in ("color", "category", "brand", "name"):
        data.setdefault(field, None)
    data.setdefault("material", [])
    data.setdefault("occasion", [])
    data.setdefault("source", "camera")
    data.setdefault("is_favorite", False)
    data.setdefault("is_available", True)
    data.update(detected_color=None, color_confirmed=data["color"] is not None, created_at=now_utc())
    data["updated_at"] = data["created_at"]
    refresh_derived(data)
    return str(db.clothing_items.insert_one(data).inserted_id)


def get_clothing(item_id):
    object_id = to_object_id(item_id)
    return db.clothing_items.find_one({"_id": object_id}) if object_id is not None else None


def get_all_clothing():
    return list(db.clothing_items.find({}).sort([("created_at", -1), ("_id", -1)]))


def _save(existing, change):
    data = {**existing, **change}
    if "occasions" not in data and "occasion" in data:
        data["occasions"] = data["occasion"]
    refresh_derived(data)
    updates = dict(change)
    for key in ("category", "main_category", "material", "occasion", "season"):
        updates[key] = data[key]
    updates.pop("_id", None)
    updates["updated_at"] = now_utc()
    return db.clothing_items.update_one({"_id": existing["_id"]},
                                        {"$set": updates}).matched_count == 1


def update_clothing(item_id, updates):
    changes = _user_fields(updates, partial=True)
    existing = get_clothing(item_id)
    if existing is None:
        return False
    if not changes:
        return True
    if "image_url" in changes and changes["image_url"] != existing["image_url"]:
        changes = {"detected_color": None, "color": None, "category": None, "color_confirmed": False, **changes}
    if "color" in changes and changes["color"] is not None:
        changes["color_confirmed"] = True
    return _save(existing, changes)


def set_clothing_analysis(item_id, *, image_url, detected_color, category=None):
    existing = get_clothing(item_id)
    if existing is None:
        return False
    change = {"detected_color": clean_text(detected_color, "detected_color", lower=True)}  
    category = normalize_category(category)  
    if not existing.get("category"):
        change["category"] = category
    return _save(existing, change)


def confirm_clothing_color(item_id, color=None):
    existing = get_clothing(item_id)
    if existing is None:
        return False
    final_color = color if color is not None else existing.get("detected_color")
    final_color = clean_text(final_color, "color", lower=True)
    change = {"color": clean_text(final_color, "color", lower=True), "color_confirmed": True}
    return _save(existing, change)


def search_clothing(*, category=None, main_category=None, color=None, material=None, occasion=None,
                    season=None, brand=None, favorite=None, available=None, min_warmth=None,
                    max_warmth=None, exclude_colors=None, q=None, confirmed=None, 
                    sort_by="created_at", descending=True, limit=50):
    query = {}
    if category is not None:
        query["category"] = normalize_category(category)
    if main_category is not None:
        main_category = "-".join(clean_text(main_category, "main_category", lower=True).split())
        query["main_category"] = main_category
    if material is not None:
        query["material"] = normalize_materials([material])[0]
    if occasion is not None:
        query["occasion"] = normalize_occasions([occasion])[0]
    for field, value in (("color", color),
                         ("season", season)):
        if value is not None:
            query[field] = clean_text(value, field, lower=True)
    if brand is not None:
        query["brand"] = {"$regex": "^" + re.escape(clean_text(brand, "brand")) + "$", "$options": "i"}
    for field, value in (("is_favorite", favorite),
                         ("is_available", available),
                         ("color_confirmed", confirmed)):
        if value is not None:
            query[field] = value
    bounds = {}
    for op, value in (("$gte", min_warmth), ("$lte", max_warmth)):
        if value is not None:
            bounds[op] = warmth(value)
    if bounds:
        query["warmth_level"] = bounds
    if exclude_colors is not None:
        colors = text_list(exclude_colors, "exclude_colors")
        if color is not None and query["color"] in colors:
            return []
        if color is None:
            query["color"] = {"$nin": colors}
    if q is not None:
        pattern = {"$regex": re.escape(clean_text(q, "q")), "$options": "i"}
        query["$or"] = [{field: pattern} for field in ("name", "category", "main_category", "color", "material", "brand", "occasion")]
    direction = -1 if descending else 1
    cursor = db.clothing_items.find(query).sort(
        [(sort_by, direction), ("_id", direction)]
    )
    if limit is not None:
        cursor = cursor.limit(limit)
    return list(cursor)


def get_favorite_clothing(*, limit=30):
    return search_clothing(favorite=True, limit=limit)


def delete_clothing(item_id):
    object_id = to_object_id(item_id)
    if object_id is None:
        return False
    return db.clothing_items.delete_one({"_id": object_id}).deleted_count == 1


def sort_clothing(sort_by="created_at", descending=True):
    direction = -1 if descending else 1
    return list(db.clothing_items.find({}).sort([(sort_by, direction), ("_id", direction)]))


def get_warmth_range(temperature, *, unit="F", exclude_colors=None, occasion=None):
    if unit.upper() == "F":
        temperature = (temperature - 32) * 5 / 9
    if temperature >= 25:
        return 1, 2
    elif temperature >= 16:
        return 2, 3
    elif temperature >= 8:
        return 3, 4
    else:
        return 4, 5


def get_weather_suit(clothing, temp, *, unit="F", feels_like=None, is_raining=False,
                     is_snowing=False, wind_mph=0, gust_mph=None, humidity=None):
    unit = unit.upper()
    effective = temp if feels_like is None else feels_like
    low, high = get_warmth_range(effective, unit=unit)
    level = warmth(clothing["warmth_level"])
    material = set(clothing.get("material") or [])
    category = clothing.get("category")
    celsius = (effective - 32) * 5 / 9 if unit == "F" else effective
    wind = max(wind_mph, gust_mph if gust_mph is not None else wind_mph)
    if not low <= level <= high:
        return {"suitable": False, "score":0}
    if is_raining or is_snowing:
        if "suede" in material or category == "sandals":
            return {"suitable": False, "score":0}
    if is_snowing or celsius < 10:  
        if category in {"shorts", "athletic-shorts", "tank-top", "crop-top", "sports-bra", "sandals"}:
            return {"suitable": False, "score":0}
    if wind >= 20 and category == "cap":
        return {"suitable": False, "score":0}

    score = 0
    main = clothing.get("main_category") or CATEGORY_TO_MAIN.get(category)
    if celsius >= 25:
        if main in {"tops", "bottoms", "one-piece"} and material & {"cotton", "linen"}:
            score += 2
        if humidity is not None and humidity >= 70 and "linen" in material:
            score += 1
        if material & {"wool", "cashmere", "fleece", "velvet"}:
            score -= 2
    elif celsius < 10 and material & {"wool", "cashmere", "fleece"}:
        score += 2
    if (is_raining or is_snowing) and material & {"silk", "chiffon", "satin", "velvet"}:
        score -= 2
    if is_snowing and category in {"heels", "flats", "loafers"}:
        score -= 2
    if wind >= 20 and category in {"skirt", "dress"} and material & {"silk", "chiffon", "linen"}:
        score -= 2
    return {"suitable": True, "score": score}


def get_weather_candidates(temp, *, unit="F", feels_like=None, humidity=None,
                           is_raining=False, is_snowing=False, wind_mph=0,
                           gust_mph=None, occasion=None, exclude_colors=None, limit=50):
    low, high = get_warmth_range(temp if feels_like is None else feels_like, unit=unit)
    items = search_clothing(available=True, confirmed=True, occasion=occasion, exclude_colors=exclude_colors,
                            min_warmth=low, max_warmth=high, limit=None)
    ranked = []
    for item in items:
        result = get_weather_suit(item, temp, unit=unit, feels_like=feels_like, humidity=humidity,
                                  is_raining=is_raining, is_snowing=is_snowing, wind_mph=wind_mph, gust_mph=gust_mph)
        if result["suitable"]:
            ranked.append((result["score"], item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in ranked[:limit]]


def get_weather_recommendation(weather, **filters):
    return get_weather_candidates(
        temp=weather["temperature_fahrenheit"],
        unit="F",
        feel_like=weather.get("feels_like_fahrenheit"),
        humidity=weather.get("humidity"),
        is_raining=weather.get("is_raining", False),
        is_snowing=weather.get("is_snowing", False),
        wind_mph=weather.get("wind_mph", 0),
        gust_mph=weather.get("gust_mph"),
        **filters
    )