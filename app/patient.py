from flask import Blueprint, render_template, request, redirect, current_app, abort, flash, url_for
from flask_login import login_required, current_user
from .models import DoctorProfile, Appointment, PatientProfile, Availability, User, Review, Message
from .extensions import db
from werkzeug.utils import secure_filename
import os
import razorpay


patient = Blueprint("patient", __name__, url_prefix="/patient")

@patient.route("/dashboard")
@login_required
def dashboard():

    # Fetch upcoming appointments
    upcoming = Appointment.query.filter(
        Appointment.patient_id == current_user.patient_profile.id,
        Appointment.status.in_(['pending', 'confirmed', 'paid'])
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

    # Get weekly availability
    weekly_avail = Availability.query.filter_by(
        doctor_id=id,
        type="weekly"
    ).all()

    # Get overrides
    overrides = Availability.query.filter_by(
        doctor_id=id,
        type="override"
    ).all()

    # Get booked appointments
    booked_slots = Appointment.query.filter_by(
        doctor_id=id,
        status="accepted"
    ).with_entities(Appointment.date, Appointment.time).all()
    booked_set = set((a.date, a.time) for a in booked_slots)

    # Generate slots for next 7 days
    from datetime import datetime, timedelta
    today = datetime.now().date()
    slots_by_day = {}

    for i in range(7):
        current_date = today + timedelta(days=i)
        day_name = current_date.strftime("%A")  # Monday, Tuesday, etc.

        # Check if overridden
        override = next((o for o in overrides if o.date == str(current_date)), None)
        if override:
            continue  # Skip if blocked

        # Get weekly avail for this day
        avail = next((w for w in weekly_avail if w.day == day_name), None)
        if not avail:
            continue

        # Generate hourly slots
        start_hour = int(avail.start_time.split(':')[0])
        end_hour = int(avail.end_time.split(':')[0])
        slots = []
        for hour in range(start_hour, end_hour):
            time_str = f"{hour:02d}:00"
            is_booked = (str(current_date), time_str) in booked_set
            slots.append({
                'time': time_str,
                'is_booked': is_booked
            })

        if slots:
            slots_by_day[day_name] = {
                'date': str(current_date),
                'slots': slots
            }

    # Fetch reviews
    reviews = Review.query.filter_by(doctor_id=id).order_by(Review.created_at.desc()).all()

    # Calculate average rating
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        avg_rating = round(avg_rating, 1)
    else:
        avg_rating = 0

    return render_template(
        "patient/doctor_preview.html",
        doctor=doctor,
        slots_by_day=slots_by_day,
        reviews=reviews,
        avg_rating=avg_rating
    )


@patient.route("/book/<int:doctor_id>", methods=["POST"])
@login_required
def book(doctor_id):

    date = request.form["date"]
    time = request.form["time"]

    # Check if slot is already booked
    existing = Appointment.query.filter_by(
        doctor_id=doctor_id,
        date=date,
        time=time,
        status="accepted"
    ).first()

    if existing:
        return "Slot already booked", 400

    # Check override
    blocked = Availability.query.filter_by(
        doctor_id=doctor_id,
        type="override",
        date=date
    ).first()

    if blocked:
        return "Doctor unavailable on this date", 400

    appt = Appointment(
        doctor_id=doctor_id,
        patient_id=current_user.patient_profile.id,
        date=date,
        time=time,
        status="pending"
    )

    db.session.add(appt)
    db.session.commit()
    return redirect("/patient/my-appointments")


@patient.route("/payment/<int:appointment_id>")
@login_required
def payment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.patient_profile.id or appt.status != "accepted":
        abort(403)
    
    # Create Razorpay order
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    order_data = {
        "amount": appt.doctor.fees * 100,
        "currency": "INR",
        "receipt": f"appointment_{appt.id}",
        "notes": {
            "appointment_id": appt.id
        }
    }
    order = client.order.create(data=order_data)
    
    return render_template("patient/payment.html", appointment=appt, razorpay_key=current_app.config['RAZORPAY_KEY_ID'], order_id=order['id'])


@patient.route("/payment/success/<int:appointment_id>", methods=["POST"])
@login_required
def payment_success(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.patient_profile.id:
        abort(403)
    
    data = request.get_json()
    
    # Verify payment signature
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })
        appt.status = "paid"
        db.session.commit()
    except:
        # Payment verification failed
        pass
    
    return redirect("/patient/my-appointments")


@patient.route("/my-appointments")
@login_required
def my_appointments():
    from datetime import datetime
    upcoming = Appointment.query.filter(
        Appointment.patient_id == current_user.patient_profile.id,
        Appointment.status.in_(['pending', 'confirmed', 'paid'])
    ).all()
    past = Appointment.query.filter_by(patient_id=current_user.patient_profile.id, status="completed").all()
    canceled = Appointment.query.filter_by(patient_id=current_user.patient_profile.id, status="canceled").all()
    
    def format_date(appt):
        try:
            date_obj = datetime.strptime(appt.date, '%Y-%m-%d')
            time_str = appt.time
            formatted = date_obj.strftime('%A, %B %d, %Y') + ' at ' + time_str
            appt.formatted_datetime = formatted
        except:
            appt.formatted_datetime = appt.date + ' at ' + appt.time
        return appt
    
    upcoming = [format_date(a) for a in upcoming]
    past = [format_date(a) for a in past]
    canceled = [format_date(a) for a in canceled]
    
    return render_template("patient/my_appointments.html", upcoming=upcoming, past=past, canceled=canceled)


@patient.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile = current_user.patient_profile

    if request.method == "POST":
        # Map form fields to model attributes
        profile.date_of_birth = request.form.get("date_of_birth")
        profile.gender = request.form.get("gender")
        profile.blood_group = request.form.get("blood_type")
        profile.phone = request.form.get("contact_number")
        profile.allergies = request.form.get("allergies")
        profile.conditions = request.form.get("chronic_conditions")
        profile.medications = request.form.get("medication_list")
        profile.previous_conditions = request.form.get("conditions")
        profile.surgeries = request.form.get("surgeries")
        profile.family_history = request.form.get("family_history")
        profile.father_history = request.form.get("father_s_medical_history")
        profile.mother_history = request.form.get("mother_s_medical_history")
        profile.immunizations = request.form.get("immunizations")
        profile.phone = request.form.get("primary_phone") or profile.phone
        profile.emergency_contact_phone = request.form.get("secondary_phone")
        profile.address = request.form.get("street_address")
        profile.city = request.form.get("city")
        profile.state = request.form.get("state_province")
        profile.zip_code = request.form.get("zip_postal_code")
        profile.country = request.form.get("country")

        # Handle file upload for patient profile picture
        print(f"Patient profile file: {request.files.get('patient_profile')}")
        upload_dir = os.path.join(current_app.static_folder, 'uploads')
        print(f"Upload dir: {upload_dir}")
        if 'patient_profile' in request.files:
            file = request.files['patient_profile']
            if file and file.filename:
                filename = f"{current_user.id}_{secure_filename(file.filename)}"
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                profile.profile_pic = filename
                print(f"Saved patient profile_pic: {profile.profile_pic}")
            else:
                print("No file or empty filename")

        db.session.commit()
        return redirect("/patient/profile")

    return render_template("patient/profile.html")


@patient.route("/consultations")
@login_required
def consultations():
    # Get the first upcoming appointment
    appointment = Appointment.query.filter(
        Appointment.patient_id == current_user.patient_profile.id,
        Appointment.status.in_(['pending', 'confirmed', 'paid'])
    ).order_by(Appointment.date, Appointment.time).first()
    
    if appointment:
        return redirect(url_for('patient.consultation', appointment_id=appointment.id))
    else:
        flash("No upcoming consultations found.", "info")
        return redirect(url_for('patient.my_appointments'))


@patient.route("/consultation/<int:appointment_id>")
@login_required
def consultation(appointment_id):
    appointment = Appointment.query.filter_by(id=appointment_id, patient_id=current_user.patient_profile.id).first_or_404()
    
    # Get all patient's appointments grouped by doctor (most recent appointment per doctor)
    from sqlalchemy import func
    doctor_appointments = db.session.query(
        Appointment,
        func.row_number().over(
            partition_by=Appointment.doctor_id,
            order_by=[Appointment.date.desc(), Appointment.time.desc()]
        ).label('row_num')
    ).filter(
        Appointment.patient_id == current_user.patient_profile.id
    ).subquery()
    
    recent_appointments = Appointment.query.join(
        doctor_appointments,
        (Appointment.id == doctor_appointments.c.id) & (doctor_appointments.c.row_num == 1)
    ).order_by(Appointment.date.desc()).all()
    
    messages = Message.query.filter_by(appointment_id=appointment_id).order_by(Message.timestamp).all()
    
    return render_template("patient/consultation.html", appointment=appointment, doctor_appointments=recent_appointments, messages=messages)


@patient.route("/appointment/cancel/<int:appointment_id>")
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.filter_by(id=appointment_id, patient_id=current_user.patient_profile.id).first_or_404()
    
    # Only allow cancellation of pending, confirmed, or paid appointments
    if appointment.status in ['pending', 'confirmed', 'paid']:
        appointment.status = "cancelled"
        db.session.commit()
        flash("Appointment cancelled successfully.", "success")
    else:
        flash("This appointment cannot be cancelled.", "error")
    
    return redirect(url_for('patient.dashboard'))