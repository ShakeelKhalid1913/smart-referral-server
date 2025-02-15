import jwt
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timedelta

def generate_token(email: str) -> str:
    """Generate a JWT token for the user"""
    return jwt.encode(
        {'email': email, 'exp': datetime.utcnow() + timedelta(days=1)},
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

def get_user_from_request():
    """Get user email from request headers"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        token = auth_header.split(' ')[1]  # Bearer <token>
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])

        return payload.get('email')
    except Exception as e:
        # check if it company
        import requests
        res = requests.get(f"https://smartreferralhub.com/?rest_route=/simple-jwt-login/v1/auth/validate&JWT={token}")
        
        if not res.ok:
            return None
        
        payload = res.json()
        
        return payload.get('success')

def login_required(f):
    """Decorator to protect routes that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_email = get_user_from_request()
        if not user_email:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function
