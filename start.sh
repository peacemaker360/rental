# Quelle: https://github.com/Azure-Samples/msdocs-flask-postgresql-sample-app/blob/main/startup.sh
flask db upgrade
gunicorn --workers 2 --threads 4 --timeout 60 --access-logfile \
    '-' --error-logfile '-' --bind=0.0.0.0:8000 \
     --chdir=/home/site/wwwroot app:app