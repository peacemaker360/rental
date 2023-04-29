from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, Optional
from wtforms_sqlalchemy.fields import QuerySelectField

class InstrumentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    brand = StringField('Brand', validators=[DataRequired()])
    type = StringField('Type', validators=[DataRequired()])
    description = StringField('Description')
    price = FloatField('Price', validators=[DataRequired()])
    submit = SubmitField('Submit')

class CustomerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])
    submit = SubmitField('Submit')

class RentalForm(FlaskForm):
    #instrument = StringField('Instrument', validators=[DataRequired()])
    instrument = QuerySelectField(allow_blank = True, get_label = 'name', validators = [DataRequired()], blank_text=u'Select...')
    #customer = StringField('Customer', validators=[DataRequired()])
    customer = QuerySelectField(allow_blank = True, get_label = 'name', validators = [DataRequired()], blank_text=u'Select...')
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Return (End) Date', format='%Y-%m-%d', validators=[Optional()] )
    description = StringField('Notes')
    submit = SubmitField('Submit')