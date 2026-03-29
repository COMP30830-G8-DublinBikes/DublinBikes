import requests
import traceback
import datetime
import time
import os
import dbinfo
import json
from sqlalchemy import create_engine

engine = create_engine("mysql+pymysql://{}:{}@{}:{}/{}".format(
    dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT, dbinfo.DB_NAME))

def write_to_file(text):
    if not os.path.exists('data'):
        os.mkdir('data')
        print("Folder 'data' created!")
    
    now = datetime.datetime.now()
    filename = "data/bikes_{}".format(now).replace(" ", "_").replace(":", "-")
    with open(filename, "w") as f:
        f.write(text)

def write_to_db(text):
    stations = json.loads(text)
    for station in stations:
        vals_station = (
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
        sql_station = "INSERT IGNORE INTO station VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        engine.execute(sql_station, vals_station)
        
        last_update = datetime.datetime.fromtimestamp(station.get('last_update')/1000)
        vals_avail = (
            station.get('number'),
            station.get('available_bikes'),
            station.get('available_bike_stands'),
            last_update,
            station.get('status'),
            station.get('mechanical_bikes', 0),
            station.get('electrical_bikes', 0),
            station.get('bike_stands')
        )
        sql_avail = "INSERT IGNORE INTO availability VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        engine.execute(sql_avail, vals_avail)
    
    print(f"Successfully inserted data for {len(stations)} stations into the database.")

def main():
    try:
        r = requests.get(dbinfo.STATIONS_URI, params={"apiKey": dbinfo.JCKEY, "contract": dbinfo.NAME})
        print(f"Request Status: {r.status_code}")
        
        write_to_file(r.text)
        write_to_db(r.text)
        
        print(f"Job finished at {datetime.datetime.now()}")
        
    except Exception:
        print("\n--- ERROR OCCURRED ---")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()