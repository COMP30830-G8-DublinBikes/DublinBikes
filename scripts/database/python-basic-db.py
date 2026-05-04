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


connection_string = "mysql+pymysql://{}:{}@{}:{}".format(dbinfo.DB_USER, dbinfo.DB_PASS, dbinfo.DB_URI, dbinfo.DB_PORT)

engine = create_engine(connection_string, echo = True)

sql = """
CREATE DATABASE IF NOT EXISTS {};
""".format(dbinfo.DB_NAME)

engine.execute(sql)

for res in engine.execute("SHOW VARIABLES;"):
    print(res)