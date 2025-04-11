# app/models/Instrument.py
# Quelle: Eigenentwicklung, in anlehnung an Unterrichst bsp.

from datetime import date, datetime, timezone
from sqlalchemy import or_

from app import db


class Instrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    serial = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    year_of_purchase = db.Column(db.Date, nullable=True)
    created = db.Column(
        db.DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    updated = db.Column(
        db.DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    rental = db.relationship('Rental', backref='instrument', lazy=True)

    def __repr__(self):
        return str(self.id)

    def __init__(self, name=None, brand=None, type=None, description=None, price=None, serial=None, year_of_purchase=None):
        self.name = name or f"{brand} {type} ({serial})"
        self.brand = brand
        self.type = type
        self.serial = serial
        self.description = description
        self.price = price
        self.year_of_purchase = year_of_purchase
        self.updated = datetime.now(timezone.utc)
        # self.is_available = self.check_availability()

    @property
    def latest_rental(self):
        """
        Retrieve the most recent rental based on end_date and handling None values.
        """
        # Fetch all rentals; you may already have them via self.rental
        rentals = sorted(self.rental, key=lambda r: (r.end_date is None, r.end_date), reverse=True)
        return next(iter(rentals), None)

    @property
    def is_overdue(self):
        """
        Returns True if the instrument is currently rented, the rental has an end_date in the past and hasn't been returned.
        """
        rental = self.latest_rental
        if rental and rental.return_date is None:
            # Check if an end_date is defined and has passed.
            if rental.end_date and rental.end_date < date.today():
                return True
        return False

    @property
    def is_available(self):
        """
        Logic:
          - If no rental exists, return True.
          - If there is an active rental (return_date is None):
              • if no end_date is given, then it's not available.
              • if an end_date is provided:
                    - if the end_date is in the future, then it's currently in use: not available.
                    - if the end_date is in the past (overdue), we may consider it available (for re-rental) though it is overdue.
          - Otherwise, return True.
        """
        rental = self.latest_rental
        if rental is None:
            return True
        if rental.return_date is not None:
            # Rental finished.
            return True
        # Rental is active (not returned)
        if rental.end_date is None:
            # No end_date means the rental is open ended – instrument is not available.
            return False
        # There is an end_date; check if it's overdue.
        if rental.end_date < date.today():
            # Overdue rental; treat as available for re-rental (but subject to your business logic).
            return True
        # Rental is active and currently within the rental period.
        return False

    @property
    def is_rented(self):
        """
        Returns True if the instrument is currently rented and hasn't been returned.
        """
        rental = self.latest_rental
        if rental and rental.return_date is None:
            return True
        return False

    @classmethod
    def search(cls, keyword):
        # Start with a base query for the search string
        return cls.query.filter(or_(
            cls.name.ilike(f'%{keyword}%'),
            cls.brand.ilike(f'%{keyword}%'),
            cls.type.ilike(f'%{keyword}%'),
            cls.serial.ilike(f'%{keyword}%')
        ))
