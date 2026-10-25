from .db_helpers import warmth, clean_text, text_list
import math

WARMTH_LABELS = {
    1: ("very-light", ["summer"]),
    2: ("light", ["spring", "summer"]),
    3: ("medium", ["spring", "fall"]),
    4: ("warm", ["fall", "winter"]),
    5: ("very-warm", ["winter"]),
}
OCCASIONS = (
    "casual", "smart-casual", "business-casual", "business-formal", "cocktail",
    "formal", "activewear", "loungewear", "vacation", "special-occasion",
)
MATERIAL_OPTIONS = (
    "cotton", "polyester", "denim", "wool", "linen", "silk", "satin", "leather",
    "suede", "nylon", "spandex", "cashmere", "velvet", "chiffon", "lace",
    "fleece", "knit", "other",
)
CATEGORY_OPTIONS = {
    "tops": ("t-shirt", "blouse", "dress-shirt", "sweater", "button-up-shirt",
             "tank-top", "crop-top", "polo-shirt", "hoodie", "sweatshirt",
             "cardigan", "bodysuit"),
    "bottoms": ("jeans", "slacks", "skirt", "shorts", "trousers", "leggings",
                "sweatpants", "joggers"),
    "one-piece": ("dress", "jumpsuit", "romper", "overalls"),
    "outerwear": ("jacket", "blazer", "coat", "trench-coat", "vest"),
    "shoes": ("sneakers", "boots", "heels", "flats", "sandals", "loafers"),
    "accessories": ("bag", "belt", "hat", "scarf", "jewelry", "sunglasses",
                    "tie", "watch", "cap"),
    "activewear": ("sports-bra", "athletic-top", "athletic-shorts",
                   "athletic-leggings"),
}
SUBCATEGORY_OPTIONS = tuple(category for categories in CATEGORY_OPTIONS.values() for category in categories)
CATEGORY_TO_MAIN = {category: main for main, categories in CATEGORY_OPTIONS.items() for category in categories}

COLOR_OPTIONS = (
    "black", "white", "gray", "beige", "cream", "brown", "tan",
    "red", "burgundy", "pink", "coral", "orange", "peach", "yellow",
    "gold", "olive", "lime", "green", "mint", "teal", "turquoise",
    "blue", "navy", "lavender", "purple", "magenta", "silver",
)
COLOR_LIGHTNESS_OPTIONS = ("light", "medium", "dark")
COLOR_WHEEL = {
    "red": 1, "burgundy": 1, "coral": 2, "orange": 3, "peach": 4,
    "yellow": 5, "gold": 5, "olive": 6, "lime": 6, "green": 7,
    "mint": 7, "teal": 8, "turquoise": 8, "blue": 9, "navy": 9,
    "lavender": 10, "purple": 11, "pink": 12, "magenta": 12,
}
QUIZ_OPTIONS = {
    "mood": (
        "Confident",
        "Soft",
        "Creative",
        "Grounded",
    ),
    "palette": (
        "Warm & Fiery",
        "Cool & Striking",
        "Earthy & Natural",
        "Soft & Dreamlike",
        "Dark & Minimal",
        "Playful & Eclectic",
    ),
    "style": (
        "Minimalist",
        "Romantic",
        "Streetwear",
        "Classic",
    ),
    "energy": (
        "Bold & Powerful",
        "Effortless & Relaxed",
        "Elegant & Refined",
        "Fun & Expressive",
    ),
}


def normalize_category(value):
    value = clean_text(value, "category", optional=True, lower=True)
    if value is None:
        return None
    value = "-".join(value.split())
    return value


def normalize_materials(value):
    materials = text_list([] if value is None else value, "material")
    return materials


def normalize_occasions(value):
    occasions = text_list([] if value is None else value, "occasion")
    return occasions


def normalize_color(value):
    return clean_text(value, "color", lower=True)


def color_attributes(color, lightness):
    color = normalize_color(color)
    position = COLOR_WHEEL.get(color)
    return {
        "color": color,
        "color_lightness": lightness,
        "color_wheel_pos": position,
        "color_is_neutral": position is None,
        "color_temp": ("neutral" if position is None else "warm" if position <=6 else "cool")
    }


def derived_seasons(warmth_level):
    return list(WARMTH_LABELS[warmth_level][1])


def refresh_derived(document):
    document["category"] = normalize_category(document.get("category"))
    document["main_category"] = CATEGORY_TO_MAIN.get(document["category"])
    document["material"] = normalize_materials(document.get("material"))
    document["occasion"] = normalize_occasions(document.get("occasion"))
    document["season"] = derived_seasons(document["warmth_level"])
    return document