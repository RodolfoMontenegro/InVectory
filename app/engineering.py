import logging
import uuid
from flask_login import login_required, current_user
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token, get_jwt
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app
)
from app.decorators import role_required

engineering = Blueprint("engineering", __name__, template_folder="templates/engineering")

@engineering.route("/", methods=["GET"])
@jwt_required()  # Check JWT
@login_required
@role_required(["admin", "engineer"])
def engineering_home():
    """Render the Engineering Home Page."""
    logging.info(f"User {current_user.username} accessed Engineering Home.")
    return render_template("engineering.html")

@engineering.route("/tasks", methods=["POST"])
@jwt_required()  # Check JWT
@login_required
@role_required(["admin", "engineer"])
def add_task():
    """Add a new engineering task."""
    data = request.json
    task_id = data.get("task_id")
    description = data.get("description")

    if not task_id or not description:
        logging.warning("Task creation failed: Task ID or description missing.")
        return jsonify({"error": "Task ID and Description are required"}), 400

    logging.info(f"User {current_user.username} added task: {task_id}, {description}")
    return jsonify({"message": "Task added successfully"}), 201

@engineering.route("/numero_parte/nuevo", methods=["GET", "POST"])
@jwt_required()  # Check JWT
@login_required
@role_required(["admin", "engineer"])
def nuevo_numero_parte():
    """Handle adding a new 'Numero de Parte'."""
    logging.info(f"User {current_user.username} accessed nuevo_numero_parte.")
    if request.method == "GET":
        csrf_token = get_jwt()["csrf"]  # Extract the CSRF token from the JWT
        return render_template("nuevo_numero_parte.html", csrf_token=csrf_token)
    try:
        cliente = request.form.get("cliente")
        numero_parte = request.form.get("numero_parte")
        descripcion_ingles = request.form.get("descripcion_ingles")
        descripcion_espanol = request.form.get("descripcion_espanol")
        unidad_medida = request.form.get("unidad_medida")
        peso = request.form.get("peso")
        unidad_peso = request.form.get("unidad_peso")

        if not cliente or not numero_parte:
            raise ValueError("Cliente and Numero de Parte are required fields.")

        document = f"{numero_parte}: {descripcion_ingles} / {descripcion_espanol}"
        metadata = {
            "cliente": cliente,
            "numero_parte": numero_parte,
            "descripcion_ingles": descripcion_ingles,
            "descripcion_espanol": descripcion_espanol,
            "unidad_medida": unidad_medida,
            "peso": float(peso),
            "unidad_peso": unidad_peso,
        }

        chroma_db = get_chroma_db()
        chroma_db.add_item(
            collection_name="partes",
            item_id=str(uuid.uuid4()),
            descripcion=document,
            metadata=metadata
        )

        logging.info(f"User {current_user.username} added Numero de Parte {numero_parte}.")
        flash("Numero de Parte agregado exitosamente.", "success")
        return redirect(url_for("engineering.nuevo_numero_parte"))

    except ValueError as ve:
        logging.warning(f"Validation error: {str(ve)}")
        flash(str(ve), "warning")
        return redirect(url_for("engineering.nuevo_numero_parte"))

    except Exception as e:
        logging.error(f"Error adding Numero de Parte by {current_user.username}: {str(e)}")
        flash("Hubo un error al agregar el Numero de Parte.", "danger")
        return redirect(url_for("engineering.nuevo_numero_parte"))

@engineering.route("/numero_parte/list", methods=["GET"])
@jwt_required()  # Check JWT
@login_required
@role_required(["admin", "engineer"])
def list_partes():
    """List all 'Numero de Parte' from ChromaDB."""
    try:
        chroma_db = get_chroma_db()
        items = chroma_db.get_all_items("partes")
        logging.info(f"User {current_user.username} retrieved Numero de Parte list.")
        return jsonify(items), 200
    except Exception as e:
        logging.error(f"Error retrieving Numero de Parte list by {current_user.username}: {str(e)}")
        return jsonify({"error": "Failed to retrieve items"}), 500

@engineering.route("/numero_parte/modificar", methods=["GET", "POST"])
@jwt_required()  # Check JWT
@login_required
@role_required(["admin", "engineer"])
def modificar_numero_parte():
    """Query and modify an existing 'Número de Parte'."""
    chroma_db = get_chroma_db()

    if request.method == "GET":
        query = request.args.get("numero_parte_query")
        if query:
            try:
                collection = chroma_db.get_or_create_collection("partes")
                results = collection.get(include=["metadatas"], where={"numero_parte": query})

                if results["metadatas"]:
                    part = results["metadatas"][0]
                    logging.info(f"User {current_user.username} queried Numero de Parte {query}.")
                    return render_template("modificar_numero_parte.html", part=part, query=query)
                else:
                    flash("Número de Parte no encontrado.", "warning")
                    return redirect(url_for("engineering.engineering_home"))

            except Exception as e:
                logging.error(f"Error querying Numero de Parte by {current_user.username}: {str(e)}")
                flash("Hubo un error al buscar el número de parte.", "danger")
                return redirect(url_for("engineering.engineering_home"))

        return render_template("modificar_numero_parte.html")

    elif request.method == "POST":
        try:
            cliente = request.form.get("cliente")
            numero_parte = request.form.get("numero_parte")
            descripcion_ingles = request.form.get("descripcion_ingles")
            descripcion_espanol = request.form.get("descripcion_espanol")
            unidad_medida = request.form.get("unidad_medida")
            peso = request.form.get("peso")
            unidad_peso = request.form.get("unidad_peso")

            updated_metadata = {
                "cliente": cliente,
                "numero_parte": numero_parte,
                "descripcion_ingles": descripcion_ingles,
                "descripcion_espanol": descripcion_espanol,
                "unidad_medida": unidad_medida,
                "peso": float(peso),
                "unidad_peso": unidad_peso,
            }

            collection = chroma_db.get_or_create_collection("partes")
            collection.upsert(ids=[f"item_{numero_parte}"], metadatas=[updated_metadata])

            logging.info(f"User {current_user.username} updated Numero de Parte {numero_parte}.")
            flash("Número de Parte actualizado exitosamente.", "success")
            return redirect(url_for("engineering.modificar_numero_parte"))

        except Exception as e:
            logging.error(f"Error updating Numero de Parte by {current_user.username}: {str(e)}")
            flash("Hubo un error al actualizar el número de parte.", "danger")
            return redirect(url_for("engineering.modificar_numero_parte"))

@engineering.route("/numero_parte/eliminar", methods=["POST"])
@jwt_required()  # Check JWT
@login_required
@role_required(["admin", "engineer"])
def eliminar_numero_parte():
    """Delete an existing 'Número de Parte'."""
    try:
        numero_parte = request.form.get("numero_parte")

        if not numero_parte:
            logging.warning(f"User {current_user.username} attempted to delete without providing Numero de Parte.")
            flash("Debe proporcionar un número de parte para eliminar.", "danger")
            return redirect(url_for("engineering.modificar_numero_parte"))

        chroma_db = get_chroma_db()
        collection = chroma_db.get_or_create_collection("partes")
        collection.delete(where={"numero_parte": numero_parte})

        logging.info(f"User {current_user.username} deleted Numero de Parte {numero_parte}.")
        flash(f"Número de Parte '{numero_parte}' eliminado exitosamente.", "success")
        return redirect(url_for("engineering.engineering_home"))

    except Exception as e:
        logging.error(f"Error deleting Numero de Parte by {current_user.username}: {str(e)}")
        flash("Hubo un error al eliminar el número de parte.", "danger")
        return redirect(url_for("engineering.modificar_numero_parte"))


def get_chroma_db():
    """Retrieve the ChromaDBUtility instance from the current Flask app."""
    return current_app.chroma_db
