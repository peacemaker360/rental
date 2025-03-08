import os
import json
from flask import current_app as app
from flask import flash, redirect, render_template, send_from_directory, url_for, request
from flask_login import current_user, login_required

from app import db
from app.models import Instrument, Customer, Rental, RentalHistory
from .forms import InstrumentForm, CustomerForm, RentalForm, BulkCustomerImportForm

import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


#################
# MAIN Routes
# Quelle: Übernommen aus den Beispielen
#################
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    return render_template('index.html', title='Home')


#################
# Files
# Quelle: https://github.com/Azure-Samples/msdocs-flask-postgresql-sample-app/blob/main/app.py
#################
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

#################
# Instruments Routes
# Quelle: Eigenentwicklung
#################


@app.route('/instruments')
@login_required
def instruments():
    search = request.args.get('search', '').strip()
    filterAvailable = request.args.get('is_available', '').strip().lower()
    filterOverdue = request.args.get('show_overdue', '').strip().lower()
    page = request.args.get('page', 1, type=int)

    query = Instrument.query  # start with a query object

    if search:
        if len(search) < app.config.get('SEARCH_REQ_MIN'):
            flash("Please provide more than {0} search characters".format(app.config.get('SEARCH_REQ_MIN')), 'info')
            return redirect(url_for('instruments'))
        else:
            query = Instrument.search(search)

    # Paginate using ITEMS_PER_PAGE
    paginate_obj = query.order_by(Instrument.name.asc()).paginate(
        page=page, per_page=app.config.get('ITEMS_PER_PAGE', 10), error_out=False
    )
    instruments = paginate_obj.items
    prev_url = url_for('instruments', page=paginate_obj.prev_num, search=search,
                       is_available=filterAvailable) if paginate_obj.has_prev else None
    next_url = url_for('instruments', page=paginate_obj.next_num, search=search,
                       is_available=filterAvailable) if paginate_obj.has_next else None

    # Apply filterAvailable if set
    if filterAvailable == 'true':
        instruments = list(filter(lambda i: not i.is_rented, instruments))
    elif filterAvailable == 'false':
        instruments = list(filter(lambda i: i.is_rented, instruments))

    # Apply show_overdue if set
    if filterOverdue == 'true':
        instruments = list(filter(lambda i: i.is_overdue, instruments))
    elif filterOverdue == 'false' or None:
        instruments = list(filter(lambda i: not i.is_overdue, instruments))

    # Prepare some stats if needed (as in your original code)
    total_instruments = Instrument.query.count()
    available_instruments = sum(
        1 for inst in Instrument.query.all() if inst.is_available)
    stats = {
        'total': total_instruments,
        'available': available_instruments,
        'unavailable': total_instruments - available_instruments,
        'overdue': sum(1 for inst in Instrument.query.all() if inst.is_overdue)
    }

    if not instruments:
        flash('No instrument records found.', 'info')
    return render_template('instruments.html',
                           instruments=instruments,
                           title="Instrumente",
                           search=search,
                           filterAvailable=filterAvailable,
                           filterOverdue=filterOverdue,
                           paginate=paginate_obj,
                           prev_url=prev_url,
                           next_url=next_url,
                           stats=stats)


@app.route('/instruments/add', methods=['GET', 'POST'])
@login_required
def new_instrument():
    form = InstrumentForm()
    if request.method == 'POST':
        if request.form.get('submit') == 'Cancel':
            return redirect(url_for('instruments'))
    if form.validate_on_submit():
        instrument = Instrument(name=form.name.data,
                                brand=form.brand.data,
                                type=form.type.data,
                                serial=form.serial.data,
                                description=form.description.data,
                                price=form.price.data)
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
            if request.form.get('submit') == 'Cancel':
                return redirect(url_for('instruments'))
        instrument.name = form.name.data
        instrument.brand = form.brand.data
        instrument.type = form.type.data
        instrument.serial = form.serial.data
        instrument.description = form.description.data
        instrument.price = form.price.data
        db.session.commit()
        flash('Instrument updated successfully!', 'success')

        # Get the source page from the query parameter
        source_page = request.args.get('source', 'instruments')

        # Redirect to the source page
        return redirect(url_for(source_page))
    return render_template('instrument_form.html', form=form, action='Edit')


@app.route('/instruments/<int:id>/delete', methods=['POST'])
@login_required
def delete_instrument(id):
    instrument = Instrument.query.get_or_404(id)
    active_rentals = Rental.query.filter_by(instrument_id=instrument.id).all()
    if active_rentals:
        flash('Cannot delete instrument with active rentals.', 'danger')
        return redirect(url_for('instruments'))
    db.session.delete(instrument)
    db.session.commit()
    flash('Instrument deleted successfully!', 'success')
    # Get the source page from the query parameter
    source_page = request.args.get('source', 'instruments')

    # Redirect to the source page
    return redirect(url_for(source_page))


#################
# Customer Routes
# Quelle: Eigenentwicklung
#################
@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Customer.query.filter_by(is_active=True)
    if search:
        if len(search) < app.config.get('SEARCH_REQ_MIN'):
            flash("Please provide more than {0} search characters".format(app.config.get('SEARCH_REQ_MIN')), 'info')
            return redirect(url_for('customers'))
        else:
            query = Customer.search(search)

    paginate = query.order_by(Customer.lastname.asc()).paginate(
        page=page, per_page=app.config.get('USERS_PER_PAGE', 10), error_out=False
    )
    customers = paginate.items
    prev_url = url_for('customers', page=paginate.prev_num, search=search) if paginate.has_prev else None
    next_url = url_for('customers', page=paginate.next_num, search=search) if paginate.has_next else None

    if not customers:
        flash('No customer records found.', 'info')
    return render_template('customers.html',
                           customers=customers,
                           title="Mitglieder",
                           search=search,
                           paginate=paginate,
                           prev_url=prev_url,
                           next_url=next_url)


@app.route('/customers/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    form = CustomerForm()
    if request.method == 'POST':
        if request.form.get('submit') == 'Cancel':
            return redirect(url_for('customers'))
    if form.validate_on_submit():
        customer = Customer(
            firstname=form.firstname.data,
            lastname=form.lastname.data,
            email=form.email.data,
            phone=form.phone.data
        )

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
            if request.form.get('submit') == 'Cancel':
                return redirect(url_for('customers'))
        customer.firstname = form.firstname.data
        customer.lastname = form.lastname.data
        customer.email = form.email.data
        customer.phone = form.phone.data
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        # Get the source page from the query parameter
        source_page = request.args.get('source', 'customers')

        # Redirect to the source page
        return redirect(url_for(source_page))
    return render_template('customer_form.html', form=form, action='Edit')


@app.route('/customers/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    active_rentals = Rental.query.filter_by(customer_id=customer.id).all()
    if active_rentals:
        flash('Cannot delete customer with active rentals.', 'danger')
        return redirect(url_for('customers'))
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully!', 'success')
    # Get the source page from the query parameter
    source_page = request.args.get('source', 'customers')

    # Redirect to the source page
    return redirect(url_for(source_page))


#################
# Rentals Routes
# Quelle: Eigenentwicklung
#################
@app.route('/rentals')
@login_required
def rentals():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Rental.query  # start with the base query

    if search:
        if len(search) < app.config.get('SEARCH_REQ_MIN'):
            flash("Please provide more than {0} search characters".format(app.config.get('SEARCH_REQ_MIN')), 'info')
            return redirect(url_for('rentals'))
        else:
            query = Rental.search(search)

    # Paginate with ITEMS_PER_PAGE (ensure this is defined in your config)
    paginate_obj = query.order_by(Rental.start_date.desc()).paginate(
        page=page, per_page=app.config.get('ITEMS_PER_PAGE', 10), error_out=False
    )
    rentals = paginate_obj.items
    prev_url = url_for('rentals', page=paginate_obj.prev_num, search=search) if paginate_obj.has_prev else None
    next_url = url_for('rentals', page=paginate_obj.next_num, search=search) if paginate_obj.has_next else None

    if not rentals:
        flash('No rental records found.', 'info')
    return render_template('rentals.html', rentals=rentals, title="Verleihe", search=search,
                           paginate=paginate_obj, prev_url=prev_url, next_url=next_url)


@app.route('/rentals/new', methods=['GET', 'POST'])
# Below routes allow pre-selcation of elements based on URL.
@app.route('/rentals/new/instrument/<int:instrument_id>', methods=['GET', 'POST'])
@app.route('/rentals/new/customer/<int:customer_id>', methods=['GET', 'POST'])
@app.route('/rentals/new/instrument/<int:instrument_id>/customer/<int:customer_id>', methods=['GET', 'POST'])
@app.route('/rentals/new/customer/<int:customer_id>/instrument/<int:instrument_id>', methods=['GET', 'POST'])
@login_required
def new_rental(instrument_id=None, customer_id=None, ):
    form = RentalForm()
    # initialize data for the dropdowns
    form.instrument.query = db.session.query(Instrument)
    form.customer.query = db.session.query(Customer)
    form.customer.choices = [(c.id, c.display_name)
                             for c in Customer.query.filter_by(is_active=True).order_by('email')]
    form.instrument.choices = [(i.id, i.name)
                               for i in Instrument.query.order_by('name')]

    # Pre-select choices based on URL arguments, if present
    if customer_id:
        form.customer.data = Customer.query.get(customer_id)
    if instrument_id:
        form.instrument.data = Instrument.query.get(instrument_id)

    if request.method == 'POST':
        if request.form.get('submit') == 'Cancel':
            return redirect(url_for('rentals'))
    if form.validate_on_submit():
        rental = Rental(customer_id=form.customer.data.id, instrument_id=form.instrument.data.id,
                        start_date=form.start_date.data, end_date=form.end_date.data)
        # instrument = Instrument.query.get_or_404(form.instrument.data.id)
        # Check for availability of the instrument before saving. show info to user.
        if form.instrument.data.is_available is False:
            flash(
                "Rental cannot be placed. Instrument '{}' already in use!".format(form.instrument.data.name), 'danger')
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
        # Get the source page from the query parameter
        source_page = request.args.get('source', 'rentals')

        # Redirect to the source page
        return redirect(url_for(source_page))
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
        form.customer.choices = [(c.id, c.display_name)
                                 for c in Customer.query.order_by('email')]
        form.instrument.choices = [(i.id, i.name)
                                   for i in Instrument.query.order_by('name')]
    if form.validate_on_submit():
        if request.method == 'POST':
            if request.form.get('submit') == 'Cancel':
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
        # Get the source page from the query parameter
        source_page = request.args.get('source', 'rentals')

        # Redirect to the source page
        return redirect(url_for(source_page))
    return render_template('rental_form.html', form=form, action='Edit')


@app.route('/rentals/<int:id>/delete', methods=['POST'])
@login_required
def delete_rental(id):
    rental = Rental.query.get_or_404(id)
    db.session.delete(rental)
    db.session.commit()
    flash('Rental deleted successfully!', 'success')
    # Get the source page from the query parameter
    source_page = request.args.get('source', 'rentals')

    # Redirect to the source page
    return redirect(url_for(source_page))


@app.route('/rentals/<int:id>/return', methods=['POST'])
@login_required
def return_rental(id):
    # logic to return a rental
    rental = Rental.query.get_or_404(id)
    rental.end_rental()
    db.session.commit()
    flash('Rental returned successfully!', 'success')
    source_page = request.args.get('source', 'rentals')
    return redirect(url_for(source_page))

#################
# Histroy Routes
# Quelle: Eigenentwicklung
#################


@app.route('/history')
@login_required
def rentals_history():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    query = RentalHistory.query

    if search:
        if len(search) < app.config.get('SEARCH_REQ_MIN'):
            flash("Please provide more than {0} search characters".format(app.config.get('SEARCH_REQ_MIN')), 'info')
            return redirect(url_for('rentals_history'))
        else:
            query = RentalHistory.search(search)

    paginate_obj = query.order_by(RentalHistory.timestamp.desc()).paginate(
        page=page, per_page=app.config.get('HISTORY_PER_PAGE', 10), error_out=False
    )
    history = paginate_obj.items
    prev_url = url_for('rentals_history', page=paginate_obj.prev_num, search=search) if paginate_obj.has_prev else None
    next_url = url_for('rentals_history', page=paginate_obj.next_num, search=search) if paginate_obj.has_next else None

    if not history:
        flash('No history records found.', 'info')
    return render_template('history.html', history=history, title="History", search=search,
                           paginate=paginate_obj, prev_url=prev_url, next_url=next_url)

#################
# User import Routes
# Quelle: Eigenentwicklung
#################


# routes.py


@app.route('/import_users', methods=['GET', 'POST'])
@login_required
def import_users():
    if current_user.role > 1:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    form = BulkCustomerImportForm()
    if form.validate_on_submit():
        # Determine which button was pressed
        if form.submit_verify.data:
            json_data = form.json_data.data
            exclude_groups_str = form.exclude_groups.data
            exclude_group_ids = []

            if exclude_groups_str:
                try:
                    exclude_group_ids = [int(id.strip()) for id in exclude_groups_str.split(
                        ',') if id.strip().isdigit()]
                except ValueError:
                    flash('Exclude Group IDs must be integers separated by commas.', 'danger')
                    return redirect(url_for('import_users'))

            try:
                parsed_data = json.loads(json_data)
                users = parsed_data.get('data', [])

                if not isinstance(users, list) or len(users) < 1:
                    flash('Invalid JSON format: "data" should be a non-empty list.', 'danger')
                    return redirect(url_for('import_users'))

                # Exclude users belonging to specified groups
                if exclude_group_ids:
                    users = [user for user in users if user.get('attributes', {}).get(
                        'primary_group_id') not in exclude_group_ids]
                    flash(f'Excluded users from groups: {", ".join(map(str, exclude_group_ids))}', 'info')

                # Store filtered users in session or another method if needed for preview
                # For simplicity, we'll just flash the count
                user_count = len(users)
                flash(f'Verification successful. {user_count} user(s) ready for import.', 'success')
                return redirect(url_for('import_users'))

            except json.JSONDecodeError:
                flash('Invalid JSON data.', 'danger')
            except Exception as e:
                flash(f'An error occurred during verification: {str(e)}', 'danger')

        elif form.submit_import.data:
            json_data = form.json_data.data
            exclude_groups_str = form.exclude_groups.data
            exclude_group_ids = []

            if exclude_groups_str:
                try:
                    exclude_group_ids = [int(id.strip()) for id in exclude_groups_str.split(
                        ',') if id.strip().isdigit()]
                except ValueError:
                    flash('Exclude Group IDs must be integers separated by commas.', 'danger')
                    return redirect(url_for('import_users'))

            try:
                parsed_data = json.loads(json_data)
                users = parsed_data.get('data', [])

                if not isinstance(users, list) or len(users) < 1:
                    flash('Invalid JSON format: "data" should be a non-empty list.', 'danger')
                    return redirect(url_for('import_users'))

                # Exclude users belonging to specified groups
                if exclude_group_ids:
                    users = [user for user in users if user.get('attributes', {}).get(
                        'primary_group_id') not in exclude_group_ids]
                    flash(f'Excluded users from group IDs: {", ".join(map(str, exclude_group_ids))}', 'info')

                imported = 0
                updated = 0
                skipped_users = []

                for user_data in users:
                    attributes = user_data.get('attributes', {})
                    email = attributes.get('email')
                    first_name = attributes.get('first_name')
                    last_name = attributes.get('last_name')
                    groups = attributes.get('primary_group_id', [])
                    if not isinstance(groups, list):
                        groups = [groups]

                    if not email:
                        skipped_users.append({
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'reason': 'Missing email'
                        })
                        continue

                    existing_user = Customer.query.filter_by(
                        email=email).first()
                    if existing_user:
                        # Update existing user
                        existing_user.firstname = str(first_name)
                        existing_user.lastname = str(last_name)
                        existing_user.groups = json.dumps(groups)
                        existing_user.update_active_status()
                        updated += 1
                    else:
                        # Create new user
                        new_user = Customer(
                            email=email,
                            firstname=first_name,
                            lastname=last_name,
                            groups=json.dumps(groups)
                        )
                        db.session.add(new_user)
                        imported += 1

                db.session.commit()
                flash(f'Import completed: {imported} user(s) imported, {updated} user(s) updated.', 'success')

                if skipped_users:
                    skipped_message = "Skipped the following users due to errors:\n\n"
                    for user in skipped_users:
                        skipped_message += f"Name: {user.get('first_name', '')} {user.get('last_name', '')}, Email: {
                            user.get('email', 'N/A')}, Reason: {user.get('reason')}"
                    flash(skipped_message, 'warning')

            except json.JSONDecodeError:
                flash('Invalid JSON data.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred during import: {str(e)}', 'danger')

            return redirect(url_for('import_users'))
    return render_template('import.html', form=form)
