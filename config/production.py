import os

# Quelle: https://github.com/Azure-Samples/msdocs-flask-postgresql-sample-app/blob/main/azureproject/__init__.py
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

ALLOWED_HOSTS = [os.environ['WEBSITE_HOSTNAME']] if 'WEBSITE_HOSTNAME' in os.environ else []
CSRF_TRUSTED_ORIGINS = ['https://' + os.environ['WEBSITE_HOSTNAME']] if 'WEBSITE_HOSTNAME' in os.environ else []

# Configure Postgres database based on connection string of the libpq Keyword/Value form
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
#conn_str = os.environ['AZURE_POSTGRESQL_CONNECTIONSTRING']
#conn_str_params = {pair.split('=')[0]: pair.split('=')[1] for pair in conn_str.split(' ')}

# Connection string for a postgres db
# DATABASE_URI = 'postgresql+psycopg2://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
#     dbuser=conn_str_params['user'],
#     dbpass=conn_str_params['password'],
#     dbhost=conn_str_params['host'],
#     dbname=conn_str_params['dbname']

# Connection string for a mysql db
DATABASE_URI = 'mysql+pymysql://{dbuser}:{dbpass}@{dbhost}/{dbname}?ssl_key=azure_iac/DigiCertGlobalRootCA.crt.pem'.format(
    dbuser=os.environ['AZURE_MYSQL_USER'],
    dbpass=os.environ['AZURE_MYSQL_PASSWORD'],
    dbhost=os.environ['AZURE_MYSQL_HOST'],
    dbname=os.environ['AZURE_MYSQL_NAME']

)