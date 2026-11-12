#!/bin/sh
# Läuft kurz als root, um dem Datenordner den richtigen Besitzer zu geben, und gibt die Rechte dann ab.
set -eu

chown -R findling:findling /data
chmod 0700 /data
[ -f /data/options.json ] && chmod 0600 /data/options.json

# Kopierdienst für Sicherungen auf Netzlaufwerke. Er bleibt root, darf aber nur das (siehe spiegel.sh).
/bin/sh /spiegel.sh &

# Ohne Umgebung starten: Das Programm braucht und bekommt keine Zugangsdaten von Home Assistant.
exec su-exec findling:findling env -i \
    PATH=/usr/bin:/bin \
    HOME=/data \
    LANG=C.UTF-8 \
    TMPDIR=/tmp \
    PYTHONPATH=/opt/findling/lib \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    /usr/bin/python3.14 /opt/findling/app/server.py --ha
