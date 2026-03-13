from __future__ import annotations

import os
import datetime as dt
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()  # read .env 

import pymysql
import requests
from flask import Flask, jsonify, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash


# -----------------------------
# App
# -----------------------------
app = Flask(__name__)
# Session key , load from env，on EC2 should set a random string 
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")


# -----------------------------
# Config: OpenWeather 座標
# -----------------------------
LAT = float(os.getenv("OWM_LAT", "53.3498"))
LON = float(os.getenv("OWM_LON", "-6.2603"))

# OpenWeather endpoints
OWM_CURRENT_URL   = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_3H_URL = "https://api.openweathermap.org/data/2.5/forecast"

# JCDecaux endpoint
STATIONS_URI = "https://api.jcdecaux.com/vls/v1/stations"

# DB table names
TBL_WEATHER_CURRENT = "weather_current"
TBL_WEATHER_HOURLY  = "weather_hourly"
TBL_WEATHER_DAILY   = "weather_daily"
TBL_STATION         = "station"
TBL_AVAILABILITY    = "availability"
TBL_USERS           = "users"



# ==============================
# Helpers: API Key / Config 讀取
# 優先讀 .env（環境變數），沒有才 fallback 到 dbinfo.py
# ==============================


def get_jc_cfg() -> tuple[str, str]:
    """取得 JCDecaux API key 和 contract name"""
    api_key  = os.getenv("JCDECAUX_API_KEY")
    contract = os.getenv("JCDECAUX_CONTRACT", "dublin")

    if api_key:
        return api_key, contract

    # fallback: dbinfo.py（本地開發備用）
    try:
        import dbinfo  # type: ignore
        return dbinfo.JCKEY, dbinfo.NAME
    except Exception as e:
        raise RuntimeError(
            "Missing JCDecaux config. Add JCDECAUX_API_KEY to .env or dbinfo.py"
        ) from e


def get_owm_key() -> str:
    """取得 OpenWeather API key"""
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
    """取得資料庫連線設定"""
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


# -----------------------------
# Helpers: 時間 + JSON
# -----------------------------

def utcnow_naive() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def dt_to_iso(x: Any) -> Any:
    if isinstance(x, (dt.datetime, dt.date)):
        return x.isoformat()
    return x


# -----------------------------
# Helpers: HTTP
# -----------------------------

def http_get_json(url: str, params: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


# -----------------------------
# Helpers: OpenWeather
# -----------------------------

def fetch_current_live() -> Dict[str, Any]:
    data = http_get_json(
        OWM_CURRENT_URL,
        {"lat": LAT, "lon": LON, "appid": get_owm_key(), "units": "metric"},
    )
    return {
        "temp":                data.get("main", {}).get("temp"),
        "feels_like":          data.get("main", {}).get("feels_like"),
        "humidity":            data.get("main", {}).get("humidity"),
        "pressure":            data.get("main", {}).get("pressure"),
        "wind_speed":          data.get("wind", {}).get("speed"),
        "cloudiness":          data.get("clouds", {}).get("all"),
        "weather_main":        (data.get("weather") or [{}])[0].get("main"),
        "weather_description": (data.get("weather") or [{}])[0].get("description"),
        "rain_1h":             (data.get("rain") or {}).get("1h", 0.0),
        "snow_1h":             (data.get("snow") or {}).get("1h", 0.0),
    }


def fetch_forecast_live_days(max_days: int = 7) -> Dict[str, Any]:
    data = http_get_json(
        OWM_FORECAST_3H_URL,
        {"lat": LAT, "lon": LON, "appid": get_owm_key(), "units": "metric"},
    )

    daily: Dict[str, Dict[str, Any]] = {}
    for item in data.get("list", []):
        dt_txt = item.get("dt_txt")
        if not dt_txt:
            continue
        day  = dt_txt.split(" ")[0]
        main = item.get("main", {})
        tmin = main.get("temp_min")
        tmax = main.get("temp_max")
        pop  = item.get("pop", 0.0)

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
# Helpers: MySQL (read-only)
# -----------------------------

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


# ==============================
# 頁面路由
# ==============================

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/sign-in")
def sign_in():
    return render_template("sign_in.html")

@app.get("/weather")
def weather_page():
    return render_template("weather.html")

@app.get("/about")
def about():
    return render_template("about.html")


# ==============================
# API: 健康檢查
# ==============================

@app.get("/api/ping")
def ping():
    return jsonify({"ok": True, "message": "pong"})


# ==============================
# API: LIVE — 即時向外部 API 取資料
# ==============================

# --- Weather ---

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

# 向下相容的舊路徑 alias
@app.get("/api/weather/current")
def api_weather_current_alias():
    return api_live_weather_current()

@app.get("/api/weather/forecast")
def api_weather_forecast_alias():
    return api_live_weather_forecast()


# --- Bike (JCDecaux 即時) ---

@app.get("/api/live/bike/current")
@app.route("/api/bike/current")   # 向下相容舊路徑
def get_bike_data():
    try:
        api_key, contract = get_jc_cfg()
        data = http_get_json(STATIONS_URI, {"contract": contract, "apiKey": api_key})
        return jsonify({"ok": True, "source": "jcdecaux", "data": data})
    except requests.exceptions.HTTPError as e:
        return jsonify({"ok": False, "error": "JCDecaux HTTP error", "detail": str(e)}), 502
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ==============================
# API: DB — 從資料庫讀歷史資料
# ==============================

# --- Weather DB ---

@app.get("/api/db/weather/current")
def api_db_weather_current():
    hours = int(request.args.get("hours", "48"))
    limit = int(request.args.get("limit", "2000"))
    sql = f"""
        SELECT * FROM {TBL_WEATHER_CURRENT}
        WHERE dt >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
        ORDER BY dt DESC LIMIT %s
    """
    rows = q(sql, (hours, limit))
    return jsonify({"ok": True, "source": "db", "hours": hours, "count": len(rows), "rows": rows})

@app.get("/api/db/weather/hourly")
def api_db_weather_hourly():
    hours = int(request.args.get("hours", "48"))
    limit = int(request.args.get("limit", "3000"))
    sql = f"""
        SELECT * FROM {TBL_WEATHER_HOURLY}
        WHERE dt >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
        ORDER BY dt DESC, future_dt DESC LIMIT %s
    """
    rows = q(sql, (hours, limit))
    return jsonify({"ok": True, "source": "db", "hours": hours, "count": len(rows), "rows": rows})

@app.get("/api/db/weather/daily")
def api_db_weather_daily():
    days  = int(request.args.get("days", "7"))
    sql = f"""
        SELECT * FROM {TBL_WEATHER_DAILY}
        WHERE future_date >= UTC_DATE()
        ORDER BY future_date ASC LIMIT %s
    """
    rows = q(sql, (days,))
    return jsonify({"ok": True, "source": "db", "days": days, "count": len(rows), "rows": rows})


# --- Bike DB ---

@app.get("/api/db/bikes/stations")
def api_db_stations():
    limit = int(request.args.get("limit", "200"))
    sql   = f"SELECT * FROM {TBL_STATION} ORDER BY number ASC LIMIT %s"
    rows  = q(sql, (limit,))
    return jsonify({"ok": True, "source": "db", "count": len(rows), "rows": rows})

@app.get("/api/db/bikes/availability")
def api_db_availability():
    hours  = int(request.args.get("hours", "48"))
    limit  = int(request.args.get("limit", "5000"))
    number = request.args.get("number")

    if number:
        sql  = f"""
            SELECT * FROM {TBL_AVAILABILITY}
            WHERE number = %s
              AND last_update >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
            ORDER BY last_update DESC LIMIT %s
        """
        rows = q(sql, (int(number), hours, limit))
    else:
        sql  = f"""
            SELECT * FROM {TBL_AVAILABILITY}
            WHERE last_update >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
            ORDER BY last_update DESC LIMIT %s
        """
        rows = q(sql, (hours, limit))

    return jsonify({"ok": True, "source": "db", "hours": hours, "count": len(rows), "rows": rows})

# 向下相容：/api/bike/history/<id> → 等同於 /api/db/bikes/availability?number=<id>&limit=10
@app.get("/api/bike/history/<int:station_id>")
def get_bike_history(station_id: int):
    sql  = f"""
        SELECT * FROM {TBL_AVAILABILITY}
        WHERE number = %s
        ORDER BY last_update DESC LIMIT 10
    """
    rows = q(sql, (station_id,))
    return jsonify({"ok": True, "source": "db", "history": rows})


@app.get("/api/db/bikes/hourly_avg/<int:station_id>")
def get_hourly_avg(station_id: int):
    """
    Member B 核心任務：API 重構
    將每 5 分鐘一筆的數據聚合為每小時平均值，方便前端 Chart.js 繪圖。
    """
    hours = int(request.args.get("hours", "48"))
    sql = f"""
        SELECT 
            DATE_FORMAT(last_update, '%%Y-%%m-%%d %%H:00:00') AS hour_group,
            ROUND(AVG(available_bikes), 1)                     AS avg_bikes,
            ROUND(AVG(available_bike_stands), 1)               AS avg_stands,
            COUNT(*)                                           AS sample_count
        FROM {TBL_AVAILABILITY}
        WHERE number = %s 
          AND last_update >= (UTC_TIMESTAMP() - INTERVAL %s HOUR)
        GROUP BY hour_group
        ORDER BY hour_group ASC
    """
    rows = q(sql, (station_id, hours))
    return jsonify({"ok": True, "station_id": station_id, "hours": hours, "data": rows})

# ==============================
# Task 2: Advanced SQL
# ==============================

@app.get("/api/analytics/weather-impact/<int:station_id>")
def get_weather_impact(station_id: int):
    """
    Member B 核心任務：進階 SQL 查詢
    關聯天氣與單車數據，分析不同天氣對該車站可用數量的影響。
    """
    sql = f"""
        SELECT 
            w.weather_main, 
            ROUND(AVG(a.available_bikes), 1)       AS avg_bikes,
            ROUND(AVG(a.available_bike_stands), 1) AS avg_stands,
            COUNT(*)                               AS sample_size
        FROM {TBL_AVAILABILITY} AS a
        JOIN {TBL_WEATHER_CURRENT} AS w 
          ON ABS(TIMESTAMPDIFF(MINUTE, a.last_update, w.dt)) < 10
        WHERE a.number = %s
        GROUP BY w.weather_main
        ORDER BY avg_bikes DESC
    """
    rows = q(sql, (station_id,))
    return jsonify({"ok": True, "impact": rows})

@app.get("/api/analytics/busiest-hours")
def get_busiest_hours():
    """
    進階查詢：分析全市所有車站一天中各時段的平均佔用率。
    佔用率 = 已被騎走的車 / 總容量，越高代表越多人在用。

    回傳範例：
      { "ok": true, "data": [
          {"hour": 8, "avg_occupancy_pct": 72.3, "sample_size": 840},
          {"hour": 17, "avg_occupancy_pct": 68.1, "sample_size": 820},
          ...
      ]}
    """
    sql = f"""
        SELECT 
            HOUR(last_update) AS hour,
            ROUND(
                AVG(
                    CASE 
                        WHEN (available_bikes + available_bike_stands) > 0
                        THEN (1 - available_bikes / (available_bikes + available_bike_stands)) * 100
                        ELSE NULL
                    END
                ), 1
            ) AS avg_occupancy_pct,
            COUNT(*) AS sample_size
        FROM {TBL_AVAILABILITY}
        WHERE last_update >= (UTC_TIMESTAMP() - INTERVAL 7 DAY)
        GROUP BY hour
        ORDER BY hour ASC
    """
    rows = q(sql, ())
    return jsonify({"ok": True, "data": rows})


# ==============================
# Task 2 Bonus: User Login
# ==============================

@app.post("/api/auth/register")
def register():
    """
    註冊新使用者。
    Request JSON: { "username": "alice", "password": "mypassword123" }

    密碼用 werkzeug generate_password_hash 雜湊後儲存，絕不存明文。
    需要在 DB 建立 users 資料表（見下方 SQL）。
    """
    body     = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "username and password are required"}), 400

    if len(password) < 8:
        return jsonify({"ok": False, "error": "password must be at least 8 characters"}), 400

    existing = q(f"SELECT id FROM {TBL_USERS} WHERE username = %s LIMIT 1", (username,))
    if existing:
        return jsonify({"ok": False, "error": "username already taken"}), 409

    hashed = generate_password_hash(password)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {TBL_USERS} (username, password_hash, created_at) VALUES (%s, %s, %s)",
                (username, hashed, utcnow_naive()),
            )

    return jsonify({"ok": True, "message": f"User '{username}' registered successfully"}), 201


@app.post("/api/auth/login")
def login():
    """
    登入。
    Request JSON: { "username": "alice", "password": "mypassword123" }
    成功後把 user_id / username 存入 Flask session（加密 cookie）。
    """
    body     = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "username and password are required"}), 400

    rows = q(f"SELECT id, password_hash FROM {TBL_USERS} WHERE username = %s LIMIT 1", (username,))
    if not rows or not check_password_hash(rows[0]["password_hash"], password):
        return jsonify({"ok": False, "error": "invalid username or password"}), 401

    session["user_id"]  = rows[0]["id"]
    session["username"] = username
    return jsonify({"ok": True, "message": f"Welcome, {username}!"})


@app.post("/api/auth/logout")
def logout():
    """登出，清除 session"""
    session.clear()
    return jsonify({"ok": True, "message": "Logged out"})


@app.get("/api/auth/me")
def me():
    """檢查目前登入狀態，前端可以用這個判斷要不要顯示登入按鈕"""
    if "user_id" not in session:
        return jsonify({"ok": False, "logged_in": False}), 401
    return jsonify({"ok": True, "logged_in": True, "username": session["username"]})


# ==============================
# Main
# ==============================

if __name__ == "__main__":
    host  = os.getenv("FLASK_HOST", "127.0.0.1")
    port  = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "true").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)