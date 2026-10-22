import math
from flask import Flask, render_template, request, redirect, url_for, abort
from clothing_db import get_all_clothing, get_clothing, add_clothing, update_clothing, get_favorite_clothing, delete_clothing, get_weather_candidates, search_clothing
from db_helpers import serialize_document
from weather_api import today_weather, WeatherError
from tagging import SUBCATEGORY_OPTIONS

app = Flask(__name__)

WARMTH_CHOICES = (1, 2, 3, 4, 5)

def _read_clothing_form(form):
    errors = []
    image_url = (form.get("image_url") or "").strip()
    color = (form.get("color") or "").strip().lower()
    brand = (form.get("brand") or "").strip() or None
    name = (form.get("name") or "").strip() or None
    category = (form.get("category") or "").strip().lower() or None
    raw_warm = form.get("warmth_level")

    try:
        warmth = int(raw_warm)
    except (TypeError, ValueError):
        warmth = None

    if not image_url:
        errors.append("image url is required")
    if not color:
        errors.append("color is required")

    if category is not None and category not in SUBCATEGORY_OPTIONS:
            errors.append("Invalid category")
    
    data = {"image_url": image_url, "color": color, "brand": brand, "name": name,"warmth_level": warmth}
    if warmth not in WARMTH_CHOICES:
        errors.append("warmth level must be 1-5")

    return data, errors    

@app.route("/")
def home():
    return redirect(url_for("show_wardrobe"))

@app.route("/wardrobe")
def show_wardrobe():
    items = [serialize_document(i) for i in get_all_clothing()]
    return render_template("wardrobe.html", items=items)  

@app.route("/favorites")
def favorites():
    items = [serialize_document(i) for i in get_favorite_clothing()]
    return render_template("wardrobe.html", items=items)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "GET":
        return render_template("add.html", error=None, item = {})

    data, errors = _read_clothing_form(request.form)
    if errors:
        return render_template("add.html", error="; ".join(errors), item=request.form), 400

    add_clothing(data)
    return redirect(url_for("show_wardrobe"))

@app.route("/edit/<item_id>", methods=["GET", "POST"])
def edit(item_id):
    item = get_clothing(item_id)
    if item is None:
        abort(404)

    if request.method == "GET":
        return render_template("edit.html",  item=serialize_document(item), error=None)

    data, errors = _read_clothing_form(request.form)

    data["is_favorite"] = "is_favorite" in request.form
    data["is_available"] = "is_available" in request.form
    if errors:
        return render_template("edit.html", item=serialize_document(item), error="; ".join(errors)), 400
    
    update_clothing(item_id, data)
    return redirect(url_for("show_wardrobe"))

@app.route("/delete/<item_id>", methods=["POST"])
def delete(item_id):
    if not delete_clothing(item_id):
        abort(404)
    return redirect(url_for("show_wardrobe"))

@app.route("/recommend")
def recommend():
    raw_temp = request.args.get("temperature")
    unit = (request.args.get("unit") or "F").strip().upper()
    exclude_colors = [color.strip().lower() 
                      for color in (request.args.get("exclude_colors") or "").split(",") 
                      if color.strip()]

    def render(*, items=None, error=None, temperature=None, status=200):
        body = render_template("recommend.html", items=items, error=error, temperature=temperature, unit=unit)
        return body, status

    if unit not in ("F", "C"):
        return render(error="unit must be F or C", status=400)

    if raw_temp is None:
        return render()
    try: 
        temperature = float(raw_temp)
    except ValueError:
        return render(error="temperature must be a number", status=400)

    if not math.isfinite(temperature):
        return render(error="temperature must be a finite number", status = 400)

    candidates = get_weather_candidates(temperature, unit=unit, exclude_colors=exclude_colors or None)
    return render(items=[serialize_document(i) for i in candidates], temperature=temperature)

@app.route("/recommend-today")
def recommend_today():
    location = (request.args.get("location") or "").strip() or None
    exclude_colors = [entry.strip().lower()
                      for entry in (request.args.get("exclude_colors") or "").split(",")
                      if entry.strip()
                      ]

    def render(*, items=None, error=None, temperature=None, place=None, description=None, status=200):
        body = render_template("recommend.html", items=items, error=error,
                               temperature=temperature, unit="F", place=place, description=description,
                               source="weather-api")
        return body, status

    try:
        weather = today_weather(location)
    except WeatherError as exc:
        return render(error=str(exc), status=502)

    temperature = weather.get("temperature_fahrenheit")
    if temperature is None:
        return render(error="weather service returned no temperature", status=502)

    try:
        candidates = get_weather_candidates(temperature, unit="F", exclude_colors=exclude_colors or None)
    except(TypeError, ValueError) as exc:
        return render(error=f"could not find recommendation for this weather: {exc}", status = 500)

    return render(
        items=[serialize_document(i) for i in candidates],
        temperature=temperature,
        place=weather.get("place"),
        description=weather.get("description")
    )



@app.route("/search")
def search():
    def render(*, items=None, error=None, status=200):
        body = render_template("search.html", items=items, error=error, filters=request.args)
        return body, status

    errors = []
    category = (request.args.get("category") or "").strip().lower() or None
    color = (request.args.get("color") or "").strip().lower() or None
    brand = (request.args.get("brand") or "").strip() or None
    tags = (request.args.get("tags") or "").strip().lower() or None
    season = (request.args.get("season") or "").strip().lower() or None
    material = (request.args.get("material") or "").strip().lower() or None
    occasion = (request.args.get("occasion") or "").strip().lower() or None
    q = (request.args.get("q") or "").strip() or None
    favorite = _parse_tri(request.args.get("favorite"), "favorite", errors)
    available = _parse_tri(request.args.get("available"), "available", errors)
    min_warmth = _parse_int_arg(request.args.get("min_warmth"), "min_warmth", errors, minimum=1, maximum=5)
    max_warmth = _parse_int_arg(request.args.get("max_warmth"), "max_warmth", errors, minimum=1, maximum=5)
    limit = _parse_int_arg(request.args.get("limit"), "limit", errors, minimum=1, maximum=50)
    
    exclude_colors = [entry.strip().lower()
                      for entry in (request.args.get("exclude_colors") or "").split(",")
                      if entry.strip()]

    if min_warmth is not None and max_warmth is not None and min_warmth > max_warmth:
        errors.append("min warmth level cannot exceed the maximum warmth level")
    if errors:
        return render(error="; ".join(errors), status=400)
    try:
        results = search_clothing(
            category=category,
            color=color,
            tags=tags,
            season=season,
            brand=brand,
            material=material,
            occasion=occasion,
            q=q,
            favorite=favorite,
            available=available,
            min_warmth=min_warmth,
            max_warmth=max_warmth,
            exclude_colors=exclude_colors or None,
            limit=limit if limit is not None else 50,
        )
    except ValueError as exc:
        return render(error=str(exc), status=400)
    return render(items=[serialize_document(i) for i in results])

def _parse_tri(value, label, errors):
    if value is None or not value.strip():
        return None
    lowered = value.strip().lower()
    if lowered in ("1", "true", "on", "yes"):
        return True
    if lowered in ("0", "false", "off", "no"):
        return False
    errors.append(f"{label} must be a boolean")
    return None

def _parse_int_arg(value, label, errors, *, minimum=None, maximum=None):
    if value is None or not value.strip():
        return None
    try: 
        result = int(value)
    except ValueError:
        errors.append(f"{label} must be an integer")
        return None
    if minimum is not None and result < minimum:
        errors.append(f"{label} must be at least {minimum}")
        return None
    if maximum is not None and result > maximum:
        errors.append(f"{label} must be at most {maximum}")
        return None
    return result



if __name__ == "__main__":
    app.run(debug=True)