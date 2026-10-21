from database import db

clothing = {
    "image_url": "/static/uploads/white_tshirt.png",
    "color": "white",
    "warmth_level": 1,
    "brand": "sezane",      # optional

    # system-generated information
    "category": None,
    "season": ["summer"],
    "detected_tags": [],    # info from image detection like short-sleeve, casual
    "tags": ["white", "very-light", "summer"],

    "is_favorite": False,
    "is_available": True
}

result = db.clothing_items.insert_one(clothing)
print("Inserted ID: ", result.inserted_id)

item = db.clothing_items.find_one({"_id": result.inserted_id})
print("Retrieved item: ", item)