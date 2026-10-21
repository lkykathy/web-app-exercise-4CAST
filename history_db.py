from datetime import datetime
from database import db
from db_helpers import now_utc, to_object_id, required_object_id, clean_text, page_limit
from tagging import OCCASIONS

EVENT_TYPES = ("viewed", "recommended", "save", "worn")
SNAPSHOT_FIELDS = ("image_url", "name", "category", "main_category", "color", 
                   "material", "brand", "warmth_level", "season", "occasion")


def add_history(item_ids, *, event_type="viewed", occasion=None, note=None, occurred_at=None):
    ids = list(dict.fromkeys(required_object_id(x, "item_id") for x in item_ids))
    note = clean_text(note, "note", optional=True)
    if occurred_at is None:
        occurred_at = now_utc()
    items = list(db.clothing_items.find({"_id": {"$in": ids}}))
    by_id = {x["_id"]: x for x in items}
    snapshots = [dict(item_id=oid, **{f: by_id[oid].get(f) for f in SNAPSHOT_FIELDS}) for oid in ids]
    data = dict(event_type=event_type, item_ids=ids, items=snapshots, occasion=occasion,
                note=note, occurred_at=occurred_at, created_at=now_utc())
    return str(db.history.insert_one(data).inserted_id)


def get_history(history_id):
    oid = to_object_id(history_id)
    return db.history.find_one({"_id": oid}) if oid is not None else None


def list_history(*, event_type=None, item_id=None, limit=50):
    query = {}
    if event_type is not None:
        query["event_type"] = event_type
    if item_id is not None:
        query["item_ids"] = required_object_id(item_id, "item_id")
    return list(db.history.find(query).sort([("created_at", -1), ("_id", -1)]).limit(page_limit(limit)))


def delete_history(hitsory_id):
    oid = to_object_id(hitsory_id)
    if oid is None:
        return False
    return db.history.delete_one({"_id": oid}).deleted_count == 1