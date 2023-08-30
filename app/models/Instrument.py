# app/models/Instrument.py
# Quelle: eigene Entwicklung, in anlehnung an Unterrichst bsp.

from datetime import date, datetime
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app import db

from .Rental import Rental

class Instrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    serial = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    rental = db.relationship('Rental', backref='instrument', lazy=True)

    def __repr__(self):
        return str(self.id)
    
    def __init__(self, name=None, brand=None, type=None, description=None, price=None, serial=None):
        self.name = name or f"{brand} {type} ({serial})"
        self.brand = brand
        self.type = type
        self.serial = serial
        self.description = description
        self.price = price
        #self.is_available = self.check_availability()
    
    @property
    def is_available(self):
        # Load the related rentals.
        # With `joinedload`, it will fetch the related rentals in the same query.
        rental = Rental.query.filter_by(instrument_id=self.id).order_by(Rental.end_date.desc()).first()

        # Check if there are any active rentals associated with this instrument.
        if rental is None:
             return True
        elif rental.end_date is None:
             return False
        elif rental.end_date < date.today():
             return True
        else:
             return False
    
    def search_instruments(keyword):
        # Start with a base query for the search string
        query = Instrument.query.filter(or_(
            Instrument.name.ilike(f'%{keyword}%'),
            Instrument.brand.ilike(f'%{keyword}%'),
            Instrument.type.ilike(f'%{keyword}%'),
            Instrument.serial.ilike(f'%{keyword}%')
        ))
        # Execute the query and return the results
        instruments = query.all()
        
        return instruments
