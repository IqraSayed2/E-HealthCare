from flask import Blueprint, render_template, request, redirect, abort
from flask_login import login_required, current_user
from .models import Appointment, Availability, PatientProfile, User
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

    doctor_id = current_user.doctor_profile.id

    # Filters from UI
    date_filter = request.args.get("date")
    status_filter = request.args.get("status")
    consultation_type_filter = request.args.get("consultation_type")
    search = request.args.get("search")

    query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id
    )

    if date_filter:
        query = query.filter(Appointment.date == date_filter)

    if status_filter and status_filter != "all":
        query = query.filter(Appointment.status == status_filter)

    if consultation_type_filter and consultation_type_filter != "All Type":
        query = query.filter(Appointment.consultation_type == consultation_type_filter)

    if search:
        query = query.join(Appointment.patient).join(PatientProfile.user).filter(
            User.name.ilike(f"%{search}%")
        )

    appointments = query.order_by(Appointment.date).all()

    # Group by status (for tabs)
    upcoming = [a for a in appointments if a.status == "accepted"]
    pending = [a for a in appointments if a.status == "pending"]
    completed = [a for a in appointments if a.status == "completed"]
    cancelled = [a for a in appointments if a.status == "cancelled"]

    # Get booked dates for calendar
    booked_dates = set(a.date for a in upcoming)

    return render_template(
        "doctor/appointments.html",
        upcoming=upcoming,
        pending=pending,
        completed=completed,
        cancelled=cancelled,
        date_filter=date_filter,
        status_filter=status_filter,
        consultation_type_filter=consultation_type_filter,
        search=search
    )


@doctor.route("/appointment/accept/<int:id>")
@login_required
def accept_appointment(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = "accepted"
    db.session.commit()
    return redirect("/doctor/appointments")


@doctor.route("/appointment/cancel/<int:id>")
@login_required
def cancel_appointment(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = "cancelled"
    db.session.commit()
    return redirect("/doctor/appointments")


@doctor.route("/appointment/complete/<int:id>")
@login_required
def complete_appointment(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = "completed"
    db.session.commit()
    return redirect("/doctor/appointments")


@doctor.route("/availability", methods=["GET", "POST"])
@login_required
def availability():

    doctor_id = current_user.doctor_profile.id

    if request.method == "POST":

        # ----- WEEKLY HOURS -----
        Availability.query.filter_by(
            doctor_id=doctor_id,
            type="weekly"
        ).delete()

        for day in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]:
            if request.form.get(f"{day}_enabled"):
                start = request.form.get(f"{day}_start")
                end = request.form.get(f"{day}_end")

                if start and end:
                    db.session.add(
                        Availability(
                            doctor_id=doctor_id,
                            type="weekly",
                            day=day,
                            start_time=start,
                            end_time=end
                        )
                    )

        # ----- DATE OVERRIDE -----
        override_date = request.form.get("override_date")
        override_label = request.form.get("override_label")

        if override_date:
            db.session.add(
                Availability(
                    doctor_id=doctor_id,
                    type="override",
                    date=override_date,
                    label=override_label or "Blocked"
                )
            )

        db.session.commit()
        return redirect("/doctor/availability")

    weekly = Availability.query.filter_by(
        doctor_id=doctor_id,
        type="weekly"
    ).all()

    overrides = Availability.query.filter_by(
        doctor_id=doctor_id,
        type="override"
    ).order_by(Availability.date).all()

    # Get booked dates (accepted appointments)
    booked_dates = set(Appointment.query.filter_by(
        doctor_id=doctor_id,
        status="accepted"
    ).with_entities(Appointment.date).all())

    weekly_map = {w.day: w for w in weekly}

    # Prepare serializable data for JS
    weekly_js = {day: {
        'start_time': avail.start_time,
        'end_time': avail.end_time
    } for day, avail in weekly_map.items()}

    overrides_js = [{'date': o.date, 'label': o.label} for o in overrides]

    return render_template(
        "doctor/availability.html",
        weekly=weekly_map,
        overrides=overrides,
        booked_dates=list(booked_dates),
        weekly_js=weekly_js,
        overrides_js=overrides_js
    )


@doctor.route("/availability/delete/<int:id>")
@login_required
def delete_availability(id):
    avail = Availability.query.get_or_404(id)
    if avail.doctor_id != current_user.doctor_profile.id:
        abort(403)
    db.session.delete(avail)
    db.session.commit()
    return redirect("/doctor/availability")


@doctor.route("/profile")
@login_required
def profile():
    return render_template("doctor/profile.html")


@doctor.route("/patient/<int:patient_id>")
@login_required
def patient_preview(patient_id):
    patient_profile = PatientProfile.query.get_or_404(patient_id)
    # Ensure the doctor can only view their own patients
    # Check if there's an appointment between this doctor and patient
    appointment = Appointment.query.filter_by(
        doctor_id=current_user.doctor_profile.id,
        patient_id=patient_id
    ).first()
    if not appointment:
        abort(403)  # Forbidden
    return render_template("doctor/patient_preview.html", patient=patient_profile)
