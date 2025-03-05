import os
from pathlib import Path

#Quelle: Eigene entwicklung
SECRET_KEY = os.environ.get('SECRET_KEY') or '1iqnFcVDN1y61Eza4lD1z2tgAZ3RF9gy'
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
basedir = os.path.abspath(os.path.dirname(__file__))
# DATABASE_URI = 'postgresql+psycopg2://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
#     dbuser=os.environ['DBUSER'],
#     dbpass=os.environ['DBPASS'],
#     dbhost=os.environ['DBHOST'],
#     dbname=os.environ['DBNAME']
# )
#DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
# DATABASE_URI = 'mysql+pymysql://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
#     dbuser='rentalapp',
#     dbpass='rentalapp',
#     dbhost='localhost',
#     dbname='rentalapp'
# )
DATABASE_URI = 'mysql+pymysql://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
    dbuser='musikge6_rent',
    dbpass='d-tQYzXdMbvq!E*2T269',
    dbhost='musikge6.mysql.db.hostpoint.ch',
    dbname='musikge6_rentalapp'
)

TIME_ZONE = 'UTC'

STATICFILES_DIRS = (str(BASE_DIR.joinpath('static')),)
STATIC_URL = 'static/'