# app/__init__.py
from config import Config
from flask import Flask, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app,db)

bootstrap = Bootstrap(app)

# Create sql schema
#db.create_all()

# import all outsourced python files, so that init remains as clean as possible
from app import models, errors, routes #, views, api
