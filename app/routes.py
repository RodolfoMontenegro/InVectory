import logging
import os
import json
import pandas as pd
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, render_template, send_file, redirect, url_for
from flask_login import login_required, current_user
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from jwt import ExpiredSignatureError, DecodeError as JWTDecodeError
from pydantic import ValidationError
from .models import InventoryResponse, InventoryItem
from .decorators import role_required

main = Blueprint("main", __name__)

# Home Route
@main.route("/", methods=["GET"])
@jwt_required(optional=True)
def main_menu():
    """Render the main menu for authenticated users or redirect unauthenticated users."""
    try:
        user_identity = get_jwt_identity()

        if user_identity:
            # Parse user_identity if it's a JSON string
            if isinstance(user_identity, str):
                user_identity = json.loads(user_identity)

            # Render the main menu template
            logging.info(f"Authenticated user: {user_identity}. Rendering main_menu.html.")
            return render_template("main_menu.html", user=user_identity)

        # Redirect unauthenticated users to manage page
        logging.info("Redirecting unauthenticated user to /user/manage.")
        return redirect(url_for("user.manage_user"))

    except Exception as e:
        logging.error(f"Error in main_menu: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

# Inventory Route
@main.route("/inventory", methods=["GET"])
@login_required  # Require user to be logged in
@role_required(["admin", "engineer", "inventory"])
def inventory_route():
    return render_template("entrada_material.html")

# Engineering Route
@main.route("/engineering", methods=["GET"])
@login_required
@role_required(["admin", "engineer"])
def engineering_route():
    return jsonify({"message": "Welcome to the engineering route."})

# Admin Route
@main.route("/admin", methods=["GET"])
@login_required
@role_required(["admin"])
def admin_route():
    return jsonify({"message": "Welcome, Admin!"})

@main.app_errorhandler(401)
def unauthorized_access(error):
    response = jsonify({"error": "Unauthorized access. Please log in again."})
    unset_jwt_cookies(response)  # Clear expired tokens
    return response, 401