# app/models/Rental.py
# Quelle: Eigenentwicklung, in anlehnung an Unterrichst bsp.

from datetime import datetime, timezone
from sqlalchemy import or_

from app import db
# from app.models import Customer, Instrument
from app.models.Instrument import Instrument
from app.models.Customer import Customer


class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey(
        'instrument.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey(
        'customer.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    return_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created = db.Column(
        db.DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    updated = db.Column(
        db.DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def end_rental(self):
        self.return_date = datetime.now()
        if self.end_date is None:
            self.end_date = datetime.now()

    @property
    def is_active(self):
        return self.return_date is None

    @property
    def is_available(self):
        return self.return_date is not None

    @property
    def is_late(self):
        if self.end_date is None:
            return False
        return self.end_date < datetime.now().date() and self.return_date is None

    @property
    def is_on_time(self):
        if self.end_date is None:
            return False
        return self.end_date >= datetime.now().date() and self.return_date is None

    @property
    def is_returned(self):
        return self.return_date is not None

    @classmethod
    def search(cls, keyword):
        return cls.query.join(Customer).join(Instrument).filter(
            or_(
                cls.id.like(f'%{keyword}%'),
                Customer.firstname.like(f'%{keyword}%'),
                Customer.lastname.like(f'%{keyword}%'),
                Instrument.name.like(f'%{keyword}%'),
                cls.start_date.like(f'%{keyword}%'),
                cls.end_date.like(f'%{keyword}%'),
                cls.description.like(f'%{keyword}%')
            )
        )
