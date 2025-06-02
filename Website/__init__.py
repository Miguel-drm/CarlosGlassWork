import os
from flask import Flask
from firebase_admin import credentials, initialize_app
from dotenv import load_dotenv
from flask_session import Session
from .admin import admin_bp
from .admin.commands import init_admin_commands
from .filters import bp as filters_bp, init_filters  # Modified import
import tempfile

load_dotenv()

def create_app():
    initial_app = Flask(__name__)
    initial_app.config['SECRET_KEY'] = os.getenv('nyahahasecret', 'dev')
    initial_app.config['SESSION_TYPE'] = 'filesystem'
    initial_app.config['SESSION_FILE_DIR'] = tempfile.gettempdir()

    # Initialize Firebase with environment variables
    cred = credentials.Certificate({
        "type": os.getenv('FIREBASE_TYPE'),
        "project_id": os.getenv('FIREBASE_PROJECT_ID'),
        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
        "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
        "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
        "client_id": os.getenv('FIREBASE_CLIENT_ID'),
        "auth_uri": os.getenv('FIREBASE_AUTH_URI'),
        "token_uri": os.getenv('FIREBASE_TOKEN_URI'),
        "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL'),
        "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
    })
    
    initialize_app(cred)

    from .views import views
    initial_app.register_blueprint(views, url_prefix='/')
    
    from .auth import auth_blueprint
    initial_app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    # Register admin blueprint with url_prefix
    initial_app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Register filters blueprint
    initial_app.register_blueprint(filters_bp)

    # Initialize filters
    init_filters(initial_app)  # Added line

    Session(initial_app)

    init_admin_commands(initial_app)

    return initial_app
