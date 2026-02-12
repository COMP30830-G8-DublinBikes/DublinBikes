import os
import datetime
import requests
import dbinfo
from sqlalchemy import create_engine

engine = create_engine(
    "mysql+pymysql://{}:{}@{}:{}/{}".format(
        dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT, dbinfo.DB_NAME
    )
)

OWM_API_KEY = os.environ.get("OWM_API_KEY")
LAT = 53.3498
LON = -6.2603

CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def fetch_current():
    if not OWM_API_KEY:
        raise RuntimeError("Missing OWM_API_KEY. Run: export OWM_API_KEY='your_key'")
    params = {"lat": LAT, "lon": LON, "appid": OWM_API_KEY, "units": "metric"}
    r = requests.get(CURRENT_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_precip_prob():
    params = {"lat": LAT, "lon": LON, "appid": OWM_API_KEY, "units": "metric"}
    r = requests.get(FORECAST_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("list"):
        return None
    pop = data["list"][0].get("pop")  # 0..1
    return None if pop is None else float(pop)


def insert_weather(current_data, precip_prob):
    observation_time = datetime.datetime.fromtimestamp(current_data["dt"], datetime.UTC).replace(tzinfo=None)

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
    current = fetch_current()
    pop = fetch_precip_prob()
    t = insert_weather(current, pop)
    print(f"[OK] Inserted 1 row into DB at UTC {t}, precip_prob={pop}")


if __name__ == "__main__":
    main()

