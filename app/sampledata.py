from flask import flash, redirect, url_for
from app import app, db
from .models import Instrument, Customer, Rental
from datetime import date
from random import choice
from flask_login import login_required

##############################################################
# SAMPLE DATA
# Quelle: Eigenentwicklung
# Help: this endpoint is used to initially generate demo data, if the application is empty
##############################################################

@app.route('/generate_data', methods=['GET', 'POST'])
@login_required
def generate_data():
    # Check if function might have been alrady triggerd.
    customers = Customer.query.filter_by(email="member0@example.com").first()
    if customers is not None:
        flash('Sample data already exists!', 'info')
        return redirect(url_for('index'))

    # Generate sample data for Instrument
    instruments = []
    for i in range(5):
        brand = choice(['Yamaha', 'Bach', 'York'])
        type = choice(['Horn', 'Posaune', 'Trompete'])
        serial = 'SN-{}'.format(i)
        price = choice([100, 200, 300])
        description = 'Description for Instrument {}'.format(i)
        instrument = Instrument(brand=brand, type=type, serial=serial, description=description, price=price)
        instruments.append(instrument)

    # Generate sample data for Customer
    customers = []
    for i in range(3):
        firstname = 'Member {}'.format(i)
        lastname = 'Name'
        phone = '031 000 10 0{}'.format(i)
        email = 'member{}@example.com'.format(i)
        customer = Customer(firstname=firstname,lastname=lastname, phone=phone, email=email)
        customers.append(customer)

    # Generate sample data for Rental
    # rentals = []
    # for i in range(2):
    #     instrument = choice(instruments)
    #     customer = choice(customers)
    #     rental = Rental(instrument_id=instrument.id, customer_id=customer.id, start_date=date.today())
    #     rentals.append(rental)

    # Add the sample data to the database
    #db.session.bulk_save_objects(instruments + customers + rentals)
    db.session.bulk_save_objects(instruments + customers)
    db.session.commit()

    # Redirect the user to the homepage
    flash('Sample data generated!', 'success')
    return redirect(url_for('index'))
