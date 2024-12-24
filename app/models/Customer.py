# app/models/Customer.py
from datetime import datetime, timezone
from sqlalchemy import or_

from app import db


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(50), nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20), nullable=False)
    created = db.Column(
        db.DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    updated = db.Column(
        db.DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    rental = db.relationship('Rental', backref='customer', lazy=True)

    @property
    def display_name(self):
        return f"{self.firstname} {self.lastname}"

    def __repr__(self):
        return f'<Customer {self.firstname} {self.lastname}>'

    def __init__(self, firstname=None, lastname=None, email=None, phone=None):
        self.firstname = firstname
        self.lastname = lastname
        # self.name = f"{firstname} {lastname}"
        self.email = email
        self.phone = phone

    @staticmethod
    def search_customers(keyword):
        customers = Customer.query.filter(or_(
            # Customer.name.ilike(f'%{keyword}%'),
            Customer.firstname.ilike(f'%{keyword}%'),
            Customer.lastname.ilike(f'%{keyword}%'),
            Customer.email.ilike(f'%{keyword}%'),
            Customer.phone.ilike(f'%{keyword}%')
        )).all()
        return customers
