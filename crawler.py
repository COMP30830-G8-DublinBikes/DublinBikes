import requests
import os
import pymysql
import json
import datetime
from sqlalchemy import create_engine

def get_env(key, default=None):
    """安全地讀取環境變數"""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"環境變數 {key} 未設定")
    return value

# 讀取環境變數（對應 YML 的 env 設定）
JCKEY = get_env('API_KEY')              # 來自 secrets.BIKE_API_KEY
CONTRACT_NAME = get_env('CONTRACT_NAME') # 來自 secrets.BIKE_CONTRACT_NAME
DB_HOST = get_env('DB_HOST')            # 來自 secrets.BIKE_DB_HOST
DB_PORT = int(get_env('DB_PORT', 3306)) # 來自 secrets.BIKE_DB_PORT
DB_USER = get_env('DB_USER')            # 來自 secrets.BIKE_DB_USER
DB_PASSWORD = get_env('DB_PASSWORD')    # 來自 secrets.BIKE_DB_PASSWORD
DB_NAME = get_env('DB_NAME')            # 來自 secrets.BIKE_DB_NAME

# 建立資料庫連線
connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl_mode=REQUIRED"
engine = create_engine(connection_string)

def create_tables():
    """建立 station 和 availability 資料表（如果不存在）"""
    
    # 建立 station 表
    sql_station = """
    CREATE TABLE IF NOT EXISTS station (
        number INTEGER PRIMARY KEY,
        address VARCHAR(256), 
        banking INTEGER,
        bikestands INTEGER,
        name VARCHAR(256),
        status VARCHAR(256),
        position_lat FLOAT,
        position_lng FLOAT,
        bonus INTEGER,
        overflow INTEGER
    );
    """
    engine.execute(sql_station)
    print(" Table 'station' is ready")
    
    # 建立 availability 表
    sql_availability = """
    CREATE TABLE IF NOT EXISTS availability (
        number INTEGER,
        available_bikes INTEGER,
        available_bike_stands INTEGER,
        last_update DATETIME,
        status VARCHAR(16),
        mechanical_bikes INTEGER,
        electrical_bikes INTEGER,
        total_bike_stands INTEGER,
        PRIMARY KEY (number, last_update)
    );
    """
    engine.execute(sql_availability)
    print(" Table 'availability' is ready")

def stations_to_db(stations):
    """
    將 JCDecaux API 資料寫入資料庫
    參考組員的 jc_decaux_local_download.py
    """
    for station in stations:
        # 插入 station 表（靜態資料）
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
        
        # 插入 availability 表（動態資料）
        last_update = datetime.datetime.fromtimestamp(station.get('last_update') / 1000)
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

def fetch_and_store():
    """主要執行函數"""
    try:
        print(f" [{datetime.datetime.now()}] Starting to fetch data...")
        
        # 1. 建立資料表（如果不存在）
        create_tables()
        
        # 2. 抓取 JCDecaux API
        response = requests.get(
            'https://api.jcdecaux.com/vls/v1/stations',
            params={
                'contract': CONTRACT_NAME,
                'apiKey': JCKEY
            }
        )
        response.raise_for_status()
        stations = response.json()
        
        print(f" Fetched {len(stations)} bike stations from JCDecaux API")
        
        # 3. 寫入資料庫
        stations_to_db(stations)
        
        print(f"   Successfully inserted data for {len(stations)} stations")
        print(f"   Static data → station table")
        print(f"   Dynamic data → availability table")
        print(f"   Timestamp: {datetime.datetime.now()}")
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    fetch_and_store()