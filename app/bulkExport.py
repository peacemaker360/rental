import csv
import io
from flask import current_app as app
from flask import Response, flash, redirect, url_for
from flask_login import current_user, login_required


from app.models import Instrument, Rental
from datetime import datetime


@app.route('/export/instruments', methods=['GET'])
@login_required
def export_instruments():
    if current_user.role > 5:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    instruments = Instrument.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    # Write header row
    writer.writerow(['Name', 'Brand', 'Type', 'Serial', 'Description', 'Price'])
    for inst in instruments:
        writer.writerow([
            inst.name,
            inst.brand,
            inst.type,
            inst.serial,
            inst.description,
            inst.price
        ])
    output.seek(0)
    today = datetime.now().strftime("%Y%m%d")
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{today}_instruments.csv"'}
    )


@app.route('/export/rentals', methods=['GET'])
@login_required
def export_rentals():
    if current_user.role > 5:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    rentals = Rental.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    # Write header row
    writer.writerow(['Customer ID', 'Instrument ID', 'Start Date', 'End Date', 'Return Date', 'Description'])
    for r in rentals:
        writer.writerow([
            r.customer_id,
            r.instrument_id,
            r.start_date,
            r.end_date,
            r.return_date,
            r.description
        ])
    output.seek(0)
    today = datetime.now().strftime("%Y%m%d")
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{today}_rentals.csv"'}
    )
