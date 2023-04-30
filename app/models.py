from datetime import date
from app import db
#from models import User

class Instrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    rental = db.relationship('Rental', backref='instrument', lazy=True)

    def __repr__(self):
        return str(self.id)
    
    def __init__(self, name, brand, type, description, price):
        self.name = name
        self.brand = brand
        self.type = type
        self.description = description
        self.price = price
        self.is_available = self.is_available()
    
    def is_available(self):
        rental = Rental.query.filter_by(instrument_id=self.id).order_by(Rental.end_date.desc()).first()
        if rental is None:
            return True
        elif rental.end_date is None:
            return False
        elif rental.end_date < date.today():
            return True
        else:
            return False

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    rental = db.relationship('Rental', backref='customer', lazy=True)

    def __repr__(self):
        return str(self.id)

class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instrument.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
