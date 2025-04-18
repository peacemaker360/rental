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

from sqlalchemy.orm import exc as orm_exc

@app.route('/import_users', methods=['GET', 'POST'])
@login_required
def import_users():
    if current_user.role > 1:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    form = BulkUserImportForm()
    if form.is_submitted():
        if not form.validate():
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'danger')
            return redirect(url_for('import_users'))
            
        reference_type = form.reference_type.data

        if form.submit_verify.data:
            json_data = form.json_data.data
            exclude_groups_str = form.exclude_groups.data
            exclude_group_ids = []

            if exclude_groups_str:
                try:
                    exclude_group_ids = [int(id.strip()) for id in exclude_groups_str.split(',') if id.strip().isdigit()]
                except ValueError:
                    flash('Exclude Group IDs must be integers separated by commas.', 'danger')
                    return redirect(url_for('import_users'))

            try:
                parsed_data = json.loads(json_data)
                users = parsed_data.get('data', [])

                if not isinstance(users, list) or len(users) < 1:
                    flash('Invalid JSON format: "data" should be a non-empty list.', 'danger')
                    return redirect(url_for('import_users'))

                if exclude_group_ids:
                    users = [user for user in users if user.get('attributes', {}).get('primary_group_id') not in exclude_group_ids]
                    flash(f'Excluded users from groups: {", ".join(map(str, exclude_group_ids))}', 'info')

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
                    exclude_group_ids = [int(id.strip()) for id in exclude_groups_str.split(',') if id.strip().isdigit()]
                except ValueError:
                    flash('Exclude Group IDs must be integers separated by commas.', 'danger')
                    return redirect(url_for('import_users'))

            try:
                parsed_data = json.loads(json_data)
                users = parsed_data.get('data', [])

                if not isinstance(users, list) or len(users) < 1:
                    flash('Invalid JSON format: "data" should be a non-empty list.', 'danger')
                    return redirect(url_for('import_users'))

                if exclude_group_ids:
                    users = [user for user in users if user.get('attributes', {}).get('primary_group_id') not in exclude_group_ids]
                    flash(f'Excluded users from group IDs: {", ".join(map(str, exclude_group_ids))}', 'info')

                imported = 0
                imported_users = []
                updated = 0
                updated_users = []
                # List to keep track of skipped users
                skipped_users = []

                for user_data in users:
                    attributes = user_data.get('attributes', {})
                    external_id = user_data.get('id')
                    email = attributes.get('email')
                    first_name = attributes.get('first_name')
                    last_name = attributes.get('last_name')
                    groups = attributes.get('primary_group_id', [])
                    if not isinstance(groups, list):
                        groups = [groups]

                    if not email and reference_type == 'email':
                        skipped_users.append({
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'reason': 'Missing email'
                        })
                        continue

                    try:
                        with db.session.no_autoflush:
                            # First try to find by reference type
                            existing_user = None
                            if reference_type == 'external_id' and external_id:
                                existing_user = Customer.query.filter_by(external_id=external_id).first()
                            if not existing_user and email:
                                existing_user = Customer.query.filter_by(email=email).first()

                            if existing_user:
                                existing_user.firstname = str(first_name)
                                existing_user.lastname = str(last_name)
                                existing_user.groups = json.dumps(groups)
                                existing_user.external_id = external_id
                                existing_user.update_active_status()
                                updated_users.append(existing_user)
                                updated += 1
                            else:
                                new_user = Customer(
                                    email=email,
                                    firstname=first_name,
                                    lastname=last_name,
                                    groups=json.dumps(groups),
                                    external_id=external_id
                                )
                                db.session.add(new_user)
                                imported_users.append(new_user)
                                imported += 1

                    except orm_exc.FlushError as e:
                        skipped_users.append({
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'reason': f'Database error: {str(e)}'
                        })

                db.session.commit()
                flash(f'Import completed: {imported} user(s) imported, {updated} user(s) updated.', 'success')

                if skipped_users:
                    skipped_message = (
                        "<strong>Skipped the following users due to errors:</strong>"
                        "<ul>"
                    )
                    for user in skipped_users:
                        skipped_message += (
                            f"<li>Name: {user.get('first_name', '')} {user.get('last_name', '')}, "
                            f"Email: {user.get('email', 'N/A')}, Reason: {user.get('reason')}</li>"
                        )
                    skipped_message += "</ul>"
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
    if form.is_submitted():
        if not form.validate():
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'danger')
            return redirect(url_for('import_instruments'))

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

                def get_case_insensitive(dictionary, key):
                    """Helper function to get dictionary value regardless of key case"""
                    if not dictionary:
                        return None
                    for k in dictionary:
                        if isinstance(k, str) and k.lower() == key.lower():
                            return dictionary[k]
                    return None

                for row in instruments_data:
                    name = get_case_insensitive(row, 'name')
                    serial = get_case_insensitive(row, 'serial')
                    if not name or not serial:
                        continue

                    instrument = Instrument.query.filter_by(serial=serial).first()
                    if instrument:
                        # update existing instrument
                        instrument.brand = get_case_insensitive(row, 'brand')
                        instrument.type = get_case_insensitive(row, 'type')
                        instrument.serial = serial
                        instrument.description = get_case_insensitive(row, 'description')
                        try:
                            instrument.price = float(get_case_insensitive(row, 'price') or 0)
                        except (ValueError, TypeError):
                            instrument.price = 0.0
                        updated += 1
                    else:
                        try:
                            price = float(get_case_insensitive(row, 'price') or 0)
                        except (ValueError, TypeError):
                            price = 0.0
                        instrument = Instrument(
                            name=name,
                            brand=get_case_insensitive(row, 'brand'),
                            type=get_case_insensitive(row, 'type'),
                            serial=serial,
                            description=get_case_insensitive(row, 'description'),
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
