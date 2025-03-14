# Description: This file contains the routes and logic for importing users and instruments in bulk.
import json
from flask import current_app as app
from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Instrument, Customer, Rental
from .forms import BulkUserImportForm, BulkInstrumentImportForm

import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/import_users', methods=['GET', 'POST'])
@login_required
def import_users():
    if current_user.role > 1:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    form = BulkUserImportForm()
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
    return render_template('bulkImportUsers.html', form=form)


@app.route('/import_instruments', methods=['GET', 'POST'])
@login_required
def import_instruments():
    # Only allow certain roles, etc.
    if current_user.role > 1:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    form = BulkInstrumentImportForm()
    if form.validate_on_submit():
        # Determine which button was pressed (similar logic as in import_users)
        if form.submit_verify.data:
            json_data = form.json_data.data
            try:
                parsed_data = json.loads(json_data)
                instruments_data = parsed_data.get('data', [])
                if not isinstance(instruments_data, list) or len(instruments_data) < 1:
                    flash('Invalid JSON format: "data" should be a non-empty list.', 'danger')
                    return redirect(url_for('import_instruments'))
                # For verification: simply flash the count of instruments
                instrument_count = len(instruments_data)
                flash(f'Verification successful. {instrument_count} instrument(s) ready for import.', 'success')
                # Optionally, you might store the verified JSON in the form or session
            except json.JSONDecodeError:
                flash('Invalid JSON data.', 'danger')
            except Exception as e:
                flash(f'An error occurred during verification: {str(e)}', 'danger')
        elif form.submit_import.data:
            json_data = form.json_data.data
            try:
                parsed_data = json.loads(json_data)
                instruments_data = parsed_data.get('data', [])
                if not isinstance(instruments_data, list) or len(instruments_data) < 1:
                    flash('Invalid JSON format: "data" should be a non-empty list.', 'danger')
                    return redirect(url_for('import_instruments'))

                imported = 0
                updated = 0
                for row in instruments_data:
                    name = row.get('name')
                    serial = row.get('serial')
                    if not name or not serial:
                        continue

                    instrument = Instrument.query.filter_by(serial=serial).first()
                    if instrument:
                        # update existing instrument
                        instrument.brand = row.get('brand')
                        instrument.type = row.get('type')
                        instrument.serial = row.get('serial')
                        instrument.description = row.get('description')
                        try:
                            instrument.price = float(row.get('price'))
                        except (ValueError, TypeError):
                            instrument.price = 0.0
                        updated += 1
                    else:
                        try:
                            price = float(row.get('price'))
                        except (ValueError, TypeError):
                            price = 0.0
                        instrument = Instrument(
                            name=name,
                            brand=row.get('brand'),
                            type=row.get('type'),
                            serial=row.get('serial'),
                            description=row.get('description'),
                            price=price
                        )
                        db.session.add(instrument)
                        imported += 1

                db.session.commit()
                flash(
                    f'Import completed: {imported} instrument(s) imported, {updated} instrument(s) updated.', 'success')
            except json.JSONDecodeError:
                flash('Invalid JSON data.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error during import: {str(e)}', 'danger')
            return redirect(url_for('import_instruments'))
    return render_template('bulkImportInstruments.html', form=form)
