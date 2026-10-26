from db.src.database import db
from db.src.db_helpers import required_object_id, now_utc


def ensure_outfit_indexes():
    db.outfits.create_index([('created_at', -1), ('_id', -1)])


def save_outfit(outfit, name=None):
    parts = outfit.get('items')
    ids = []
    roles = []
    for part in parts:
        role = part.get('role')
        ids.append(required_object_id(part['item']['_id'], 'item_id'))
        roles.append(role)
    garments = {item['_id']: item for item in db.clothing_items.find({'_id': {'$in': ids}})}
    now = now_utc()
    record = {
        'name': name.strip() if name else None,
        'source_id': outfit.get('id'),
        'occasion': outfit.get('occasion'),
        'item_ids': ids,
        'items': [{'role': role, 'item': garments[oid]} for role, oid in zip(roles, ids)],
        'created_at': now,
        'updated_at': now,
    }
    for key in ('score', 'score_breakdown', 'quiz_score', 'quiz_breakdown',
                'ranking_score', 'relationship', 'reasoning'):
        if key in outfit:
            record[key] = outfit[key]
    return str(db.outfits.insert_one(record).inserted_id)


def get_outfit(outfit_id):
    return db.outfits.find_one({'_id': required_object_id(outfit_id, 'outfit_id')})


def list_outfits(limit=50):
    cursor = db.outfits.find({}).sort([('created_at', -1), ('_id', -1)])
    if limit is not None:
        cursor = cursor.limit(limit)
    return list(cursor)


def rename_outfit(outfit_id, name):
    result = db.outfits.update_one(
        {'_id': required_object_id(outfit_id, 'outfit_id')},
        {'$set': {'name': name.strip(), 'updated_at': now_utc()}})
    return result.matched_count == 1


def delete_outfit(outfit_id):
    return db.outfits.delete_one(
        {'_id': required_object_id(outfit_id, 'outfit_id')}).deleted_count == 1
