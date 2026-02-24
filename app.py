from __future__ import annotations

import os
import datetime as dt
from typing import Any, Dict, List, Optional

import pymysql
import requests
from flask import Flask, jsonify, render_template, request

# -----------------------------
# App + basic config
# -----------------------------
app = Flask(__name__)

# Default to Dublin city centre. You can override via env vars if needed.
LAT = float(os.getenv("OWM_LAT", "53.3498"))
LON = float(os.getenv("OWM_LON", "-6.2603"))

# OpenWeather endpoints we can access with the standard free/student API key
OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_3H_URL = "https://api.openweathermap.org/data/2.5/forecast"  # 5 day / 3 hour

# Your DB schema/table names (matching what you created in MySQL)
DB_SCHEMA = os.getenv("DB_NAME")  # optional; if None, we still connect to the dbinfo.DB_NAME database
TBL_WEATHER_CURRENT = "weather_current"
TBL_WEATHER_HOURLY = "weather_hourly"
TBL_WEATHER_DAILY = "weather_daily"
TBL_STATION = "station"
TBL_AVAILABILITY = "availability"


# -----------------------------
# Helpers: time + JSON
# -----------------------------

def utcnow_naive() -> dt.datetime:
    """Return naive UTC datetime suitable for MySQL DATETIME."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def dt_to_iso(x: Any) -> Any:
    """Convert datetimes to ISO strings so jsonify() works."""
    if isinstance(x, (dt.datetime, dt.date)):
        return x.isoformat()
    return x


# -----------------------------
# Helpers: OpenWeather
# -----------------------------

def get_owm_key() -> str:
    key = os.getenv("OWM_API_KEY")
    if not key:
        raise RuntimeError("Missing OWM_API_KEY")
    return key


def http_get_json(url: str, params: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


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

    return {
        "temp": data.get("main", {}).get("temp"),
        "feels_like": data.get("main", {}).get("feels_like"),
        "humidity": data.get("main", {}).get("humidity"),
        "pressure": data.get("main", {}).get("pressure"),
        "wind_speed": data.get("wind", {}).get("speed"),
        "cloudiness": data.get("clouds", {}).get("all"),
        "weather_main": (data.get("weather") or [{}])[0].get("main"),
        "weather_description": (data.get("weather") or [{}])[0].get("description"),
        "rain_1h": (data.get("rain") or {}).get("1h", 0.0),
        "snow_1h": (data.get("snow") or {}).get("1h", 0.0),
    }


def fetch_forecast_live_days(max_days: int = 7) -> Dict[str, Any]:
    """Build a simple day-level forecast from the 5-day/3-hour endpoint.

    Note: /data/2.5/forecast returns ~5 days. We still expose it as "days".
    """
    data = http_get_json(
        OWM_FORECAST_3H_URL,
        {
            "lat": LAT,
            "lon": LON,
            "appid": get_owm_key(),
            "units": "metric",
        },
    )

    daily: Dict[str, Dict[str, Any]] = {}
    for item in data.get("list", []):
        dt_txt = item.get("dt_txt")
        if not dt_txt:
            continue
        day = dt_txt.split(" ")[0]

        main = item.get("main", {})
        tmin = main.get("temp_min")
        tmax = main.get("temp_max")
        pop = item.get("pop", 0.0)  # precipitation probability

        if day not in daily:
            daily[day] = {"temp_min": tmin, "temp_max": tmax, "pop_max": pop}
        else:
            if tmin is not None:
                daily[day]["temp_min"] = tmin if daily[day]["temp_min"] is None else min(daily[day]["temp_min"], tmin)
            if tmax is not None:
                daily[day]["temp_max"] = tmax if daily[day]["temp_max"] is None else max(daily[day]["temp_max"], tmax)
            daily[day]["pop_max"] = max(float(daily[day]["pop_max"] or 0.0), float(pop or 0.0))

    out: List[Dict[str, Any]] = []
    for day in sorted(daily.keys())[:max_days]:
        out.append({"date": day, **daily[day]})

    return {"days": out}


# -----------------------------
# Helpers: MySQL DB access (read-only for Flask)
# -----------------------------

def get_db_cfg() -> Dict[str, str]:
    """Read DB config from env vars first, then fallback to local dbinfo.py.

    dbinfo.py is local-only (gitignored) and usually contains DB_USER/DB_PASS/DB_URI/DB_PORT/DB_NAME.
    """
    env_user = os.getenv("DB_USER")
    env_pass = os.getenv("DB_PASS")
    env_host = os.getenv("DB_URI")
    env_port = os.getenv("DB_PORT")
    env_name = os.getenv("DB_NAME")

    if all([env_user, env_pass, env_host, env_port, env_name]):
        return {
            "user": env_user,
            "password": env_pass,
            "host": env_host,
            "port": env_port,
            "database": env_name,
        }

    # fallback: dbinfo.py
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
            # convert datetime/date to ISO
            for r in rows:
                for k, v in list(r.items()):
                    r[k] = dt_to_iso(v)
            return rows


# -----------------------------
# Pages
# -----------------------------


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/sign-in")
def sign_in():
    return render_template("sign_in.html")


@app.get("/weather")
def weather_page():
    return render_template("weather.html")


# -----------------------------
# API: health
# -----------------------------


@app.get("/api/ping")
def ping():
    return jsonify({"ok": True, "message": "pong"})


# -----------------------------
# API: LIVE (direct vendor calls)
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
        max_days = int(request.args.get("days", "7"))
        return jsonify({"ok": True, "source": "openweather", "data": fetch_forecast_live_days(max_days=max_days)})
    except requests.exceptions.HTTPError as e:
        return jsonify({"ok": False, "error": "OpenWeather HTTP error", "detail": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# Backwards-compatible aliases (so your frontend doesn't break if it used the earlier paths)
@app.get("/api/weather/current")
def api_weather_current_alias():
    return api_live_weather_current()


@app.get("/api/weather/forecast")
def api_weather_forecast_alias():
    return api_live_weather_forecast()


# -----------------------------
# API: DB (read stored historical data)
# -----------------------------


@app.get("/api/db/weather/current")
def api_db_weather_current():
    """Return stored weather_current rows (default: last 48 hours)."""
    hours = int(request.args.get("hours", "48"))
    limit = int(request.args.get("limit", "2000"))

    sql = f"""
        SELECT *
        FROM {TBL_WEATHER_CURRENT}
        WHERE dt >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
        ORDER BY dt DESC
        LIMIT %s
    """
    rows = q(sql, (hours, limit))
    return jsonify({"ok": True, "source": "db", "hours": hours, "count": len(rows), "rows": rows})


@app.get("/api/db/weather/hourly")
def api_db_weather_hourly():
    """Return stored weather_hourly rows.

    - hours: time window (default 48)
    - limit: max rows
    """
    hours = int(request.args.get("hours", "48"))
    limit = int(request.args.get("limit", "3000"))

    sql = f"""
        SELECT *
        FROM {TBL_WEATHER_HOURLY}
        WHERE dt >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
        ORDER BY dt DESC, future_dt DESC
        LIMIT %s
    """
    rows = q(sql, (hours, limit))
    return jsonify({"ok": True, "source": "db", "hours": hours, "count": len(rows), "rows": rows})


@app.get("/api/db/weather/daily")
def api_db_weather_daily():
    """Return stored weather_daily rows (default: next 7 days)."""
    days = int(request.args.get("days", "7"))
    sql = f"""
        SELECT *
        FROM {TBL_WEATHER_DAILY}
        WHERE future_date >= UTC_DATE()
        ORDER BY future_date ASC
        LIMIT %s
    """
    rows = q(sql, (days,))
    return jsonify({"ok": True, "source": "db", "days": days, "count": len(rows), "rows": rows})


@app.get("/api/db/bikes/stations")
def api_db_stations():
    """Return station metadata from DB (for map markers later)."""
    limit = int(request.args.get("limit", "200"))
    sql = f"SELECT * FROM {TBL_STATION} ORDER BY number ASC LIMIT %s"
    rows = q(sql, (limit,))
    return jsonify({"ok": True, "source": "db", "count": len(rows), "rows": rows})


@app.get("/api/db/bikes/availability")
def api_db_availability():
    """Return availability history from DB.

    You can filter by station number:
      /api/db/bikes/availability?number=42&hours=48
    """
    hours = int(request.args.get("hours", "48"))
    limit = int(request.args.get("limit", "5000"))
    number = request.args.get("number")

    if number:
        sql = f"""
            SELECT *
            FROM {TBL_AVAILABILITY}
            WHERE number = %s
              AND last_update >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
            ORDER BY last_update DESC
            LIMIT %s
        """
        rows = q(sql, (int(number), hours, limit))
    else:
        sql = f"""
            SELECT *
            FROM {TBL_AVAILABILITY}
            WHERE last_update >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
            ORDER BY last_update DESC
            LIMIT %s
        """
        rows = q(sql, (hours, limit))

    return jsonify({"ok": True, "source": "db", "hours": hours, "count": len(rows), "rows": rows})


# -----------------------------
# Main
# -----------------------------


if __name__ == "__main__":
    # 0.0.0.0 is useful on EC2 later; locally 127.0.0.1 is fine.
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "true").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)