#!/usr/bin/env python3
"""Entrypoint script compatible avec une image distroless."""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
from pathlib import Path


DATA_DIR = Path("/data")
DB_PATH = DATA_DIR / "gestebenevole.sqlite"
GUNICORN_CMD = (
    "gunicorn",
    "--workers",
    "3",
    "--timeout",
    "60",
    "--bind",
    "0.0.0.0:8080",
    "app.app:app",
)


def ensure_database() -> None:
    """Initialise la base de données si nécessaire."""

    if DB_PATH.exists():
        return

    # L'import crée l'application et les tables par effet de bord.
    from app import app as flask_app  # noqa: WPS433 (import tardif intentionnel)

    with flask_app.app_context():
        pass


def import_csv_file(connection: sqlite3.Connection, csv_path: Path) -> None:
    """Importe un fichier CSV dans la table correspondant à son nom."""

    table_name = csv_path.stem
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        headers = next(reader, None)
        if not headers:
            return

        columns = ", ".join(f'"{header}"' for header in headers)
        placeholders = ", ".join(["?"] * len(headers))
        rows = list(reader)
        if not rows:
            return

        connection.executemany(
            f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})',
            rows,
        )


def import_csv_files() -> None:
    """Importe les fichiers CSV présents dans /data."""

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        return

    with sqlite3.connect(DB_PATH) as connection:
        for csv_path in csv_files:
            print(f"Import {csv_path.name}...")
            import_csv_file(connection, csv_path)
        connection.commit()


def start_gunicorn() -> None:
    """Lance Gunicorn en remplaçant le processus courant."""

    os.execvp(GUNICORN_CMD[0], GUNICORN_CMD)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    ensure_database()
    import_csv_files()
    print("Démarrage de Gunicorn...")
    start_gunicorn()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - surface les erreurs au démarrage
        print(f"Erreur lors du démarrage: {exc}", file=sys.stderr)
        raise
