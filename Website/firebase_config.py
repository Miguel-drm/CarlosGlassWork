import os
import firebase_admin
from firebase_admin import credentials

# Get the current directory path
current_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(current_dir, 'credentials', 'carlosglasswebsite-firebase-adminsdk-fbsvc-956efd3ac0.json')

def initialize_firebase():
    try:
        # Check if Firebase app is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Initialize Firebase only if it hasn't been initialized yet
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)