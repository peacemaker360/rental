# app/__init__.py
# Quelle: Eigenentwicklung
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
bootstrap = Bootstrap()


def create_app():
    app = Flask(__name__, static_folder='static')

    # Determine the configuration based on the environment
    if 'WEBSITE_HOSTNAME' not in os.environ:
        # Local development
        # Default to 'development' if ENV is not set
        env = os.getenv('ENV', 'development')
        if env == 'local':
            print("Loading config.local and environment variables from .env file.")
            app.config.from_object('config.local')
        else:
            print("Loading config.development and environment variables from .env file.")
            app.config.from_object('config.development')
    else:
        # Production
        print("Loading config.production.")
        app.config.from_object('config.production')

    # Update SQLAlchemy settings
    app.config.update(
        SQLALCHEMY_DATABASE_URI=app.config.get('DATABASE_URI'),
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        # Pagination settings
        ITEMS_PER_PAGE=5,
        USERS_PER_PAGE=10,
        # Search settings
        SEARCH_REQ_MIN=3,
    )

    # Initialize extensions with the app
    db.init_app(app)
    login.init_app(app)
    bootstrap.init_app(app)
    migrate.init_app(app, db)

    # Configure login settings
    # Replace with your actual login view endpoint
    login.login_view = 'auth.login'
    # Bootstrap class for flash messages
    login.login_message_category = 'info'
    with app.app_context():
        # Import parts of our application
        from . import models, routes, errors, auth, api, sampledata

        # Create database tables if they don't exist
        db.create_all()
    return app


# @app.before_request
# def api_auth():
#     if request.path.startswith('/api') and not current_user.is_authenticated:
#         return jsonify({'error': 'Unauthorized', 'message': 'Please log in to access this resource.'}), 401


# import all outsourced python files, so that init remains as clean as possible
