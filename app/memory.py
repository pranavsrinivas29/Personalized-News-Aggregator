import chromadb

# Create a ChromaDB client to store and retrieve user preferences
client = chromadb.Client()
collection = client.create_collection(name="user_preferences")

def update_user_memory(user_id, data):
    # Add user preferences or new interactions to the memory
    collection.add_documents([{
        "user_id": user_id,
        "preferences": data
    }])

def get_user_preferences(user_id):
    # Retrieve user preferences based on user_id
    result = collection.query(filters={"user_id": user_id})
    if result:
        return result['preferences']
    return {}
