# admin.py

from datetime import datetime
from io import BytesIO

from flask import Blueprint, abort, send_file
from flask_login import current_user, login_required
from openpyxl import Workbook
from sqlalchemy import select

from . import db
from .roles import Role

admin = Blueprint("admin", __name__)

SENSITIVE_COLUMNS = {"lastname", "firstname", "name", "notes"}
SENSITIVE_SUBSTRINGS = ("comment",)
EXCLUDED_TABLES = {"appointment"}


def is_sensitive_column(column_name):
    normalized = column_name.lower()
    if normalized in SENSITIVE_COLUMNS:
        return True
    return any(substring in normalized for substring in SENSITIVE_SUBSTRINGS)


@admin.route("/export", methods=["GET"])
@login_required
def export_database():
    if not current_user.has_role(Role.ADMIN):
        return abort(403)

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    for table in db.metadata.sorted_tables:
        if table.name in EXCLUDED_TABLES:
            continue

        allowed_columns = [
            column for column in table.columns if not is_sensitive_column(column.name)
        ]
        if not allowed_columns:
            continue

        sheet = workbook.create_sheet(title=table.name)
        sheet.append([column.name for column in allowed_columns])
        rows = db.session.execute(select(*allowed_columns)).all()
        for row in rows:
            sheet.append(list(row))

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = f"export-{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
