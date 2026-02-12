import os
import time
import datetime
import traceback
import requests
import dbinfo
from sqlalchemy import create_engine

# --- DB connection ---
engine = create_engine(
    "mysql+pymysql://{}:{}@{}:{}/{}".format(
        dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT, dbinfo.DB_NAME
    )
)

# --- OpenWeather settings ---
OWM_API_KEY = os.environ.get("OWM_API_KEY")
LAT = 53.3498
LON = -6.2603

CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

SLEEP_SECONDS = 30 * 60   # FINAL: 30 minutes


def fetch_json(url: str) -> dict:
    if not OWM_API_KEY:
        raise RuntimeError("Missing OWM_API_KEY. Run: export OWM_API_KEY='your_key'")
    params = {"lat": LAT, "lon": LON, "appid": OWM_API_KEY, "units": "metric"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def get_precip_prob(forecast_data: dict):
    # forecast returns 3-hour steps; pop is 0..1
    if not forecast_data.get("list"):
        return None
    pop = forecast_data["list"][0].get("pop")
    return None if pop is None else float(pop)


def latest_observation_time():
    """Return the latest observation_time already stored in DB, or None."""
    sql = "SELECT observation_time FROM weather ORDER BY observation_time DESC LIMIT 1"
    with engine.begin() as conn:
        row = conn.exec_driver_sql(sql).fetchone()
    return row[0] if row else None


def build_observation_time(current_data: dict) -> datetime.datetime:
    # timezone-aware UTC -> convert to naive for MySQL DATETIME
    return datetime.datetime.fromtimestamp(current_data["dt"], datetime.UTC).replace(tzinfo=None)


def insert_weather(current_data: dict, precip_prob):
    observation_time = build_observation_time(current_data)

    temperature = current_data["main"].get("temp")
    feels_like = current_data["main"].get("feels_like")
    humidity = current_data["main"].get("humidity")
    pressure = current_data["main"].get("pressure")
    wind_speed = (current_data.get("wind") or {}).get("speed")
    cloudiness = (current_data.get("clouds") or {}).get("all")

    weather_main = None
    weather_description = None
    if current_data.get("weather"):
        weather_main = current_data["weather"][0].get("main")
        weather_description = current_data["weather"][0].get("description")

    rain_1h = (current_data.get("rain") or {}).get("1h")

    sql = """
    INSERT INTO weather (
        observation_time,
        temperature,
        feels_like,
        precip_prob,
        humidity,
        pressure,
        wind_speed,
        weather_main,
        weather_description,
        rain_1h,
        cloudiness
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    vals = (
        observation_time,
        temperature,
        feels_like,
        precip_prob,
        humidity,
        pressure,
        wind_speed,
        weather_main,
        weather_description,
        rain_1h,
        cloudiness,
    )

    with engine.begin() as conn:
        conn.exec_driver_sql(sql, vals)

    return observation_time


def main():
    print(f"[START] Weather scraper. DB={dbinfo.DB_NAME}, interval={SLEEP_SECONDS}s")

    while True:
        try:
            current = fetch_json(CURRENT_URL)

            # Compute observation time from API payload
            obs_time = build_observation_time(current)

            # De-dup: if API dt hasn't changed, skip insert (prevents duplicates)
            latest = latest_observation_time()
            if latest is not None and latest == obs_time:
                print(f"[SKIP] observation_time unchanged: {obs_time} UTC")
            else:
                forecast = fetch_json(FORECAST_URL)
                pop = get_precip_prob(forecast)

                inserted_time = insert_weather(current, pop)

                if pop is not None and pop >= 0.7:
                    print(f"[OK] {inserted_time} UTC inserted. precip_prob={pop:.2f} (>=0.70 WARNING)")
                else:
                    print(f"[OK] {inserted_time} UTC inserted. precip_prob={pop}")

        except Exception:
            print("[ERROR] scrape failed:")
            print(traceback.format_exc())

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
