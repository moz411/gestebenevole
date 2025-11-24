# main.py

from datetime import datetime
import json
from flask import Blueprint, request, render_template, redirect, url_for, make_response, abort
from flask_login import login_required, current_user
from sqlalchemy import desc, sql
from weasyprint import HTML
from .models import db
from . import utils
import locale

locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
today = datetime.now().strftime('%d %b %Y')

def create_blueprint_for_model(model_class):
    blueprint = Blueprint(model_class.__tablename__, __name__)

    @blueprint.route('/create', methods=['POST'])
    @login_required
    def create():
        if not current_user.can_write(model_class.__tablename__):
            return abort(403)
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
        if not current_user.can_write(model_class.__tablename__):
            return abort(403)
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
        can_write = current_user.can_write(model_class.__tablename__)
        payload = {'table': model_class.__tablename__,
                   'data':  model_class.query.get(id) if id else model_class(),
                   'user': current_user,
                   'deletable': False,
                   'today': False,
                   'id': id,
                   'columns': [],
                   'can_write': can_write,
                   'read_only': not can_write}
        # Replace text by Python datetime object.
        form_data = utils.convert_form_data(request.form)

        # Update the entry if the form is submitted.
        if request.method == 'POST' and not can_write:
            return abort(403)

        if id and request.method == 'POST':
            for key in form_data:
                if hasattr(payload['data'], key):
                    setattr(payload['data'], key, form_data[key])
            db.session.commit()
            
            return redirect(url_for(f"{model_class.__tablename__}.all"))
        
        # Create a new entry if the form is submitted.
        elif not id and request.method == 'POST':
            if model_class.__tablename__ == 'consultation':
                form_data["location"] = utils.determine_consultation_location()
            new_entry = model_class(**form_data)
            db.session.add(new_entry)
            db.session.commit()
            return redirect(url_for(f"{payload['table']}.update") + "/" + repr(new_entry.id))
        else:
            # Generate the form fields.
            payload['rows'] = utils.generate_rows(model_class, payload)
            payload['sections'] = utils.build_sections(model_class.__tablename__, payload, current_user)
            if hasattr(payload['data'], 'date') and payload['data'].date == datetime.now().date() and can_write:
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
