# app/__init__.py
#Quelle: Eigenentwicklung
import os
from flask import Flask, jsonify, render_template, redirect, request, url_for
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime

# Initiate the app with flask, and set the "static" resoruces folder
app = Flask(__name__, static_folder='static')
#app.config.from_object(Config)

# Loads the environment from the config folder depending on if running in azure (prod) or locally (dev)
# Quelle: https://github.com/Azure-Samples/msdocs-flask-postgresql-sample-app/blob/main/app.py
if 'WEBSITE_HOSTNAME' not in os.environ:
    # local development, where we'll use environment variables
    print("Loading config.development and environment variables from .env file.")
    app.config.from_object('config.development')
else:
    # production
    print("Loading config.production.")
    app.config.from_object('config.production')

# Quelle: https://github.com/Azure-Samples/msdocs-flask-postgresql-sample-app/blob/main/app.py
app.config.update(
    SQLALCHEMY_DATABASE_URI=app.config.get('DATABASE_URI'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

# Set default config values
app.config.update(    
    # Pagination settings
    ITEMS_PER_PAGE = 5,
    USERS_PER_PAGE = 10,
    # Search settings
    SEARCH_REQ_MIN = 3,
)

# Initiate the db and migrate objects from sqlalchemy
db = SQLAlchemy(app)
migrate = Migrate(app,db)

# Initiate the login manger
login = LoginManager(app)
login.login_view = 'login'

# Load the Bootstrap framwork from the module
bootstrap = Bootstrap(app)

# Create sql schema
#db.create_all()

# This endpoint ensures all request to /api are protected with login and if not a 401 error is returned
@app.before_request
def api_auth():
    if request.path.startswith('/api') and not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized', 'message': 'Please log in to access this resource.'}), 401

# import all outsourced python files, so that init remains as clean as possible
from app import models, errors, routes, auth, api, sampledata #, views

