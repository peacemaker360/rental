from datetime import date
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, PasswordField, FloatField, DateField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, Optional
from wtforms_sqlalchemy.fields import QuerySelectField

from app.models.User import User
from .models import Instrument, Customer, Rental

#################################
# Forms for User handling
# Quelle: aus Unterricht (microblog) mit anpassungen übernommen
# Help: diese formulare werden für die app user dialoge gebraucht
#################################

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Request Password Reset')

class UserSelectForm(FlaskForm):
    user = QuerySelectField(allow_blank = False, 
                                  get_label = 'username', 
                                  validators = [DataRequired()], 
                                  blank_text=u'Select user...'
                                  )
    submit = SubmitField('Select')

class UserConfigForm(FlaskForm):
    #username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    enabled = BooleanField('Account enabled', default=False)
    admin = BooleanField('Is admin', default=False)
    submit = SubmitField('Update')

#################################
# Forms for custom app 
# Quelle: aus Unterricht (microblog) mit anpassungen übernommen
#################################

class InstrumentForm(FlaskForm):
    name = StringField('Name', validators=[Optional()], default=None)
    brand = StringField('Marke*', validators=[DataRequired()])
    type = StringField('Typ*', validators=[DataRequired()])
    serial = StringField('Serial*', validators=[DataRequired()])
    description = StringField('Beschreibung')
    price = FloatField('Wert*', validators=[DataRequired()])
    submit = SubmitField('Ok')
    cancel = SubmitField('Cancel')

class CustomerForm(FlaskForm):
    firstname = StringField('Vorname*', validators=[DataRequired()])
    lastname = StringField('Nachname*', validators=[DataRequired()])
    name = StringField('Name', validators=[Optional()], default=None)
    email = StringField('Email*', validators=[DataRequired(), Email()])
    phone = StringField('Phone*', validators=[DataRequired(),])
    submit = SubmitField('Ok')
    cancel = SubmitField('Cancel')

class RentalForm(FlaskForm):
    #instrument = StringField('Instrument', validators=[DataRequired()])
    instrument = QuerySelectField(allow_blank = True, 
                                  get_label = 'name', 
                                  validators = [DataRequired()], 
                                  blank_text=u'Select...'
                                  )
    #customer = StringField('Customer', validators=[DataRequired()])
    customer = QuerySelectField(allow_blank = True, 
                                get_label = 'name', 
                                validators = [DataRequired()], 
                                blank_text=u'Select...'
                                )
    start_date = DateField('Start Datum*', format='%Y-%m-%d', validators=[DataRequired()], default=date.today())
    end_date = DateField('Rückgabe (End) Datum*', format='%Y-%m-%d', validators=[Optional()], default=None )
    description = StringField('Notitz')
    submit = SubmitField('Ok')
    cancel = SubmitField('Cancel')