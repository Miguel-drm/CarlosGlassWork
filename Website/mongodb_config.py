from pymongo import MongoClient
from gridfs import GridFS
from dotenv import load_dotenv
import os
from bson.objectid import ObjectId

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')

def get_db():
    try:
        # Create client with explicit authentication options
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        
        # Test connection with server info command
        client.server_info()
        
        # Get database
        db = client.carlosglass
        print("MongoDB connection successful!")
        return db
    except Exception as e:
        print(f"MongoDB Connection Error Details: {str(e)}")
        return None

def get_gridfs():
    try:
        db = get_db()
        if db is not None:
            fs = GridFS(db)
            # Verify GridFS connection with a simple operation
            fs.exists(ObjectId())
            print("GridFS connection successful!")
            return fs
        print("Database connection failed, GridFS not initialized")
        return None
    except Exception as e:
        print(f"GridFS Error Details: {str(e)}")
        return None

def check_mongodb_connection():
    """Test MongoDB and GridFS connections"""
    try:
        db = get_db()
        if db is not None:
            fs = GridFS(db)
            fs.exists(ObjectId())
            return True
        return False
    except Exception as e:
        print(f"Connection Check Error: {str(e)}")
        return False