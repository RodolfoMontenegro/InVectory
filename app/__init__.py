import os
import logging
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect, url_for
from flask_jwt_extended import JWTManager, unset_jwt_cookies, verify_jwt_in_request, get_jwt_identity
from app.chromadb_utility import ChromaDBUtility
from app.routes import main
from app.inventory import inventory
from app.engineering import engineering
from app.user import user_bp, login_manager

def create_app():
    # Load environment variables from .env file
    load_dotenv()

    # Explicitly set the template folder to /inv/app/templates
    app = Flask(__name__, template_folder=os.path.join(os.getcwd(), "app/templates"))
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = os.getenv('FLASK_ENV', 'development') == 'production'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

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
    chroma_db_utility = ChromaDBUtility(persist_directory="./data")  # Relative to the project root
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
    login_manager.login_view = "user.manage_user"

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        if request.path.startswith("/api"):
            logging.warning("Unauthorized API access attempt detected.")
            return jsonify({"error": "Unauthorized access. Please log in."}), 401
        logging.warning("Unauthorized access detected.")
        return redirect(url_for("user.manage_user"))

    # Register blueprints
    app.register_blueprint(main, url_prefix="/")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(engineering, url_prefix="/engineering")
    app.register_blueprint(inventory, url_prefix="/inventory")

    @app.before_request
    def log_request_info():
        logging.info(f"Request: {request.method} {request.url}")
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                logging.info(f"Authenticated JWT Identity: {identity}")
            else:
                logging.info("No JWT identity found. Proceeding as unauthenticated.")
        except Exception as e:
            logging.warning(f"JWT verification failed: {str(e)}")

    @app.after_request
    def add_jwt_headers(response):
        """Unset JWT cookies if the user logs out or JWT verification fails."""
        if response.status_code == 401:
            logging.info("Clearing JWT cookies due to 401 response.")
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
            chroma_db_utility.add_user(username="admin", password="admin", role="admin")
            logging.info("Default admin user created with username: 'admin' and password: 'admin'.")
        else:
            logging.info("Default admin user already exists.")
        return True
    except Exception as e:
        logging.error(f"Error checking/creating default admin user: {str(e)}")
        return False
