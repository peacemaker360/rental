from app import app, db
from .forms import InstrumentForm, CustomerForm, RentalForm
from flask import flash, jsonify, redirect, render_template, url_for, request
from datetime import datetime
from .models import Instrument, Customer, Rental

#################
## MAIN Routes 
#################
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
#@login_required
def index():
    return render_template('index.html', title='Home')


#################
## Instruments Routes 
#################

@app.route('/instruments')
def instruments():
    instruments = Instrument.query.all()
    return render_template('instruments.html', instruments=instruments)

@app.route('/instruments/<int:id>', methods=['GET', 'POST'])
def instrument_detail(id):
    instrument = Instrument.query.get_or_404(id)
    if request.method == 'POST':
        name = request.form['name']
        type = request.form['type']
        description = request.form['description']
        price = request.form['price']
        instrument.name = name
        instrument.type = type
        instrument.description = description
        instrument.price = price
        db.session.commit()
        return redirect(url_for('instruments'))
    else:
        return render_template('instrument_detail.html', instrument=instrument)

@app.route('/instruments/add', methods=['GET', 'POST'])
def instrument_add():
    form = InstrumentForm()
    if form.validate_on_submit():
        name = form.name.data
        type = form.type.data
        description = form.description.data
        price = form.price.data
        instrument = Instrument(name=name, type=type, description=description, price=price)
        db.session.add(instrument)
        db.session.commit()
        return redirect(url_for('instruments'))
    return render_template('instrument_add.html', form)


#################
## Customer Routes 
#################

@app.route('/customers')
def customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)


@app.route('/customers/new', methods=['GET', 'POST'])
def new_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(name=form.name.data, email=form.email.data, phone=form.phone.data)
        db.session.add(customer)
        db.session.commit()
        flash('Customer created successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', form=form, action='New')


@app.route('/customers/<int:id>')
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    return render_template('customer.html', customer=customer)


@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        customer.name = form.name.data
        customer.email = form.email.data
        customer.phone = form.phone.data
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('customer_form.html', form=form, action='Edit')


@app.route('/customers/<int:id>/delete', methods=['POST'])
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
def rentals():
    rentals = Rental.query.all()
    return render_template('rentals.html', rentals=rentals)


@app.route('/rentals/new', methods=['GET', 'POST'])
def new_rental():
    form = RentalForm()
    form.customer.choices = [(c.id, c.name) for c in Customer.query.order_by('name')]
    form.instrument.choices = [(i.id, i.name) for i in Instrument.query.order_by('name')]
    if form.validate_on_submit():
        rental = Rental(customer_id=form.customer.data, instrument_id=form.instrument.data, start_date=form.start_date.data, end_date=form.end_date.data)
        db.session.add(rental)
        db.session.commit()
        flash('Rental created successfully!', 'success')
        return redirect(url_for('rentals'))
    return render_template('rental_form.html', form=form, action='New')


@app.route('/rentals/<int:id>')
def view_rental(id):
    rental = Rental.query.get_or_404(id)
    return render_template('rental.html', rental=rental)


@app.route('/rentals/<int:id>/edit', methods=['GET', 'POST'])
def edit_rental(id):
    rental = Rental.query.get_or_404(id)
    form = RentalForm(obj=rental)
    form.customer.choices = [(c.id, c.name) for c in Customer.query.order_by('name')]
    form.instrument.choices = [(i.id, i.name) for i in Instrument.query.order_by('name')]
    if form.validate_on_submit():
        rental.customer_id = form.customer.data
        rental.instrument_id = form.instrument.data
        rental.start_date = form.start_date.data
        rental.end_date = form.end_date.data
        db.session.commit()
        flash('Rental updated successfully!', 'success')
        return redirect(url_for('rentals'))
    return render_template('rental_form.html', form=form, action='Edit')


@app.route('/rentals/<int:id>/delete', methods=['POST'])
def delete_rental(id):
    rental = Rental.query.get_or_404(id)
    db.session.delete(rental)
    db.session.commit()
    flash('Rental deleted successfully!', 'success')
    return redirect(url_for('rentals'))
