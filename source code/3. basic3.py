from flask import Flask
# Create our flask app. Static files are served
#from 'static' directory

app = Flask(__name__, static_url_path='')

@app.route('/station/<int:station_id>')
def station(station_id):
# show the station with the given id, the id is an integer
    return f'Retrieving info for Station: {station_id}'

if __name__ == "__main__":
    app.run(debug=True) 