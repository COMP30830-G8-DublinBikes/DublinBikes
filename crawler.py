import requests
import os
import json
import datetime
from sqlalchemy import create_engine, text

def get_env(key, default=None):
    """安全地讀取環境變數"""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"環境變數 {key} 未設定")
    return value

# 讀取環境變數
JCKEY = get_env('API_KEY')
CONTRACT_NAME = get_env('CONTRACT_NAME')
DB_HOST = get_env('DB_HOST')
DB_PORT = int(get_env('DB_PORT', 3306))
DB_USER = get_env('DB_USER')
DB_PASSWORD = get_env('DB_PASSWORD')
DB_NAME = get_env('DB_NAME')

# 建立資料庫連線（修正 SSL 參數）
connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 使用 connect_args 傳遞 SSL 設定
engine = create_engine(
    connection_string,
    connect_args={
        'ssl': {'ssl-mode': 'REQUIRED'}
    }
)

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
    )
    """
    
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
    )
    """
    
    # 使用 connection 執行 SQL
    with engine.connect() as conn:
        conn.execute(text(sql_station))
        conn.commit()
        print("✅ Table 'station' is ready")
        
        conn.execute(text(sql_availability))
        conn.commit()
        print("✅ Table 'availability' is ready")

def stations_to_db(stations):
    """將 JCDecaux API 資料寫入資料庫"""
    
    with engine.connect() as conn:
        for station in stations:
            # 插入 station 表（靜態資料）
            vals_station = {
                'number': station.get('number'),
                'address': station.get('address'),
                'banking': 1 if station.get('banking') else 0,
                'bike_stands': station.get('bike_stands'),
                'name': station.get('name'),
                'status': station.get('status'),
                'position_lat': station.get('position', {}).get('lat'),
                'position_lng': station.get('position', {}).get('lng'),
                'bonus': 1 if station.get('bonus') else 0,
                'overflow': 1 if station.get('overflow') else 0
            }
            
            sql_station = text("""
                INSERT IGNORE INTO station 
                VALUES (:number, :address, :banking, :bike_stands, :name, :status, 
                        :position_lat, :position_lng, :bonus, :overflow)
            """)
            conn.execute(sql_station, vals_station)
            
            # 插入 availability 表（動態資料）
            last_update = datetime.datetime.fromtimestamp(station.get('last_update') / 1000)
            
            vals_avail = {
                'number': station.get('number'),
                'available_bikes': station.get('available_bikes'),
                'available_bike_stands': station.get('available_bike_stands'),
                'last_update': last_update,
                'status': station.get('status'),
                'mechanical_bikes': station.get('mechanical_bikes', 0),
                'electrical_bikes': station.get('electrical_bikes', 0),
                'total_bike_stands': station.get('bike_stands')
            }
            
            sql_avail = text("""
                INSERT IGNORE INTO availability 
                VALUES (:number, :available_bikes, :available_bike_stands, :last_update, 
                        :status, :mechanical_bikes, :electrical_bikes, :total_bike_stands)
            """)
            conn.execute(sql_avail, vals_avail)
        
        # 提交所有變更
        conn.commit()

def fetch_and_store():
    """主要執行函數"""
    try:
        print(f"🔍 [{datetime.datetime.now()}] Starting to fetch data...")
        
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
        
        print(f"✅ Fetched {len(stations)} bike stations from JCDecaux API")
        
        # 3. 寫入資料庫
        stations_to_db(stations)
        
        print(f"✅ Successfully inserted data for {len(stations)} stations")
        print(f"   Static data → station table")
        print(f"   Dynamic data → availability table")
        print(f"   Timestamp: {datetime.datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    fetch_and_store()
