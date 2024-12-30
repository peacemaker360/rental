# app/models/Customer.py
from datetime import datetime, timezone
from sqlalchemy import JSON, or_

from app import db


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(50), nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20), nullable=True)
    created = db.Column(
        db.DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    updated = db.Column(
        db.DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    is_active = db.Column(db.Boolean, default=True)
    groups = db.Column(db.String(200), nullable=True)
    rental = db.relationship('Rental', backref='customer', lazy=True)

    @property
    def display_name(self):
        return f"{self.firstname} {self.lastname}"

    def __repr__(self):
        return f'<Customer {self.firstname} {self.lastname}>'

    def __init__(self, firstname=None, lastname=None, email=None, phone=None, groups=None):
        self.firstname = firstname
        self.lastname = lastname
        # self.name = f"{firstname} {lastname}"
        self.email = email
        self.phone = phone
        self.groups = groups
        self.update_active_status()

    def update_active_status(self):
        # Check if self.groups contains a specific group ID (e.g., '3742')
        if self.groups and '3742' in self.groups:
            self.is_active = True
        else:
            self.is_active = False

    def set_groups(self, groups):
        self.groups = groups
        self.update_active_status()

    def deactivate(self):
        self.is_active = False
        db.session.commit()
        return self

    def activate(self):
        self.is_active = True
        db.session.commit()
        return self

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
