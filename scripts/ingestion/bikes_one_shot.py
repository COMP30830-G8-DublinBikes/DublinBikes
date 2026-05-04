import requests
import traceback
import datetime
import time
import os
import dbinfo
import json
from sqlalchemy import create_engine, text

# 建立数据库引擎
engine = create_engine("mysql+pymysql://{}:{}@{}:{}/{}".format(
    dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT, dbinfo.DB_NAME))

def write_to_file(text_data):
    if not os.path.exists('data'):
        os.mkdir('data')
        print("Folder 'data' created!")
    
    now = datetime.datetime.now()
    filename = "data/bikes_{}".format(now).replace(" ", "_").replace(":", "-")
    with open(filename, "w") as f:
        f.write(text_data)

def write_to_db(text_data):
    stations = json.loads(text_data)
    
    # SQLAlchemy 2.0 必须使用 connection 并在结束后 commit
    with engine.connect() as conn:
        for station in stations:
            # 准备 station 表的数据
            vals_station = {
                "num": station.get('number'),
                "addr": station.get('address'),
                "bank": 1 if station.get('banking') else 0,
                "stands": station.get('bike_stands'),
                "name": station.get('name'),
                "status": station.get('status'),
                "lat": station.get('position', {}).get('lat'),
                "lng": station.get('position', {}).get('lng'),
                "bonus": 1 if station.get('bonus') else 0,
                "overflow": 1 if station.get('overflow') else 0
            }
            
            sql_station = text("""
                INSERT IGNORE INTO station 
                VALUES (:num, :addr, :bank, :stands, :name, :status, :lat, :lng, :bonus, :overflow)
            """)
            conn.execute(sql_station, vals_station)
            
            # 准备 availability 表的数据
            last_update = datetime.datetime.fromtimestamp(station.get('last_update')/1000)
            vals_avail = {
                "num": station.get('number'),
                "avail_bikes": station.get('available_bikes'),
                "avail_stands": station.get('available_bike_stands'),
                "update": last_update,
                "status": station.get('status'),
                "mech": station.get('mechanical_bikes', 0),
                "elec": station.get('electrical_bikes', 0),
                "stands": station.get('bike_stands')
            }
            
            sql_avail = text("""
                INSERT IGNORE INTO availability 
                VALUES (:num, :avail_bikes, :avail_stands, :update, :status, :mech, :elec, :stands)
            """)
            conn.execute(sql_avail, vals_avail)
        
        # 核心：必须手动提交，否则数据不会存入数据库
        conn.commit()
    
    print(f"Successfully inserted data for {len(stations)} stations into the database.")

def main():
    try:
        # 从 API 获取数据
        r = requests.get(dbinfo.STATIONS_URI, params={"apiKey": dbinfo.JCKEY, "contract": dbinfo.NAME})
        print(f"Request Status: {r.status_code}")
        
        if r.status_code == 200:
            write_to_file(r.text)
            write_to_db(r.text)
        else:
            print(f"Error: API returned status code {r.status_code}")
            
        print(f"Job finished at {datetime.datetime.now()}")
        
    except Exception:
        print("\n--- ERROR OCCURRED ---")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()