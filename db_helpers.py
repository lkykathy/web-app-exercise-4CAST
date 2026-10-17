from datetime import datetime, timezone
from bson.objectid import ObjectId

def now_utc():
    return datetime.now(timezone.utc)

def to_object_id(value):
    try:
        return ObjectId(str(value))
    except(ValueError, TypeError):
        return None

def required_object_id(value, label="ID"):
    object_id = to_object_id(value)
    if object_id is None:
        raise ValueError(f"{label} is not a valid ObjectId")
    return object_id

def serialize_document(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_document(item) for item in value]
    if isinstance(value, dict):
        return {key:serialize_document(item) for key,item in value}
    return value