## DB Migrations

### Init
flask db init
flask db revision --autogenerate -m "Initial migration"
flask db upgrade

### Updates
flask db revision --autogenerate -m "Made change XYZ"
flask db upgrade