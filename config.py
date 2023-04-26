import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    # The secret key used for generating hashes
    SECRET_KEY = os.environ.get('SECRET_KEY') or '1iqnFcVDN1y61Eza4lD1z2tgAZ3RF9gy'
    # SQLAlchemy configuration parameters
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Detect if server is running as WYSGI dev server and set name if required
    if os.environ.get('SERVER_TYPE') != 'gunicorn':
        SERVER_NAME = 'localhost:5000'

    # Who gets email notifications?
    ADMINS = ["admin@lab2.ifalabs.org"]

    # Pagination settings
    POSTS_PER_PAGE = 5
    USERS_PER_PAGE = 10