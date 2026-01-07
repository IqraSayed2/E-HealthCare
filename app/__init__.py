from flask import Flask
from .extensions import db, migrate, login_manager
from flask_login import login_required
from .models import User

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['SECRET_KEY'] = "your_secret_key"
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:root@localhost/ehealthcare"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Init Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

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