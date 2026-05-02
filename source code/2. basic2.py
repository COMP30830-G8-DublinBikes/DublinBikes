from flask import Flask
# Create our flask app. Static files are served
#from 'static' directory

app = Flask(__name__, static_url_path='')

# this route simply serves 'static/user.html'
# make sure you have an user.html file in the folder static

@app.route('/user') # path that will be given as input on the command line
def user(): # function that will be called when entering that path
    return app.send_static_file('user.html') # file that will be retrieved

if __name__ == "__main__":
    app.run(debug=True) 