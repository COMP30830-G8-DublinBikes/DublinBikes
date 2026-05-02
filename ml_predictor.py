from __future__ import annotations

import os
import datetime as dt
from typing import Any, Dict, List

import joblib
import pandas as pd
import holidays


MODEL_PATH = os.path.join(os.path.dirname(__file__), "bike_model.pkl")

FEATURE_COLUMNS = [
    "station_id",
    "hour",
    "minute",
    "day_of_week",
    "month",
    "max_air_temperature_celsius",
    "max_relative_humidity_percent",
    "max_barometric_pressure_hpa",
    "is_holiday",
]

_ie_holidays = holidays.Ireland()
_model = None


def get_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)
    return _model


def get_is_holiday(target_dt: dt.datetime) -> int:
    return 1 if target_dt.date() in _ie_holidays else 0


def build_feature_row(
    station_id: int,
    target_dt: dt.datetime,
    temp_c: float,
    humidity_percent: float,
    pressure_hpa: float,
) -> Dict[str, Any]:
    return {
        "station_id": int(station_id),
        "hour": int(target_dt.hour),
        "minute": int(target_dt.minute),
        "day_of_week": int(target_dt.weekday()),
        "month": int(target_dt.month),
        "max_air_temperature_celsius": float(temp_c),
        "max_relative_humidity_percent": float(humidity_percent),
        "max_barometric_pressure_hpa": float(pressure_hpa),
        "is_holiday": int(get_is_holiday(target_dt)),
    }


def predict_station_bikes(
    station_id: int,
    capacity: int,
    weather_inputs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if capacity is None:
        capacity = 0

    rows = []
    for item in weather_inputs:
        feature_row = build_feature_row(
            station_id=station_id,
            target_dt=item["target_time"],
            temp_c=item["temp"],
            humidity_percent=item["humidity"],
            pressure_hpa=item["pressure"],
        )
        rows.append(feature_row)

    df = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    preds = get_model().predict(df)

    results: List[Dict[str, Any]] = []
    for source_item, pred in zip(weather_inputs, preds):
        bikes = int(round(float(pred)))
        bikes = max(0, min(bikes, int(capacity)))
        docks = max(0, int(capacity) - bikes)

        results.append(
            {
                "hour_offset": int(source_item["hour_offset"]),
                "target_time": source_item["target_time"].isoformat(),
                "weather_main": source_item.get("weather_main"),
                "weather_description": source_item.get("weather_description"),
                "temp": round(float(source_item["temp"]), 1),
                "humidity": round(float(source_item["humidity"]), 1),
                "pressure": round(float(source_item["pressure"]), 1),
                "rain_prob": source_item.get("rain_prob"),
                "predicted_bikes": bikes,
                "predicted_docks": docks,
                "capacity": int(capacity),
            }
        )

    return results