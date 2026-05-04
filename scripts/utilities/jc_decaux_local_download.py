####################DOWNLOAD from JCDECAUX###############
import requests
import traceback
import datetime
import time
import os
import dbinfo
import json
from sqlalchemy import create_engine

"""
Data are in dbinfo.py
CKEY = "...."
NAME = "dublin"
STATIONS_URI = "https://api.jcdecaux.com/vls/v1/stations"
"""

engine = create_engine("mysql+pymysql://{}:{}@{}:{}/{}".format(dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT, dbinfo.DB_NAME))
# Will be used to store text in a file
def write_to_file(text):
   
    # I first need to create a folder data where the files will be stored.
    
    if not os.path.exists('data'):
        os.mkdir('data')
        print("Folder 'data' created!")
    else:
        print("Folder 'data' already exists.")

    # now is a variable from datetime, which will go in {}.
    # replace is replacing white spaces with underscores in the file names
    now = datetime.datetime.now()
    filename = "data/bikes_{}".format(now).replace(" ", "_").replace(":", "-")
    with open(filename, "w") as f:
        f.write(text)

# Empty for now
def write_to_db(text):
    stations= json.loads(text)
    for station in stations:
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
    print(f"Successfully inserted data for {len(stations)} stations into the database.")

def main():
    while True:
        try:
            r = requests.get(dbinfo.STATIONS_URI, params={"apiKey": dbinfo.JCKEY, "contract": dbinfo.NAME})
            print(r)
            write_to_file(r.text)
            write_to_db(r.text)
            print("Next update in 5 minutes...")
            time.sleep(5*60)
        except KeyboardInterrupt:
            print("\nScript stopped by user (Ctrl+C).")
            break
        except Exception:
            print("\n--- ERROR OCCURRED ---")
            print(traceback.format_exc())
            print('Trying again in 10 seconds...')
            time.sleep(10)

# CTRL + Z to stop it
if __name__=="__main__":
    main()    