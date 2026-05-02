from flask import Flask
# Create our flask app. Static files are served
#from 'static' directory

app = Flask(__name__, static_url_path='')

# this route simply serves 'static/index.html'
@app.route('/')
def root():
    return app.send_static_file('index.html')

if __name__ == "__main__":
    app.run(debug=True) 