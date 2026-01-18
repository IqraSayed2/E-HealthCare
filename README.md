# E-HealthCare

A comprehensive web-based healthcare platform built with Flask that enables patients to book appointments, consult with doctors online, and manage their health records digitally.

## Features

### For Patients

- User registration and authentication
- Comprehensive patient profile management
- Find and book appointments with doctors
- Online consultations via chat
- Payment processing with Razorpay
- Review and rate doctors
- Emergency contact management
- Medical history tracking

### For Doctors

- Doctor profile and specialization management
- Set availability schedules
- Manage appointments
- Conduct online consultations
- Patient record access
- Communication with patients

### General Features

- Secure user authentication
- Real-time messaging with Socket.IO
- Email notifications
- File uploads for profile pictures
- Responsive web design

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MySQL with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Real-time Communication**: Flask-SocketIO
- **Email**: Flask-Mail
- **Payments**: Razorpay
- **Frontend**: HTML, CSS, JavaScript
- **Migrations**: Flask-Migrate (Alembic)

## Installation

### Prerequisites

- Python 3.8+
- MySQL Server
- Git

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd E-HealthCare
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv env
   env\Scripts\activate  # On Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Database Setup**
   - Create a MySQL database named `ehealthcare`
   - Update database credentials in `app/__init__.py` if needed

5. **Run database migrations**

   ```bash
   flask db upgrade
   ```

6. **Configure Email (Optional)**
   - Update email settings in `app/__init__.py` for Gmail SMTP

7. **Configure Payments (Optional)**
   - Update Razorpay keys in `app/__init__.py`

## Usage

1. **Run the application**

   ```bash
   python run.py
   ```

2. **Access the application**
   - Open your browser and go to `http://localhost:5000`

3. **Register/Login**
   - Create an account as a patient or doctor
   - Complete your profile setup

4. **For Patients**
   - Search for doctors
   - Book appointments
   - Participate in consultations

5. **For Doctors**
   - Set your availability
   - Manage appointments
   - Conduct consultations

## Configuration

Key configuration options in `app/__init__.py`:

- `SECRET_KEY`: Flask secret key
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `MAIL_*`: Email server settings
- `RAZORPAY_*`: Payment gateway keys

## Database Schema

The application uses the following main models:

- User: Base user model with roles
- PatientProfile: Detailed patient information
- DoctorProfile: Doctor specialization and details
- Appointment: Consultation bookings
- Availability: Doctor schedules
- Message: Chat messages
- Review: Doctor ratings

## File Structure

```
E-HealthCare/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── auth.py              # Authentication routes
│   ├── main.py              # Main routes
│   ├── patient.py           # Patient-specific routes
│   ├── doctor.py            # Doctor-specific routes
│   ├── models.py            # Database models
│   ├── extensions.py        # Flask extensions
│   ├── static/              # CSS, JS, images
│   └── templates/           # HTML templates
├── migrations/              # Database migrations
├── env/                     # Virtual environment
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```
