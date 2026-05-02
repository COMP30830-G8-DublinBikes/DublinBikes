####################DOWNLOAD from JCDECAUX###############
import requests
import traceback
import datetime
import time
import os
import dbinfo

"""
Data are in dbinfo.py
CKEY = "...."
NAME = "dublin"
STATIONS_URI = "https://api.jcdecaux.com/vls/v1/stations"
"""

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
    with open("data/bikes_{}".format(now).replace(" ", "_"), "w") as f:
        f.write(text)

# Empty for now
def write_to_db(text):
    return 0

def main():
    while True:
        try:
            r = requests.get(dbinfo.STATIONS_URI, params={"apiKey": dbinfo.JCKEY, "contract": dbinfo.NAME})
            print(r)
            write_to_file(r.text)
            time.sleep(5*60)
        except:
            print(traceback.format_exc())

# CTRL + Z to stop it
main()    