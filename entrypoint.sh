#!/bin/bash

# Arrêt du script en cas d'erreur
set -e

DATA_DIR=/data
DB_FILE=${DATA_DIR}/gestebenevole.sqlite

cd /

if [ ! -f "$DB_FILE" ]; then
python -c "from app import app, db; app.create_app()"
for file in $DATA_DIR/*.csv
do
echo "Import $file..."
TABLE_NAME=$(basename $file .csv)
sqlite3 $DB_FILE <<EOF
.mode csv
.import $file $TABLE_NAME
EOF
done
fi

echo "Démarrage de Gunicorn..."
exec gunicorn --workers 3 --timeout=60 --bind 0.0.0.0:8080 app.app:app
