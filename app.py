from __future__ import annotations

import os
import datetime as dt
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

import pymysql
import requests
from flask import Flask, jsonify, render_template, request, session
from werkzeug.security import generate_password_hash, check_password_hash


# -----------------------------
# App
# -----------------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")


# -----------------------------
# Config
# -----------------------------
LAT = float(os.getenv("OWM_LAT", "53.3498"))
LON = float(os.getenv("OWM_LON", "-6.2603"))

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_3H_URL = "https://api.openweathermap.org/data/2.5/forecast"
STATIONS_URI = "https://api.jcdecaux.com/vls/v1/stations"

TBL_WEATHER_CURRENT = "weather_current"
TBL_WEATHER_HOURLY = "weather_hourly"
TBL_WEATHER_DAILY = "weather_daily"
TBL_STATION = "station"
TBL_AVAILABILITY = "availability"
TBL_USERS = "users"


# -----------------------------
# Helpers
# -----------------------------
def dt_to_iso(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    return value


def get_jc_cfg() -> tuple[str, str]:
    api_key = os.getenv("JCDECAUX_API_KEY")
    contract = os.getenv("JCDECAUX_CONTRACT", "dublin")

    if api_key:
        return api_key, contract

    try:
        import dbinfo  # type: ignore
        return dbinfo.JCKEY, dbinfo.NAME
    except Exception as e:
        raise RuntimeError(
            "Missing JCDecaux config. Add JCDECAUX_API_KEY to .env or dbinfo.py"
        ) from e


def get_owm_key() -> str:
    key = os.getenv("OWM_API_KEY")
    if key:
        return key

    try:
        import dbinfo  # type: ignore
        return dbinfo.OWM_API_KEY
    except Exception as e:
        raise RuntimeError(
            "Missing OWM config. Set OWM_API_KEY env var or add OWM_API_KEY to dbinfo.py"
        ) from e


def get_db_cfg() -> Dict[str, str]:
    env_user = os.getenv("DB_USER")
    env_pass = os.getenv("DB_PASS")
    env_host = os.getenv("DB_URI")
    env_port = os.getenv("DB_PORT", "3306")
    env_name = os.getenv("DB_NAME")

    if all([env_user, env_pass, env_host, env_port, env_name]):
        return {
            "user": env_user,
            "password": env_pass,
            "host": env_host,
            "port": env_port,
            "database": env_name,
        }

    try:
        import dbinfo  # type: ignore
        return {
            "user": dbinfo.DB_USER,
            "password": dbinfo.DB_PASS,
            "host": dbinfo.DB_URI,
            "port": str(dbinfo.DB_PORT),
            "database": dbinfo.DB_NAME,
        }
    except Exception as e:
        raise RuntimeError(
            "Missing DB config. Set DB_USER/DB_PASS/DB_URI/DB_PORT/DB_NAME env vars or create dbinfo.py"
        ) from e


def get_conn() -> pymysql.connections.Connection:
    cfg = get_db_cfg()
    return pymysql.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=int(cfg["port"]),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def q(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            for r in rows:
                for k, v in list(r.items()):
                    r[k] = dt_to_iso(v)
            return rows


def exec_sql(sql: str, params: Optional[tuple] = None) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            affected = cur.execute(sql, params or ())
            return affected


def http_get_json(url: str, params: Dict[str, Any]) -> Any:
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


# -----------------------------
# Live vendor fetchers
# -----------------------------
def fetch_current_live() -> Dict[str, Any]:
    data = http_get_json(
        OWM_CURRENT_URL,
        {
            "lat": LAT,
            "lon": LON,
            "appid": get_owm_key(),
            "units": "metric",
        },
    )

    rain = data.get("rain", {}) or {}
    snow = data.get("snow", {}) or {}
    weather_list = data.get("weather", []) or [{}]
    main = data.get("main", {}) or {}
    wind = data.get("wind", {}) or {}
    clouds = data.get("clouds", {}) or {}

    return {
        "temp": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "pressure": main.get("pressure"),
        "wind_speed": wind.get("speed"),
        "cloudiness": clouds.get("all"),
        "weather_main": weather_list[0].get("main"),
        "weather_description": weather_list[0].get("description"),
        "rain_1h": rain.get("1h"),
        "snow_1h": snow.get("1h"),
        "source_time": dt.datetime.utcnow().isoformat(),
    }


def fetch_forecast_live_days(max_days: int = 5) -> Dict[str, Any]:
    raw = http_get_json(
        OWM_FORECAST_3H_URL,
        {
            "lat": LAT,
            "lon": LON,
            "appid": get_owm_key(),
            "units": "metric",
        },
    )

    buckets: Dict[str, Dict[str, Any]] = {}

    for item in raw.get("list", []):
        dt_txt = item.get("dt_txt")
        if not dt_txt:
            continue

        date_key = dt_txt[:10]
        main = item.get("main", {}) or {}
        pop = item.get("pop", 0) or 0

        if date_key not in buckets:
            buckets[date_key] = {
                "date": date_key,
                "temp_min": main.get("temp_min"),
                "temp_max": main.get("temp_max"),
                "pop_max": pop,
            }
        else:
            row = buckets[date_key]
            if main.get("temp_min") is not None:
                row["temp_min"] = min(row["temp_min"], main.get("temp_min")) if row["temp_min"] is not None else main.get("temp_min")
            if main.get("temp_max") is not None:
                row["temp_max"] = max(row["temp_max"], main.get("temp_max")) if row["temp_max"] is not None else main.get("temp_max")
            row["pop_max"] = max(row["pop_max"], pop)

    days = list(buckets.values())[:max_days]
    return {"days": days}


# -----------------------------
# DB init helpers
# -----------------------------
def ensure_users_table() -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS {TBL_USERS} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
    exec_sql(sql)


# -----------------------------
# Pages
# -----------------------------
@app.get("/")
def home():
    return render_template("index.html")


@app.get("/dashboard")
def dashboard():
    return render_template(
        "dashboard.html",
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", "")
    )


@app.get("/weather")
def weather_page():
    return render_template("weather.html")


@app.get("/sign-in")
def sign_in():
    return render_template("sign_in.html")


@app.get("/journey-planner")
def journey_planner():
    return render_template("journey_planner.html")


# -----------------------------
# API: health
# -----------------------------
@app.get("/api/ping")
def ping():
    return jsonify({"ok": True, "message": "pong"})


# -----------------------------
# API: live weather
# -----------------------------
@app.get("/api/live/weather/current")
def api_live_weather_current():
    try:
        return jsonify({"ok": True, "source": "openweather", "data": fetch_current_live()})
    except requests.exceptions.HTTPError as e:
        return jsonify({"ok": False, "error": "OpenWeather HTTP error", "detail": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/live/weather/forecast")
def api_live_weather_forecast():
    try:
        max_days = int(request.args.get("days", "5"))
        return jsonify({"ok": True, "source": "openweather", "data": fetch_forecast_live_days(max_days=max_days)})
    except requests.exceptions.HTTPError as e:
        return jsonify({"ok": False, "error": "OpenWeather HTTP error", "detail": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/weather/current")
def api_weather_current_alias():
    return api_live_weather_current()


@app.get("/api/weather/forecast")
def api_weather_forecast_alias():
    return api_live_weather_forecast()


# -----------------------------
# API: bikes from DB
# -----------------------------
@app.get("/api/bike/all")
def api_bike_all():
    sql = f"""
        SELECT
            s.number AS station_id,
            s.name AS name,
            s.address AS address,
            s.position_lat AS latitude,
            s.position_lng AS longitude,
            s.banking AS banking,
            s.bikestands AS station_capacity,
            COALESCE(a.total_bike_stands, s.bikestands) AS capacity,
            a.available_bikes AS available_bikes,
            a.available_bike_stands AS available_bike_stands,
            a.last_update AS last_update,
            a.status AS status,
            a.mechanical_bikes AS mechanical_bikes,
            a.electrical_bikes AS electrical_bikes,
            s.bonus AS bonus,
            s.overflow AS overflow
        FROM {TBL_STATION} s
        LEFT JOIN (
            SELECT a1.*
            FROM {TBL_AVAILABILITY} a1
            INNER JOIN (
                SELECT number, MAX(last_update) AS max_last_update
                FROM {TBL_AVAILABILITY}
                GROUP BY number
            ) latest
            ON a1.number = latest.number
            AND a1.last_update = latest.max_last_update
        ) a
        ON s.number = a.number
        ORDER BY s.number ASC
    """
    rows = q(sql)
    return jsonify({"ok": True, "count": len(rows), "rows": rows})


@app.get("/api/bike/history")
def api_bike_history():
    number = request.args.get("number")
    if not number:
        return jsonify({"ok": False, "error": "Missing required query parameter: number"}), 400

    hours = int(request.args.get("hours", "48"))

    sql = f"""
        SELECT
            number AS station_id,
            available_bikes AS available_bikes,
            available_bike_stands AS available_bike_stands,
            last_update AS timestamp,
            status AS status,
            mechanical_bikes AS mechanical_bikes,
            electrical_bikes AS electrical_bikes,
            total_bike_stands AS capacity
        FROM {TBL_AVAILABILITY}
        WHERE number = %s
          AND last_update >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
        ORDER BY last_update ASC
    """
    rows = q(sql, (int(number), hours))

    return jsonify({
        "ok": True,
        "station_id": int(number),
        "hours": hours,
        "count": len(rows),
        "rows": rows
    })


@app.get("/api/db/bikes/hourly_avg/<int:station_id>")
def api_db_bikes_hourly_avg(station_id: int):
    hours = int(request.args.get("hours", "48"))

    sql = f"""
        SELECT
            number AS station_id,
            DATE_FORMAT(last_update, '%%Y-%%m-%%d %%H:00:00') AS hour_bucket,
            AVG(available_bikes) AS avg_bikes,
            AVG(available_bike_stands) AS avg_stands,
            AVG(total_bike_stands) AS avg_capacity,
            COUNT(*) AS sample_count
        FROM {TBL_AVAILABILITY}
        WHERE number = %s
          AND last_update >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
        GROUP BY number, DATE_FORMAT(last_update, '%%Y-%%m-%%d %%H:00:00')
        ORDER BY hour_bucket ASC
    """
    rows = q(sql, (station_id, hours))
    return jsonify({
        "ok": True,
        "station_id": station_id,
        "hours": hours,
        "count": len(rows),
        "rows": rows
    })


# -----------------------------
# API: auth
# -----------------------------
@app.post("/api/auth/register")
def api_auth_register():
    try:
        ensure_users_table()

        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip().lower()
        password = data.get("password") or ""

        if not username or not password:
            return jsonify({"ok": False, "error": "Username and password are required."}), 400

        if len(password) < 6:
            return jsonify({"ok": False, "error": "Password must be at least 6 characters."}), 400

        existing = q(f"SELECT id FROM {TBL_USERS} WHERE username = %s", (username,))
        if existing:
            return jsonify({"ok": False, "error": "Username already exists."}), 409

        password_hash = generate_password_hash(password)

        exec_sql(
            f"INSERT INTO {TBL_USERS} (username, password_hash) VALUES (%s, %s)",
            (username, password_hash)
        )

        session["username"] = username

        return jsonify({
            "ok": True,
            "message": "Registration successful.",
            "user": {"username": username}
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/auth/login")
def api_auth_login():
    try:
        ensure_users_table()

        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip().lower()
        password = data.get("password") or ""

        if not username or not password:
            return jsonify({"ok": False, "error": "Username and password are required."}), 400

        rows = q(f"SELECT * FROM {TBL_USERS} WHERE username = %s LIMIT 1", (username,))
        if not rows:
            return jsonify({"ok": False, "error": "Invalid username or password."}), 401

        user = rows[0]
        if not check_password_hash(user["password_hash"], password):
            return jsonify({"ok": False, "error": "Invalid username or password."}), 401

        session["username"] = username

        return jsonify({
            "ok": True,
            "message": "Login successful.",
            "user": {"username": username}
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/auth/logout")
def api_auth_logout():
    session.pop("username", None)
    return jsonify({"ok": True, "message": "Logged out."})


@app.get("/api/auth/me")
def api_auth_me():
    username = session.get("username")
    if not username:
        return jsonify({"ok": True, "authenticated": False, "user": None})
    return jsonify({
        "ok": True,
        "authenticated": True,
        "user": {"username": username}
    })


# -----------------------------
# API: analytics
# -----------------------------
@app.get("/api/analytics/weather-impact/<int:station_id>")
def api_analytics_weather_impact(station_id: int):
    sql = f"""
        SELECT
            w.weather_main,
            w.weather_description,
            ROUND(AVG(a.available_bikes), 2) AS avg_bikes,
            ROUND(AVG(a.available_bike_stands), 2) AS avg_stands,
            COUNT(*) AS sample_count
        FROM {TBL_AVAILABILITY} a
        JOIN {TBL_WEATHER_CURRENT} w
          ON ABS(TIMESTAMPDIFF(MINUTE, a.last_update, w.dt)) <= 10
        WHERE a.number = %s
        GROUP BY w.weather_main, w.weather_description
        ORDER BY sample_count DESC, avg_bikes DESC
    """
    rows = q(sql, (station_id,))
    return jsonify({
        "ok": True,
        "station_id": station_id,
        "count": len(rows),
        "rows": rows
    })


@app.get("/api/analytics/busiest-hours")
def api_analytics_busiest_hours():
    sql = f"""
        SELECT
            DATE_FORMAT(last_update, '%%H:00') AS hour_of_day,
            ROUND(AVG(total_bike_stands - available_bike_stands), 2) AS avg_bikes_in_use,
            COUNT(*) AS sample_count
        FROM {TBL_AVAILABILITY}
        GROUP BY DATE_FORMAT(last_update, '%%H:00')
        ORDER BY hour_of_day ASC
    """
    rows = q(sql)
    return jsonify({"ok": True, "count": len(rows), "rows": rows})


# -----------------------------
# API: assistant (rule-based MVP)
# -----------------------------
@app.post("/api/assistant/recommend")
def api_assistant_recommend():
    try:
        data = request.get_json(silent=True) or {}
        station_id = data.get("station_id")

        weather = fetch_current_live()
        stations = q(f"""
            SELECT
                s.number AS station_id,
                s.name,
                s.address,
                s.position_lat AS latitude,
                s.position_lng AS longitude,
                COALESCE(a.total_bike_stands, s.bikestands) AS capacity,
                a.available_bikes,
                a.available_bike_stands,
                a.status
            FROM {TBL_STATION} s
            LEFT JOIN (
                SELECT a1.*
                FROM {TBL_AVAILABILITY} a1
                INNER JOIN (
                    SELECT number, MAX(last_update) AS max_last_update
                    FROM {TBL_AVAILABILITY}
                    GROUP BY number
                ) latest
                ON a1.number = latest.number
                AND a1.last_update = latest.max_last_update
            ) a
            ON s.number = a.number
            ORDER BY s.number ASC
        """)

        if not stations:
            return jsonify({"ok": False, "error": "No station data available."}), 404

        selected = None
        if station_id is not None:
            for s in stations:
                if int(s["station_id"]) == int(station_id):
                    selected = s
                    break

        if selected is None:
            selected = max(
                stations,
                key=lambda x: int(x["available_bikes"] or 0)
            )

        bikes = int(selected.get("available_bikes") or 0)
        docks = int(selected.get("available_bike_stands") or 0)
        condition = (weather.get("weather_description") or "unknown weather").lower()
        temp = weather.get("temp")

        advice_parts = []

        if bikes == 0:
            advice_parts.append(
                f"{selected['name']} currently has no bikes available, so it is not a good pickup station right now."
            )
        elif bikes < 3:
            advice_parts.append(
                f"{selected['name']} has only {bikes} bikes available, so availability is limited."
            )
        else:
            advice_parts.append(
                f"{selected['name']} looks like a reasonable pickup station with {bikes} bikes available."
            )

        if docks < 3:
            advice_parts.append(
                f"If you plan to return a bike there later, dock space may be tight because only {docks} stands are free."
            )
        else:
            advice_parts.append(
                f"It also has {docks} free docks, so return availability is acceptable."
            )

        if "rain" in condition or "drizzle" in condition:
            advice_parts.append(
                f"The current weather suggests {condition}, so bringing waterproof clothing would be a good idea."
            )
        elif temp is not None and float(temp) <= 5:
            advice_parts.append(
                f"It is quite cold at about {temp}°C, so extra layers would help."
            )
        else:
            advice_parts.append(
                f"The current weather is {condition}, which is generally manageable for cycling."
            )

        advice = " ".join(advice_parts)

        return jsonify({
            "ok": True,
            "station": selected,
            "weather": weather,
            "advice": advice
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    ensure_users_table()
    app.run(debug=True)