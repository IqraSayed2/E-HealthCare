from flask import Blueprint, render_template, redirect, url_for

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return render_template("index.html")

@main.route("/about")
def about():
    return render_template("about.html")

@main.route("/services")
def services():
    return render_template("services.html")


@main.route("/find-doctor")
def find_doctor():
    # Top-level route that forwards to the patient blueprint's find_doctor view.
    # That view is protected with @login_required and will redirect to login if needed.
    return redirect(url_for('patient.find_doctor'))