import logging
import os
import pandas as pd
from flask_login import login_required
from flask import Blueprint, jsonify, request, current_app, send_file, render_template
from pydantic import ValidationError
from app.models import InventoryItem, InventoryResponse
from app.decorators import role_required

inventory = Blueprint("inventory", __name__)

@inventory.route("/entrada_material", methods=["GET"])
@login_required
@role_required(["admin", "engineer", "inventory"])
def entrada_material():
    """Render the Entrada de Material page."""
    return render_template("entrada_material.html")
    
# Add Item Route
@inventory.route("/add_item", methods=["POST"])
@login_required
@role_required(["admin", "engineer", "inventory"])
def add_item():
    chroma_db = current_app.chroma_db

    try:
        data = request.json
        item = InventoryItem(**data)
        logging.info(f"Adding item: {item.dict()}")
    except ValidationError as e:
        logging.error(f"Failed to validate item data: {e.errors()}")
        return jsonify({"error": e.errors()}), 400

    try:
        # Check for duplicates
        existing_items = chroma_db.get_all_items("inventory")
        for existing_item in existing_items:
            if existing_item.get("numero_parte") == item.numero_parte:
                logging.warning(f"Duplicate numero_parte detected: {item.numero_parte}")
                return jsonify({"error": "Numero Parte must be unique!"}), 400

        # Add to ChromaDB
        chroma_db.add_item(
            collection_name="inventory",
            descripcion=item.descripcion,
            metadata=item.dict()
        )
        logging.info(f"Item added successfully: {item.dict()}")
        return jsonify({"message": "Item added successfully!"}), 201
    except Exception as e:
        logging.error(f"Error adding item to ChromaDB: {str(e)}")
        return jsonify({"error": "Failed to add item to database"}), 500

# Get Inventory Route
@inventory.route("/get_inventory", methods=["GET"])
@login_required
@role_required(["admin", "engineer", "inventory"])
def get_inventory():
    chroma_db = current_app.chroma_db
    try:
        raw_items = chroma_db.get_all_items("inventory")
        items = [InventoryItem(**item) for item in raw_items if isinstance(item, dict)]
        items = sorted(items, key=lambda x: int(x.numero_parte))
        response = InventoryResponse(items=items)
        return jsonify(response.dict())
    except Exception as e:
        logging.error(f"Error retrieving inventory: {str(e)}")
        return jsonify({"error": "Failed to retrieve inventory"}), 500

# Update Item Route
@inventory.route("/update_item", methods=["PUT"])
@login_required
@role_required(["admin", "engineer"])
def update_item():
    chroma_db = current_app.chroma_db

    try:
        data = request.json
        updated_item = InventoryItem(**data)
    except ValidationError as e:
        logging.error(f"Update validation failed: {e.errors()}")
        return jsonify({"error": e.errors()}), 400

    try:
        items = chroma_db.get_all_items("inventory")
        for item in items:
            if item.get("numero_parte") == updated_item.numero_parte:
                chroma_db.get_or_create_collection("inventory").update(
                    ids=[f"item_{updated_item.numero_parte}"],
                    metadatas=[updated_item.dict()]
                )
                logging.info(f"Item updated successfully: {updated_item.dict()}")
                return jsonify({"message": "Item updated successfully!"}), 200
    except Exception as e:
        logging.error(f"Error updating item: {str(e)}")
        return jsonify({"error": "Failed to update item"}), 500

    logging.warning(f"Item not found for update: {updated_item.numero_parte}")
    return jsonify({"error": "Item not found"}), 404

# Delete Item Route
@inventory.route("/delete_item", methods=["DELETE"])
@login_required
@role_required(["admin"])
def delete_item():
    chroma_db = current_app.chroma_db
    numero_parte = request.args.get("numero_parte")

    if not numero_parte:
        logging.error("Delete failed: 'numero_parte' is required")
        return jsonify({"error": "Numero Parte is required"}), 400

    try:
        chroma_db.get_or_create_collection("inventory").delete(ids=[f"item_{numero_parte}"])
        logging.info(f"Item with numero_parte '{numero_parte}' deleted successfully")
        return jsonify({"message": "Item deleted successfully!"}), 200
    except Exception as e:
        logging.error(f"Error deleting item: {str(e)}")
        return jsonify({"error": "Failed to delete item"}), 500

# Export Inventory
@inventory.route("/export_inventory", methods=["GET"])
@login_required
@role_required(["admin", "engineer", "inventory"])
def export_inventory():
    chroma_db = current_app.chroma_db
    output_folder = os.path.abspath("./exports")
    os.makedirs(output_folder, exist_ok=True)
    file_path = os.path.join(output_folder, "inventory.xlsx")

    try:
        items = chroma_db.get_all_items("inventory")
        df = pd.DataFrame(items)
        df.to_excel(file_path, index=False)
        logging.info(f"Exported inventory to {file_path}")
        return send_file(file_path, as_attachment=True, download_name="inventory.xlsx")
    except Exception as e:
        logging.error(f"Failed to export inventory: {str(e)}")
        return jsonify({"error": "Failed to export inventory"}), 500
