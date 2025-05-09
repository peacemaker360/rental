from flask import current_app as app
from flask_restful import Api, Resource, abort, fields, marshal_with, marshal, reqparse
from flask_login import login_required

from app import db
from app.models import Customer, Instrument, Rental, RentalHistory

#################
# API
# Erstellt mit hilfe des modules flask_restful
# Quelle: Eigenentwicklung
# Docs: https://flask-restful.readthedocs.io/en/latest/quickstart.html
# Help: flask restful ist ein effizientes modul um REST API für klassen zu erstellen
#################

# Initiate the api from flask_restful
api = Api(app)

#################
# Fields overloading
# Help: wird genutzt, damit z.b. nicht alle felder eines objekts/klasse in der API gelistet wird
#################

# Fields for Customer
customer_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'firstname': fields.String,
    'lastname': fields.String,
    'email': fields.String,
    'phone': fields.String,
    # Using RFC 822 format for datetime
    'created': fields.DateTime(dt_format='rfc822')
}

# Fields for Instrument
instrument_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'brand': fields.String,
    'type': fields.String,
    'serial': fields.String,
    'description': fields.String,
    'price': fields.Float,
    'created': fields.DateTime(dt_format='rfc822'),
    'is_available': fields.Boolean
}

# Fields for Rental
rental_fields = {
    'id': fields.Integer,
    'start_date': fields.String,
    'end_date': fields.String,
    'description': fields.String,
    'customer': fields.Nested(customer_fields),  # Nested Customer fields
    'instrument': fields.Nested(instrument_fields),  # Nested Instrument fields
    # 'self': fields.Url('rentalresource', absolute=True)  # Generate URL for specific rental # => does not work ATM
}

# Fields for RentalHistory
rentalHistory_fields = {
    'id': fields.Integer,
    'rental': fields.Nested(rental_fields),  # Nested Rental fields
    'timestamp': fields.String
}

#################
# Params parser
# Help: wird genutzt, bei post/put inputs korrekt geparsed werden
#################
# Define the parser for the Customer model
parser = reqparse.RequestParser()
parser.add_argument('name', type=str)  # Not required anymore
parser.add_argument('firstname', type=str, required=True,
                    help='First name cannot be blank')
parser.add_argument('lastname', type=str, required=True,
                    help='Last name cannot be blank')
parser.add_argument('email', type=str, required=True,
                    help='Email cannot be blank')
parser.add_argument('phone', type=str, required=True,
                    help='Phone cannot be blank')


#################
# Definitions
#################
class CustomerListResource(Resource):
    @login_required
    def get(self):
        customers = Customer.query.all()
        # Using marshal directly since it's a list
        return marshal(customers, customer_fields)

    @login_required
    @marshal_with(customer_fields)
    def post(self):
        args = parser.parse_args()

        # Create a new customer instance
        customer = Customer(
            name=args.get('name') or f"{args['firstname']} {args['lastname']}",
            firstname=args['firstname'],
            lastname=args['lastname'],
            email=args['email'],
            phone=args['phone']
        )

        # Try add the new customer to the database
        try:
            db.session.add(customer)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            abort(500, message="An error occurred while processing your request.")

        # Return the newly created customer
        return customer, 201


class InstrumentListResource(Resource):
    @login_required
    def get(self):
        instruments = Instrument.query.all()
        return marshal(instruments, instrument_fields)


class RentalListResource(Resource):
    @login_required
    def get(self):
        rentals = Rental.query.all()
        return marshal(rentals, rental_fields)


class CustomerResource(Resource):
    @login_required
    @marshal_with(customer_fields)
    def get(self, customer_id):
        customer = Customer.query.get(customer_id)
        if not customer:
            abort(404, message="Customer not found")
        return customer

    @login_required
    def delete(self, customer_id):
        # Retrieve the customer by ID
        customer = Customer.query.get(customer_id)

        # Check if the customer exists
        if not customer:
            abort(404, message="Customer not found")

        # Delete the customer from the database
        db.session.delete(customer)
        db.session.commit()

        return {'message': 'Customer deleted successfully'}, 200


class InstrumentResource(Resource):
    @login_required
    @marshal_with(instrument_fields)
    def get(self, instrument_id):
        instrument = Instrument.query.get(instrument_id)
        if not instrument:
            abort(404, message="Instrument not found")
        return instrument

    @login_required
    def delete(self, instrument_id):
        # Retrieve the instrument by ID
        instrument = Instrument.query.get(instrument_id)

        # Check if the instrument exists
        if not instrument:
            abort(404, message="Instrument not found")

        # Delete the instrument from the database
        db.session.delete(instrument)
        db.session.commit()

        return {'message': 'Instrument deleted successfully'}, 200


class RentalResource(Resource):
    @login_required
    @marshal_with(rental_fields)
    def get(self, rental_id):
        rental = Rental.query.get(rental_id)
        if not rental:
            abort(404, message="Rental not found")
        return rental
    
class BulkUserCustomerAPI(Resource):

    def post(self):
        data = request.json
        skipped_users = []

        customer_data = data['data']
        phone_data = {item['id']: item['attributes'] for item in data['included'] if item['type'] == 'phone_numbers'}

        for item in customer_data:
            attributes = item['attributes']
            # Extract relevant details
            first_name = attributes['first_name']
            last_name = attributes['last_name']
            email = attributes['email']
            if not email:  # Validate email existence
                skipped_users.append(customer_data)
                continue  # Skip processing this user   
            phone = None
            if 'phone_numbers' in item['relationships']:
                phone_id = item['relationships']['phone_numbers']['data'][0]['id']
                phone = phone_data[phone_id]['number']

            # Get foreign object ID
            foreign_id = item['id']

            # Check if customer already exists in the database
            customer = Customer.query.filter_by(email=email).first()
            if customer:
                # Update customer details if they have changed
                customer.name = f"{first_name} {last_name}"
                customer.firstname = first_name
                customer.lastname = last_name
                customer.phone = phone
                customer.connected = True  # mark as connected
            else:
                # Add new customer
                new_customer = Customer(
                    name=f"{first_name} {last_name}",
                    firstname=first_name,
                    lastname=last_name,
                    email=email,
                    phone=phone,
                    foreign_id=foreign_id,
                    connected=True
                )
                db.session.add(new_customer)

        # Mark customers not in the JSON input as disconnected
        all_emails_in_input = [item['attributes']['email'] for item in customer_data]
        customers_to_disconnect = Customer.query.filter(~Customer.email.in_(all_emails_in_input)).all()
        for customer in customers_to_disconnect:
            customer.connected = False

        db.session.commit()

        if skipped_users:
            return jsonify({
                "message": "Import completed with some users skipped.",
                "skipped_users": skipped_users
            }), 200

        return jsonify({"message": "Import successful"}), 200

class RentalHistoryListResource(Resource):
    @login_required
    def get(self):
        rentalHistory = RentalHistory.query.all()
        # Using marshal directly since it's a list
        return marshal(rentalHistory, rentalHistory_fields)


#################
# API Resources (routes)
#################
# Associate resources with routes
api.add_resource(CustomerListResource, '/api/customers/')
api.add_resource(InstrumentListResource, '/api/instruments/')
api.add_resource(RentalListResource, '/api/rentals/')
api.add_resource(RentalHistoryListResource, '/api/history/')

api.add_resource(CustomerResource, '/api/customers/<int:customer_id>')
api.add_resource(InstrumentResource, '/api/instruments/<int:instrument_id>')
api.add_resource(RentalResource, '/api/rentals/<int:rental_id>')


# Add this resource to your API
api.add_resource(BulkUserCustomerAPI, '/api/bulkusercustomer')
