# main.py

from datetime import datetime
import json
from flask import Blueprint, request, render_template, redirect, url_for, make_response
from flask_login import login_required, current_user
from sqlalchemy import desc, sql
from weasyprint import HTML
from .models import db
from . import utils
import locale

locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
today = datetime.now().strftime('%d %b %Y')


def build_sections(table, payload, user):
    sections = []
    id = payload.get('id')

    if table == 'patient' and id:
        sections.append({
            'title': 'Résidence',
            'popup': 'residency',
            'table_headers': ['Date', 'Ville', 'Nature hébergement', 'Adresse', 'Notes'],
            'table_content': ['date', 'city', 'accommodation', 'address', 'notes'],
            'items': payload.get('residencies'),
            'form_action': url_for('residency.create'),
            'delete_action': url_for('residency.delete'),
            'name': 'patient',
            'form_fields': [
                {'label': 'Ville', 'input': payload.get('cities')},
                {'label': 'Nature Hébergement', 'input': payload.get('accommodations')},
                {'label': 'Adresse', 'input': '<input type="text" name="address" class="col-md-12">'},
                {'label': 'Notes', 'input': '<input type="text" name="notes" class="col-md-12">'}
            ],
            'print_url': False,
            'print_items': False,
        })

        sections.append({
            'title': 'Droits sociaux',
            'popup': 'coverage',
            'table_headers': ['Date', 'Droits sociaux', 'Notes'],
            'table_content': ['date', 'current', 'notes'],
            'items': payload.get('coverages'),
            'form_action': url_for('coverage.create'),
            'delete_action': url_for('coverage.delete'),
            'name': 'patient',
            'form_fields': [
                {
                    'label': 'Couverture',
                    'input': (
                        '<select name="current" class="col-md-12">'
                        '<option disabled selected value="default">Sélectionner</option>'
                        '<option value="oui">Oui</option>'
                        '<option value="non">Non</option>'
                        '<option value="inprogress">En cours</option>'
                        '</select>'
                    ),
                },
                {'label': 'Notes', 'input': '<input type="text" name="notes" class="col-md-12">'},
            ],
            'print_url': False,
            'print_items': False,
        })

    if table == 'consultation' and id:
        sections.append({
            'title': 'Prescription médicaments',
            'popup': 'prescription',
            'table_headers': [
                'Date',
                'Médicament',
                "Nombre d'unités",
                'Notes',
                'Posologie',
                'Remis',
            ],
            'table_content': ['date', 'drugstore', 'qty', 'notes', 'posology', 'given'],
            'items': payload.get('prescriptions'),
            'form_action': url_for('prescription.create'),
            'delete_action': url_for('prescription.delete'),
            'name': 'consultation',
            'form_fields': [
                {'label': 'Médicament', 'input': payload.get('drugstore')},
                {
                    'label': "Nombre d'unités",
                    'input': '<input type="number" name="qty" min="1" max="100" required>',
                },
                {'label': 'Notes', 'input': '<input type="text" name="notes" class="col-md-12">'},
                {'label': 'Posologie', 'input': '<input type="text" name="posology" class="col-md-12">'},
                {'label': 'Remis', 'input': '<input type="checkbox" name="given">'},
            ],
            'print_url': url_for('consultation.print_prescriptions', consultation_id=id),
            'print_items': False,
        })

        sections.append({
            'title': 'Orientations',
            'popup': 'orientations',
            'table_headers': ['Date', 'Spécialiste', 'Notes'],
            'table_content': ['date', 'specialist', 'notes'],
            'items': payload.get('orientations'),
            'form_action': url_for('orientation.create'),
            'delete_action': url_for('orientation.delete'),
            'name': 'consultation',
            'form_fields': [
                {'label': 'Spécialiste', 'input': payload.get('specialists')},
                {
                    'label': 'Notes',
                    'input': '<textarea rows="4" name="notes" class="col-md-12"></textarea>',
                },
            ],
            'print_url': False,
            'print_items': True,
        })

    if table == 'patient' and id and user and user.can_create('appointment'):
        sections.append({
            'title': 'Assistance sociale',
            'popup': 'appointments',
            'table_headers': ['Date', 'Motif', 'Notes sur le rendez-vous'],
            'table_content': ['date', 'motive', 'notes'],
            'items': payload.get('appointments'),
            'form_action': url_for('appointment.create'),
            'delete_action': url_for('appointment.delete'),
            'name': 'patient',
            'form_fields': [
                {'label': 'Motif', 'input': '<input type="text" name="motive" class="col-md-12">'},
                {
                    'label': 'Notes',
                    'input': '<textarea rows="4" name="notes" class="col-md-12"></textarea>',
                },
                {
                    'input': f'<input type="number" name="healer" value="{user.id}" hidden>'
                },
            ],
            'print_url': False,
            'print_items': False,
        })

    return sections

def create_blueprint_for_model(model_class):
    blueprint = Blueprint(model_class.__tablename__, __name__)

    @blueprint.route('/create', methods=['POST'])
    @login_required
    def create():
        form_data = utils.convert_form_data(request.form)
        new_entry = model_class(**form_data)
        db.session.add(new_entry)
        db.session.commit()
        # Remove qty from drugstore stock if update is a prescription.
        if (model_class.__tablename__ == 'prescription' 
            and form_data.get('given')
            and form_data.get('drugstore')
            and form_data.get('drugstore') != 'default'): 
            text = sql.text(f"UPDATE drugstore SET qty = qty - {form_data['qty']} WHERE id = {form_data['drugstore']}")
            db.session.execute(text)
            db.session.commit()
        if model_class.__tablename__ in ['prescription', 'orientation', 'residency', 'coverage', 'appointment']:
            return redirect(request.referrer + '#bottom')
        elif model_class.__tablename__ in ['patient']:
            return redirect(url_for(f"{model_class.__tablename__}.update") + "/" + repr(new_entry.id))
        else:
            return redirect(url_for(f"{model_class.__tablename__}.all"))
        
    @blueprint.route('/delete', defaults={ 'id': None }, methods=['POST'])
    @login_required
    def delete(id):
        id = request.form.get('id')
        if id:
            entry = model_class.query.get(id)
            db.session.delete(entry)
            db.session.commit()
        return redirect(request.referrer + '#bottom')
        
    
    @blueprint.route('/update', defaults={ 'id': None }, methods=['GET','POST'])    
    @blueprint.route('/update/<id>', methods=['GET','POST'])
    @login_required
    def update(id):
        payload = {'table': model_class.__tablename__,
                   'data':  model_class.query.get(id) if id else model_class(),
                   'user': current_user,
                   'deletable': False,
                   'today': False,
                   'id': id,
                   'columns': []}
        # Replace text by Python datetime object.
        form_data = utils.convert_form_data(request.form)

        # Update the entry if the form is submitted.
        if id and request.method == 'POST':
            for key in form_data:
                if hasattr(payload['data'], key):
                    setattr(payload['data'], key, form_data[key])
            db.session.commit()
            
            return redirect(url_for(f"{model_class.__tablename__}.all"))
        
        # Create a new entry if the form is submitted.
        elif not id and request.method == 'POST':
            new_entry = model_class(**form_data)
            db.session.add(new_entry)
            db.session.commit()
            return redirect(url_for(f"{payload['table']}.update") + "/" + repr(new_entry.id))
        else:
            # Generate the form fields.
            payload['rows'] = utils.generate_rows(model_class, payload)
            payload['sections'] = build_sections(model_class.__tablename__, payload, current_user)
            if hasattr(payload['data'], 'date') and payload['data'].date == datetime.now().date():
                payload['deletable'] = True
                payload['today'] = True
            # Update the "viewed" field for patient
            if (id and model_class.__tablename__ == "patient"):
                text = sql.text(f"UPDATE patient SET viewed = CURRENT_TIMESTAMP WHERE id = {id}")
                db.session.execute(text)
                db.session.commit()
            return render_template('entry.html', **payload)

    @blueprint.route('/', methods=['GET'])
    @login_required
    def all():
        order_by = desc(model_class.id)
        if model_class.__tablename__  == "patient":
            order_by = sql.text("viewed desc")
        elif model_class.__tablename__  == "drugstore":
            order_by = sql.text("name")
        if model_class.__tablename__ in ['consultation', 'prescription', 'appointment']:
            return redirect(url_for(f"patient.all"))

        payload = {'table': model_class.__tablename__, 
                   'data': model_class.query.order_by(order_by).all(),
                   'user': current_user,
                   'datasets': utils.prepare_datasets(model_class), 
                   'columns': [(col.name, col.info.get('name')) 
                                for col in model_class.__table__.columns 
                                if col.info.get('list') == 'visible']}
        return render_template('entries.html', **payload)
    
    # add a route to print prescriptions
    @blueprint.route('/print/<consultation_id>/prescriptions', methods=['GET'])
    @login_required
    def print_prescriptions(consultation_id):
        items = []
        patient = ''
        birth = ''
        text = sql.text(f"""SELECT patient.firstname, patient.lastname, patient.birth,
                                   COALESCE(drugstore.name, ' '),
                                   prescription.notes, prescription.posology, prescription.given 
                            FROM prescription 
                            LEFT JOIN  drugstore ON prescription.drugstore = drugstore.id,
                            consultation ON consultation.id = {consultation_id},
                            patient ON patient.id = consultation.patient
                            WHERE consultation = {consultation_id}""")
        results = db.session.execute(text).fetchall()

        for row in results:
            patient = f"{row[0]} {row[1]}"
            birth = f"Né(e) le {row[2]}"
            drug = row[3] if row[3] != 'Autre' else ''
            prescription = f'{drug}\n{row[4]} {row[5]}'
            prescription += '\n (REMIS)' if row[6] else ''
            items.append(prescription)
        rendered = render_template('print.html', items=items, 
                                    today=today, patient=patient, birth=birth)
        pdf = HTML(string=rendered).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=output.pdf'
        return response
    
    # add a route to print orientation
    @blueprint.route('/print/orientation/<orientation_id>', methods=['GET'])
    @login_required
    def print_orientation(orientation_id):
        text = sql.text(f"""SELECT patient.firstname, patient.lastname, patient.birth,
                                   specialist.name, orientation.notes
                            FROM orientation 
                            JOIN specialist ON orientation.specialist = specialist.id,
                            consultation ON consultation.id = orientation.consultation,
                            patient ON patient.id = consultation.patient
                            WHERE orientation.id = {orientation_id}""")

        results = db.session.execute(text).fetchall()
        items = []
        for row in results:
            patient = f"{row[0]} {row[1]}"
            birth = f"Né(e) le {row[2]}"
            orientation = f'Orientation : {row[3]}\n\n{row[4]}'
            items.append(orientation)
        rendered = render_template('print.html', items=items, 
                                    today=today, patient=patient, birth=birth)
        pdf = HTML(string=rendered).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=output.pdf'
        return response
    return blueprint
