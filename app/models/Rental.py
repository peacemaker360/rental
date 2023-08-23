from datetime import date, datetime
from sqlalchemy import or_, event
from app import db
from app.models import Customer, Instrument
# from .Customer import Customer
# from .Instrument import Instrument

class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instrument.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated = db.Column(db.DateTime, onupdate=datetime.utcnow)

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