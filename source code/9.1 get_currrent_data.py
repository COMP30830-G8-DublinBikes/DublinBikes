from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

# API Keys (Replace with your own keys)
JCDECAUX_API_KEY = "your_jcdecaux_api_key"
OPENWEATHER_API_KEY = "your_openweather_api_key"
CITY_NAME = "Dublin"  # Change to your desired city
CONTRACT_NAME = "dublin"  # Change as needed

# JCDecaux API - Get bike stations
def get_bike_data():
    url = f"https://api.jcdecaux.com/vls/v1/stations?contract={CONTRACT_NAME}&apiKey={JCDECAUX_API_KEY}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else []

# OpenWeatherMap API - Get current weather
def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else {}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/bikes")
def bikes():
    return jsonify(get_bike_data())

@app.route("/api/weather")
def weather():
    return jsonify(get_weather())

if __name__ == "__main__":
    app.run(debug=True)
