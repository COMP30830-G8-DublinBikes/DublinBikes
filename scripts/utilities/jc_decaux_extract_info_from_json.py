import requests
import traceback
import datetime
import time
import os
import dbinfo
import json
import glob
from sqlalchemy import create_engine

engine = create_engine("mysql+pymysql://{}:{}@{}:{}/{}".format(dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT, dbinfo.DB_NAME))

def stations_to_db(text):
    """
    Parses JSON text and maps data into the 'station' and 'availability' tables.
    This function processes the content of a single file at a time.
    """
    stations = json.loads(text)
    
    for station in stations:
        #station
        vals_station=(
            station.get('number'),
            station.get('address'),
            1 if station.get('banking') else 0,
            station.get('bike_stands'),
            station.get('name'),
            station.get('status'),
            station.get('position', {}).get('lat'),
            station.get('position', {}).get('lng'),
            1 if station.get('bonus') else 0,
            1 if station.get('overflow') else 0
        )
        sql_station="INSERT IGNORE INTO station VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        engine.execute(sql_station, vals_station)
        #availability
        last_update= datetime.datetime.fromtimestamp(station.get('last_update')/1000)
        vals_avail=(
            station.get('number'),
            station.get('available_bikes'),
            station.get('available_bike_stands'),
            last_update,
            station.get('status'),
            station.get('mechanical_bikes', 0),
            station.get('electrical_bikes', 0),
            station.get('bike_stands')
        )
        sql_avail="INSERT IGNORE INTO availability VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        engine.execute(sql_avail, vals_avail)


def main():
    """
    Main execution logic for offline data recovery.
    This script batch-processes all JSON files backed up in the 'data' folder.
    Note: No time.sleep() is required as this processes local historical data.
    """
    files = glob.glob("data/bikes_*")
    print(f"Found {len(files)} files to process in 'data' folder.")
    for file_path in files:
        print(f"Processing file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                stations_to_db(content)
        except Exception:
            print(f"Error processing {file_path}")
            print(traceback.format_exc())
    print("\n--- All historical data extracted. ---")

if __name__ == "__main__":
    main()   