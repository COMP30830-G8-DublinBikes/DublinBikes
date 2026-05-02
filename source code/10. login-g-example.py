from flask import Flask, g, jsonify, request

app = Flask(__name__)

# Mock function to fetch user details (e.g., from a database or external API)
def fetch_user_from_db(user_id):
    # Simulate a database query or API call
    users = {
        1: {'id': 1, 'name': 'Alice', 'role': 'admin'},
        2: {'id': 2, 'name': 'Bob', 'role': 'user'},
    }
    return users.get(user_id)

# Middleware to authenticate the user and store their details in `g`
def authenticate_user():
    # Get the user ID from the request (e.g., from a token or session)
    user_id = request.args.get('user_id', type=int)
    if user_id:
        user = fetch_user_from_db(user_id)
        if user:
            g.user = user  # Store the user details in `g`
        else:
            g.user = None  # User not found
    else:
        g.user = None  # No user ID provided

# Route that requires user authentication
@app.route('/profile')
def profile():
    authenticate_user()  # Authenticate the user and store their details in `g`
    if g.user:
        return jsonify({'message': f"Welcome, {g.user['name']}!", 'role': g.user['role']})
    else:
        return jsonify({'error': 'User not authenticated'}), 401

# Route that requires admin access
@app.route('/admin')
def admin_dashboard():
    authenticate_user()  # Authenticate the user and store their details in `g`
    if g.user and g.user['role'] == 'admin':
        return jsonify({'message': f"Welcome to the admin dashboard, {g.user['name']}!"})
    else:
        return jsonify({'error': 'Access denied'}), 403

if __name__ == '__main__':
    app.run(debug=True)