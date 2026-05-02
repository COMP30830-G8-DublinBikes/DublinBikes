'''
Project structure is

project/
├── app.py (this file)
├── templates/
│   ├── index.html
│   ├── about.html
└── static/
    └── styles.css
'''

from flask import Flask, render_template

app = Flask(__name__)

# Route for the homepage
@app.route('/')
def home():
    return render_template('index.html', title="Home Page")

# Route for the about page
@app.route('/about')
def about():
    return render_template('about.html', title="About Us", description="This is the about page")

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
