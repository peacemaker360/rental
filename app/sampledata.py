from flask import flash, redirect, url_for
from app import app, db
from .models import Instrument, Customer, Rental
from datetime import date
from random import choice

##############################################################
# SAMPLE DATA
##############################################################

@app.route('/generate_data', methods=['GET', 'POST'])
def generate_data():
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
        #db.session.add(customer)

    # Add the sample data to the database
    db.session.bulk_save_objects(instruments + customers)
    db.session.commit()

    # Redirect the user to the homepage
    flash('Sample data generated!', 'info')
    return redirect(url_for('index'))
