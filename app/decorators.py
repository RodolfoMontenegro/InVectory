from flask import jsonify
from flask_login import current_user

def role_required(required_roles):
    """Decorator to enforce role-based access control."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if current_user.role not in required_roles:
                return jsonify({"error": "Access denied. Insufficient permissions."}), 403
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
