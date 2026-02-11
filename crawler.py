import requests
import os
import pymysql
import json
from datetime import datetime

def create_table_if_not_exists(cursor):
    """如果資料表不存在，自動建立"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS bike_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        timestamp DATETIME NOT NULL,
        data JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    cursor.execute(create_table_sql)
    print(" Table 'bike_data' is ready")

def fetch_and_store():
    try:
        # 1. 讀取環境變數
        jc_api_key = os.getenv('API_KEY')
        contract_name = os.getenv('CONTRACT_NAME')  # ← 新增這個
        db_host = os.getenv('DB_HOST')
        db_port = int(os.getenv('DB_PORT', 3306))
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_name = os.getenv('DB_NAME')
        
        print(f"🔍 Connecting to database: {db_host}:{db_port}")
        
        # 2. 抓取 JCDecaux Bike 資料
        response = requests.get(
            'https://api.jcdecaux.com/vls/v1/stations',
            params={
                'contract': contract_name,  # ← 從環境變數讀取
                'apiKey': jc_api_key
            }
        )
        response.raise_for_status()
        data = response.json()
        
        print(f" Fetched {len(data)} bike stations from JCDecaux API")
        
        # 3. 連接 Aiven MySQL
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            ssl={'ssl': True}
        )
        cursor = conn.cursor()
        
        # 4. 自動建立資料表（如果不存在）
        create_table_if_not_exists(cursor)
        
        # 5. 存入資料庫
        cursor.execute(
            "INSERT INTO bike_data (timestamp, data) VALUES (%s, %s)",
            (datetime.now(), json.dumps(data, ensure_ascii=False))
        )
        
        conn.commit()
        print(f" Bike data saved to database at {datetime.now()}")
        print(f"   Saved {len(data)} stations")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    fetch_and_store()
