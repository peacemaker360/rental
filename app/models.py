from datetime import date, datetime
from sqlalchemy import or_, event
from app import db
#from models import User

class Instrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    serial = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=True)
    rental = db.relationship('Rental', backref='instrument', lazy=True)

    def __repr__(self):
        return str(self.id)
    
    def __init__(self, name=None, brand=None, type=None, description=None, price=None, serial=None):
        self.name = name or f"{brand} {type} ({serial})"
        self.brand = brand
        self.type = type
        self.serial = type
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
    
    def search_instruments(keyword):
        instruments = Instrument.query.filter(or_(
            Instrument.name.ilike(f'%{keyword}%'),
            Instrument.brand.ilike(f'%{keyword}%'),
            Instrument.type.ilike(f'%{keyword}%'),
            Instrument.serial.ilike(f'%{keyword}%')
        )).all()
        return instruments

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    rental = db.relationship('Rental', backref='customer', lazy=True)
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return str(self.id)
    
    def __init__(self, name=None, firstname=None, lastname=None, email=None, phone=None):
        self.name = name or f"{firstname} {lastname}"
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.phone = phone
    
    def search_customers(keyword):
        customers = Customer.query.filter(or_(
            Customer.name.ilike(f'%{keyword}%'),
            Customer.firstname.ilike(f'%{keyword}%'),
            Customer.lastname.ilike(f'%{keyword}%'),
            Customer.email.ilike(f'%{keyword}%'),
            Customer.phone.ilike(f'%{keyword}%')
        )).all()
        return customers

class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instrument.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def search_rentals(keyword):
        rentals = Rental.query.join(Customer).join(Instrument).filter(
            or_(
                Rental.id.like(f'%{keyword}%'),
                Customer.name.like(f'%{keyword}%'),
                Instrument.name.like(f'%{keyword}%'),
                Rental.start_date.like(f'%{keyword}%'),
                Rental.end_date.like(f'%{keyword}%'),
                Rental.description.like(f'%{keyword}%')
            )
        ).all()
        return rentals

@event.listens_for(Rental, 'after_insert')
def after_rent_insert(mapper, connection, target):
    history = RentalHistory(target)
    db.session.add(history)
    db.session.commit()

class RentalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rental_id = db.Column(db.Integer, db.ForeignKey('rental.id'))
    instrument_id = db.Column(db.Integer)
    customer_id = db.Column(db.Integer)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    # Additional columns as needed
    def __init__(self, rental):
        self.rental_id = rental.id
        self.instrument_id = rental.instrument_id
        self.customer_id = rental.customer_id
        self.start_date = rental.start_date
        self.end_date = rental.end_date