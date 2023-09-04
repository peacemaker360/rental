import os
from random import choice
from sqlalchemy import and_, or_
from app import app, db
from .forms import InstrumentForm, CustomerForm, RentalForm
from flask import flash, jsonify, redirect, render_template, send_from_directory, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from datetime import date, datetime
from app.models import Instrument, Customer, Rental, RentalHistory


#################
## MAIN Routes 
#################
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    return render_template('index.html', title='Home')


#################
## Files
# Quelle: https://github.com/Azure-Samples/msdocs-flask-postgresql-sample-app/blob/main/app.py
#################
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

#################
## Instruments Routes 
#################
@app.route('/instruments')
@login_required
def instruments():
    search = request.args.get('search', '').strip()
    filterAvailable = request.args.get('is_available', '').strip().lower()

    total_instruments = Instrument.query.count()
    available_instruments = sum(1 for inst in Instrument.query.all() if inst.is_available)
    unavailable_instruments = total_instruments - available_instruments
    stats = {
        'total': total_instruments,
        'available': available_instruments,
        'unavailable': unavailable_instruments
    }
       
    if search:
        if len(search) < 3:
            flash('Please provide more than 3 search characters', 'info')
            return redirect(url_for('instruments'))
        else:
            instruments = Instrument.search_instruments(search)
    else:
        instruments = Instrument.query.all()
    # If filterAvailable is 'true' or 'false', return a filtered list
    if filterAvailable == 'true':
        instruments = list(filter(lambda i: i.is_available, instruments))
    elif filterAvailable == 'false':
        instruments = list(filter(lambda i: not i.is_available, instruments))

    # Return a help message, if the retruned instruments list is null or zero.
    if instruments is None or len(instruments) == 0:
        flash('No instrument records found.', 'info')
    return render_template('instruments.html', instruments=instruments, title="Instrumente", search=search, filterAvailable=filterAvailable, stats=stats)

@app.route('/instruments/add', methods=['GET', 'POST'])
@login_required
def new_instrument():
    form = InstrumentForm()
    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('instruments'))
    if form.validate_on_submit():
        instrument = Instrument(name=form.name.data, brand=form.brand.data, type=form.type.data, serial=form.serial.data, description=form.description.data, price=form.price.data)
        db.session.add(instrument)
        db.session.commit()
        flash('Instrument created successfully!', 'success')
        return redirect(url_for('instruments'))
    return render_template('instrument_form.html', form=form, action='Add')

@app.route('/instruments/<int:id>')
@login_required
def view_instrument(id):
    instrument = Instrument.query.get_or_404(id)
    instrumentHistory = RentalHistory.getBy_instrumentId(id)
    return render_template('instrument.html', instrument=instrument, history=instrumentHistory)

@app.route('/instruments/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_instrument(id):
    instrument = Instrument.query.get_or_404(id)
    form = InstrumentForm(obj=instrument)
    if form.validate_on_submit():
        if request.method == 'POST':
            if form.cancel.data:
                return redirect(url_for('instruments'))
        instrument.name = form.name.data
        instrument.brand = form.brand.data
        instrument.type = form.type.data
        instrument.serial = form.serial.data
        instrument.description = form.description.data
        instrument.price = form.price.data
        db.session.commit()
        flash('Instrument updated successfully!', 'success')
        return redirect(url_for('instruments'))
    return render_template('instrument_form.html', form=form, action='Edit')

@app.route('/instruments/<int:id>/delete', methods=['POST'])
@login_required
def delete_instrument(id):
    instrument = Instrument.query.get_or_404(id)
    db.session.delete(instrument)
    db.session.commit()
    flash('Instrument deleted successfully!', 'success')
    return redirect(url_for('instruments'))


#################
## Customer Routes 
#################
@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '').strip()
    if search:
        if len(search) < 3:
            flash('Please provide more than 3 search characters', 'info')
            return redirect(url_for('customers'))
        else:
            customers = Customer.search_customers(search)
    else:
        customers = Customer.query.all()
    if customers is None or len(customers) == 0:
        flash('No customer records found.', 'info')
    return render_template('customers.html', customers=customers, title="Mitglieder", search=search)

@app.route('/customers/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    form = CustomerForm()
    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('customers'))
    if form.validate_on_submit():
        customer = Customer(name=form.name.data, firstname=form.firstname.data, lastname=form.lastname.data, email=form.email.data, phone=form.phone.data)
        db.session.add(customer)
        db.session.commit()
        flash('Customer created successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', form=form, action='New')

@app.route('/customers/<int:id>')
@login_required
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    return render_template('customer.html', customer=customer)

@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        if request.method == 'POST':
            if form.cancel.data:
                return redirect(url_for('customers'))
        customer.name = form.name.data
        customer.firstname = form.firstname.data
        customer.lastname = form.lastname.data
        customer.email = form.email.data
        customer.phone = form.phone.data
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', form=form, action='Edit')

@app.route('/customers/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers'))


#################
## Rentals Routes 
#################
@app.route('/rentals')
@login_required
def rentals():
    search = request.args.get('search', '').strip()
    if search:
        if len(search) < 3:
            flash('Please provide more than 3 search characters', 'info')
            return redirect(url_for('rentals'))
        else:
            rentals = Rental.search_rentals(search)
    else:
        rentals = Rental.query.all()
    if rentals is None or len(rentals) == 0:
        flash('No rental records found.', 'info')
    return render_template('rentals.html', rentals=rentals, title="Verleihe", search=search)

@app.route('/rentals/new', methods=['GET', 'POST'])
# Below routes allow pre-selcation of elements based on URL.
@app.route('/rentals/new/instrument/<int:instrument_id>', methods=['GET', 'POST'])
@app.route('/rentals/new/customer/<int:customer_id>', methods=['GET', 'POST'])
@app.route('/rentals/new/instrument/<int:instrument_id>/customer/<int:customer_id>', methods=['GET', 'POST'])
@app.route('/rentals/new/customer/<int:customer_id>/instrument/<int:instrument_id>', methods=['GET', 'POST'])
@login_required
def new_rental(instrument_id=None,customer_id=None, ):
    form = RentalForm()
    form.instrument.query = db.session.query(Instrument)
    form.customer.query = db.session.query(Customer)
    form.customer.choices = [(c.id, c.name) for c in Customer.query.order_by('name')]
    form.instrument.choices = [(i.id, i.name) for i in Instrument.query.order_by('name')]

    # Pre-select choices based on URL arguments, if present
    if customer_id:
        form.customer.data = Customer.query.get(customer_id)
    if instrument_id:
        form.instrument.data = Instrument.query.get(instrument_id)

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('rentals'))
    if form.validate_on_submit():
        rental = Rental(customer_id=form.customer.data.id, instrument_id=form.instrument.data.id, start_date=form.start_date.data, end_date=form.end_date.data)
        #instrument = Instrument.query.get_or_404(form.instrument.data.id)
        if form.instrument.data.is_available is False:
           flash("Rental cannot be placed. Instrument '{}' already in use!".format(form.instrument.data.name), 'danger')
           return redirect(url_for('rentals'))
        try:
            db.session.add(rental)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            flash("Error: '{}'".format(e), 'danger')
            return redirect(url_for('rentals'))
        history = RentalHistory(rental)
        db.session.add(history)
        db.session.commit()
        flash('Rental created successfully!', 'success')
        return redirect(url_for('rentals'))
    return render_template('rental_form.html', form=form, action='New')

@app.route('/rentals/<int:id>')
@login_required
def view_rental(id):
    rental = Rental.query.get_or_404(id)
    return render_template('rental.html', rental=rental)

@app.route('/rentals/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_rental(id):
    rental = Rental.query.get_or_404(id)
    form = RentalForm(obj=rental)
    form.instrument.query = db.session.query(Instrument)
    form.customer.query = db.session.query(Customer)
    if request.method == 'GET':
        form.customer.choices = [(c.id, c.name) for c in Customer.query.order_by('name')]
        form.instrument.choices = [(i.id, i.name) for i in Instrument.query.order_by('name')]
    if form.validate_on_submit():
        if request.method == 'POST':
            if form.cancel.data:
                return redirect(url_for('rentals'))
        rental.customer_id = form.customer.data.id
        rental.instrument_id = form.instrument.data.id
        rental.start_date = form.start_date.data
        rental.end_date = form.end_date.data
        rental.description = form.description.data
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            flash("Error: '{}'".format(e), 'danger')
            return redirect(url_for('rentals'))
        history = RentalHistory(rental)
        db.session.add(history)
        db.session.commit()
        flash('Rental updated successfully!', 'success')
        return redirect(url_for('rentals'))
    return render_template('rental_form.html', form=form, action='Edit')

@app.route('/rentals/<int:id>/delete', methods=['POST'])
@login_required
def delete_rental(id):
    rental = Rental.query.get_or_404(id)
    db.session.delete(rental)
    db.session.commit()
    flash('Rental deleted successfully!', 'success')
    return redirect(url_for('rentals'))


#################
## Histroy Routes 
#################
@app.route('/history')
@login_required
def rentals_history():
    search = request.args.get('search', '').strip()
    if search:
        if len(search) < 3:
            flash('Please provide more than 3 search characters', 'info')
            return redirect(url_for('rentals_history'))
        else:
            history = RentalHistory.search_rentalshistory(search)
    else:
        history = RentalHistory.query.order_by(RentalHistory.timestamp.desc()).all()
    if history is None or len(history) == 0:
        flash('No history records found.', 'info')
    return render_template('history.html', history=history, title="History", search=search)