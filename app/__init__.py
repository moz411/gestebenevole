# init.py
import os
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager 

from .roles import Role as RoleEnum

db = SQLAlchemy()


ROLE_LABELS = {
    RoleEnum.ADMIN: "Admin",
    RoleEnum.RECEPTION: "Accueil",
    RoleEnum.PHARMACIST: "Pharmacien.ne",
    RoleEnum.SOCIAL_WORKER: "Assistant.e social.e",
    RoleEnum.PSYCHOLOGIST: "Psychologue",
    RoleEnum.DOCTOR: "Médecin",
    RoleEnum.PHYSIOTHERAPIST: "Kinésithérapeute",
}


def _ensure_roles(RoleModel):
    for role_enum, role_label in ROLE_LABELS.items():
        existing_role = RoleModel.query.get(role_enum.value)
        if existing_role:
            if existing_role.name != role_label:
                existing_role.name = role_label
            continue
        db.session.add(RoleModel(id=role_enum.value, name=role_label))
    db.session.commit()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data/gestebenevole.sqlite'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 60
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    with app.app_context():
        from .models import User, Patient, Consultation, Appointment, Physiotherapy, Psychology, Drugstore, Prescription, Orientation, Residency, Coverage, Role as RoleModel

        from .main import create_blueprint_for_model
        db.create_all()
        _ensure_roles(RoleModel)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    user_blueprint = create_blueprint_for_model(User)
    patient_blueprint = create_blueprint_for_model(Patient)
    consultation_blueprint = create_blueprint_for_model(Consultation)
    appointment_blueprint = create_blueprint_for_model(Appointment)
    physiotherapy_blueprint = create_blueprint_for_model(Physiotherapy)
    psychology_blueprint = create_blueprint_for_model(Psychology)
    drugstore_blueprint = create_blueprint_for_model(Drugstore)
    prescription_blueprint = create_blueprint_for_model(Prescription)
    orientation_blueprint = create_blueprint_for_model(Orientation)
    residency_blueprint = create_blueprint_for_model(Residency)
    coverage_blueprint = create_blueprint_for_model(Coverage)

    app.register_blueprint(patient_blueprint, name='landing', url_prefix='/')
    app.register_blueprint(user_blueprint, url_prefix='/utilisateurs')
    app.register_blueprint(patient_blueprint, url_prefix='/patients')
    app.register_blueprint(consultation_blueprint, url_prefix='/consultations')
    app.register_blueprint(appointment_blueprint, url_prefix='/appointments')
    app.register_blueprint(physiotherapy_blueprint, url_prefix='/physiotherapy')
    app.register_blueprint(psychology_blueprint, url_prefix='/psychology')
    app.register_blueprint(drugstore_blueprint, url_prefix='/pharmacie')
    app.register_blueprint(prescription_blueprint, url_prefix='/prescriptions')
    app.register_blueprint(orientation_blueprint, url_prefix='/orientations')
    app.register_blueprint(residency_blueprint, url_prefix='/residencies')
    app.register_blueprint(coverage_blueprint, url_prefix='/coverage')
    return app
