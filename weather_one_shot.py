#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import datetime as dt
from typing import Any, Dict, List, Optional
import requests
import pymysql
import dbinfo 

CURRENT_URI = dbinfo.CURRENT_URI
FORECAST_URI = dbinfo.FORECAST_URI

DEFAULT_LAT = 53.3498
DEFAULT_LON = -6.2603
RETENTION_HOURS = 48 

def utc_now() -> dt.datetime:
    return dt.datetime.utcnow().replace(tzinfo=None)

def require_api_key() -> str:
    k = dbinfo.OWM_API_KEY
    if not k:
        print("[ERROR] OWM_API_KEY not found in dbinfo.py", file=sys.stderr)
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

def http_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def get_table_columns(conn, table: str) -> List[str]:
    sql = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s"
    with conn.cursor() as cur:
        cur.execute(sql, (dbinfo.DB_NAME, table))
        rows = cur.fetchall()
    return [r["COLUMN_NAME"] for r in rows]

def build_upsert_sql(table: str, cols: List[str], pk_cols: List[str]) -> str:
    col_str = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    update_str = ", ".join([f"{c}=VALUES({c})" for c in cols if c not in pk_cols])
    return f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_str if update_str else 'dt=dt'}"

def safe_get(d: Dict[str, Any], *path):
    for p in path:
        if isinstance(d, dict) and p in d: d = d[p]
        else: return None
    return d

def main():
    api_key = require_api_key()
    dt_run = utc_now()
    
    current_data = http_get_json(CURRENT_URI, {"lat": DEFAULT_LAT, "lon": DEFAULT_LON, "units": "metric", "appid": api_key})
    forecast_data = http_get_json(FORECAST_URI, {"lat": DEFAULT_LAT, "lon": DEFAULT_LON, "units": "metric", "appid": api_key})
    items = forecast_data.get("list", [])
    pop_now = items[0].get("pop") if items else None

    conn = db_connect()
    try:
        cols_cur = get_table_columns(conn, "weather_current")
        row_cur = {
            "dt": dt_run,
            "temp": safe_get(current_data, "main", "temp"),
            "feels_like": safe_get(current_data, "main", "feels_like"),
            "humidity": safe_get(current_data, "main", "humidity"),
            "weather_id": (current_data.get("weather") or [{}])[0].get("id"),
            "pop": pop_now
        }
        sql_cur = build_upsert_sql("weather_current", [c for c in cols_cur if c in row_cur], ["dt"])
        with conn.cursor() as cur:
            cur.execute(sql_cur, [row_cur[c] for c in cols_cur if c in row_cur])

        cols_h = get_table_columns(conn, "weather_hourly")
        sql_h = build_upsert_sql("weather_hourly", [c for c in cols_h if c in {"dt", "future_dt", "temp", "weather_id", "pop"}], ["dt", "future_dt"])
        with conn.cursor() as cur:
            for item in items[:16]:
                f_dt = dt.datetime.utcfromtimestamp(item["dt"])
                r_h = {"dt": dt_run, "future_dt": f_dt, "temp": safe_get(item, "main", "temp"), "weather_id": safe_get(item, "weather", 0, "id"), "pop": item.get("pop")}
                cur.execute(sql_h, [r_h.get(c) for c in cols_h if c in r_h])

        print(f"[SUCCESS] Weather data synced at {dt_run} UTC using dbinfo config.")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
