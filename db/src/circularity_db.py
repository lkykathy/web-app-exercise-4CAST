from datetime import datetime
from db.src.database import db
from db.src.db_helpers import required_object_id, now_utc

CARE_STATUSES = ('ready', 'needs-wash', 'needs-repair', 'in-repair')
REHOME_METHODS = ('donated', 'sold', 'gifted', 'recycled', 'archived')


def ensure_circularity_indexes():
    db.history.create_index([('event_type', 1), ('occurred_at', -1)])
    db.history.create_index([('item_ids', 1), ('event_type', 1), ('occurred_at', -1)])
    db.clothing_items.create_index([('lifecycle_status', 1), ('care_status', 1), ('is_available', 1)])


def _active_items():
    return list(db.clothing_items.find({'$or': [{'lifecycle_status': 'active'},
                                                {'lifecycle_status': {'$exists': False}}]}))


def _wear_stats(ids, start_at=None, end_at=None):
    query = {'event_type': 'worn', 'item_ids': {'$in': ids}}
    if start_at is not None:
        query['occurred_at'] = {'$gte': start_at, '$lt': end_at}
    rows = db.history.aggregate([
        {'$match': query}, {'$unwind': '$item_ids'},
        {'$match': {'item_ids': {'$in': ids}}},
        {'$group': {'_id': '$item_ids', 'wear_count': {'$sum': 1},
                    'last_worn_at': {'$max': '$occurred_at'}}}
    ])
    return {row['_id']: row for row in rows}


def get_circularity_summary(start_at, end_at):
    items = _active_items()
    worn = _wear_stats([item['_id'] for item in items], start_at, end_at)
    count = len(items)
    ready = sum(item.get('care_status') == 'ready' and item.get('is_available', True) for item in items)
    return {'active_count': count,
            'worn_unique_count': len(worn),
            'worn_percentage': round(100 * len(worn) / count, 2) if count else 0,
            'ready_to_rewear_count': ready}


def get_rewear_tracker():
    items = _active_items()
    stats = _wear_stats([item['_id'] for item in items])
    return [dict(item_id=item['_id'], name=item.get('name'), image_url=item.get('image_url'),
                 wear_count=stats.get(item['_id'], {}).get('wear_count', 0),
                 last_worn_at=stats.get(item['_id'], {}).get('last_worn_at')) for item in items]


def get_care_items():
    return [dict(item_id=item['_id'], name=item.get('name'),
                 image_url=item.get('image_url'), category=item.get('category'),
                 care_status=item.get('care_status') or 'unknown',
                 care_notes=item.get('care_notes'),
                 is_available=item.get('is_available', True)) for item in _active_items()]


def get_rehome_items():
    active = [dict(item_id=item['_id'], name=item.get('name'),
                   image_url=item.get('image_url'), category=item.get('category'),
                   lifecycle_status='active') for item in _active_items()]
    rehomed = [dict(item_id=item['_id'], name=item.get('name'),cimage_url=item.get('image_url'), category=item.get('category'),
                    lifecycle_status=item['lifecycle_status']) for item in db.clothing_items.find({'lifecycle_status': {'$in': list(REHOME_METHODS)}})]
    return {'active_items': active, 'rehomed_items': rehomed}


def get_circularity_dashboard(start_at, end_at):
    summary = get_circularity_summary(start_at, end_at)
    return {
        'summary': {
            'pieces': summary['active_count'],
            'worn_this_week': summary['worn_unique_count'],
            'worn_this_week_percentage': summary['worn_percentage'],
            'ready_to_rewear': summary['ready_to_rewear_count'],
        },
        'rewear_tracker': get_rewear_tracker(),
        'repair_and_care': get_care_items(),
        'rehome_and_recirculate': get_rehome_items(),
        'care_status_options': list(CARE_STATUSES),
        'rehome_method_options': list(REHOME_METHODS),
        'period': {'start_at': start_at, 'end_at': end_at},
    }


def _transition(item_id, changes, event_type, note):
    oid = required_object_id(item_id, 'item_id')
    with db.client.start_session() as session:
        with session.start_transaction():
            item = db.clothing_items.find_one({'_id': oid}, session=session)
            if item is None:
                return False
            now = now_utc()
            changes = dict(changes, updated_at=now)
            db.clothing_items.update_one({'_id': oid}, {'$set': changes}, session=session)
            snapshot = {key: value for key, value in {**item, **changes}.items() if key != '_id'}
            db.history.insert_one(dict(event_type=event_type, item_ids=[oid],
                                       items=[dict(item_id=oid, **snapshot)], note=note,
                                       occurred_at=now, created_at=now), session=session)
    return True


def update_care_status(item_id, status, note=None):
    event = {'ready': 'care-ready', 'needs-wash': 'needs-wash',
             'needs-repair': 'needs-repair', 'in-repair': 'repair-started'}[status]
    return _transition(item_id, {'care_status': status, 'care_notes': note,
                                'is_available': status == 'ready'}, event, note)


def rehome_clothing(item_id, method, note=None):
    return _transition(item_id, {'lifecycle_status': method, 'is_available': False}, method, note)
