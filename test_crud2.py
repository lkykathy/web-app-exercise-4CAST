from pathlib import Path
from clothing_db import (
    add_clothing,
    get_clothing,
    get_all_clothing,
    update_clothing,
    delete_clothing,
    search_clothing,
    get_favorite_clothing,
    get_weather_candidates,
)
from tagging import generate_tags, derived_seasons

picture = Path("static/uploads/white_tshirt.png")
assert picture.is_file(), f"Image missing: {picture}"


assert generate_tags("white", 1) == [
    "white", "very-light", "summer"
]
assert derived_seasons(3) == ["spring", "fall"]
print("PASS: Tag generation")


item_id = None
try:
    item_id = add_clothing({
        "image_url": "/static/uploads/white_tshirt.png",
        "color": "white",
        "warmth_level": 1,
        "brand": "Sezane"
    })


    item = get_clothing(item_id)
    assert item is not None
    assert item["color"] == "white"
    assert item["warmth_level"] == 1
    assert item["tags"] == [
        "white", "very-light", "summer"
    ]
    assert item["is_available"] is True
    print("PASS: Create / Read / Automatic tags")


    assert any(
        str(x["_id"]) == item_id
        for x in get_all_clothing()
    )
    assert any(
        str(x["_id"]) == item_id
        for x in search_clothing(color="white")
    )
    assert any(
        str(x["_id"]) == item_id
        for x in search_clothing(brand="sezane")
    )
    assert any(
        str(x["_id"]) == item_id
        for x in search_clothing(tags="summer")
    )
    print("PASS: List / Search / Brand / Tag")


    assert any(
        str(x["_id"]) == item_id
        for x in get_weather_candidates(86)
    )
    assert any(
        str(x["_id"]) == item_id
        for x in get_weather_candidates(30, unit="C")
    )
    assert all(
        str(x["_id"]) != item_id
        for x in get_weather_candidates(
            68, exclude_colors=["white"]
        )
    )
    print("PASS: Fahrenheit / Celsius / Excluded colors")


    assert update_clothing(
        item_id,
        {"warmth_level": 4, "is_favorite": True}
    )
    item = get_clothing(item_id)
    assert item["warmth_level"] == 4
    assert item["season"] == ["fall", "winter"]
    assert "warm" in item["tags"]
    assert any(
        str(x["_id"]) == item_id
        for x in get_favorite_clothing()
    )


    assert update_clothing(
        item_id,
        {"is_available": False}
    )
    assert get_clothing(item_id)["is_available"] is False
    print("PASS: Update / Favorite / Availability")

    
    
finally:
    if item_id is not None:
        assert delete_clothing(item_id), "Cleanup failed"
        assert get_clothing(item_id) is None
        print("PASS: Delete / Cleanup")


print("All clothing database tests passed!")
