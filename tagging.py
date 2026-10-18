WARMTH_LABELS = {
    1: ("very-light", ["summer"]),
    2: ("light", ["spring", "summer"]),
    3: ("medium", ["spring", "fall"]),
    4: ("warm", ["fall", "winter"]),
    5: ("very-warm", ["winter"]),
}

def derived_seasons(warmth_level):
    return list(WARMTH_LABELS[warmth_level][1])

def generate_tags(color, warmth_level, *, detected_tags=None, category=None):
    label, seasons = WARMTH_LABELS[warmth_level]
    tags = [color, label, *seasons]
    if category:
        tags.append(category)
    if detected_tags is not None:
        tags.extend(detected_tags)
    return list(dict.fromkeys(tag for tag in tags if tag))