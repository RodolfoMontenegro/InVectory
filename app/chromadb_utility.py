import chromadb
import os
import logging
import bcrypt
import uuid
import json
from chromadb.errors import InvalidCollectionException
from chromadb.utils import embedding_functions

class ChromaDBUtility:
    def __init__(self, persist_directory="./data"):
        """Initialize ChromaDB persistent client."""
        # Resolve the path relative to the current file's directory
        self.persist_directory = os.path.abspath(persist_directory)
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # Log the directory being used
        logging.info(f"ChromaDB initialized with persist_directory: {self.persist_directory}")

    def get_or_create_collection(self, collection_name):
        """Get an existing collection or create a new one."""
        try:
            return self.client.get_collection(name=collection_name)
        except InvalidCollectionException:
            logging.info(f"Creating new collection: {collection_name}")
            return self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )

    @staticmethod
    def flatten_nested_list(nested_list):
        """Utility to flatten nested lists."""
        if isinstance(nested_list, list):
            return [item for sublist in nested_list for item in sublist] if any(isinstance(i, list) for i in nested_list) else nested_list
        return nested_list
        
    def add_user(self, username, password, role="user"):
        """Add a new user to the 'users' collection."""
        users_collection = self.get_or_create_collection("users")
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Check for duplicate username
        results = users_collection.query(
            where={"username": username},  # Query metadata for the username
            n_results=1,
            include=["documents"]
        )
        documents = self.flatten_nested_list(results.get("documents", []))

        if any(doc == username for doc in documents):
            raise ValueError(f"Username '{username}' already exists.")

        # Prepare metadata
        metadata = {
            "id": username,  # Use the username as the ID
            "username": username,
            "password": hashed_password,
            "role": role
        }

        # Add user to collection
        try:
            users_collection.add(
                ids=[username],  # Use the username as the ID
                documents=[username],  # Store username in documents for direct querying
                metadatas=[metadata]
            )
            logging.info(f"User '{username}' added successfully with ID: {username}.")
        except Exception as e:
            logging.error(f"Failed to add user '{username}': {str(e)}")
            raise

    def get_user(self, username):
        """Retrieve user metadata by username."""
        users_collection = self.get_or_create_collection("users")
        try:
            # Query using `query_texts` to locate the user by username
            results = users_collection.query(
                query_texts=[username],
                n_results=1,
                include=["metadatas", "documents"]
            )

            # Extract metadata
            metadatas = self.flatten_nested_list(results.get("metadatas", []))
            if not metadatas:
                logging.warning(f"No user found with username '{username}'.")
                return None

            user_metadata = metadatas[0]
            logging.info(f"Query results for username '{username}': {user_metadata}")
            return user_metadata
        except Exception as e:
            logging.error(f"Failed to retrieve user '{username}': {str(e)}")
            raise

    def get_user_by_id(self, user_id):
        """Retrieve a user by their ID."""
        users_collection = self.get_or_create_collection("users")
        try:
            # Use `.get` to retrieve by ID
            results = users_collection.get(
                ids=[user_id],
                include=["metadatas"]
            )
            metadatas = self.flatten_nested_list(results.get("metadatas", []))
            if not metadatas:
                logging.warning(f"No user found with ID '{user_id}'.")
                return None

            user_metadata = metadatas[0]
            logging.info(f"Query results for user_id '{user_id}': {user_metadata}")
            return user_metadata
        except Exception as e:
            logging.error(f"Failed to retrieve user by ID '{user_id}': {str(e)}")
            raise

    def authenticate_user(self, username, password):
        """Authenticate a user using their username and password."""
        try:
            # Use `get_user` to retrieve user metadata
            user_metadata = self.get_user(username)
            if not user_metadata:
                raise ValueError("Invalid username or password.")

            # Ensure required fields are present in metadata
            if "password" not in user_metadata:
                raise KeyError("Missing 'password' in user metadata.")
            if "id" not in user_metadata:
                raise KeyError("Missing 'id' in user metadata.")

            # Validate the password
            if not bcrypt.checkpw(password.encode("utf-8"), user_metadata["password"].encode("utf-8")):
                raise ValueError("Invalid username or password.")

            # Return user data
            return {
                "id": user_metadata["id"],
                "username": user_metadata["username"],
                "role": user_metadata["role"]
            }
        except Exception as e:
            logging.error(f"Error authenticating user '{username}': {str(e)}")
            raise e

    def hash_password(self, password):
        """Hash a plain-text password."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    def reset_password(self, username, new_password):
        """Reset a user's password."""
        users_collection = self.get_or_create_collection("users")
        hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

        try:
            # Generate embedding for the username document
            document = f"User: {username}"
            embedding = self.embedding_function([document])[0]  # Generate embedding for query

            # Query using metadata and embeddings
            results = users_collection.query(
                where={"username": username},  # Filter by username
                query_embeddings=[embedding],  # Use embedding for similarity
                n_results=1,
                include=["metadatas", "documents"]
            )

            metadatas = self.flatten_nested_list(results.get("metadatas", []))
            if not metadatas:
                raise ValueError("Username not found")

            user_id = metadatas[0]["id"]

            # Update the user's password
            users_collection.update(
                ids=[user_id],
                metadatas=[{"password": hashed_password.decode("utf-8")}]
            )
            logging.info(f"Password reset successfully for user '{username}'.")
        except Exception as e:
            logging.error(f"Failed to reset password for user '{username}': {str(e)}")
            raise e

    def add_item(self, collection_name, item_id=None, descripcion="", metadata=None):
        """Add an item to a ChromaDB collection."""
        collection = self.get_or_create_collection(collection_name)
        item_id = item_id or str(uuid.uuid4())
        embedding = self.embedding_function([descripcion])[0]

        try:
            collection.add(
                ids=[item_id],
                documents=[descripcion],
                metadatas=[metadata or {}],
                embeddings=[embedding]
            )
            logging.info(f"Item added successfully: ID={item_id}, Description='{descripcion}'")
        except Exception as e:
            logging.error(f"Failed to add item to collection '{collection_name}': {str(e)}")
            raise

    def get_all_items(self, collection_name):
        """Retrieve all items from a ChromaDB collection."""
        collection = self.get_or_create_collection(collection_name)
        try:
            results = collection.query(
                query_texts=[""],
                n_results=100,
                include=["metadatas"]
            )
            return self.flatten_nested_list(results.get("metadatas", []))
        except Exception as e:
            logging.error(f"Failed to retrieve items from collection '{collection_name}': {str(e)}")
            return []
            
    def update_item(self, collection_name, item_id, metadata):
        """Update an item's metadata in a ChromaDB collection."""
        collection = self.get_or_create_collection(collection_name)
        try:
            collection.update(ids=[item_id], metadatas=[metadata])
            logging.info(f"Item updated successfully: ID={item_id}")
        except Exception as e:
            logging.error(f"Failed to update item in collection '{collection_name}': {str(e)}")
            
    def migrate_users(self):
        """Ensure all users have an 'id' field in their metadata."""
        users_collection = self.get_or_create_collection("users")
        try:
            # Retrieve all users using 'get'
            results = users_collection.get(
                include=["metadatas", "documents"]  # Include metadatas and documents
            )

            metadatas = self.flatten_nested_list(results.get("metadatas", []))
            ids = results.get("ids", [])  # 'ids' is always returned by default

            for metadata, user_id in zip(metadatas, ids):
                # Add 'id' to metadata if missing
                if "id" not in metadata:
                    metadata["id"] = user_id  # Use the existing ID from the collection

                    # Upsert the updated user data
                    users_collection.upsert(
                        ids=[user_id],  # Use the existing ID
                        metadatas=[metadata],  # Update metadata
                        documents=[metadata["username"]]  # Ensure the document is preserved
                    )
                    logging.info(f"Updated user '{metadata['username']}' with ID: {metadata['id']}")
        except Exception as e:
            logging.error(f"Failed to migrate users: {str(e)}")
