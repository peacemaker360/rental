# app/__init__.py
#from config import Config
from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime

app = Flask(__name__, static_folder='static')
#app.config.from_object(Config)

if 'WEBSITE_HOSTNAME' not in os.environ:
    # local development, where we'll use environment variables
    print("Loading config.development and environment variables from .env file.")
    app.config.from_object('azureproject.development')
else:
    # production
    print("Loading config.production.")
    app.config.from_object('azureproject.production')

# Quelle: https://github.com/Azure-Samples/msdocs-flask-postgresql-sample-app/blob/main/app.py
app.config.update(
    SQLALCHEMY_DATABASE_URI=app.config.get('DATABASE_URI'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

app.config.update(
    # Admins to notify via email
    #ADMINS = ["admin@lab2.ifalabs.org"]
    
    # Pagination settings
    POSTS_PER_PAGE = 5,
    USERS_PER_PAGE = 10,
)


db = SQLAlchemy(app)
migrate = Migrate(app,db)

bootstrap = Bootstrap(app)

# Create sql schema
#db.create_all()

# import all outsourced python files, so that init remains as clean as possible
from app import models, errors, routes, sampledata #, views, api
