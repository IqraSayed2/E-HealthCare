from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from .models import User, PatientProfile, DoctorProfile
from .extensions import db

auth = Blueprint("auth", __name__)

@auth.route("/login-signup", methods=["GET", "POST"])
def login_signup():
    # Accept ?tab=login or ?tab=signup to open a specific tab
    tab = request.args.get('tab', 'login')
    return render_template("auth.html", active_tab=tab)

@auth.route("/signup", methods=["POST"])
def signup():
    role = request.form.get("role")
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    password_confirm = request.form.get("password_confirm")

    # Basic validation
    if not password or password != password_confirm:
        flash('Passwords do not match', 'signup')
        return redirect(url_for('auth.login_signup', tab='signup'))

    if User.query.filter_by(email=email).first():
        flash('An account with that email already exists', 'signup')
        return redirect(url_for('auth.login_signup', tab='signup'))

    hashed = generate_password_hash(password)
    user = User(name=name, email=email, password=hashed, role=role)
    db.session.add(user)
    db.session.commit()

    if role == "patient":
        db.session.add(PatientProfile(user_id=user.id))
    else:
        db.session.add(DoctorProfile(user_id=user.id))

    db.session.commit()
    flash('Account created successfully — please login', 'login')
    return redirect(url_for("auth.login_signup", tab='login'))

@auth.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        flash('Invalid email or password', 'login')
        return redirect(url_for('auth.login_signup', tab='login'))

    login_user(user)

    if user.role == "patient":
        return redirect("/patient/dashboard")
    else:
        return redirect("/doctor/dashboard")

@auth.route("/logout")
def logout():
    logout_user()
    return redirect("/")