from datetime import date, datetime
from sqlalchemy import or_, event
from app import db


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    rental = db.relationship('Rental', backref='customer', lazy=True)
    foreign_id = db.Column(db.String(50), unique=True)
    connected = db.Column(db.Boolean, default=True)
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

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