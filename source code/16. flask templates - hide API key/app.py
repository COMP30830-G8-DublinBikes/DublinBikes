import os
from flask import Flask, render_template

app = Flask(__name__)

# Load your Google Maps API key securely from environment variables
app.config['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY')

@app.route('/')
def index():
    return render_template('map.html', google_maps_api_key=app.config['GOOGLE_MAPS_API_KEY'])

if __name__ == '__main__':
    app.run(debug=True)

