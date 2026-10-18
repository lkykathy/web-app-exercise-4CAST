import re
from database import db
from db_helpers import now_utc, to_object_id
from tagging import derived_seasons, generate_tags

CREATE_FIELDS = {"image_url", "color", "warmth_level", "brand"}
EDIT_FIELDS = CREATE_FIELDS | {"is_favorite", "is_available"}
ANALYSIS_FILEDS = {"category", "tags"}

def _image_url(value):
    value = value.strip()
    return value

def _user_fields(data, *, partial=False):
    result = {}
    if "image_url" in data:
        result["image_url"] = _image_url(data["image_url"])
    if "color" in data:
        result["color"] = data["color"]
    if "warmth_level" in data:
        level = data["warmth_level"]
        result["warmth_level"] = level
    if "brand" in data:
        brand = data["brand"]
        result["brand"] = brand if brand is not None else None
    for field in ("is_favorite", "is_available"):
        if field in data:
            result[field] = data[field]
    return result

def add_clothing(clothing):
    data = _user_fields(clothing)
    data.setdefault("brand", None)
    data.update({
        "category": None,
        "detected_tags": [],
        "season": derived_seasons(data["warmth_level"]),
        "tags": generate_tags(data["color"], data["warmth_level"]),
        "is_favorite": False,
        "is_available": True,
        "created_at": now_utc(),
    })
    data["updated_at"] = data["created_at"]
    return str(db.clothing_items.insert_one(data).inserted_id)

def get_clothing(item_id):
    object_id = to_object_id(item_id)
    return db.clothing_items.find_one({"_id": object_id}) if object_id is not None else None

def get_all_clothing():
    return list(db.clothing_items.find({}).sort("created_at", -1))

def update_clothing(item_id, updates):
    object_id = to_object_id(item_id)
    if object_id is None:
        return False
    data = _user_fields(updates, partial=True)
    existing = db.clothing_items.find_one({"_id": object_id})
    if existing is None:
        return False
    color = data.get("color", existing["color"])
    warmth = data.get("warmth_level", existing["warmth_level"])
    if "image_url" in data and data["image_url"] != existing.get("image_url"):
        data.update({"category": None, "detected_tags": []})
    data["tags"] = generate_tags(color, warmth, 
                                 detected_tags=data.get("detected_tags", existing.get("detected_tags", [])), 
                                 category=data.get("category", existing.get("category")))
    data["season"] = derived_seasons(warmth)
    data["updated_at"] = now_utc()
    result = db.clothing_items.update_one({"_id": object_id}, {"$set": data})
    return result.matched_count == 1

def search_clothing(*, category=None, color=None, tags=None, season=None, brand=None, favorite=None, 
                    available=None, min_warmth=None, max_warmth=None, exclude_colors=None, limit=50):
    query = {}
    for field, value in (("category", category), ("color", color), ("tags", tags), ("season", season)):
        if value:
            query[field] = value
    if brand:
        query["brand"] = {"$regex": "^" + re.escape(brand) + "$", "$options": "i"}
    for key, value in (("is_favorite", favorite), ("is_available", available)):
        if value is not None:
            query[key] = value
    if min_warmth is not None or max_warmth is not None:
        bounds = {}
        for name, op, value in (("min_warmth", "$gte", min_warmth), ("max_warmth", "$lte", max_warmth)):
            if value is not None:
                bounds[op] = value
        if min_warmth is not None and max_warmth is not None and min_warmth > max_warmth:
            raise ValueError("min warmth level cannot exceed max warmth level")
        query["warmth_level"] = bounds
    if exclude_colors:
        colors = exclude_colors
        if "color" in query and query["color"] in colors:
            return []
        if "color" not in query:
            query["color"] = {"$nin": colors}
    return list(db.clothing_items.find(query).sort("created_at", -1).limit(limit))

def get_favorite_clothing():
    return search_clothing(favorite=True)

def get_weather_candidates(temperature, *, unit="F", exclude_colors=None):
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
        



