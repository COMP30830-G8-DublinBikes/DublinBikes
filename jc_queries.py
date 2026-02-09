'''
If done locally, remember to input mysql -u root -p in the terminal
If MySQL does not work, export PATH=${PATH}:/usr/local/mysql/bin
Let us do some queries on the database
'''
from sqlalchemy import create_engine
import dbinfo
import datetime

engine = create_engine("mysql+pymysql://{}:{}@{}:{}/{}".format(
    dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT, dbinfo.DB_NAME
))

# 1. Check total number of static stations
res = engine.execute("SELECT COUNT(*) FROM station;").fetchone()
print(f"Total stations in 'station' table: {res[0]}")

# 2. Check total number of dynamic records collected
res_avail = engine.execute("SELECT COUNT(*) FROM availability;").fetchone()
print(f"Total records in 'availability' table: {res_avail[0]}")

# 3. Show the latest 5 entries to confirm time sync
print("\n--- Latest 5 Availability Records ---")
latest = engine.execute("SELECT * FROM availability ORDER BY last_update DESC LIMIT 5;").fetchall()
for row in latest:
    print(row)

# 4. ...