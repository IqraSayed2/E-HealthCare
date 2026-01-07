from flask import Blueprint, render_template, request, redirect
from flask_login import login_required, current_user
from .models import Appointment, Availability
from .extensions import db
from datetime import date

doctor = Blueprint("doctor", __name__, url_prefix="/doctor")


@doctor.route("/dashboard")
@login_required
def dashboard():

    doctor_id = current_user.doctor_profile.id

    # All appointments
    appointments = Appointment.query.filter_by(
        doctor_id=doctor_id
    ).order_by(Appointment.date).all()

    # Today appointments
    today_appointments = Appointment.query.filter_by(
        doctor_id=doctor_id,
        date=date.today()
    ).all()

    # Counts
    total_appointments = len(appointments)
    pending_appointments = Appointment.query.filter_by(
        doctor_id=doctor_id,
        status="pending"
    ).count()

    completed_appointments = Appointment.query.filter_by(
        doctor_id=doctor_id,
        status="completed"
    ).count()

    return render_template(
        "doctor/dashboard.html",
        appointments=appointments,
        today_appointments=today_appointments,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        completed_appointments=completed_appointments
    )


@doctor.route("/appointments")
@login_required
def appointments():
    appts = Appointment.query.filter_by(doctor_id=current_user.doctor_profile.id).all()
    return render_template("doctor/appointments.html", appointments=appts)

@doctor.route("/accept/<int:id>")
@login_required
def accept(id):
    appt = Appointment.query.get(id)
    appt.status = "accepted"
    db.session.commit()
    return redirect("/doctor/appointments")

@doctor.route("/availability", methods=["GET", "POST"])
@login_required
def availability():
    if request.method == "POST":
        date = request.form["date"]
        time = request.form["time"]
        avail = Availability(doctor_id=current_user.doctor_profile.id, date=date, time=time)
        db.session.add(avail)
        db.session.commit()

    availability = Availability.query.filter_by(doctor_id=current_user.doctor_profile.id).all()
    return render_template("doctor/availability.html", availability=availability)