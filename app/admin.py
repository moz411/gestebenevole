# admin.py

from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
import csv
import re
import unicodedata

from flask import Blueprint, Response, abort, current_app, render_template, send_file
from flask_login import current_user, login_required
from openpyxl import Workbook
from sqlalchemy import select, text
import yaml

from . import db
from .roles import Role

admin = Blueprint("admin", __name__)

SENSITIVE_COLUMNS = {"treatment", "vaccination", "history", 
                     "notes", "infos", "motive", "posology",
                     "password"}
EXCLUDED_TABLES = {"appointment", "drugstore"}


def is_sensitive_column(column_name):
    normalized = column_name.lower()
    if normalized in SENSITIVE_COLUMNS:
        return True


def _slugify(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", ascii_value).strip("-").lower()
    return slug or "export"


def _load_datasette_queries():
    datasette_path = Path(current_app.root_path).parent / "datasette.yml"
    if not datasette_path.exists():
        return {}

    datasette_config = yaml.safe_load(datasette_path.read_text(encoding="utf-8")) or {}
    databases = datasette_config.get("databases", {})
    database_config = databases.get("gestebenevole")
    if not database_config and databases:
        database_config = next(iter(databases.values()))

    queries = (database_config or {}).get("queries", {})
    return {
        name: {"sql": details.get("sql", "").strip(), "hide_sql": details.get("hide_sql", False)}
        for name, details in queries.items()
    }


@admin.route("/stats", methods=["GET"])
@login_required
def stats():
    if not current_user.has_role(Role.ADMIN):
        return abort(403)

    queries = _load_datasette_queries()
    return render_template(
        "admin_stats.html",
        user=current_user,
        queries=[{"name": name, **details} for name, details in queries.items()],
    )


@admin.route("/stats/<path:query_name>/csv", methods=["GET"])
@login_required
def export_stats_query(query_name):
    if not current_user.has_role(Role.ADMIN):
        return abort(403)

    queries = _load_datasette_queries()
    query = queries.get(query_name)
    if not query or not query["sql"]:
        return abort(404)

    result = db.session.execute(text(query["sql"]))
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(result.keys())
    for row in result:
        writer.writerow(list(row))

    filename = f"{_slugify(query_name)}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
