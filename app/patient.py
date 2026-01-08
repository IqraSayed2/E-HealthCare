from flask import Blueprint, render_template, request, redirect
from flask_login import login_required, current_user
from .models import DoctorProfile, Appointment, PatientProfile, Availability, User, Review
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

    slots = Availability.query.filter_by(
        doctor_id=id
    ).order_by(Availability.date, Availability.start_time).all()

    # group slots by date
    slots_by_date = {}
    for s in slots:
        slots_by_date.setdefault(s.date, []).append(s)

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
        slots_by_date=slots_by_date,
        reviews=reviews,
        avg_rating=avg_rating
    )


@patient.route("/book/<int:doctor_id>", methods=["POST"])
@login_required
def book(doctor_id):

    date = request.form["date"]
    time = request.form["time"]

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

        db.session.commit()
        return redirect("/patient/profile")

    return render_template("patient/profile.html")
