import dbinfo
import requests
import json
import sqlalchemy as sqla
from sqlalchemy import create_engine
import traceback
import glob
import os
from pprint import pprint
import simplejson as json
import time
from IPython.display import display


USER = "root"
PASSWORD = "..."
PORT = "3306"
DB = "local_databasejcdecaux"
URI = "127.0.0.1"

connection_string = "mysql+pymysql://{}:{}@{}:{}/{}".format(USER, PASSWORD, URI, PORT, DB)

engine = create_engine(connection_string, echo = True)

for res in engine.execute("SHOW VARIABLES;"):
    print(res)

# Let us create a simplified JCDecaux table: ADD ALL YOUR VARIABLES!
# VARCHAR(256) indicates a string with max 256 chars

sql = '''
CREATE TABLE IF NOT EXISTS station (
address VARCHAR(256), 
banking INTEGER,
bikestands INTEGER,
name VARCHAR(256),
status VARCHAR(256));
'''

# Execute the query
res = engine.execute(sql)

# Use the engine to execute the DESCRIBE command to inspect the table schema
tab_structure = engine.execute("SHOW COLUMNS FROM station;")

# Fetch and print the result to see the columns of the table
columns = tab_structure.fetchall()
print(columns)

##################CREATE AVAILABILITY TABLE: DO NOT FORGET ALL VARIABLES############
sql = """
CREATE TABLE IF NOT EXISTS availability (
number INTEGER,
available_bikes INTEGER,
available_bike_stands INTEGER,
last_update DATETIME
);
"""

engine.execute(sql)