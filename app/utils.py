import re
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
from flask import url_for
from flask_login import login_required, current_user
from .roles import Role
from sqlalchemy import sql
from .models import db

def prepare_datasets(model_class):
    datasets = {}
    # if model_class is a string
    if isinstance(model_class, str):
        text = sql.text(f"SELECT id, name FROM {model_class} ORDER BY name")
        results = db.session.execute(text)
        datasets.update({model_class: results})
        return datasets
    
    # if model_class is a list
    if isinstance(model_class, list):
        for model in model_class:
            text = sql.text(f"SELECT id, name FROM {model} ORDER BY name")
            results = db.session.execute(text)
            datasets.update({model: results})
        return datasets
    
    # if model_class is a class
    for col in model_class.__table__.columns:
        if col.info.get('list') == 'visible':
            for key in col.foreign_keys:
                text = sql.text(f"SELECT id, name FROM {key.column.table.name} ORDER BY name")
                results = db.session.execute(text)
                datasets.update({key.column.table.name: results})
    return datasets


def retreive(table, column, id):
    text = sql.text(f"SELECT * FROM {table} where {column} = {id} ORDER BY id DESC")
    results = db.session.execute(text).fetchall()
    return results

def convert_form_data(form_data):
    form_data = form_data.to_dict()
    isoformat_regex = r'^\d{4}-\d{2}-\d{2}'
    dates = {key: datetime.strptime(value, '%Y-%m-%d').date() 
                 for key, value in form_data.items()  if re.match(isoformat_regex, value)}
    form_data.update(dates)
    bools = {key: True if value in ['true','on'] else False 
                 for key, value in form_data.items() if value in ['true','on']}
    form_data.update(bools)
    return form_data

def determine_consultation_location():
    """Return the automatic location for a consultation based on the creation datetime."""

    current_datetime = datetime.now()
    weekday = current_datetime.weekday()

    if weekday == 2:  # Wednesday
        return "ES"
    if weekday == 3:  # Thursday
        noon = time(12, 0)
        if current_datetime.time() < noon:
            return "Elancourt"
        return "IPS"
    if weekday == 4:  # Friday
        return "IPS"
    return None

def append_select(col, rows, foreign_id, disabled=False):
    text = sql.text(f"SELECT id, name FROM {col.name}")
    results = db.session.execute(text)
    required = "required" if col.nullable == False else ""
    disabled_attr = 'disabled' if disabled else ''
    select = f'''<select name="{col.name}" class="col-md-12" {required} {disabled_attr}>
                <option disabled selected>Sélectionner</option>'''
    for res in results:
        selected = ' selected' if res[0] == foreign_id else ''
        select += f'<option value={ res[0] }{selected}>{ res[1] }</option>'
    select += '</select>'
    rows.append((col.info.get('name'), select))
    return rows

def append_select_2(col, disabled=False):
    text = sql.text(f"SELECT id, name FROM {col} ORDER BY name")
    results = db.session.execute(text)
    disabled_attr = 'disabled' if disabled else ''
    select = f'''<select name="{col}" class="col-md-12" {disabled_attr}>
                <option selected value="default">Sélectionner</option>'''
    for res in results:
        select += f'<option value={ res[0] }>{ res[1] }</option>'
    select += '</select>'
    return select

def append_select_3(col, disabled=False):
    if disabled:
        return f'<input type="text" class="col-md-12" readonly>'
    select = f'''<input id="{col}-search" type="search"
                class="search col-md-12" placeholder="Rechercher...">
                <input type="hidden" name="{col}" id="{col}-value">
                <div class="table-responsive" style="max-height: 200px; overflow-y: auto;">
                <table id="{col}-table">
                <tbody></tbody></table></div>'''
    return select

def generate_rows(model_class, payload):
    data = payload.get('data')
    id = payload.get('id')
    read_only = payload.get('read_only', False)
    disabled_attr = 'disabled' if read_only else ''
    readonly_attr = 'readonly' if read_only else ''
    rows = []
    next_time = date.today()  + relativedelta(years=1)
    before = date.today() - relativedelta(years=100)
    if id and model_class.__tablename__ == 'patient':
        payload['consultations'] = retreive('consultation', 'patient', id)
        payload['appointments'] = retreive('appointment', 'patient', id)
        payload['residencies'] = retreive('residency', 'patient', id)
        payload['coverages'] = retreive('coverage', 'patient', id)
        payload['datasets'] = prepare_datasets(['user', 'city', 'accommodation'])
        payload['cities'] = append_select_2('city', disabled=read_only)
        payload['accommodations'] = append_select_2('accommodation', disabled=read_only)
    elif id and model_class.__tablename__ == 'consultation':
        payload['prescriptions'] = retreive('prescription', 'consultation', id)
        payload['orientations'] = retreive('orientation', 'consultation', id)
        payload['datasets'] = prepare_datasets(['drugstore', 'specialist'])
        payload['drugstore'] = append_select_3('drugstore', disabled=read_only)
        payload['specialists'] = append_select_2('specialist', disabled=read_only)
    for col in model_class.__table__.columns:
        value = getattr(data, col.name)
        required = "required" if col.nullable == False else ""
        if col.name == 'id' or (col.name in ["history", "vaccination", "notes", "treatment"] and not current_user.has_role(Role.DOCTOR)):
            continue
        elif str(col.type) == 'INTEGER':
            if model_class.__tablename__ == 'drugstore':
                rows.append((col.info.get('name'), f'<input type="number" name="{col.name}" value="{value or 0}" {required} class="col-md-12" {disabled_attr}></input>'))
            elif id and model_class.__tablename__ == 'prescription':
                if col.name == 'qty':
                    rows.append((col.info.get('name'), f'<input type="text" name="{col.name}" value="{value}" {required} class="col-md-12" {disabled_attr}></input>'))

            # Retreive data from the foreign key table
            for foreign_key in col.foreign_keys:
                foreign_id = getattr(data, col.name)
                if model_class.__tablename__ == 'user':
                    if col.name == 'role':
                        rows = append_select(col, rows, foreign_id, disabled=read_only)
                elif model_class.__tablename__ == 'consultation':
                    if col.name == 'patient':
                        sql_query = sql.text(f"SELECT id, firstname, lastname FROM patient WHERE id = {foreign_id}")
                        patient = db.session.execute(sql_query).first()
                        rows.append(('Patient', patient))
                    if col.name == 'healer':
                        sql_query = sql.text(f"SELECT name FROM user WHERE id = {foreign_id}")
                        patient = db.session.execute(sql_query).first()
                        rows.append(('Soignant', patient[0]))
                elif model_class.__tablename__ == 'patient':
                    if col.name in ['accommodation', 'city']:
                        rows = append_select(col, rows, foreign_id, disabled=read_only)
                elif model_class.__tablename__ == 'prescription':
                    if col.name in ['drugstore']:
                        rows = append_select(col, rows, foreign_id, disabled=read_only)
        elif str(col.type) == 'VARCHAR':
            value = value if value else ""
            if col.name in ['gender']:
                rows.append((col.info.get('name'), f'''<select name="{col.name}" class="col-md-1" {disabled_attr}>
                             <option disabled selected>Sélectionner</option>
                             <option value="M" { "selected" if value == "M" else "" }>Masculin</option>
                             <option value="F" { "selected" if value == "F" else "" }>Féminin</option>
                             <option value="A" { "selected" if value == "A" else "" }>Autre</option></select>'''))
            elif col.name in ['location']:
                rows.append((col.info.get('name'), f'''<select name="{col.name}" class="col-md-2" {disabled_attr}>
                             <option disabled selected>Sélectionner</option>
                             <option value="ES" { "selected" if value == "ES" else "" }>Espace Solidarité</option>
                             <option value="IPS" { "selected" if value == "IPS" else "" }>IPS</option>
                             <option value="Elancourt" { "selected" if value == "Elancourt" else "" }>Elancourt</option>'''))
            else:
                rows.append((col.info.get('name'), f'<input type="text" name="{col.name}" value="{value}" {required} class="col-md-12" {readonly_attr} {disabled_attr}></input>'))
        elif str(col.type) == 'TEXT':
            if value:
                rows.append((col.info.get('name'), f'<textarea rows="4" name="{col.name}" {required} class="col-md-12" {readonly_attr} {disabled_attr}>{value}</textarea>'))
            else:
                rows.append((col.info.get('name'), f'<textarea rows="4" name="{col.name}" {required} class="col-md-12" {readonly_attr} {disabled_attr}></textarea>'))
        elif str(col.type) == 'DATE':
            if id and model_class.__table__.name == 'file':
                rows.append((col.info.get('name'), f'<span class="date">{value}</span>'))
            elif id:
                rows.append((col.info.get('name'), f'<input type="date" name="{col.name}" value="{value}" class="date" {disabled_attr}></input>'))
            else:
                rows.append((col.info.get('name'), f'<input type="date" name="{col.name}" value="{value}" {required} min="{before}" max="{next_time}" {disabled_attr}></input>'))
        elif str(col.type) == 'BOOLEAN':
            if id:
                checked = "checked" if value else ""
                rows.append((col.info.get('name'), f'<input type="checkbox" name="{col.name}" value="true" {required} {checked} {disabled_attr}></input>'))
    return rows

def build_sections(table, payload, user):
    sections = []
    id = payload.get('id')

    if table == 'patient' and id:
        sections.append({
            'title': 'Résidence',
            'popup': 'residency',
            'table_headers': ['Date', 'Ville', 'Nature hébergement', 'Adresse', 'Notes'],
            'table_content': ['date', 'city', 'accommodation', 'address', 'notes'],
            'rows': payload.get('residencies'),
            'form_action': url_for('residency.create'),
            'delete_action': url_for('residency.delete'),
            'name': 'patient',
            'writable': user.can_write('patient') if user else False,
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
            'rows': payload.get('coverages'),
            'form_action': url_for('coverage.create'),
            'delete_action': url_for('coverage.delete'),
            'name': 'patient',
            'writable': user.can_write('patient') if user else False,
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
            'rows': payload.get('prescriptions'),
            'form_action': url_for('prescription.create'),
            'delete_action': url_for('prescription.delete'),
            'name': 'consultation',
            'writable': user.can_write('consultation') if user else False,
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
            'rows': payload.get('orientations'),
            'form_action': url_for('orientation.create'),
            'delete_action': url_for('orientation.delete'),
            'name': 'consultation',
            'writable': user.can_write('consultation') if user else False,
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
            'rows': payload.get('appointments'),
            'form_action': url_for('appointment.create'),
            'delete_action': url_for('appointment.delete'),
            'name': 'patient',
            'writable': user.can_write('appointment'),
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
