from .extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(255))
    role = db.Column(db.String(20))    # "patient" or "doctor"

    # Use back_populates to avoid duplicate/conflicting backrefs
    doctor_profile = db.relationship("DoctorProfile", back_populates="user", uselist=False)
    patient_profile = db.relationship("PatientProfile", back_populates="user", uselist=False)

### Patient Profile ###
class PatientProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="patient_profile", uselist=False)

### Doctor Profile ###
class DoctorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    specialization = db.Column(db.String(120))
    experience = db.Column(db.Integer)
    fees = db.Column(db.Integer)
    about = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="doctor_profile", uselist=False)

### Availability ###
class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_profile.id'))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_profile.id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profile.id'))
    status = db.Column(db.String(20), default="pending")
    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship("DoctorProfile", backref="appointments")
    patient = db.relationship("PatientProfile", backref="appointments")


### Payment ###
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(20))  # paid / failed / pending










from .extensions import login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))