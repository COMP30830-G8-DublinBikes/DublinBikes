import os
import requests
import json
from flask import Flask, render_template, jsonify, g
from sqlalchemy import create_engine

# 匯入你的配置檔案
import dbinfo 

# 初始化 Flask 應用程式
app = Flask(__name__)

# --- 1. 從 dbinfo 讀取配置 ---
USER = dbinfo.DB_USER
PASSWORD = dbinfo.DB_PASS
PORT = dbinfo.DB_PORT
DB = dbinfo.DB_NAME
URI = dbinfo.DB_URI

JCDECAUX_API_KEY = dbinfo.JCKEY
CONTRACT_NAME = dbinfo.NAME

# 地圖 API Key 通常建議存在系統環境變數中
# app.config['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY')

# --- 2. 資料庫連線邏輯 (file 8) ---
# 建立連線字串，告訴 SQLAlchemy 用什麼帳號密碼去哪裡連哪個資料庫
def connect_to_db():
    connection_string = f"mysql+pymysql://{USER}:{PASSWORD}@{URI}:{PORT}/{DB}"
    # echo=True 會在終端機印出 SQL 執行過程，方便偵錯
    engine = create_engine(connection_string, echo=True)
    return engine

def get_db():
    # 使用 Flask 的 g 物件來確保在同一個 request 中只連線一次
    db_engine = getattr(g, '_database', None)
    if db_engine is None:
        # 如果沒有，就建立一個並存入 g，確保不會重複連線浪費資源
        db_engine = g._database = connect_to_db()
    return db_engine

# --- 3. 路由設定 ---

# 首頁：渲染地圖頁面
@app.route('/')
def index():
    # 暫時不載入 map.html，避免地圖 Key 錯誤導致頁面崩潰
    # 直接回傳一個簡單的 HTML 導覽
    return render_template('index.html', title="Dublin Bike App")

@app.route('/about')
def about():
    return render_template('about.html', title="About Us")

# --- 你負責的 Module B 核心功能 ---

@app.route('/api/bike/current')
def get_bike_data():
    # 參考老師的 9.1 檔案實作 組合 JCDecaux 的 API 網址
    url = f"https://api.jcdecaux.com/vls/v1/stations?contract={CONTRACT_NAME}&apiKey={JCDECAUX_API_KEY}"
    try:
        # requests.get 會去抓取該網址的內容，timeout=5 代表超過 5 秒沒反應就放棄
        response = requests.get(url, timeout=5)
        # 如果狀態碼是 200 (成功)，就將資料轉成 JSON 格式回傳給瀏覽器
        return jsonify(response.json()) if response.status_code == 200 else jsonify({"error": "API Fail"})
    except Exception as e:
        # 如果抓取過程出錯（如斷網），回傳錯誤訊息
        return jsonify({"error": str(e)}), 500

@app.route("/api/bike/history/<int:station_id>")
def get_bike_history(station_id):
    # 參考老師的 9 號檔案實作
    engine = get_db() # 取得資料庫引擎
    data = []
    # 執行 SQL 查詢
    query = f"SELECT * FROM availability WHERE number = {station_id} ORDER BY last_update DESC LIMIT 10;"
    try:
        rows = engine.execute(query)
        for row in rows:
            # 將每一列資料轉成 Python 字典，這樣才能轉成 JSON
            data.append(dict(row))
        # 回傳包含歷史資料清單的 JSON
        return jsonify(history=data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)