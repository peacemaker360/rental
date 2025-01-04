# app/models/RentalHistory.py
# Quelle: Eigenentwicklung, in anlehnung an Unterrichst bsp.

from datetime import date, datetime, timezone
from sqlalchemy import or_, event
from sqlalchemy.orm import Session

from app import db


class RentalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rental_id = db.Column(db.Integer, db.ForeignKey('rental.id'))
    instrument_id = db.Column(db.Integer, db.ForeignKey(
        'instrument.id'), nullable=False)
    instrument_name = db.Column(db.Text, nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey(
        'customer.id'), nullable=False)
    customer_name = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    rental_note = db.Column(db.Text, nullable=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    rental = db.relationship('Rental', backref='history', lazy=True)

    # Additional columns as needed
    def __init__(self, rental):
        self.rental_id = rental.id
        self.instrument_id = rental.instrument_id
        self.instrument_name = rental.instrument.name
        self.customer_id = rental.customer_id
        self.customer_name = rental.customer.display_name
        self.start_date = rental.start_date
        self.end_date = rental.end_date
        self.rental_note = rental.description

    @staticmethod
    def search_rentalshistory(keyword):
        rentalshistory = RentalHistory.query.filter(or_(
            RentalHistory.rental_note.ilike(f'%{keyword}%'),
            RentalHistory.instrument_name.ilike(f'%{keyword}%'),
            RentalHistory.customer_name.ilike(f'%{keyword}%')
        )).order_by(RentalHistory.timestamp.desc()).all()
        return rentalshistory

    @staticmethod
    def getBy_instrumentId(id):
        rentalshistory = RentalHistory.query.filter_by(instrument_id=id).distinct(
            RentalHistory.customer_id, RentalHistory.rental_id).order_by(RentalHistory.timestamp.desc())
        return rentalshistory

    @staticmethod
    def getBy_customerId(id):
        rentalshistory = RentalHistory.query.filter_by(customer_id=id).all()
        return rentalshistory
