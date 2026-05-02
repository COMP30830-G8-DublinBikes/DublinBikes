from flask import Flask, abort

app = Flask(__name__)

@app.route('/profile/<username>')
def profile(username):
    users = ["alice", "bob"]  # Simulated user list
    if username not in users:
        abort(404)  # User not found
    return f"Welcome {username}!"

if __name__ == '__main__':
    app.run(debug=True)
