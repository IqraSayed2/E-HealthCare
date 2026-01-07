from flask import Blueprint, render_template, request, redirect
from flask_login import login_required, current_user
from .models import DoctorProfile, Appointment, PatientProfile, Availability, User
from .extensions import db


patient = Blueprint("patient", __name__, url_prefix="/patient")

@patient.route("/dashboard")
@login_required
def dashboard():

    # Fetch upcoming appointments
    upcoming = Appointment.query.filter_by(
        patient_id=current_user.patient_profile.id
    ).order_by(Appointment.date).limit(5).all()

    # Count values
    upcoming_count = len(upcoming)
    total_doctors = DoctorProfile.query.count()

    total_consultations = Appointment.query.filter_by(
        patient_id=current_user.patient_profile.id,
        status="completed"
    ).count()

    return render_template(
        "patient/dashboard.html",
        upcoming=upcoming,
        upcoming_count=upcoming_count,
        total_doctors=total_doctors,
        total_consultations=total_consultations
    )



@patient.route("/find-doctor")
@login_required
def find_doctor():
    search = request.args.get("search")

    query = DoctorProfile.query.join(DoctorProfile.user)

    if search:
        query = query.filter(
            (DoctorProfile.specialization.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )

    doctors = query.all()
    return render_template(
        "patient/find_doctor.html",
        doctors=doctors,
        search=search
    )


@patient.route("/doctor/<int:id>")
@login_required
def doctor_preview(id):
    doctor = DoctorProfile.query.get_or_404(id)
    availability = Availability.query.filter_by(doctor_id=id).all()
    return render_template(
        "patient/doctor_preview.html",
        doctor=doctor,
        availability=availability
    )


@patient.route("/book/<int:doctor_id>", methods=["POST"])
@login_required
def book(doctor_id):
    date = request.form["date"]
    time = request.form["time"]

    appt = Appointment(
        doctor_id=doctor_id,
        patient_id=current_user.patient_profile.id,
        date=date,
        time=time
    )
    db.session.add(appt)
    db.session.commit()
    return redirect("/patient/my-appointments")


@patient.route("/my-appointments")
@login_required
def my_appointments():
    appts = Appointment.query.filter_by(patient_id=current_user.patient_profile.id).all()
    return render_template("patient/my_appointments.html", appointments=appts)