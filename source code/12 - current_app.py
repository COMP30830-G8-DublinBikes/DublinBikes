from flask import Flask, current_app

app = Flask(__name__)

@app.route('/')
def home():
    """Accessing current_app inside a request context."""
    app_name = current_app.name  # Get the name of the Flask application
    return f"Hello from {app_name}!"

if __name__ == '__main__':
    app.run(debug=True)
