import os
from pathlib import Path

# Quelle: Eigene Entwicklung
SECRET_KEY = os.environ.get('SECRET_KEY') or '1iqnFcVDN1y61Eza4lD1z2tgAZ3RF9gy'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
basedir = os.path.abspath(os.path.dirname(__file__))

# Use a local SQLite database instead of MySQL
DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
TIME_ZONE = 'UTC'

STATICFILES_DIRS = (str(BASE_DIR.joinpath('static')),)
STATIC_URL = 'static/'