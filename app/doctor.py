from flask import Blueprint, render_template, request, redirect, abort, current_app, flash, url_for
from flask_login import login_required, current_user
from .models import Appointment, Availability, PatientProfile, User, Message
from .extensions import db, mail
from datetime import date
import os
from werkzeug.utils import secure_filename

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
    upcoming = [a for a in appointments if a.status == "paid"]
    accepted = [a for a in appointments if a.status == "accepted"]
    pending = [a for a in appointments if a.status == "pending"]
    completed = [a for a in appointments if a.status == "completed"]
    cancelled = [a for a in appointments if a.status == "cancelled"]

    # Get booked dates for calendar
    booked_dates = set(a.date for a in upcoming)

    return render_template(
        "doctor/appointments.html",
        upcoming=upcoming,
        accepted=accepted,
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
    if appt.doctor_id != current_user.doctor_profile.id:
        abort(403)

    # Check if slot is still available
    existing_accepted = Appointment.query.filter_by(
        doctor_id=appt.doctor_id,
        date=appt.date,
        time=appt.time,
        status="accepted"
    ).first()

    if existing_accepted:
        # Slot taken, cancel this request
        appt.status = "cancelled"
        db.session.commit()
        return redirect("/doctor/appointments")

    appt.status = "accepted"
    db.session.commit()

    # Send email to patient
    patient = appt.patient.user
    msg = Message('Appointment Accepted',
                  sender='your-email@gmail.com',
                  recipients=[patient.email])
    msg.body = f'Your appointment with Dr. {appt.doctor.user.name} on {appt.date} at {appt.time} has been accepted. Please proceed to payment.'
    mail.send(msg)

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


@doctor.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        # Update doctor profile
        profile = current_user.doctor_profile
        # Personal Information
        current_user.name = request.form.get('full_name', current_user.name)
        profile.phone = request.form.get('contact') or None
        current_user.email = request.form.get('email_id', current_user.email)
        profile.date_of_birth = request.form.get('date_of_birth') or None
        profile.gender = request.form.get('gender') or None
        profile.about = request.form.get('professional_bio') or None
        profile.medical_licence_no = request.form.get('medical_licence_no_') or None
        profile.experience = int(request.form.get('years_of_experience')) if request.form.get('years_of_experience') else None
        profile.specialization = request.form.get('primary_specialization') or None
        profile.secondary_specialization = request.form.get('secondary_specialization') or None
        fees_str = request.form.get('consultation_fees')
        profile.fees = int(fees_str) if fees_str and fees_str.isdigit() else None
        # Qualification and Credentials
        profile.medical_degree = request.form.get('medical_degree') or None
        profile.medical_school = request.form.get('medical_school') or None
        profile.graduation_year = int(request.form.get('graduation_year')) if request.form.get('graduation_year') else None
        profile.board_certifications = request.form.get('board_certifications') or None
        # Clinic/Hospital Information
        profile.clinic_name = request.form.get('clinic_hospital_name') or None
        profile.clinic_address = request.form.get('address') or None
        profile.clinic_city = request.form.get('city') or None
        profile.clinic_state = request.form.get('state') or None
        profile.clinic_country = request.form.get('country') or None
        profile.clinic_zip_code = request.form.get('zip_code') or None
        # Additional Information
        profile.areas_of_expertise = request.form.get('areas_of_expertise') or None
        profile.awards_recognitions = request.form.get('awards_and_recognition') or None
        profile.research_publications = request.form.get('research___publications') or None
        profile.professional_memberships = request.form.get('professional_membership') or None
        
        # Handle file upload
        print(f"Doctor profile file: {request.files.get('doctor_profile')}")
        print(f"Licence file: {request.files.get('upload_medical_licence')}")
        upload_dir = os.path.join(current_app.static_folder, 'uploads')
        print(f"Upload dir: {upload_dir}")
        if 'upload_medical_licence' in request.files:
            file = request.files['upload_medical_licence']
            if file and file.filename:
                filename = f"{current_user.id}_{secure_filename(file.filename)}"
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                profile.licence_file = filename
        
        if 'doctor_profile' in request.files:
            file = request.files['doctor_profile']
            if file and file.filename:
                filename = f"{current_user.id}_{secure_filename(file.filename)}"
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                profile.profile_pic = filename
                print(f"Saved profile_pic: {profile.profile_pic}")
        
        db.session.commit()
        return redirect("/doctor/profile")
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


@doctor.route("/consultations")
@login_required
def consultations():
    doctor_id = current_user.doctor_profile.id
    
    # Get unique patients with their most recent appointment
    from sqlalchemy import func
    subquery = db.session.query(
        Appointment.patient_id,
        func.max(Appointment.date).label('max_date')
    ).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status != 'cancelled'
    ).group_by(Appointment.patient_id).subquery()
    
    all_appointments = Appointment.query.join(
        subquery,
        db.and_(
            Appointment.patient_id == subquery.c.patient_id,
            Appointment.date == subquery.c.max_date
        )
    ).filter(
        Appointment.doctor_id == doctor_id
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    # Find the most recent appointment for the main chat
    appointment = all_appointments[0] if all_appointments else None
    
    return render_template("doctor/consultation.html", appointment=appointment, all_appointments=all_appointments)


@doctor.route("/consultation/<int:appointment_id>")
@login_required
def consultation(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    # Ensure the appointment belongs to the current doctor
    if appointment.doctor_id != current_user.doctor_profile.id:
        abort(403)
    
    # Get unique patients with their most recent appointment
    from sqlalchemy import func
    subquery = db.session.query(
        Appointment.patient_id,
        func.max(Appointment.date).label('max_date')
    ).filter(
        Appointment.doctor_id == current_user.doctor_profile.id,
        Appointment.status != 'cancelled'
    ).group_by(Appointment.patient_id).subquery()
    
    all_appointments = Appointment.query.join(
        subquery,
        db.and_(
            Appointment.patient_id == subquery.c.patient_id,
            Appointment.date == subquery.c.max_date
        )
    ).filter(
        Appointment.doctor_id == current_user.doctor_profile.id
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    messages = Message.query.filter_by(appointment_id=appointment_id).order_by(Message.timestamp).all()
    
    return render_template("doctor/consultation.html", appointment=appointment, all_appointments=all_appointments, messages=messages)
