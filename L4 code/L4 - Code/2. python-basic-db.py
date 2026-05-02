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
PASSWORD = "......."
PORT = "3306"
DB = "local_databasejcdecaux"
URI = "127.0.0.1"

connection_string = "mysql+pymysql://{}:{}@{}:{}".format(USER, PASSWORD, URI, PORT)

engine = create_engine(connection_string, echo = True)

sql = """
CREATE DATABASE IF NOT EXISTS {};
""".format(DB)

engine.execute(sql)

for res in engine.execute("SHOW VARIABLES;"):
    print(res)
