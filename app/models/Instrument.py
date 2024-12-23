# app/models/Instrument.py
# Quelle: Eigenentwicklung, in anlehnung an Unterrichst bsp.

from datetime import date, datetime
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app import db

#from .Rental import Rental

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
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

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
        #rental = Rental.query.filter_by(instrument_id=self.id).order_by(Rental.end_date.desc()).first() # => using this, we have cricular references because we need Rental class
        instrument_instance = Instrument.query.get(self.id)
        # create a sorted list of rentals using a lambda function inline. Importend to handle the "empty end_date" here.
        rentals = sorted(instrument_instance.rental, key=lambda rental: (rental.end_date is None, rental.end_date), reverse=True)
        # get the top/first result from the sorted list
        rental = next(iter(rentals), None)

        # Check if there are any active rentals associated with this instrument.
        if rental is None: # Means, it has no active renatals => is available
             return True
        elif rental.end_date is None: # Means, its open ended => not available
             return False
        elif rental.end_date < date.today():  # Means, it is overdue => tecnically, its available
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
