#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
weather_one_shot.py
- Fetches:
  1) Current weather: /data/2.5/weather  (works for your key)
  2) Forecast 5d/3h:  /data/2.5/forecast (works for your key)
- Writes into MySQL tables:
  - weather_current
  - weather_hourly   (3-hour forecast stored as "hourly-style" rows)
  - weather_daily    (aggregated from forecast by date)
- Prunes rows older than 48h based on dt column (fetch time).
- Robust to schema differences: reads actual table columns and only inserts matching fields.
"""

import os
import sys
import time
import datetime as dt
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional

import requests
import pymysql

import dbinfo  # LOCAL ONLY (ignored by .gitignore)

CURRENT_URI = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URI = "https://api.openweathermap.org/data/2.5/forecast"

DEFAULT_LAT = 53.3498
DEFAULT_LON = -6.2603

RETENTION_HOURS = int(os.getenv("WEATHER_RETENTION_HOURS", "48"))


def utc_now() -> dt.datetime:
    return dt.datetime.utcnow().replace(tzinfo=None)  # store naive UTC DATETIME


def require_api_key() -> str:
    k = os.getenv("OWM_API_KEY")
    if not k:
        print("[ERROR] Missing OWM_API_KEY. Example: export OWM_API_KEY='xxxx'", file=sys.stderr)
        sys.exit(1)
    return k


def db_connect():
    return pymysql.connect(
        host=dbinfo.DB_URI,
        user=dbinfo.DB_USER,
        password=dbinfo.DB_PASS,
        database=dbinfo.DB_NAME,
        port=int(dbinfo.DB_PORT),
        autocommit=True,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def http_get_json(url: str, params: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def get_table_columns(conn, table: str) -> List[str]:
    sql = """
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
    ORDER BY ORDINAL_POSITION;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (dbinfo.DB_NAME, table))
        rows = cur.fetchall()
    return [r["COLUMN_NAME"] for r in rows]


def build_insert_sql(table: str, cols: List[str], pk_cols: List[str]) -> str:
    """
    INSERT ... ON DUPLICATE KEY UPDATE ...
    Updates all non-PK cols.
    """
    col_list = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))

    update_cols = [c for c in cols if c not in pk_cols]
    if update_cols:
        update_clause = ", ".join([f"{c}=VALUES({c})" for c in update_cols])
    else:
        update_clause = "dt=dt"  # no-op

    return f"""
    INSERT INTO {table} ({col_list})
    VALUES ({placeholders})
    ON DUPLICATE KEY UPDATE {update_clause};
    """.strip()


def cleanup_older_than(conn, hours: int) -> None:
    cutoff = utc_now() - dt.timedelta(hours=hours)
    with conn.cursor() as cur:
        for t in ("weather_current", "weather_hourly", "weather_daily"):
            # we assume all three tables have a `dt` column as fetch time (teacher design)
            cur.execute(f"DELETE FROM {t} WHERE dt < %s", (cutoff,))
    print(f"[CLEANUP] keep dt >= {cutoff} UTC (retention={hours}h)")


def fetch_current(api_key: str, lat: float, lon: float) -> Dict[str, Any]:
    return http_get_json(CURRENT_URI, {"lat": lat, "lon": lon, "units": "metric", "appid": api_key})


def fetch_forecast(api_key: str, lat: float, lon: float) -> Dict[str, Any]:
    return http_get_json(FORECAST_URI, {"lat": lat, "lon": lon, "units": "metric", "appid": api_key})


def safe_get(d: Dict[str, Any], *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def insert_current(conn, dt_run: dt.datetime, current_json: Dict[str, Any], pop_now: Optional[float]) -> None:
    table = "weather_current"
    cols = get_table_columns(conn, table)

    # Prepare a superset row; we will filter to existing cols
    row = {
        "dt": dt_run,
        "temp": safe_get(current_json, "main", "temp"),
        "feels_like": safe_get(current_json, "main", "feels_like"),
        "humidity": safe_get(current_json, "main", "humidity"),
        "pressure": safe_get(current_json, "main", "pressure"),
        "wind_speed": safe_get(current_json, "wind", "speed"),
        "wind_gust": safe_get(current_json, "wind", "gust"),
        "clouds": safe_get(current_json, "clouds", "all"),
        "weather_id": (current_json.get("weather") or [{}])[0].get("id"),
        "rain_1h": safe_get(current_json, "rain", "1h", default=0.0),
        "snow_1h": safe_get(current_json, "snow", "1h", default=0.0),
        "pop": pop_now,
        # optional if your schema has them
        "sunrise": dt.datetime.utcfromtimestamp(safe_get(current_json, "sys", "sunrise", default=0)) if safe_get(current_json, "sys", "sunrise") else None,
        "sunset": dt.datetime.utcfromtimestamp(safe_get(current_json, "sys", "sunset", default=0)) if safe_get(current_json, "sys", "sunset") else None,
        "uvi": None,
    }

    use_cols = [c for c in cols if c in row]
    pk_cols = ["dt"]  # teacher-style current table uses dt as PK

    sql = build_insert_sql(table, use_cols, pk_cols)
    vals = [row[c] for c in use_cols]

    with conn.cursor() as cur:
        cur.execute(sql, vals)


def forecast_list_items(forecast_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    return forecast_json.get("list") or []


def derive_pop_now_from_forecast(items: List[Dict[str, Any]], dt_run: dt.datetime) -> Optional[float]:
    """
    forecast list items include 'pop' (0..1) for each 3-hour step.
    Use the first item as proxy for "now".
    """
    if not items:
        return None
    pop = items[0].get("pop")
    try:
        return float(pop) if pop is not None else None
    except Exception:
        return None


def insert_hourly_from_forecast(conn, dt_run: dt.datetime, items: List[Dict[str, Any]], max_steps: int = 16) -> int:
    """
    Stores next ~48h of forecast (3-hour steps) into weather_hourly:
    - dt = fetch time (dt_run)
    - future_dt = forecast target time
    """
    table = "weather_hourly"
    cols = get_table_columns(conn, table)

    pk_cols = ["dt", "future_dt"]
    use_pk = all(pk in cols for pk in pk_cols)
    if not use_pk:
        raise RuntimeError(f"{table} must have columns dt and future_dt for composite PK. Found cols={cols}")

    sql_cols_superset = {
        "dt", "future_dt", "temp", "feels_like", "humidity", "pressure",
        "wind_speed", "wind_gust", "weather_id", "pop", "rain_1h", "snow_1h", "clouds", "uvi"
    }
    use_cols = [c for c in cols if c in sql_cols_superset]

    sql = build_insert_sql(table, use_cols, pk_cols)

    inserted = 0
    with conn.cursor() as cur:
        for item in items[:max_steps]:
            future_ts = item.get("dt")
            if future_ts is None:
                continue
            future_dt = dt.datetime.utcfromtimestamp(int(future_ts))

            row = {
                "dt": dt_run,
                "future_dt": future_dt,
                "temp": safe_get(item, "main", "temp"),
                "feels_like": safe_get(item, "main", "feels_like"),
                "humidity": safe_get(item, "main", "humidity"),
                "pressure": safe_get(item, "main", "pressure"),
                "wind_speed": safe_get(item, "wind", "speed"),
                "wind_gust": safe_get(item, "wind", "gust"),
                "clouds": safe_get(item, "clouds", "all"),
                "weather_id": (item.get("weather") or [{}])[0].get("id"),
                "pop": item.get("pop"),
                # forecast rain/snow volume is often in 3h blocks
                "rain_1h": safe_get(item, "rain", "3h", default=0.0),  # stored into rain_1h column if that's what you have
                "snow_1h": safe_get(item, "snow", "3h", default=0.0),
                "uvi": None,
            }

            vals = [row.get(c) for c in use_cols]
            cur.execute(sql, vals)
            inserted += 1

    return inserted


def aggregate_daily_from_forecast(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group 3-hour forecasts by UTC date, compute:
    - temp_min, temp_max
    - pop_max (max precipitation probability that day)
    - rain_sum (sum of rain 3h)
    - humidity_avg, pressure_avg (optional)
    """
    by_date = defaultdict(list)
    for it in items:
        ts = it.get("dt")
        if ts is None:
            continue
        d = dt.datetime.utcfromtimestamp(int(ts)).date()
        by_date[d].append(it)

    daily_rows = []
    for d, lst in sorted(by_date.items()):
        temps = [safe_get(x, "main", "temp") for x in lst if safe_get(x, "main", "temp") is not None]
        if not temps:
            continue
        tmin = min(temps)
        tmax = max(temps)

        pops = []
        for x in lst:
            p = x.get("pop")
            try:
                if p is not None:
                    pops.append(float(p))
            except Exception:
                pass
        pop_max = max(pops) if pops else None

        rain_sum = 0.0
        for x in lst:
            val = safe_get(x, "rain", "3h", default=0.0)
            try:
                rain_sum += float(val or 0.0)
            except Exception:
                pass

        humidity_vals = [safe_get(x, "main", "humidity") for x in lst if safe_get(x, "main", "humidity") is not None]
        pressure_vals = [safe_get(x, "main", "pressure") for x in lst if safe_get(x, "main", "pressure") is not None]

        humidity_avg = sum(humidity_vals) / len(humidity_vals) if humidity_vals else None
        pressure_avg = sum(pressure_vals) / len(pressure_vals) if pressure_vals else None

        # weather_id: take first slot’s weather id as representative
        weather_id = (lst[0].get("weather") or [{}])[0].get("id")

        daily_rows.append({
            "future_date": d,
            "temp_min": tmin,
            "temp_max": tmax,
            "pop": pop_max,
            "rain": rain_sum,
            "humidity": int(round(humidity_avg)) if humidity_avg is not None else None,
            "pressure": int(round(pressure_avg)) if pressure_avg is not None else None,
            "weather_id": weather_id,
        })

    return daily_rows


def insert_daily(conn, dt_run: dt.datetime, daily_rows: List[Dict[str, Any]], max_days: int = 3) -> int:
    """
    Insert aggregated daily rows into weather_daily:
    - dt = fetch time (dt_run)
    - future_date = date
    """
    table = "weather_daily"
    cols = get_table_columns(conn, table)
    pk_cols = ["dt", "future_date"]
    if not all(pk in cols for pk in pk_cols):
        raise RuntimeError(f"{table} must have columns dt and future_date. Found cols={cols}")

    superset = {
        "dt", "future_date", "temp_min", "temp_max", "humidity", "pressure",
        "wind_speed", "wind_gust", "weather_id", "pop", "rain", "snow", "uvi", "clouds"
    }
    use_cols = [c for c in cols if c in superset]

    sql = build_insert_sql(table, use_cols, pk_cols)

    inserted = 0
    with conn.cursor() as cur:
        for r in daily_rows[:max_days]:
            row = {"dt": dt_run, **r}
            vals = [row.get(c) for c in use_cols]
            cur.execute(sql, vals)
            inserted += 1
    return inserted


def main():
    api_key = require_api_key()
    lat = float(os.getenv("OWM_LAT", str(DEFAULT_LAT)))
    lon = float(os.getenv("OWM_LON", str(DEFAULT_LON)))

    dt_run = utc_now()

    current_json = fetch_current(api_key, lat, lon)
    forecast_json = fetch_forecast(api_key, lat, lon)
    items = forecast_list_items(forecast_json)

    pop_now = derive_pop_now_from_forecast(items, dt_run)

    conn = db_connect()
    try:
        cleanup_older_than(conn, RETENTION_HOURS)

        insert_current(conn, dt_run, current_json, pop_now)

        # next ~48h: 16 steps * 3h = 48h
        hourly_n = insert_hourly_from_forecast(conn, dt_run, items, max_steps=16)

        daily_rows = aggregate_daily_from_forecast(items)
        daily_n = insert_daily(conn, dt_run, daily_rows, max_days=3)

        warn = ""
        if pop_now is not None and float(pop_now) >= 0.70:
            warn = " (>=0.70 WARNING)"

        print(f"[OK] inserted current + hourly({hourly_n}) + daily({daily_n}) at {dt_run} UTC, pop_now={pop_now}{warn}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

