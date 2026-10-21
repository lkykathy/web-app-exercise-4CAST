from db_helpers import warmth, clean_text, text_list

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
                    "tie", "watch"),
    "activewear": ("sports-bra", "athletic-top", "athletic-shorts",
                   "athletic-leggings"),
}
BASE_OCCASIONS = {
    "t-shirt": {"casual", "loungewear", "vacation"},
    "blouse": {"smart-casual", "business-casual"},
    "dress-shirt": {"smart-casual", "business-casual", "business-formal"},
    "sweater": {"casual", "smart-casual"},
    "button-up-shirt": {"casual", "smart-casual", "business-casual"},
    "tank-top": {"casual", "loungewear", "vacation"},
    "crop-top": {"casual", "vacation"},
    "polo-shirt": {"casual", "smart-casual", "business-casual"},
    "hoodie": {"casual", "loungewear"},
    "sweatshirt": {"casual", "loungewear"},
    "cardigan": {"casual", "smart-casual", "business-casual"},
    "bodysuit": {"casual", "smart-casual"},
    "jeans": {"casual", "smart-casual"},
    "slacks": {"smart-casual", "business-casual", "business-formal"},
    "skirt": {"casual", "smart-casual"},
    "shorts": {"casual", "vacation"},
    "trousers": {"smart-casual", "business-casual"},
    "leggings": {"casual", "loungewear"},
    "sweatpants": {"casual", "loungewear"},
    "joggers": {"casual", "loungewear"},
    "dress": {"casual", "smart-casual"},
    "jumpsuit": {"casual", "smart-casual"},
    "romper": {"casual", "vacation"},
    "overalls": {"casual"},
    "jacket": {"casual"},
    "blazer": {"smart-casual", "business-casual"},
    "coat": {"casual", "smart-casual"},
    "trench-coat": {"smart-casual", "business-casual"},
    "vest": {"casual", "smart-casual"},
    "sneakers": {"casual", "vacation"},
    "boots": {"casual", "smart-casual"},
    "heels": {"smart-casual", "business-casual", "cocktail", "formal", "special-occasion"},
    "flats": {"casual", "smart-casual", "business-casual"},
    "sandals": {"casual", "vacation"},
    "loafers": {"smart-casual", "business-casual", "business-formal"},
    "bag": {"casual"},
    "belt": {"casual", "smart-casual"},
    "hat": {"casual", "vacation"},
    "scarf": {"casual", "smart-casual"},
    "jewelry": {"casual", "smart-casual"},
    "sunglasses": {"casual", "vacation"},
    "tie": {"business-formal", "formal", "special-occasion"},
    "watch": {"casual", "smart-casual", "business-casual"},
    "sports-bra": {"activewear"},
    "athletic-top": {"casual", "activewear"},
    "athletic-shorts": {"casual", "activewear"},
    "athletic-leggings": {"casual", "activewear"},
}
SUBCATEGORY_OPTIONS = tuple(category for categories in CATEGORY_OPTIONS.values() for category in categories)
CATEGORY_TO_MAIN = {category: main for main, categories in CATEGORY_OPTIONS.items() for category in categories}


def normalize_category(value):
    value = clean_text(value, "category", optional=True, lower=True)
    if value is None:
        return None
    value = "-".join(value.split())
    return value


def normalize_materials(value):
    materials = text_list([] if value is None else value, "material")
    return materials


def derived_seasons(warmth_level):
    return list(WARMTH_LABELS[warmth_level][1])


def derive_occasions(category, color, material=None):
    category = normalize_category(category)
    fabrics = set(normalize_materials(material))
    if not category or not color:
        return []
    color = color.strip().lower()
    neutral = color in {
        "black", "white", "gray", "grey", "navy", "beige", "brown", "cream",
        "tan", "charcoal", "dark gray", "dark grey",
    }
    dark = color in {"black", "navy", "charcoal", "dark gray", "dark grey"}
    bright = color in {"yellow", "orange", "pink", "red", "turquoise", "coral"}
    dressy = bool(fabrics & {"silk", "satin", "velvet", "chiffon", "lace"})
    polished = bool(fabrics & {"wool", "cashmere", "silk"})
    relaxed = bool(fabrics & {"denim", "fleece"})
    breathable = bool(fabrics & {"cotton", "linen"})
    result = set(BASE_OCCASIONS[category])

    if neutral and polished and category in {
        "blouse", "sweater", "cardigan", "button-up-shirt", "skirt", "dress",
        "trousers", "blazer", "coat", "vest",
    }:
        result.add("business-casual")
    if dark and "wool" in fabrics and category in {"blazer", "slacks", "trousers"}:
        result.add("business-formal")
    if dressy and category in {"dress", "jumpsuit", "skirt", "blouse", "bodysuit"}:
        result.update({"cocktail", "special-occasion"})
    if dressy and category in {"dress", "jumpsuit"}:
        result.add("formal")
        result.discard("casual")
    if dressy and neutral and category == "blazer":
        result.update({"cocktail", "special-occasion"})
    if breathable and category in {
        "t-shirt", "blouse", "button-up-shirt", "tank-top", "crop-top",
        "polo-shirt", "shorts", "trousers", "skirt", "dress", "jumpsuit", "romper",
    }:
        result.add("vacation")
    if bright and category in {"blouse", "skirt", "dress", "jumpsuit", "romper"}:
        result.add("vacation")
    if dressy and category in {"dress", "jumpsuit"}:
        result.discard("vacation")

    if category == "scarf" and fabrics & {"silk", "wool", "cashmere"}:
        result.add("business-casual")
        if neutral and "silk" in fabrics:
            result.update({"business-formal", "formal", "special-occasion"})
    if category in {"bag", "belt", "watch", "loafers", "boots"}:
        if neutral and "leather" in fabrics:
            result.update({"smart-casual", "business-casual"})
    if category == "bag" and dressy:
        result.update({"cocktail", "formal", "special-occasion"})

    if relaxed:
        result.difference_update({"business-formal", "cocktail", "formal", "special-occasion"})
        if CATEGORY_TO_MAIN[category] != "activewear":
            result.add("casual")
        if category not in {"dress-shirt", "slacks"}:
            result.discard("business-casual")
    if "fleece" in fabrics and category in {"hoodie", "sweatshirt", "sweatpants", "joggers"}:
        result.add("loungewear")

    return [occasion for occasion in OCCASIONS if occasion in result]


def generate_tags(color, warmth_level, *, detected_tags=None, category=None, material=None, occasions=None):
    label, seasons = WARMTH_LABELS[warmth(warmth_level)]
    category = normalize_category(category)
    values = [color, label, *seasons, category, CATEGORY_TO_MAIN.get(category), 
              *normalize_materials(material), *(occasions or []), *(detected_tags or [])]
    return list(dict.fromkeys(x for x in values if x))


def refresh_derived(document):
    document["category"] = normalize_category(document.get("category"))
    document["main_category"] = CATEGORY_TO_MAIN.get(document["category"])
    document["material"] = normalize_materials(document.get("material"))
    document["season"] = derived_seasons(document["warmth_level"])
    document["occasion"] = derive_occasions(document["category"], document.get("color"), document["material"])
    document["tags"] = generate_tags(document.get("color"),
                                    document["warmth_level"],
                                    detected_tags=document.get("detected_tags", []),
                                    category=document["category"],
                                    material=document["material"],
                                    occasions=document["occasion"])
    return document