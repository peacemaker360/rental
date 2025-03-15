# app/models/RentalHistory.py
# Quelle: Eigenentwicklung, in anlehnung an Unterrichst bsp.

from datetime import date, datetime, timezone
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import db


class RentalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rental_id = db.Column(db.Integer, nullable=True)
    instrument_id = db.Column(db.Integer, nullable=True)
    instrument_name = db.Column(db.Text, nullable=True)
    customer_id = db.Column(db.Integer, nullable=True)
    customer_name = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    rental_note = db.Column(db.Text, nullable=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    update_type = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.Text, nullable=True)
    # rental = db.relationship(
    #     'Rental',
    #     primaryjoin="RentalHistory.rental_id == Rental.id",
    #     backref='history',
    #     lazy=True,
    # )

    # Additional columns as needed
    def __init__(self, rental, updated_by=None, update_type="General"):
        self.rental_id = rental.id
        self.instrument_id = rental.instrument_id
        self.instrument_name = rental.instrument.name
        self.customer_id = rental.customer_id
        self.customer_name = rental.customer.display_name
        self.start_date = rental.start_date
        self.end_date = rental.end_date
        self.rental_note = rental.description
        self.updated_by = updated_by
        self.update_type = update_type

    @classmethod
    def search(cls, keyword):
        return cls.query.filter(
            or_(
                cls.rental_note.ilike(f'%{keyword}%'),
                cls.instrument_name.ilike(f'%{keyword}%'),
                cls.customer_name.ilike(f'%{keyword}%')
            )
        ).order_by(cls.timestamp.desc())

    @staticmethod
    def getBy_instrumentId(id):
        return RentalHistory.query.filter_by(instrument_id=id).distinct(
            RentalHistory.customer_id, RentalHistory.rental_id
        ).order_by(RentalHistory.timestamp.desc())

    @staticmethod
    def getBy_customerId(id):
        return RentalHistory.query.filter_by(customer_id=id).all()
