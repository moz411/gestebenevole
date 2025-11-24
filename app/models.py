# models.py

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, Boolean

from . import rbac
from .roles import Role

from . import db

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True) 
    name = Column(String, nullable=False, info={'name': 'Nom', 'list': 'visible'})
    email = Column(String, nullable=False, info={'name': 'Email', 'list': 'visible'})
    password = Column(String, nullable=False, info={'name': 'Mot de passe'})
    role = Column(Integer, ForeignKey('role.id'), nullable=False, info={'name': 'Rôle', 'list': 'visible'})

    # RBAC helper methods
    def has_role(self, *roles):
        allowed = [r.value if isinstance(r, Role) else r for r in roles]
        return self.role in allowed

    def can_create(self, table):
        return rbac.can_create(self, table)

    def can_read(self, item):
        return rbac.can_read(self, item)

    def can_write(self, table):
        return rbac.can_write(self, table)

class Patient(db.Model):
    __tablename__ = 'patient'
    id = Column(Integer, primary_key=True)
    lastname = Column(String, nullable=False, info={'name': 'Nom', 'list': 'visible'})
    firstname = Column(String, nullable=False, info={'name': 'Prénom', 'list': 'visible'})
    added = Column(Date, nullable=False,  info={'name': 'Première visite', 'list': 'visible'})
    birth = Column(Date, nullable=False,  info={'name': 'Date de naissance', 'list': 'visible'})
    arrival = Column(Date, nullable=False,  info={'name': "Date d'arrivée en France"})
    gender = Column(String, info={'name': 'Genre'})
    phone = Column(String, info={'name': 'Téléphone'})
    email = Column(String, info={'name': 'Email/Facebook'})
    nationality = Column(String, info={'name': 'Nationalité'})
    addressed_by = Column(String, info={'name': 'Adressé par'})
    treatment = Column(String, info={'name': 'Traitement en cours'})
    vaccination = Column(String, info={'name': 'Vaccination'})
    history = Column(Text, info={'name': 'ATCD'})
    notes = Column(Text, info={'name': 'Notes réservées au médecin'})
    infos = Column(Text, info={'name': 'Notes pour les accueillant.es', 'list': 'visible'})
    
class Residency(db.Model):
    __tablename__ = 'residency'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False,  info={'name': 'Date'})
    patient = Column(Integer, ForeignKey('patient.id'), nullable=False, info={'name': 'Patient', 'list': 'visible'})
    city = Column(Integer, ForeignKey('city.id'), info={'name': 'Ville', 'list': 'visible'})
    accommodation = Column(Integer, ForeignKey('accommodation.id'), info={'name': 'Nature hébergement', 'list': 'visible'})
    address = Column(String, info={'name': 'Adresse', 'list': 'visible'})
    notes = Column(Text, info={'name': 'Notes sur la résidence', 'list': 'visible'})

class Consultation(db.Model):
    __tablename__ = 'consultation'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False,  info={'name': 'Date'})
    patient = Column(Integer, ForeignKey('patient.id'), nullable=False, info={'name': 'Patient', 'list': 'visible'})
    healer = Column(Integer,ForeignKey('user.id'), nullable=False, info={'name': 'Soignant', 'list': 'visible'})
    motive = Column(String, nullable=False, info={'name': 'Motif'})
    notes = Column(Text, info={'name': 'Notes sur la consultation'})
    location = Column(String, info={'name': 'Emplacement'})

class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False,  info={'name': 'Date'})
    patient = Column(Integer, ForeignKey('patient.id'), nullable=False, info={'name': 'Patient', 'list': 'visible'})
    healer = Column(Integer,ForeignKey('user.id'), nullable=False, info={'name': 'Assistant.e', 'list': 'visible'})
    motive = Column(String, nullable=False, info={'name': 'Motif'})
    notes = Column(Text, info={'name': 'Notes sur le rendez-vous'})

class Prescription(db.Model):
    __tablename__ = 'prescription'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, info={'name': 'Date'})
    consultation = Column(Integer, ForeignKey('consultation.id'), nullable=False, info={'name': 'Consultation'})
    drugstore = Column(Integer, ForeignKey('drugstore.id'),  nullable=False, info={'name': 'Médicament'})
    qty = Column(Integer, nullable=False, info={'name': "Nombre d'unités"})
    posology = Column(Text, info={'name': 'Posologie'})
    notes = Column(Text, info={'name': 'Notes sur la prescription'})
    given = Column(Boolean, info={'name': 'Remis'})

class Orientation(db.Model):
    __tablename__ = 'orientation'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, info={'name': 'Date', 'list': 'visible'})
    consultation = Column(Integer, ForeignKey('consultation.id'), nullable=False, info={'name': 'Consultation', 'list': 'visible'})
    specialist = Column(String, info={'name': 'Spécialiste', 'list': 'visible'})
    notes = Column(Text, info={'name': "Notes sur l'orientation", 'list': 'visible'})

class Coverage(db.Model):
    __tablename__ = 'coverage'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, info={'name': 'Date', 'list': 'visible'})
    patient = Column(Integer, ForeignKey('patient.id'), nullable=False, info={'name': 'Patient', 'list': 'visible'})
    current = Column(String, info={'name': 'Droits sociaux', 'list': 'visible'})
    notes = Column(String, info={'name': 'Notes sur la couverture sociale', 'list': 'visible'})

class Role(db.Model):
    __tablename__ = 'role'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class Drugstore(db.Model):
    __tablename__ = 'drugstore'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, info={'name': 'Nom', 'list': 'visible'})
    qty = Column(Integer, info={'name': 'Quantité', 'list': 'visible'})

class Specialist(db.Model):
    __tablename__ = 'specialist'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, info={'name': 'Nom', 'list': 'visible'})

class City(db.Model):
    __tablename__ = 'city'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, info={'name': 'Ville'})

class Accommodation(db.Model):
    __tablename__ = 'accommodation'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, info={'name': 'Nature hébergement'})
