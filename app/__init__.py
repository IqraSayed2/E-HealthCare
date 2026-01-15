from flask import Flask
from .extensions import db, migrate, login_manager, mail
from flask_login import login_required
from flask_socketio import SocketIO, join_room
from .models import User, Message

socketio = SocketIO()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
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
    socketio.init_app(app)

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

    # Custom template filters
    from datetime import datetime

    @app.template_filter('calculate_age')
    def calculate_age(dob_str):
        if not dob_str:
            return "N/A"
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d')
            today = datetime.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except ValueError:
            return "N/A"

    # SocketIO events
    @socketio.on('join')
    def handle_join(data):
        join_room(data['appointment_id'])

    @socketio.on('send_message')
    def handle_send_message(data):
        appointment_id = data['appointment_id']
        sender_id = data['sender_id']
        content = data['content']
        
        from .models import Message, User
        message = Message(appointment_id=appointment_id, sender_id=sender_id, content=content)
        db.session.add(message)
        db.session.commit()
        
        sender = User.query.get(sender_id)
        sender_name = sender.name
        socketio.emit('receive_message', {
            'content': content,
            'sender_name': sender_name,
            'sender_id': sender_id,
            'timestamp': message.timestamp.strftime('%I:%M %p'),
            'sender_initials': ''.join([name[0] for name in sender.name.split()]).upper()
        }, room=appointment_id)

    return app