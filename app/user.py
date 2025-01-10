import logging
import bcrypt
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from flask_login import login_user, logout_user, current_user, UserMixin, LoginManager
from flask_jwt_extended import (
    create_access_token, set_access_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity
)

# Initialize Blueprint and utilities
user_bp = Blueprint("user", __name__)

# Function to get the ChromaDBUtility instance
def get_chroma_db():
    """Retrieve the ChromaDBUtility instance from the current Flask app."""
    return current_app.chroma_db

# Initialize LoginManager
login_manager = LoginManager()

# Define User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

# Register the user loader function
@login_manager.user_loader
def load_user(user_id):
    """Load user from ChromaDB by user ID."""
    try:
        user_data = get_chroma_db().get_user_by_id(user_id)
        if user_data:
            logging.info(f"Loaded user: {user_data['username']} with ID: {user_data['id']}")
            return User(id=user_data["id"], username=user_data["username"], role=user_data["role"])
        else:
            logging.warning(f"User with ID '{user_id}' not found.")
            return None
    except Exception as e:
        logging.error(f"Failed to load user by ID '{user_id}': {str(e)}")
        return None

# Route to render the user management HTML page
@user_bp.route("/manage", methods=["GET"])
@jwt_required(optional=True)
def manage_user():
    """Render user management page or redirect authenticated users to main menu."""
    try:
        user_identity = get_jwt_identity()

        if user_identity:
            # Parse user_identity if it's a JSON string
            if isinstance(user_identity, str):
                user_identity = json.loads(user_identity)

            # Redirect authenticated users to main menu
            logging.info(f"Authenticated user detected: {user_identity}. Redirecting to main menu.")
            return redirect(url_for("main.main_menu"))

        # Render login page for unauthenticated users
        logging.info("Unauthenticated user. Rendering user management page.")
        return render_template("user.html")  # Ensure this is your login template

    except Exception as e:
        logging.error(f"Error in manage_user: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

# Admin-only route example
@user_bp.route("/admin_only", methods=["GET"])
@jwt_required()
def admin_only():
    """Admin-only route."""
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return jsonify({"message": "Welcome, Admin!"}), 200

# Register a new user
@user_bp.route("/register", methods=["POST"])
@jwt_required()
def register():
    """Register a new user (admin-only)."""
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"error": "Admin access required to register new users"}), 403

    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "inventory")  # Default role is 'inventory'

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    try:
        get_chroma_db().add_user(username, password, role)
        return jsonify({"message": "User registered successfully"}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# Handle GET requests for login
@user_bp.route("/login", methods=["GET"])
def login_get():
    """Handle GET requests to /login."""
    logging.info(f"[{datetime.utcnow()}] GET /login accessed.")
    return jsonify({"message": "Please log in using POST /user/login"}), 200

# Login route
@user_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and create a JWT token."""
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        logging.warning(f"[{datetime.utcnow()}] Login attempt with missing credentials.")
        return jsonify({"error": "Username and password are required"}), 400

    try:
        # Authenticate user
        user_data = get_chroma_db().authenticate_user(username, password)
        logging.info(
            f"[{datetime.utcnow()}] User login successful: "
            f"Username: {user_data['username']}, Role: {user_data['role']}, ID: {user_data['id']}"
        )

        # Serialize user_data to a JSON string
        user_identity = json.dumps(user_data)

        # Create access token
        access_token = create_access_token(identity=user_identity)

        # Set access token in cookies
        response = jsonify({"message": "Login successful"})
        set_access_cookies(response, access_token)
        return response, 200

    except ValueError as e:
        logging.warning(f"[{datetime.utcnow()}] Failed login for username: {username}. Error: {str(e)}")
        return jsonify({"error": str(e)}), 401

    except ExpiredSignatureError:
        logging.warning(f"[{datetime.utcnow()}] Expired token used for login.")
        response = jsonify({"error": "Session expired. Please log in again."})
        unset_jwt_cookies(response)
        return response, 401

    except Exception as e:
        logging.error(f"[{datetime.utcnow()}] Unexpected error during login: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

# Logout route
@user_bp.route("/logout", methods=["POST"])
def logout():
    """Clear the user's session."""
    response = jsonify({"message": "Logged out successfully"})
    unset_jwt_cookies(response)  # Clear JWT cookies
    return response, 200

@user_bp.route("/reset_password", methods=["POST"])
@jwt_required()
def reset_password():
    """Reset the password for a user."""
    identity = get_jwt_identity()
    data = request.json
    username = data.get("username")
    new_password = data.get("new_password")

    # Admins can reset any user's password; users can reset their own
    if identity["role"] != "admin" and identity["username"] != username:
        return jsonify({"error": "Unauthorized to reset this password"}), 403

    if not username or not new_password:
        return jsonify({"error": "Username and new password are required"}), 400

    try:
        get_chroma_db().reset_password(username, new_password)
        return jsonify({"message": "Password reset successfully!"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"An error occurred while resetting password: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@user_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Return the current authenticated user's information."""
    try:
        user_identity = get_jwt_identity()
        if not user_identity:
            return jsonify({"error": "Not authenticated"}), 401

        if isinstance(user_identity, str):
            user_identity = json.loads(user_identity)

        return jsonify(user_identity), 200
    except Exception as e:
        logging.error(f"Error fetching user information: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500
