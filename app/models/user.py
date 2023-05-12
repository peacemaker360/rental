# app/models.py

from datetime import datetime, timedelta
from app import app, db, login
from flask import url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from hashlib import md5
from time import time
import base64
import jwt
import os

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Integer, default=1)

    # API Token unterstüstzung
    # Der aktuelle API-Token in der Datenbank
    token = db.Column(db.String(32), index=True, unique=True)
    # Das Ablaufdatum des Token in der Datenbank
    token_expiration = db.Column(db.DateTime)

    #Basic accounting functionality
    def set_password(self,password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash,password)

    #Reset password via mail logic
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)
    
    #API Auth support functionality
    # Token erzeugen, speichern und zurückgeben
    def get_token(self, expires_in=3600):
        now = datetime.utcnow()
        if self.token and self.token_expiration > now + timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token
    
    # Token ungültig machen
    def revoke_token(self):
        # Ablaufdatum auf aktuelle Zeit - 1 sek. setzen
        #self.token = "" => is key and must be unique
        self.token_expiration = datetime.utcnow() - timedelta(seconds=1)

    # Token prüfen
    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.utcnow():
            return None # Token nicht gefunden oder abgelaufen
        return user # Token ist gültig

    #Formatting and dispay of class
    def to_json(self):        
        return {"id": self.id,
            "name": self.username,
            "email": self.email}
    
    def to_dict(self, include_email=False):
        data = {
        'id': self.id,
        'username': self.username,
        '_links': {
            'self': url_for('get_user', id=self.id, _external=True),
        }
        }
        if include_email:
            data['email'] = self.email
        return data
    
    def from_dict(self, data, new_user=False):
        for field in ['username', 'email']:
            if field in data:
                setattr(self, field, data[field])
            if new_user and 'password' in data:
                self.set_password(data['password'])
    
    @staticmethod
    def to_collection():
        users = User.query.all()
        data = {'items': [item.to_dict() for item in users]}
        return(data)

    def __repr__(self):
        return '<User {}>'.format(self.username)
    