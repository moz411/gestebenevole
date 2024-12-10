from flask import Flask, send_from_directory
from . import create_app

app = create_app()

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/x-icon')