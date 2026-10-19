import re
import math 
from database import db
from db_helpers import now_utc, to_object_id, clean_text, text_list, warmth, page_limit
from tagging import refresh_derived, OCCASIONS, CATEGORY_OPTIONS, normalize_category, normalize_materials

CREATE_FIELDS = {"image_url", "color", "warmth_level","brand", "catgeory", "material",
                 "name", "is_favorite", "is_available", "source"}
EDIT_FIELDS = CREATE_FIELDS - {"source"}
SOURCES = ("camera", "photo-library", "search", "manual")


def _user_fields(data, *, partial=False):
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
    data.setdefault("source", "manual")
    data.setdefault("is_favorite", False)
    data.setdefault("is_available", True)
    data.update(detected_color=None, detected_tags=[],
                color_confirmed=data["color"] is not None,
                created_at=now_utc(), revision=0)
    data["updated_at"] = data["created_at"]
    refresh_derived(data)
    return str(db.clothing_items.insert_one(data).inserted_id)


def get_clothing(item_id):
    object_id = to_object_id(item_id)
    return db.clothing_items.find_one({"_id": object_id}) if object_id is not None else None


def get_all_clothing():
    return list(db.clothing_items.find({}).sort([("created_at", -1), ("_id", -1)]))


def _save(existing, data):
    refresh_derived(data)
    data["updated_at"] = now_utc()
    data.pop("_id", None)
    result = db.clothing_items.update_one(
        {"_id": existing["_id"]},
        {"$set": data},
    )
    return result.matched_count == 1


def update_clothing(item_id, updates):
    changes = _user_fields(updates, partial=True)
    existing = get_clothing(item_id)
    if existing is None:
        return False
    if not changes:
        return True
    data = dict(existing)
    if "image_url" in changes and changes["image_url"] != existing["image_url"]:
        data.update(detected_color=None, detected_tags=[], color=None,
                    category=None, color_confirmed=False)
    data.update(changes)
    if "color" in changes:
        data["color_confirmed"] = True
    return _save(existing, data)


def set_clothing_analysis(item_id, *, image_url, detected_color, category=None, detected_tags=None):
    detected_color = clean_text(detected_color, "detected_color", lower=True)
    category = normalize_category(category)
    tags = text_list(detected_tags if detected_tags is not None else [], "detected_tags")
    existing = get_clothing(item_id)
    if existing is None:
        return False
    data = dict(existing)
    data.update(detected_color=detected_color, detected_tags=tags)
    if not data.get("category"):
        data["category"] = category
    return _save(existing, data)


def confirm_clothing_color(item_id, color=None):
    existing = get_clothing(item_id)
    if existing is None:
        return False
    final_color = color if color is not None else existing.get("detected_color")
    final_color = clean_text(final_color, "color", lower=True)
    data = dict(existing)
    data.update(color=final_color, color_confirmed=True)
    return _save(existing, data)


def search_clothing(*, category=None, main_category=None, color=None, material=None, occasion=None,
                    tags=None, season=None, brand=None, favorite=None, available=None, min_warmth=None,
                    max_warmth=None, exclude_colors=None, q=None, confirmed=None, limit=50):
    query = {}
    if category is not None:
        query["category"] = normalize_category(category)
    if main_category is not None:
        main_category = "-".join(clean_text(main_category, "main_category", lower=True).split())
        query["main_category"] = main_category
    if material is not None:
        query["material"] = normalize_materials([material])[0]
    for field, value in (("color", color),
                         ("occasion", occasion),
                         ("season", season)):
        if value is not None:
            query[field] = clean_text(value, field, lower=True)
    if tags is not None:
        query["tags"] = ({"$all": text_list(tags, "tags")} if isinstance(tags, list) else clean_text(tags, "tags", lower=True))
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
        query["$or"] = [{field: pattern} for field in ("name", "category", "main_category", "color", "material", "brand", "tags")]
    return list(db.clothing_items.find(query).sort([("created_at", -1), ("_id", -1)]).limit(page_limit(limit)))


def get_favorite_clothing(*, limit=30):
    return search_clothing(favorite=True, limit=limit)


def get_weather_candidates(temperature, *, unit="F", exclude_colors=None, occasion=None):
    if unit.upper() == "F":
        temperature = (temperature - 32) * 5 / 9
    if temperature >= 25:
        low, high = 1, 2
    elif temperature >= 16:
        low, high = 2, 3
    elif temperature >= 8:
        low, high = 3, 4
    else:
        low, high = 4, 5
    return search_clothing(
        min_warmth=low,
        max_warmth=high,
        available=True,
        exclude_colors=exclude_colors
    )


def delete_clothing(item_id):
    object_id = to_object_id(item_id)
    if object_id is None:
        return False
    return db.clothing_items.delete_one({"_id": object_id}).deleted_count == 1


def sort_clothing(sort_by="created_at", descending=True):
    allowed_fields = {"material", "color", "occasion", "category", "warmth_level"}
    if sort_by not in allowed_fields:
        raise ValueError(f"Can only sort by creation time, warmth level, material, category, color, and occasion. ")
    direction = -1 if descending else 1
    return list(db.clothing_items.find({}).sort([
        (sort_by, direction), ("_id", direction)
    ]))
        