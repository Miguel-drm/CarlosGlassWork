from flask import Flask
from flask_session import Session
from Website.firebase_config import initialize_firebase
from .admin import admin_bp
from .admin.commands import init_admin_commands
from .filters import bp as filters_bp, init_filters  # Modified import

def create_app():
    initial_app = Flask(__name__)
    initial_app.config['SECRET_KEY'] = 'secret'
    initial_app.config['SESSION_TYPE'] = 'filesystem'

    # Initialize Firebase before registering blueprints
    initialize_firebase()

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
