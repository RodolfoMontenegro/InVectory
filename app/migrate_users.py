import chromadb
import uuid
from chromadb_utility import ChromaDBUtility
import logging
from chromadb.utils import embedding_functions
import logging
import bcrypt

def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

def reset_users_collection():
    """Reset the `users` collection and ensure users have an `id`."""
    chroma_db = ChromaDBUtility()
    default_ef = embedding_functions.DefaultEmbeddingFunction()

    try:
        # Delete the existing `users` collection
        try:
            chroma_db.client.delete_collection(name="users")
            logging.info("Deleted existing 'users' collection.")
        except Exception as e:
            logging.warning(f"Error deleting 'users' collection (if it existed): {str(e)}")

        # Recreate the `users` collection
        users_collection = chroma_db.get_or_create_collection("users")
        logging.info("'users' collection recreated successfully.")

        # Add the default admin user with explicit `id`
        admin_password = "admin"
        hashed_password = hash_password(admin_password).decode("utf-8")
        admin_metadata = {
            "id": "admin",  # Explicitly include the `id` in the metadata
            "username": "admin",
            "password": hashed_password,
            "role": "admin"
        }

        # Generate embedding for the admin user
        try:
            admin_embedding = default_ef(["admin"])[0]
        except Exception as e:
            logging.error(f"Failed to generate embedding for admin: {str(e)}")
            raise

        # Add admin user to the collection
        users_collection.add(
            ids=["admin"],  # Explicitly set the ID
            documents=["admin"],  # Username as the document
            metadatas=[admin_metadata],
            embeddings=[admin_embedding]
        )
        logging.info("Default admin user created successfully (username: 'admin', password: 'admin').")

    except Exception as e:
        logging.error(f"Failed to reset 'users' collection: {str(e)}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reset_users_collection()
