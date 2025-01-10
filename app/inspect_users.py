import logging
from chromadb_utility import ChromaDBUtility

def inspect_users_collection():
    """Inspect the structure of the `users` collection."""
    chroma_db = ChromaDBUtility()
    try:
        # Access the `users` collection
        users_collection = chroma_db.get_or_create_collection("users")

        # Query all users
        results = users_collection.query(
            query_texts=[""],  # This will return all entries
            n_results=100,
            include=["metadatas", "documents"]
        )

        # Extract and print metadata and documents
        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])

        print(f"Metadata: {metadatas}")
        print(f"Documents: {documents}")

        # Check if all users have the required fields
        for metadata_list in metadatas:  # In case of nested lists
            for user in metadata_list:
                print("Validating user:", user)
                required_fields = ["id", "username", "password", "role"]
                missing_fields = [field for field in required_fields if field not in user]
                if missing_fields:
                    print(f"User missing fields: {missing_fields}")
                else:
                    print("User structure is valid.")

    except Exception as e:
        logging.error(f"Failed to inspect 'users' collection: {str(e)}")
        raise

if __name__ == "__main__":
    inspect_users_collection()
