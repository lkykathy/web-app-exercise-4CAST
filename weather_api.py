import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
openWeather_url = "https://api.openweathermap.org/data/2.5/weather"
Timeout = 5
cache_TTL = 600

_cache = {}

class WeatherError(Exception):
    pass

def autolocate():
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        response.raise_for_status()
        data = response.json()
        city = data.get("city")
        country = data.get("country")
        if city and country:
            return f"{city}, {country}"
    except ValueError:
        pass
    raise WeatherError("could not automatically detect your location")

def _cached(key, producer):
    now = time.monotonic()
    entry = _cache.get(key)
    if entry is not None:
        expires_at, value = entry
        if now < expires_at:
            return value
    value = producer()
    _cache[key] = (now + cache_TTL, value)
    return value

def fetch_weather(location):
    if not API_key:
        raise WeatherError("API key error")
    if not location:
        raise WeatherError("location required")

    def fetch():
        try:
            response = requests.get(
                openWeather_url,
                params={"q": location, "appid": API_key, "units": "imperial"},
                timeout=Timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 401:
                raise WeatherError("Weather API rejected the key (401), check API key") from exc
            if status == 404:
                raise WeatherError(f"Weather API has no data for {location}") from exc
            raise WeatherError("failed to connect to weather service") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherError("weather API returned non-JSON response") from exc
        try:
            return{
                "temperature_fahrenheit": float(payload["main"]["temp"]),
                "feels_like_fahrenheit": float(payload["main"]["feels_like"]),
                "description": (payload["weather"][0]["description"] or "").capitalize(),
                "place": payload.get("name") or location,
            }
        except(KeyError, TypeError, ValueError, IndexError) as exc:
            raise WeatherError("weather API returned malformed data") from exc
    return _cached(("own", location.lower()), fetch)

def today_weather(location=None):
    if not location:
        location=autolocate()
    return fetch_weather(location)

# today_weather will run fetch_weather and will return the following information:
# "temperature_fahrenheit": {temp}
# "feels_like_fahrenheit": {feels_like}
# "description:" {description}
# "place": {name}