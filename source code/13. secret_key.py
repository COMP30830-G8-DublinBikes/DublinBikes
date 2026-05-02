import os
import logging
from flask import Flask, current_app

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

@app.route('/')
def home():
    # Directly access current_app.config inside a request (no need for app_context)
    secret_key = current_app.config.get('SECRET_KEY', 'default_value')
    current_app.logger.info("SECRET_KEY has been accessed securely.")  # Log instead of showing it

    return "Welcome to the Flask App!"

if __name__ == '__main__':
    # Load SECRET_KEY from environment variable
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secret')

    app.run(debug=True)
