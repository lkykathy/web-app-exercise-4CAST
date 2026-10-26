import math
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for, abort, jsonify
from db.src.clothing_db import (
    get_all_clothing,
    get_clothing,
    add_clothing,
    update_clothing,
    get_favorite_clothing,
    delete_clothing,
    get_weather_candidates,
    search_clothing,
)
from db.src.db_helpers import serialize_document
from weather_api import today_weather, WeatherError
from db.src.tagging import SUBCATEGORY_OPTIONS
from db.src.history_db import add_history, list_history
from db.src.circularity_db import get_circularity_dashboard, update_care_status, rehome_clothing
from db.src.styling import get_outfits
from db.src.outfit import get_featured_outfits, get_outfits_for_weather
from db.src.database import db
from bson.objectid import ObjectId
from db.src.circularity_db import get_circularity_dashboard, update_care_status


#required HTML template
"""
add.html
edit.html
history.html
"""

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

WARMTH_CHOICES = (1, 2, 3, 4, 5)


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


def _read_clothing_form(form):
    errors = []
    color = (form.get("color") or "").strip().lower()
    brand = (form.get("brand") or "").strip() or None
    name = (form.get("name") or "").strip() or None
    category = (form.get("category") or "").strip().lower() or None
    material = [m.strip().lower() for m in (form.get("material") or "").split(",") if m.strip()]
    raw_warm = form.get("warmth_level")

    try:
        warmth = int(raw_warm)
    except (TypeError, ValueError):
        warmth = None

    if not color:
        errors.append("color is required")

    if category is None:
        errors.append("category is required")
    elif category not in SUBCATEGORY_OPTIONS:
        errors.append("invalid category")

    data = {
        "color": color,
        "brand": brand,
        "name": name,
        "category": category,
        "material" : material,
        "warmth_level": warmth,
    }
    if warmth not in WARMTH_CHOICES:
        errors.append("warmth level must be 1-5")

    return data, errors


@app.route("/")
def home():
    try:
        weather = today_weather()
        error = None
    except WeatherError as e:
        weather = None
        error = str(e)

    outfits = {}
    if weather and request.args.get("generate")=="true":
        try:
            featured=get_featured_outfits(weather)
            outfits = {k: serialize_document(v) for k,v in featured.items() if v is not None}
        except Exception as e:
            print(f"Failed to generate outfits: {e}")
    return render_template("index.html", weather=weather, error=error, outfits=outfits)


@app.route("/wardrobe")
def show_wardrobe():
    items = [serialize_document(i) for i in get_all_clothing()]
    return render_template("wardrobe.html", items=items)

@app.route("/garment/<item_id>")
def garment_details(item_id):
    item = get_clothing(item_id)
    if item is None:
        abort(404)
    return render_template("garment-details.html", item=serialize_document(item))

@app.route("/mood", methods=["GET", 'POST'])
def mood():
    if request.method == "POST":
        quiz_answers = {
            "mood": request.form.get("mood"),
            "palette": request.form.get("palette"),
            "style": request.form.get("style"),
            "energy": request.form.get("energy")
        }

        try:
            weather = today_weather()
        except WeatherError:
            weather = {"temperature_fahrenheit": 70, "feels_like_fahrenheit": 70}

        looks = get_outfits(weather, limit=5, quiz_answers=quiz_answers)
        mood_outfits = [serialize_document(look) for look in looks]
        favorites = list(db.favorite_outfits.find({}))

        return render_template("outfits.html", favorites=favorites, mood_outfits=mood_outfits)
    return render_template("mood.html")

@app.route("/favorites")
def favorites():
    items = [serialize_document(i) for i in get_favorite_clothing()]
    return render_template("wardrobe.html", items=items)

@app.route("/save_favorite", methods=["POST"])
def save_favorite():
    try:
        data = request.json
        if data:
            data.pop("_id", None)
            db.favorite_outfits.insert_one(data)
            return jsonify({"success": True}), 200
    except Exception as e:
        print(f"Error saveing favorite: {e}")
        return jsonify({"success": False}), 500
    return jsonify({"success": False}), 400

@app.route("/delete_favorite/<favorite_id>", methods=["POST"])
def delete_favorite(favorite_id):
    try:
        result = db.favorite_outfits.delete_one({"_id": ObjectId(favorite_id)})
        if result.deleted_count == 1:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Nod found"}), 404
    except Exception as e:
        print(f"Error deleting favorite: {e}")
        return jsonify({"success": False}), 500


@app.route("/outfits")
def outfits_page():
    favorites = [serialize_document(f) for f in db.favorite_outfits.find({})]
    return render_template("outfits.html", favorites=favorites)

@app.route("/history")
def history():
    events = list_history(event_type="worn", limit=50)

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_events = []
    for e in events:
        occurred_at = e.get("occurred_at")
        if occurred_at:
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
            if occurred_at >= seven_days_ago:
                recent_events.append(e)

    serialized_events = [serialize_document(e) for e in recent_events]
    return render_template("history.html", events=serialized_events)


@app.route("/wear/<item_id>", methods=["POST"])
def wear(item_id):
    if get_clothing(item_id) is None:
        abort(404)
    try:
        add_history([item_id], event_type="worn")
        update_care_status(item_id, "needs-wash")
    except (KeyError, ValueError):
        abort(404)

    return redirect(url_for("show_wardrobe"))

@app.route("/wash/<item_id>", methods=["POST"])
def wash_item(item_id):
    if get_clothing(item_id) is None:
        abort(404)
    try:
        update_care_status(item_id, "ready")
    except(KeyError, ValueError):
        abort(404)
    return redirect( url_for("circularity"))

@app.route("/wash_all", methods=["POST"])
def wash_all():
    items = get_all_clothing()
    for item in items:
        if item.get("care_status") == "needs-wash":
            update_care_status(str(item["_id"]), "ready")
    return redirect(url_for("circularity"))


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "GET":
        return render_template("add.html", error=None, item={})

    data, errors = _read_clothing_form(request.form)

    image_url = None
    filepath = None
    file = None

    if "image_file" not in request.files:
        errors.append("No image file provided")
    else:
        file = request.files["image_file"]
        if file.filename == "":
            errors.append("No selected file")
        elif not allowed_file(file.filename):
            errors.append("invalid file type. Use on of the following types: png, jpg, jpeg, webp, gif")
        else:
            filename = secure_filename(file.filename)
            if not filename:
                errors.append("invalid filename")
            else:
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                image_url = f"/static/uploads/{unique_filename}"

    if errors:
        return render_template("add.html", error="; ".join(errors), item=request.form), 400

    if file and filepath:
        file.save(filepath)

    data["image_url"] = image_url

    try:
        add_clothing(data)
    except (ValueError, KeyError) as exc:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
        return render_template("add.html", error="could not save the clothing item, check the information and try again", item=request.form,), 400

    return redirect(url_for("show_wardrobe"))

@app.route("/circularity")
def circularity():
    end_at = datetime.now(timezone.utc)
    start_at = end_at - timedelta(days=7)

    dashboard_data = get_circularity_dashboard(start_at, end_at)
    return render_template("circularity.html", data=dashboard_data)
    
@app.route("/edit/<item_id>", methods=["GET", "POST"])
def edit(item_id):
    item = get_clothing(item_id)
    if item is None:
        abort(404)

    if request.method == "GET":
        return render_template("edit.html", item=serialize_document(item), error=None)

    data, errors = _read_clothing_form(request.form)

    data["is_favorite"] = "is_favorite" in request.form
    data["is_available"] = "is_available" in request.form
    if errors:
        return (
            render_template(
                "edit.html", item=serialize_document(item), error="; ".join(errors)
            ),
            400,
        )

    if data.get("category") is None:
        data.pop("category", None)

    try:
        update_clothing(item_id, data)
    except (ValueError, KeyError) as exc:
        return (
            render_template("edit.html", item=serialize_document(item), error=str(exc)),
            400,
        )

    return redirect(url_for("show_wardrobe"))


@app.route("/delete/<item_id>", methods=["POST"])
def delete(item_id):
    if not delete_clothing(item_id):
        abort(404)
    return redirect(url_for("show_wardrobe"))


@app.route("/recommend")
def recommend():
    raw_temp = request.args.get("temperature")

    def render(*, items=None, error=None, temperature=None, status=200):
        body = render_template("recommend.html", items=items, error=error, temperature=temperature)
        return body, status

    if raw_temp is None:
        return render()

    try:
        temperature = float(raw_temp)
    except ValueError:
        return render(error="temperature must be a number", status=400)

    if not math.isfinite(temperature):
        return render(error="temperature must be finite number", status=400)

    weather_mock = {"temperature_fahrenheit": temperature, "feels_like_dahrenheit": temperature, "unit": "F"}

    try:
        looks = get_outfits(weather_mock, limit=5)
    except Exception as e:
        return render(error="unable to generate recommendations.", status=500)

    return render(items=looks, temperature=temperature)


@app.route("/recommend-today")
def recommend_today():
    location = (request.args.get("location") or "").strip() or None
    occasion = request.args.get("occasion", "casual")
    
    def render(
        *,
        items=None,
        error=None,
        temperature=None,
        place=None,
        description=None,
        status=200,
    ):
        body = render_template(
            "recommend.html",
            items=items,
            error=error,
            temperature=temperature,
            place=place,
            description=description,
        )
        return body, status

    try:
        weather = today_weather(location)
    except WeatherError as exc:
        return render(error=str(exc), status=502)

    temperature = weather.get("temperature_fahrenheit")
    if temperature is None:
        return render(error="weather service returned no temperature", status=502)

    try:
        looks = get_outfits_for_weather(weather, occasion=occasion, limit=5)
    except Exception as e:
        return render(error="could not generate recommendations for this weather.", status=500)

    return render(
        items=looks,
        temperature=temperature,
        place=weather.get("place"),
        description=weather.get("description"),
    )


@app.route("/search")
def search():
    def render(*, items=None, error=None, status=200):
        body = render_template(
            "search.html", items=items, error=error, filters=request.args
        )
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
    min_warmth = _parse_int_arg(
        request.args.get("min_warmth"), "min_warmth", errors, minimum=1, maximum=5
    )
    max_warmth = _parse_int_arg(
        request.args.get("max_warmth"), "max_warmth", errors, minimum=1, maximum=5
    )
    limit = _parse_int_arg(
        request.args.get("limit"), "limit", errors, minimum=1, maximum=50
    )

    exclude_colors = [
        entry.strip().lower()
        for entry in (request.args.get("exclude_colors") or "").split(",")
        if entry.strip()
    ]

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


if __name__ == "__main__":
    app.run(debug=True)
