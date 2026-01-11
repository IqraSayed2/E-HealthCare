from .extensions import db
from flask_login import UserMixin
from datetime import datetime
from .extensions import login_manager


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
    # Personal
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(10))
    date_of_birth = db.Column(db.String(20))
    profile_pic = db.Column(db.String(255))  # File path for uploaded profile picture
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    # Contact
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    country = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    # Medical
    allergies = db.Column(db.Text)
    conditions = db.Column(db.Text)
    medications = db.Column(db.Text)
    previous_conditions = db.Column(db.Text)
    surgeries = db.Column(db.Text)
    family_history = db.Column(db.Text)
    father_history = db.Column(db.Text)
    mother_history = db.Column(db.Text)
    immunizations = db.Column(db.Text)
    # Insurance
    insurance_provider = db.Column(db.String(100))
    policy_number = db.Column(db.String(50))
    group_number = db.Column(db.String(50))
    coverage_type = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="patient_profile", uselist=False)


### Doctor Profile ###
class DoctorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    specialization = db.Column(db.String(120))
    secondary_specialization = db.Column(db.String(120))
    experience = db.Column(db.Integer)
    fees = db.Column(db.Integer)
    about = db.Column(db.Text)
    # Personal Information
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    medical_licence_no = db.Column(db.String(50))
    profile_pic = db.Column(db.String(255))  # File path for uploaded profile picture
    # Qualification and Credentials
    medical_degree = db.Column(db.String(120))
    medical_school = db.Column(db.String(120))
    graduation_year = db.Column(db.Integer)
    board_certifications = db.Column(db.Text)
    licence_file = db.Column(db.String(255))  # File path for uploaded licence
    # Clinic/Hospital Information
    clinic_name = db.Column(db.String(120))
    clinic_address = db.Column(db.Text)
    clinic_city = db.Column(db.String(50))
    clinic_state = db.Column(db.String(50))
    clinic_country = db.Column(db.String(50))
    clinic_zip_code = db.Column(db.String(20))
    # Additional Information
    areas_of_expertise = db.Column(db.Text)
    awards_recognitions = db.Column(db.Text)
    research_publications = db.Column(db.Text)
    professional_memberships = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="doctor_profile", uselist=False)


### Availability ###
class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_profile.id'))
    type = db.Column(db.String(20))  # weekly / override
    day = db.Column(db.String(10))   # Monday, Tuesday, etc.
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))
    date = db.Column(db.String(20))  # YYYY-MM-DD
    label = db.Column(db.String(50)) # Holiday / Vacation
    doctor = db.relationship("DoctorProfile", backref="availability")
    is_booked = db.Column(db.Boolean, default=False)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_profile.id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profile.id'))
    status = db.Column(db.String(20), default="pending")
    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    consultation_type = db.Column(db.String(50), default="Chat Consultation")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    doctor = db.relationship("DoctorProfile", backref="appointments")
    patient = db.relationship("PatientProfile", backref="appointments")


### Payment ###
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(20))  # paid / failed / pending


### Review ###
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_profile.id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('patient_profile.id'))
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    doctor = db.relationship("DoctorProfile", backref="reviews")
    patient = db.relationship("PatientProfile", backref="reviews")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))