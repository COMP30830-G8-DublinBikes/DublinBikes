#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
weather_scraper.py
- Runs forever (until Ctrl+C), default every 3600s (1 hour)
- Each loop:
  - calls weather_one_shot.main-like logic by importing it (no OneCall)
  - writes to weather_current / weather_hourly / weather_daily
  - prunes >48h old rows (dt-based)
- Suitable to run for 48 hours as sprint deliverable.
"""

import os
import time
import traceback

import weather_one_shot


def main():
    loop_seconds = int(os.getenv("WEATHER_LOOP_SECONDS", "3600"))  # 1 hour
    print(f"[START] Weather scraper (forecast-based). loop={loop_seconds}s retention={weather_one_shot.RETENTION_HOURS}h")

    while True:
        try:
            weather_one_shot.main()
        except KeyboardInterrupt:
            print("\n[STOP] KeyboardInterrupt. Exiting.")
            return
        except Exception:
            print("[ERROR] ingestion loop failed:")
            print(traceback.format_exc())

        time.sleep(loop_seconds)


if __name__ == "__main__":
    main()