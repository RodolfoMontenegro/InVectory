import os
import logging
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, request
from flask_jwt_extended import JWTManager, unset_jwt_cookies
from app.chromadb_utility import ChromaDBUtility
from app.routes import main  # Updated import for the main blueprint
from app.inventory import inventory  # Import the inventory blueprint
from app.user import user_bp, login_manager  # Import the user blueprint and LoginManager instance

def create_app():
    # Load environment variables from .env file
    load_dotenv()

    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = False  # Set True in production
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)  # Increase the expiry to 2 hours
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)  # Optional refresh token

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    logging.info("Flask app initialized")

    # Initialize ChromaDBUtility
    chroma_db_utility = ChromaDBUtility(persist_directory="./data")
    app.chroma_db = chroma_db_utility

    # Ensure `users` collection is created
    if not initialize_users_collection(chroma_db_utility):
        logging.error("Critical error: Could not initialize 'users' collection.")
        exit(1)

    # Migrate existing users
    chroma_db_utility.migrate_users()

    # Ensure default admin user exists
    if not ensure_admin_user_exists(chroma_db_utility):
        logging.error("Critical error: Could not ensure admin user exists.")
        exit(1)

    # Initialize Flask-JWT-Extended
    jwt = JWTManager(app)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "user.manage_users"

    # Register blueprints
    app.register_blueprint(main, url_prefix="/")  # Updated main blueprint
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(inventory, url_prefix="/inventory")

    @app.before_request
    def log_request_info():
        logging.info(f"Request: {request.method} {request.url}")

    @app.after_request
    def add_jwt_headers(response):
        """Unset JWT cookies if the user logs out."""
        if response.status_code == 401:
            unset_jwt_cookies(response)
        return response

    return app

def initialize_users_collection(chroma_db_utility):
    """Ensure the `users` collection exists."""
    try:
        chroma_db_utility.get_or_create_collection("users")
        logging.info("'users' collection initialized successfully.")
        return True
    except Exception as e:
        logging.error(f"Error ensuring 'users' collection exists: {str(e)}")
        return False

def ensure_admin_user_exists(chroma_db_utility):
    """Ensure the default admin user exists."""
    try:
        admin_user = chroma_db_utility.get_user("admin")
        if not admin_user:
            # Use the add_user method to properly add the admin user
            chroma_db_utility.add_user(username="admin", password="admin", role="admin")
            logging.info("Default admin user created with username: 'admin' and password: 'admin'.")
        else:
            logging.info("Default admin user already exists.")
        return True
    except Exception as e:
        logging.error(f"Error checking/creating default admin user: {str(e)}")
        return False
