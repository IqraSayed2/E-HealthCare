from flask import Flask
from .extensions import db, migrate, login_manager, mail
from flask_login import login_required
from .models import User

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['SECRET_KEY'] = "your_secret_key"
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:root@localhost/ehealthcare"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Mail config
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = '1qrasayed002@gmail.com' 
    app.config['MAIL_PASSWORD'] = 'ssun uxuu hslz oejy'  

    # Razorpay config
    app.config['RAZORPAY_KEY_ID'] = 'rzp_test_mq3sbKjLFm3iSq'
    app.config['RAZORPAY_KEY_SECRET'] = 'sky7oMoflB2U7go95g6KgDgE'  

    # Init Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Import Blueprints
    from .main import main
    from .auth import auth
    from .patient import patient
    from .doctor import doctor

    # Register Blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(patient)
    app.register_blueprint(doctor)

    return app