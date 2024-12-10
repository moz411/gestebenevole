import re
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from flask_login import login_required, current_user
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
    results = db.session.execute(text)
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

def append_select(col, rows, foreign_id):
    text = sql.text(f"SELECT id, name FROM {col.name}")
    results = db.session.execute(text)
    required = "required" if col.nullable == False else ""
    select = f'''<select name="{col.name}" class="col-md-12" {required}>
                <option disabled selected>Sélectionner</option>'''
    for res in results:
        select += f'<option value={ res[0] }>{ res[1] }</option>'
        if res[0] == foreign_id:
            select += f'<option value={ res[0] } selected>{ res[1] }</option>'
    select += '</select>'
    rows.append((col.info.get('name'), select))
    return rows

def append_select_2(col):
    text = sql.text(f"SELECT id, name FROM {col} ORDER BY name") 
    results = db.session.execute(text)
    select = f'''<select name="{col}" class="col-md-12">
                <option selected value="default">Sélectionner</option>'''
    for res in results:
        select += f'<option value={ res[0] }>{ res[1] }</option>'
    select += '</select>'
    return select

def generate_rows(model_class, payload):
    data = payload.get('data')
    id = payload.get('id')
    rows = []
    next_time = date.today()  + relativedelta(years=1)
    before = date.today() - relativedelta(years=100)
    if id and model_class.__tablename__ == 'patient':
        payload['consultations'] = retreive('consultation', 'patient', id)
        payload['appointments'] = retreive('appointment', 'patient', id)
        payload['residencies'] = retreive('residency', 'patient', id)
        payload['coverages'] = retreive('coverage', 'patient', id)
        payload['datasets'] = prepare_datasets(['user', 'city', 'accommodation'])
        payload['cities'] = append_select_2('city')
        payload['accommodations'] = append_select_2('accommodation')
    elif id and model_class.__tablename__ == 'consultation':
        payload['prescriptions'] = retreive('prescription', 'consultation', id)
        payload['orientations'] = retreive('orientation', 'consultation', id)
        payload['datasets'] = prepare_datasets(['drugstore', 'specialist'])
        payload['drugstore'] = append_select_2('drugstore')
        payload['specialists'] = append_select_2('specialist')
    for col in model_class.__table__.columns:
        value = getattr(data, col.name)
        required = "required" if col.nullable == False else ""
        if col.name == 'id':
            continue
        elif col.name in ["history", "vaccination"] and current_user.role not in [1,6]:
            continue
        elif str(col.type) == 'INTEGER':
            if model_class.__tablename__ == 'drugstore':
                rows.append((col.info.get('name'), f'<input type="number" name="{col.name}" value="{value or 0}" {required} class="col-md-12"></input>')) 
            elif id and model_class.__tablename__ == 'prescription':
                if col.name == 'qty':
                    rows.append((col.info.get('name'), f'<input type="text" name="{col.name}" value="{value}" {required} class="col-md-12"></input>')) 

            # Retreive data from the foreign key table
            for foreign_key in col.foreign_keys:
                foreign_id = getattr(data, col.name)
                if model_class.__tablename__ == 'user':
                    if col.name == 'role':
                        rows = append_select(col, rows, foreign_id)
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
                        rows = append_select(col, rows, foreign_id)
                elif model_class.__tablename__ == 'prescription':
                    if col.name in ['drugstore']:
                        rows = append_select(col, rows, foreign_id)
        elif str(col.type) == 'VARCHAR':
            value = value if value else ""
            if col.name in ['gender']:
                rows.append((col.info.get('name'), f'''<select name="{col.name}" class="col-md-1">
                             <option disabled selected>Sélectionner</option>
                             <option value="M" { "selected" if value == "M" else "" }>Masculin</option>
                             <option value="F" { "selected" if value == "F" else "" }>Féminin</option>
                             <option value="A" { "selected" if value == "A" else "" }>Autre</option></select>'''))
            else:
                rows.append((col.info.get('name'), f'<input type="text" name="{col.name}" value="{value}" {required} class="col-md-12"></input>')) 
        elif str(col.type) == 'TEXT':
            if value:
                rows.append((col.info.get('name'), f'<textarea rows="4" name="{col.name}" {required} class="col-md-12">{value}</textarea>')) 
            else:
                rows.append((col.info.get('name'), f'<textarea rows="4" name="{col.name}" {required} class="col-md-12"></textarea>'))
        elif str(col.type) == 'DATE':
            if id and model_class.__table__.name == 'file':
                rows.append((col.info.get('name'), f'<span class="date">{value}</span>'))
            elif id:
                rows.append((col.info.get('name'), f'<input type="date" name="{col.name}" value="{value}" class="date"></input>'))
            else:
                rows.append((col.info.get('name'), f'<input type="date" name="{col.name}" value="{value}" {required} min="{before}" max="{next_time}"></input>'))
        elif str(col.type) == 'BOOLEAN':
            if id:
                checked = "checked" if value else ""
                rows.append((col.info.get('name'), f'<input type="checkbox" name="{col.name}" value="true" {required} {checked}></input>'))
    return rows