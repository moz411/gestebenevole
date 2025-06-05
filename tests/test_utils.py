import importlib.util
import os
import sys
import types
from datetime import date

# Ensure the application package is on the path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

# Create stub modules for dependencies missing in the test environment
flask_login = types.ModuleType('flask_login')
flask_login.login_required = lambda x: x
flask_login.current_user = None
sys.modules.setdefault('flask_login', flask_login)

sqlalchemy_stub = types.ModuleType('sqlalchemy')
sqlalchemy_stub.sql = types.SimpleNamespace(text=lambda x: x)
sys.modules.setdefault('sqlalchemy', sqlalchemy_stub)

app_models_stub = types.ModuleType('app.models')
app_models_stub.db = None
sys.modules.setdefault('app.models', app_models_stub)

# Stub for python-dateutil.relativedelta
relativedelta_mod = types.ModuleType('dateutil.relativedelta')
relativedelta_mod.relativedelta = lambda *args, **kwargs: None
dateutil_pkg = types.ModuleType('dateutil')
dateutil_pkg.relativedelta = relativedelta_mod
sys.modules.setdefault('dateutil', dateutil_pkg)
sys.modules.setdefault('dateutil.relativedelta', relativedelta_mod)

# Create a stub package for 'app' to avoid importing its __init__
app_package = types.ModuleType('app')
app_package.__path__ = [os.path.join(BASE_DIR, 'app')]
sys.modules.setdefault('app', app_package)

# Load app.utils manually from its file to bypass dependencies
spec = importlib.util.spec_from_file_location('app.utils', os.path.join(BASE_DIR, 'app', 'utils.py'))
utils = importlib.util.module_from_spec(spec)
sys.modules['app.utils'] = utils
spec.loader.exec_module(utils)

class DummyForm:
    def __init__(self, data):
        self._data = data
    def to_dict(self):
        return dict(self._data)

def test_convert_form_data_converts_date_and_bool():
    form = DummyForm({'when': '2023-04-05', 'flag': 'true', 'name': 'John', 'check': 'on'})
    result = utils.convert_form_data(form)
    assert result['when'] == date(2023, 4, 5)
    assert result['flag'] is True
    assert result['check'] is True
    assert result['name'] == 'John'

def test_append_select_3_builds_html():
    html = utils.append_select_3('drugstore')
    assert 'id="drugstore-search"' in html
    assert 'name="drugstore"' in html
    assert 'id="drugstore-table"' in html
