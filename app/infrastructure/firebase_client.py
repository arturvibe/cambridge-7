import firebase_admin
from firebase_admin import credentials

def initialize_firebase_app():
    """Initializes the Firebase Admin SDK."""
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

def get_firebase_app():
    """Returns the initialized Firebase app."""
    if not firebase_admin._apps:
        initialize_firebase_app()
    return firebase_admin.get_app()
