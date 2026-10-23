from datetime import datetime, timezone
from bson.objectid import ObjectId
from bson.errors import InvalidId


def now_utc():
    return datetime.now(timezone.utc)


def to_object_id(value):
    if value is None:
        return None
    try:
        return ObjectId(str(value))
    except(ValueError, InvalidId, TypeError):
        return None


def required_object_id(value, label="ID"):
    object_id = to_object_id(value)
    if object_id is None:
        raise ValueError(f"{label} is not a valid ObjectId")
    return object_id


def clean_text(value, field, *, optional=False, lower=False):
    if optional and (value is None or value == ""):
        return None
    value = value.strip()
    return value.lower() if lower else value


def text_list(value, field):
    return list(dict.fromkeys(clean_text(x, field, lower=True) for x in value))


def warmth(value):
    if type(value) is not int or value not in range(1,6):
        raise ValueError("Warmth level must be in the range of 1 to 5")
    return value


def page_limit(value):
    if type(value) is not int or not 1 <= value <= 50:
        raise ValueError("Limit must be below 50")
    return value


def serialize_document(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo = timezone.utc)
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_document(item) for item in value]
    if isinstance(value, dict):
        return {key:serialize_document(val) for key,val in value.items()}
    return value