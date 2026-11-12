#!/usr/bin/env python3
"""Lokaler Server von findling. Braucht nur die Python-Standardbibliothek.

Ohne --lan ist die App nur auf diesem Rechner erreichbar. Mit --lan ist sie im
Heimnetz erreichbar und durch eine PIN geschützt. Die Verbindung im Heimnetz ist
unverschlüsselt (HTTP), die PIN schützt also nicht vor Mithören im eigenen WLAN.
"""
import argparse
import csv
import datetime
import hashlib
import hmac
import html
import io
import json
import math
import mimetypes
import re
import secrets
import shutil
import socket
import ssl
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import recognition
import zugang

APP_VERSION = "1.1.0"
STATIC_DIR = Path(__file__).resolve().parent / "static"
mimetypes.add_type("application/manifest+json", ".webmanifest")
DEFAULT_DATA_DIR = Path.home() / "Werkstatt-Daten"
DEFAULT_PORT = 8787
MAX_JSON_BYTES = 1024 * 1024
MAX_PHOTO_BYTES = 30 * 1024 * 1024
FILL_LEVELS = ("voll", "ok", "wenig", "leer")
# Dieselbe Stufe heißt bei Geräten anders: Material hat einen Füllstand, ein Gerät einen Zustand.
SCALES = ("fill", "state")
STATE_WORDS = {"voll": ("ausgezeichnet", "excellent"), "ok": ("in Ordnung", "fine"),
               "wenig": ("zu überprüfen", "to check"), "leer": ("kaputt", "broken")}
FILL_WORDS = {"voll": ("voll", "full"), "ok": ("ok", "ok"), "wenig": ("wenig", "low"), "leer": ("leer", "empty")}


def level_word(item):
    """Füllstand oder Zustand eines Eintrags in der eingestellten Sprache."""
    words = STATE_WORDS if item["scale"] == "state" else FILL_WORDS
    return L(*words[item["fill"]])


def quantity_name(item):
    """„3× Schraubzwinge“, bei einem Stück nur der Name."""
    return f"{item['quantity']}× {item['name']}" if item["quantity"] > 1 else item["name"]


def runs_low(item):
    """Gehört auf die Mitbringliste: nur Material, kein Gerät."""
    return item["scale"] != "state" and item["fill"] in ("wenig", "leer")
DEFAULT_SITE_NAME = "Mein Zuhause"
MAX_INSTRUCTION = 300
MAX_CHAT_ANSWER = 200000
# Schwellen für die Empfehlungen. Es sind Vorschläge, kein Forschungsergebnis.
STALE_DAYS = 180
OVERFULL_ITEMS = 15
FREQUENT_FINDS = 3
MAX_PER_KIND = 5
TRASH_DAYS = 30
BACKUP_FOLDER = "sicherungen"
BACKUP_NAME = re.compile(r"^findling-(\d{4}-\d{2}-\d{2})(?:-\d{4,6}|-vor-(\d{1,4}\.\d{1,4}\.\d{1,4}))?\.zip$")
# Wie oft gesichert wird (Stunden) und wie viele Stände bleiben. Beides stellt man in der App ein.
BACKUP_INTERVALS = (6, 12, 24, 168)
BACKUP_INTERVAL_DEFAULT = 24
BACKUP_KEEP_DEFAULT = 7
BACKUP_KEEP_MIN = 3
BACKUP_KEEP_MAX = 30
# Sicherungen vor einem Update zählen extra, von ihnen bleiben die letzten zwei.
BACKUP_KEEP_BEFORE_UPDATE = 2
BACKUP_CHECK_SECONDS = 600
# Diese Einstellungen gehören zum Gerät, nicht zum Inventar. Beim Einspielen bleiben sie erhalten.
BACKUP_SETTING_KEYS = ("backup_mirror", "backup_interval", "backup_keep")
# Austausch mit dem Kopierdienst in Home Assistant, falls die App selbst nicht ins Ziel schreiben darf.
# Symbole, die statt eines Fotos auf einer Raumkachel stehen können.
COVER_ICONS = ("werkzeug", "werkzeugkasten", "auto", "fahrrad", "garten", "haus", "keller", "dachboden", "kiste", "regal")
COVER_ZOOM_MAX = 4.0

# Steckbrief: Angaben, die man jederzeit später zu einem Eintrag ergänzen kann. Nichts davon ist Pflicht.
PASSPORT_TEXT = {"maker": 60, "model": 80, "serial": 60, "price": 30, "shop": 60}
PASSPORT_LONG = {"accessories": 500, "usage": 3000, "care": 3000}
PASSPORT_DATES = ("bought", "warranty", "service_last")
PASSPORT_KEYS = (*PASSPORT_TEXT, *PASSPORT_LONG, *PASSPORT_DATES, "link", "service_months")
PASSPORT_LINK_MAX = 300
SERVICE_MONTHS_MAX = 240
# Dokumente am Steckbrief: Anleitung, Rechnung und Co. als PDF oder Bild.
DOCUMENT_KINDS = ("anleitung", "rechnung", "garantie", "wartung", "sonstiges")
MAX_DOCUMENT_BYTES = 30 * 1024 * 1024
MAX_DOCUMENTS_PER_ITEM = 40
DOCUMENT_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
BACKUP_DOCUMENT = re.compile(r"^dokumente/[0-9a-f]{32}\.(?:pdf|jpg|png|webp)$")
# Dokumente laufen nie als Teil der App: keine Skripte, keine Formulare, nichts von außen.
# Bilder kommen in eine Sandbox. Bei PDFs nicht, denn Safari zeigt PDFs über ein Plugin an, das die Sandbox abschaltet.
DOCUMENT_CSP_IMAGE = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox; frame-ancestors 'self'"
DOCUMENT_CSP_PDF = "default-src 'none'; object-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
# Verlauf je Eintrag: verliehen, zurück, gewartet, Notiz. Ältere Zeilen fallen weg.
LOG_KEEP = 100

# Anpassungen der Oberfläche. Sie liegen in der Datenbank und sind damit in jeder Sicherung.
PHOTO_LOOKS = ("gruen", "blau", "bernstein", "violett", "grau", "aus")
CHAT_CHOICES = ("chatgpt", "claude")
LABEL_SIZES = ("size-s", "size-m", "size-l")
DASHBOARD_SECTIONS = ("progress", "minimap", "rooms", "low", "watch", "checkin")
# Nach wie vielen Tagen ohne Bestätigung findling nachfragt, ob etwas noch da ist.
CHECKIN_DAYS = (30, 90, 180, 365)
PREFERENCE_DEFAULTS = {
    "dashboard": {"hidden_rooms": [], "progress": True, "minimap": True, "rooms": True, "low": True, "watch": True, "checkin": True},
    "checkin_days": 90,
    "checkin_next": "",
    "photo_look": "gruen",
    "chat": "chatgpt",
    "label_size": "size-m",
}
MIRROR_CONF = "spiegel.conf"
MIRROR_STATUS = "spiegel-status"
BACKUP_PHOTO = re.compile(r"^fotos/[0-9a-f]{32}\.[a-z0-9]{2,5}$")
CERT_DOWNLOAD = "/findling-zertifikat.crt"
SESSION_DAYS = 30
MAX_CONNECTIONS = 64
SOCKET_TIMEOUT_SECONDS = 60
MAX_BACKUP_UPLOAD = 20 * 1024 * 1024 * 1024
MAX_BACKUP_ENTRIES = 200000
MIN_DIRECT_PIN = 8
INGRESS_PEER = "172.30.32.2"  # Nur von dieser Adresse kommt der geschützte Zugang von Home Assistant.
HOST_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
# Meilensteine: Einmal erreicht, bleiben sie. Niemand verliert etwas durch eine Pause.
# Sprache der Oberfläche und der Texte, die der Server erzeugt: "de" oder "en". Kommt aus der Konfiguration.
LANGUAGES = ("de", "en")
LANGUAGE = "de"


def L(de, en):
    """Wählt den Text in der eingestellten Sprache."""
    return en if LANGUAGE == "en" else de


MILESTONE_TITLES_EN = {
    "first_place": "First spot recorded", "ten_items": "10 things in the inventory", "first_find": "Found for the first time",
    "room_done": "First room complete", "ten_places": "10 spots recorded", "ten_finds": "Found 10 times instead of searching",
    "hundred_items": "100 things in the inventory", "fifty_places": "50 spots recorded", "all_done": "Everything recorded",
    "five_hundred_items": "500 things in the inventory",
    "first_move": "Rearranged for the first time", "twenty_moves": "Moved 20 things to a better spot",
    "first_merge": "Merged duplicates", "ten_merges": "Merged duplicates 10 times",
    "first_sorted_out": "Sorted something out for the first time", "twentyfive_sorted_out": "Sorted out 25 things",
    "first_care": "Looked after the inventory", "fifty_care": "Looked after the inventory 50 times",
    "first_repair": "Got a device working again", "five_repairs": "Got 5 devices working again",
    "first_service": "First maintenance done", "ten_services": "10 maintenance jobs done",
    "first_lend": "Lent something out for the first time", "ten_lends": "Lent out 10 times instead of buying new",
    "fifty_finds": "Found 50 times instead of buying new",
}
# Abzeichen für erste Male. Mengen zählen im Stufensystem, das ohne Obergrenze weiterwächst.
MILESTONES = (
    ("first_place", "Erster Platz erfasst", "surveyed", 1),
    ("first_find", "Zum ersten Mal gefunden", "finds", 1),
    ("room_done", "Erster Raum komplett", "rooms_done", 1),
    ("all_done", "Alles erfasst", "all_done", 1),
    ("first_move", "Zum ersten Mal umgeräumt", "moves", 1),
    ("first_care", "Inventar gepflegt", "care", 1),
    ("first_lend", "Zum ersten Mal verliehen", "lends", 1),
    ("first_sorted_out", "Zum ersten Mal aussortiert", "sorted_out", 1),
    ("first_merge", "Doppeltes zusammengelegt", "merges", 1),
    ("first_repair", "Ein Gerät wieder in Ordnung gebracht", "repairs", 1),
    ("first_service", "Erste Wartung erledigt", "services", 1),
)
# Stufen je Bereich. Punkte gibt es nicht nur fürs Sammeln, sondern genauso fürs Ordnen, Pflegen und Benutzen.
LEVEL_POINTS = {
    "erfassen": {"items": 1, "surveyed": 3},
    "ordnen": {"moves": 2, "merges": 3, "sorted_out": 2},
    "pflegen": {"care": 1, "repairs": 5, "services": 5},
    "nutzen": {"finds": 2, "lends": 3},
}
LEVEL_GROUPS = {"erfassen": ("Erfassen", "Recording"), "ordnen": ("Ordnen", "Sorting"), "pflegen": ("Pflegen", "Care"), "nutzen": ("Benutzen", "Using")}
LEVEL_TITLES = (
    (0, "Neu dabei", "Newcomer"), (1, "Lehrling", "Apprentice"), (3, "Geselle", "Journeyman"), (6, "Meister", "Master"),
    (10, "Obermeister", "Grandmaster"), (15, "Legende", "Legend"),
)


def level_floor(level):
    """Punkte für eine Stufe. Jede Stufe braucht etwas mehr als die vorige, eine Obergrenze gibt es nicht."""
    return 0 if level <= 0 else math.ceil(15 * level ** 1.8)


def level_of(points):
    level = 0
    while points >= level_floor(level + 1):
        level += 1
    return level


def level_title(level):
    return next(L(de, en) for start, de, en in reversed(LEVEL_TITLES) if level >= start)


LENT_WORDS = ("Verliehen", "Lent out")


def milestone_title(key, title):
    return L(title, MILESTONE_TITLES_EN.get(key, title))
# Wie ein gelöschter Bereich am Bestand hängt: Spalte und Tabelle des übergeordneten Eintrags.
TRASH_TABLES = {
    "site": "sites", "room": "rooms", "map": "maps", "place": "places", "item": "items", "photo": "photos",
    "document": "documents",
}
TRASH_PARENTS = {
    "room": ("site_id", "sites"), "map": ("room_id", "rooms"), "place": ("map_id", "maps"),
    "item": ("place_id", "places"), "photo": ("place_id", "places"),
}
PHOTO_ID = re.compile(r"^[0-9a-f]{32}$")
SESSION_COOKIE = "werkstatt_session"
MAX_PIN_FAILURES = 10
PIN_LOCK_SECONDS = 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS photos (
    id TEXT PRIMARY KEY, ext TEXT NOT NULL, place_id TEXT, created REAL NOT NULL, item_id TEXT
);
CREATE TABLE IF NOT EXISTS sites (
    id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, created REAL NOT NULL, map_x REAL, map_y REAL
);
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY, site_id TEXT NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name TEXT NOT NULL, code TEXT NOT NULL UNIQUE, plan_photo TEXT, created REAL NOT NULL,
    cover_photo TEXT, cover_x REAL, cover_y REAL, cover_zoom REAL, cover_icon TEXT,
    map_x REAL, map_y REAL, UNIQUE (site_id, name)
);
CREATE TABLE IF NOT EXISTS maps (
    id TEXT PRIMARY KEY, room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    name TEXT NOT NULL, code TEXT NOT NULL, photo TEXT, plan_x REAL, plan_y REAL,
    created REAL NOT NULL, UNIQUE (room_id, code)
);
CREATE TABLE IF NOT EXISTS places (
    id TEXT PRIMARY KEY, map_id TEXT NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
    code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    x REAL NOT NULL, y REAL NOT NULL, w REAL NOT NULL, h REAL NOT NULL,
    surveyed INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL, surveyed_at REAL
);
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY, place_id TEXT NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    name TEXT NOT NULL, synonyms TEXT NOT NULL DEFAULT '', fill TEXT NOT NULL DEFAULT 'ok',
    note TEXT NOT NULL DEFAULT '', missing INTEGER NOT NULL DEFAULT 0, last_seen REAL,
    created REAL NOT NULL, updated REAL NOT NULL, away TEXT NOT NULL DEFAULT '', away_since REAL,
    details TEXT NOT NULL DEFAULT '', passport TEXT NOT NULL DEFAULT '',
    away_to TEXT NOT NULL DEFAULT '', away_due TEXT NOT NULL DEFAULT '', scale TEXT NOT NULL DEFAULT 'fill',
    quantity INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, type TEXT NOT NULL,
    q TEXT, hits INTEGER, item_id TEXT, place_id TEXT
);
CREATE TABLE IF NOT EXISTS recognitions (
    photo_id TEXT PRIMARY KEY REFERENCES photos(id) ON DELETE CASCADE, result TEXT NOT NULL,
    instruction TEXT NOT NULL DEFAULT '', created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL NOT NULL, source TEXT NOT NULL,
    result TEXT NOT NULL, status TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS trash (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, label TEXT NOT NULL, detail TEXT NOT NULL,
    created REAL NOT NULL, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS achievements (key TEXT PRIMARY KEY, at REAL NOT NULL);
-- Nicht mehr benutzt. Ältere Datenbanken enthalten diese Tabelle noch, deshalb bleibt sie stehen.
CREATE TABLE IF NOT EXISTS code_counters (prefix TEXT PRIMARY KEY, next_no INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    kind TEXT NOT NULL, title TEXT NOT NULL, ext TEXT NOT NULL, size INTEGER NOT NULL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS item_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    at REAL NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL DEFAULT '', who TEXT NOT NULL DEFAULT '',
    day TEXT NOT NULL DEFAULT ''
);
"""


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def new_id():
    return uuid.uuid4().hex


def clean_text(value, field, max_len=200, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ApiError(400, f"{field} muss Text sein")
    value = value.strip()
    if required and not value:
        raise ApiError(400, f"{field} fehlt")
    if len(value) > max_len:
        raise ApiError(400, f"{field} ist zu lang")
    return value


# Inhaltsliste im Detailmodus: eine Zeile je Teil, etwa „Bit T20“ oder „Innensechskant 4 mm“.
DETAIL_LINE_MAX = 80
DETAIL_LINES_MAX = 150


def clean_details(value):
    """Nimmt eine Liste oder Text mit einer Zeile je Teil. Leere und doppelte Zeilen fallen weg."""
    if value is None:
        return ""
    if isinstance(value, str):
        lines = value.split("\n")
    elif isinstance(value, list) and all(isinstance(line, str) for line in value):
        lines = value
    else:
        raise ApiError(400, "Inhalt muss eine Liste aus Text sein")
    kept, seen = [], set()
    for line in lines:
        line = " ".join(line.split())
        if not line:
            continue
        if len(line) > DETAIL_LINE_MAX:
            raise ApiError(400, "Eine Zeile im Inhalt ist zu lang")
        if normalize_name(line) in seen:
            continue
        seen.add(normalize_name(line))
        kept.append(line)
    if len(kept) > DETAIL_LINES_MAX:
        raise ApiError(400, "Der Inhalt hat zu viele Zeilen")
    return "\n".join(kept)


def clean_date(value, field):
    """Ein Tag als JJJJ-MM-TT. Leer heißt: nicht angegeben."""
    if value is None or value == "":
        return ""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ApiError(400, f"{field}: Datum bitte als JJJJ-MM-TT")
    try:
        day = datetime.date.fromisoformat(value)
    except ValueError:
        raise ApiError(400, f"{field}: Dieses Datum gibt es nicht")
    if not 1900 <= day.year <= 2200:
        raise ApiError(400, f"{field}: Dieses Datum gibt es nicht")
    return value


PASSPORT_FIELDS = {
    "maker": "Hersteller", "model": "Modell", "serial": "Seriennummer", "price": "Kaufpreis", "shop": "Gekauft bei",
    "accessories": "Gehört dazu", "usage": "Bedienung", "care": "Wartungshinweise", "bought": "Kaufdatum",
    "warranty": "Garantie bis", "service_last": "Zuletzt gewartet", "link": "Webseite", "service_months": "Wartung alle",
}


def clean_link(value):
    """Nur gewöhnliche Webadressen, damit ein Klick darauf nichts anderes ausführen kann."""
    value = clean_text(value, "Webseite", PASSPORT_LINK_MAX)
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or re.search(r"[\s<>\"'\\]", value):
        raise ApiError(400, "Die Webseite muss mit https:// beginnen")
    return value


def clean_passport(value, current=None):
    """Prüft Änderungen am Steckbrief. Nur bekannte Angaben, leere Werte entfernen die Angabe."""
    if not isinstance(value, dict):
        raise ApiError(400, "Ungültige Daten")
    if set(value) - set(PASSPORT_KEYS):
        raise ApiError(400, "Unbekannte Angabe im Steckbrief")
    result = dict(current or {})
    for key, raw in value.items():
        label = PASSPORT_FIELDS[key]
        if key in PASSPORT_TEXT:
            cleaned = " ".join(clean_text(raw, label, PASSPORT_TEXT[key]).split())
        elif key in PASSPORT_LONG:
            text = raw.replace("\r\n", "\n").replace("\r", "\n") if isinstance(raw, str) else raw
            cleaned = "\n".join(line.rstrip() for line in clean_text(text, label, PASSPORT_LONG[key]).split("\n"))
        elif key in PASSPORT_DATES:
            cleaned = clean_date(raw, label)
        elif key == "link":
            cleaned = clean_link(raw)
        else:
            if raw in (None, "", 0):
                cleaned = ""
            elif isinstance(raw, int) and not isinstance(raw, bool) and 1 <= raw <= SERVICE_MONTHS_MAX:
                cleaned = raw
            else:
                raise ApiError(400, "Wartung alle: 1 bis 240 Monate")
        if cleaned in ("", None):
            result.pop(key, None)
        else:
            result[key] = cleaned
    return result


def read_passport(text):
    try:
        value = json.loads(text) if text else {}
    except ValueError:
        return {}
    return {key: value[key] for key in PASSPORT_KEYS if key in value} if isinstance(value, dict) else {}


def add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return datetime.date(year, month, min(day.day, last))


def next_service(passport, created):
    """Wann die nächste Wartung fällig ist: ab der letzten Wartung, sonst ab Kauf oder Erfassung."""
    months = passport.get("service_months")
    if not months:
        return ""
    start = passport.get("service_last") or passport.get("bought")
    base = datetime.date.fromisoformat(start) if start else datetime.date.fromtimestamp(created)
    return add_months(base, months).isoformat()


def sniff_document_ext(head):
    if head.startswith(b"%PDF-"):
        return ".pdf"
    return sniff_image_ext(head)


def document_title(name, kind):
    """Der Titel kommt aus dem Dateinamen, ohne Endung. Fehlt er, steht dort die Art."""
    name = name if isinstance(name, str) else ""
    name = re.sub(r"\.(pdf|jpe?g|png|webp|heic)$", "", name.strip(), flags=re.IGNORECASE)
    name = " ".join("".join(ch for ch in name if ch.isprintable()).replace("_", " ").split())[:120]
    return name or {
        "anleitung": L("Anleitung", "Manual"), "rechnung": L("Rechnung", "Invoice"),
        "garantie": L("Garantie", "Warranty"), "wartung": L("Wartung", "Maintenance"),
    }.get(kind, L("Dokument", "Document"))


QUANTITY_MAX = 9999


def clean_quantity(value):
    """Wie viele gleiche Stücke an einem Platz liegen. Ganze Zahl von 1 bis 9999."""
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= QUANTITY_MAX:
        raise ApiError(400, "Anzahl: bitte eine ganze Zahl von 1 bis 9999")
    return value


def clean_fraction(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ApiError(400, f"{field} muss zwischen 0 und 1 liegen")
    return float(value)


def map_position(body):
    """Die Lage eines Punkts auf der Übersichtskarte, als Anteil von Breite und Höhe."""
    if "map_x" not in body and "map_y" not in body:
        return {}
    return {"map_x": clean_fraction(body.get("map_x"), "Position"), "map_y": clean_fraction(body.get("map_y"), "Position")}


def say(message):
    """Eine Meldung im Protokoll darf das Programm nie zu Fall bringen."""
    try:
        print(message, flush=True)
    except OSError:
        pass


def normalize_name(text):
    text = text.lower()
    for old, new in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(old, new)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def code_words(text):
    text = text.upper()
    for umlaut, plain in (("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE"), ("ß", "SS")):
        text = text.replace(umlaut, plain)
    return re.findall(r"[A-Z0-9]+", text)


def short_code(name):
    """Macht aus "Regal 2" das Kürzel R2 und aus "Schrank links" SL."""
    parts = code_words(name)
    return "".join(part if part.isdigit() else part[0] for part in parts)[:5]


def sniff_image_ext(head):
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def is_heic(head):
    return head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"heif", b"mif1", b"msf1")


def heic_to_jpeg(data):
    """Wandelt iPhone-Fotos am Mac um, denn nicht jeder Browser kann HEIC lesen."""
    if not is_heic(data[:16]):
        raise ApiError(415, "Dieses Bildformat wird nicht unterstützt")
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "foto.heic"
        target = Path(tmp) / "foto.jpg"
        source.write_bytes(data)
        try:
            subprocess.run(
                ["/usr/bin/sips", "-s", "format", "jpeg", str(source), "--out", str(target)],
                capture_output=True, timeout=60, check=True,
            )
            return target.read_bytes()
        except (OSError, subprocess.SubprocessError):
            raise ApiError(415, "Dieses Foto konnte nicht umgewandelt werden. Speichere es bitte als JPEG.")


def csv_safe(value):
    """Verhindert, dass Tabellenprogramme einen Eintrag als Formel ausführen."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


# Massenimport: eine Tabelle (CSV) mit einer Zeile je Gegenstand. Erst prüfen, dann alles oder nichts übernehmen.
MAX_IMPORT_BYTES = 5 * 1024 * 1024
IMPORT_MAX_ROWS = 5000
IMPORT_MAX_ERRORS = 50
IMPORT_COLUMNS = {
    "site": ("haus oder grundstueck", "haus", "grundstueck", "standort", "house or property", "property", "site"),
    "room": ("raum", "bereich", "raum oder bereich", "room", "area", "room or area"),
    "map": ("schrank", "regal", "schrank oder regal", "cabinet", "shelf", "cabinet or shelf"),
    "place": ("platz", "fach", "spot", "place"),
    "code": ("adresse", "address"),
    "name": ("name", "gegenstand", "bezeichnung", "item"),
    "quantity": ("anzahl", "menge", "stueck", "stueckzahl", "quantity", "count"),
    "device": ("geraet", "device"),
    "fill": ("fuellstand", "zustand", "fuellstand oder zustand", "stock level", "condition", "stock level or condition"),
    "note": ("notiz", "note"),
    "synonyms": ("auch genannt", "also called"),
    "details": ("inhalt", "contents"),
    "maker": ("hersteller", "maker"),
    "model": ("modell", "model"),
    "serial": ("seriennummer", "serial number"),
    "bought": ("kaufdatum", "purchase date"),
    "warranty": ("garantie bis", "warranty until"),
}
IMPORT_LEVELS = {
    "voll": ("voll", None), "full": ("voll", None), "ok": ("ok", None), "wenig": ("wenig", None), "low": ("wenig", None),
    "leer": ("leer", None), "empty": ("leer", None),
    "ausgezeichnet": ("voll", "state"), "excellent": ("voll", "state"), "sehr gut": ("voll", "state"),
    "in ordnung": ("ok", "state"), "fine": ("ok", "state"), "gut": ("ok", "state"), "good": ("ok", "state"),
    "zu ueberpruefen": ("wenig", "state"), "zu pruefen": ("wenig", "state"), "pruefen": ("wenig", "state"),
    "to check": ("wenig", "state"), "check": ("wenig", "state"),
    "kaputt": ("leer", "state"), "defekt": ("leer", "state"), "broken": ("leer", "state"), "defective": ("leer", "state"),
}
IMPORT_YES = {"ja", "j", "x", "1", "yes", "y", "true", "wahr", "geraet", "device"}
IMPORT_NO = {"nein", "n", "0", "no", "false", "falsch"}


def import_cell(value):
    """Entfernt das Schutz-Apostroph aus dem eigenen Export, etwa bei '-Profil."""
    value = (value or "").strip()
    if len(value) > 1 and value[0] == "'" and value[1] in "=+-@":
        value = value[1:]
    return value


def import_date(value, field):
    if not value:
        return ""
    match = re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", value)
    if match:
        value = f"{match.group(3)}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"
    return clean_date(value, field)


def read_import_table(raw):
    """Liest UTF-8 oder Windows-1252, mit Semikolon, Komma oder Tabulator. Die erste Zeile nennt die Spalten."""
    if len(raw) > MAX_IMPORT_BYTES:
        raise ApiError(413, "Die Datei ist zu groß")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    if "\x00" in text:
        raise ApiError(400, "Das ist keine Tabelle im CSV-Format")
    first = text.split("\n", 1)[0]
    delimiter = max(";,\t", key=first.count)
    try:
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    except csv.Error:
        raise ApiError(400, "Die Tabelle lässt sich nicht lesen")
    rows = [(line, row) for line, row in enumerate(rows, 1) if any(cell.strip() for cell in row)]
    if not rows:
        raise ApiError(400, "Die Tabelle ist leer")
    if len(rows) - 1 > IMPORT_MAX_ROWS:
        raise ApiError(400, f"Höchstens {IMPORT_MAX_ROWS} Zeilen auf einmal")
    columns, ignored = {}, []
    for index, title in enumerate(rows[0][1]):
        key = next((key for key, names in IMPORT_COLUMNS.items() if normalize_name(title) in names), None)
        if key and key not in columns:
            columns[key] = index
        elif title.strip():
            ignored.append(title.strip()[:40])
    if "name" not in columns:
        raise ApiError(400, "Die erste Zeile muss die Spaltennamen enthalten, mindestens „Name“")
    if "code" not in columns and not ("room" in columns and "map" in columns):
        raise ApiError(400, "Es fehlen die Spalten „Raum“ und „Schrank oder Regal“")
    records = []
    for line, row in rows[1:]:
        records.append((line, {key: import_cell(row[index]) if index < len(row) else "" for key, index in columns.items()}))
    return records, sorted(columns), ignored


IMPORT_TEMPLATE = {
    "de": (
        ["Haus oder Grundstück", "Raum", "Schrank oder Regal", "Platz", "Name", "Anzahl", "Gerät", "Füllstand oder Zustand",
         "Notiz", "Auch genannt", "Inhalt", "Hersteller", "Modell", "Seriennummer", "Kaufdatum", "Garantie bis"],
        [
            ["", "Werkstatt", "Werkbank", "Schublade 1", "Holzschrauben 4 x 40", "", "", "wenig", "Torx, verzinkt", "Spax", "", "", "", "", "", ""],
            ["", "Werkstatt", "Werkbank", "Schublade 2", "Bitbox", "", "", "ok", "", "Bits", "Bit T20 | Bit T25 | PH2", "Wera", "", "", "", ""],
            ["", "Werkstatt", "Regal links", "Fach oben", "Akkuschrauber", "", "ja", "in Ordnung", "2 Akkus, Ladegerät", "Bohrschrauber", "", "Bosch", "GSR 18V-55", "SN 4711", "01.03.2024", "01.03.2027"],
            ["", "Garage", "Wandregal", "", "Rasenmäher", "", "ja", "zu überprüfen", "Messer stumpf", "", "", "", "", "", "", ""],
            ["", "Werkstatt", "Wand", "", "Schraubzwinge 300 mm", "4", "", "ok", "", "Zwinge", "", "Bessey", "", "", "", ""],
        ],
    ),
    "en": (
        ["House or property", "Room", "Cabinet or shelf", "Spot", "Name", "Quantity", "Device", "Stock level or condition",
         "Note", "Also called", "Contents", "Maker", "Model", "Serial number", "Purchase date", "Warranty until"],
        [
            ["", "Workshop", "Workbench", "Drawer 1", "Wood screws 4 x 40", "", "", "low", "Torx, zinc-plated", "Screws", "", "", "", "", "", ""],
            ["", "Workshop", "Workbench", "Drawer 2", "Bit box", "", "", "ok", "", "Bits", "Bit T20 | Bit T25 | PH2", "Wera", "", "", "", ""],
            ["", "Workshop", "Left shelf", "Top", "Cordless drill", "", "yes", "fine", "2 batteries, charger", "Drill driver", "", "Bosch", "GSR 18V-55", "SN 4711", "2024-03-01", "2027-03-01"],
            ["", "Garage", "Wall shelf", "", "Lawn mower", "", "yes", "to check", "Blade blunt", "", "", "", "", "", "", ""],
            ["", "Workshop", "Wall", "", "Clamp 300 mm", "4", "", "ok", "", "Clamp", "", "Bessey", "", "", "", ""],
        ],
    ),
}


def import_template():
    header, examples = IMPORT_TEMPLATE["en" if LANGUAGE == "en" else "de"]
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(header)
    writer.writerows(examples)
    return "﻿" + buffer.getvalue()


# Ein schlichtes PDF ohne Bibliothek: A4, Helvetica, Text in Windows-1252. Reicht für Listen zum Teilen.
PDF_W, PDF_H, PDF_MARGIN = 595.28, 841.89, 48


def pdf_text(value):
    data = str(value).encode("cp1252", errors="replace")
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def pdf_fit(text, size, width):
    """Kürzt grob nach Zeichen: Helvetica ist im Mittel etwa halb so breit wie hoch."""
    limit = max(4, int(width / (size * 0.52)))
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def pdf_document(pages):
    """pages: Liste von Listen mit Zeichenbefehlen (bytes)."""
    objects = [None, None, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
    kids = []
    for ops in pages:
        stream = b"\n".join(ops)
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content = len(objects)
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>" % content
        )
        kids.append(len(objects))
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % kid for kid in kids) + b"] /Count %d >>" % len(kids)
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


class Store:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        # In Home Assistant liegen Speicherorte nur unter /share, dort hilft notfalls der Kopierdienst.
        self.target_root = None
        self.mirror_helper = False
        self.photo_dir = self.data_dir / "fotos"
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        self.document_dir = self.data_dir / "dokumente"
        self.document_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "inventar.sqlite"
        update_backup_error = self._backup_before_update()
        self._prepare()
        self.set_setting("app_version", APP_VERSION)
        if update_backup_error:
            self.set_setting("backup_error", update_backup_error)
        self.purge_trash()

    def _backup_before_update(self):
        """Sichert den alten Stand, bevor eine neue Version irgendetwas an der Datenbank ändert."""
        if not self.db_path.exists():
            return None
        probe = sqlite3.connect(self.db_path)
        try:
            try:
                row = probe.execute("SELECT value FROM settings WHERE key = 'app_version'").fetchone()
            except sqlite3.Error:
                row = None
            if row and row[0] == APP_VERSION:
                return None
            has_data = False
            for table in ("rooms", "maps", "items", "trash"):
                try:
                    has_data = has_data or bool(probe.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone())
                except sqlite3.Error:
                    continue
        finally:
            probe.close()
        if not has_data:
            return None
        try:
            self.backup_dir.mkdir(exist_ok=True)
            target = self.backup_dir / f"findling-{time.strftime('%Y-%m-%d')}-vor-{APP_VERSION}.zip"
            temporary = self.backup_dir / f".{target.name}.tmp"
            self._write_backup(temporary)
            temporary.replace(target)
            self._prune_backups(self.backup_dir, self._read_keep())
            say(f"Alter Stand gesichert vor Version {APP_VERSION}: {target.name}")
            return None
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            message = f"Sicherung vor dem Update fehlgeschlagen: {error}"[:200]
            say(message)
            return message

    def _prepare(self):
        self._upgrade_old_database()
        with self.connect() as db:
            db.executescript(SCHEMA)
            if "away" not in {r["name"] for r in db.execute("PRAGMA table_info(items)")}:
                db.execute("ALTER TABLE items ADD COLUMN away TEXT NOT NULL DEFAULT ''")
                db.execute("ALTER TABLE items ADD COLUMN away_since REAL")
            if "instruction" not in {r["name"] for r in db.execute("PRAGMA table_info(recognitions)")}:
                db.execute("ALTER TABLE recognitions ADD COLUMN instruction TEXT NOT NULL DEFAULT ''")
            for table in ("sites", "rooms"):
                if "map_x" not in {r["name"] for r in db.execute(f"PRAGMA table_info({table})")}:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN map_x REAL")
                    db.execute(f"ALTER TABLE {table} ADD COLUMN map_y REAL")
            if "cover_photo" not in {r["name"] for r in db.execute("PRAGMA table_info(rooms)")}:
                # Titelbild der Raumkachel: eigenes Foto mit Ausschnitt oder ein Symbol.
                for column, kind in (("cover_photo", "TEXT"), ("cover_x", "REAL"), ("cover_y", "REAL"), ("cover_zoom", "REAL"), ("cover_icon", "TEXT")):
                    db.execute(f"ALTER TABLE rooms ADD COLUMN {column} {kind}")
            if "surveyed_at" not in {r["name"] for r in db.execute("PRAGMA table_info(places)")}:
                db.execute("ALTER TABLE places ADD COLUMN surveyed_at REAL")
            # Detailmodus: Inhaltsliste je Eintrag und Detailfotos, die zu einem Eintrag gehören.
            if "details" not in {r["name"] for r in db.execute("PRAGMA table_info(items)")}:
                db.execute("ALTER TABLE items ADD COLUMN details TEXT NOT NULL DEFAULT ''")
            if "item_id" not in {r["name"] for r in db.execute("PRAGMA table_info(photos)")}:
                db.execute("ALTER TABLE photos ADD COLUMN item_id TEXT")
            # Steckbrief: Angaben als JSON, dazu bei wem etwas gerade ist und bis wann.
            item_columns = {r["name"] for r in db.execute("PRAGMA table_info(items)")}
            for column in ("passport", "away_to", "away_due"):
                if column not in item_columns:
                    db.execute(f"ALTER TABLE items ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
            if "scale" not in item_columns:
                db.execute("ALTER TABLE items ADD COLUMN scale TEXT NOT NULL DEFAULT 'fill'")
            # Anzahl: Manches hat man doppelt oder mehrfach, etwa drei gleiche Zwingen.
            if "quantity" not in item_columns:
                db.execute("ALTER TABLE items ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
            if not db.execute("SELECT 1 FROM sites").fetchone():
                db.execute(
                    "INSERT INTO sites (id, name, created) VALUES (?, ?, ?)",
                    (new_id(), DEFAULT_SITE_NAME, time.time()),
                )

    def _upgrade_old_database(self):
        """Bringt Datenbanken aus der Zeit vor Haus und Räumen auf den neuen Aufbau."""
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        try:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(maps)")}
            if not columns or "room_id" in columns:
                return
            db.execute("PRAGMA foreign_keys = OFF")
            # Sonst zeigten die Verweise der Plätze nach dem Umbenennen auf die alte Tabelle.
            db.execute("PRAGMA legacy_alter_table = ON")
            db.executescript(SCHEMA.split("CREATE TABLE IF NOT EXISTS maps (")[0])
            site_id = new_id()
            now = time.time()
            with db:
                db.execute("INSERT INTO sites (id, name, created) VALUES (?, ?, ?)", (site_id, DEFAULT_SITE_NAME, now))
                db.execute("ALTER TABLE maps RENAME TO maps_old")
                db.execute(
                    "CREATE TABLE maps (id TEXT PRIMARY KEY, room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE, "
                    "name TEXT NOT NULL, code TEXT NOT NULL, photo TEXT, plan_x REAL, plan_y REAL, "
                    "created REAL NOT NULL, UNIQUE (room_id, code))"
                )
                rooms = {}
                for row in db.execute("SELECT DISTINCT room, room_code FROM maps_old").fetchall():
                    rooms[row["room_code"]] = new_id()
                    db.execute(
                        "INSERT INTO rooms (id, site_id, name, code, created) VALUES (?, ?, ?, ?, ?)",
                        (rooms[row["room_code"]], site_id, row["room"], row["room_code"], now),
                    )
                for row in db.execute("SELECT * FROM maps_old").fetchall():
                    db.execute(
                        "INSERT INTO maps (id, room_id, name, code, photo, created) VALUES (?, ?, ?, ?, ?, ?)",
                        (row["id"], rooms[row["room_code"]], row["name"], row["code"], row["photo"], row["created"]),
                    )
                db.execute("DROP TABLE maps_old")
        finally:
            db.close()

    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA journal_mode = WAL")
        return db

    # Lesen

    def state(self):
        self.purge_trash()
        with self.connect() as db:
            trash_count = db.execute("SELECT COUNT(*) FROM trash").fetchone()[0]
            sites = [dict(r) for r in db.execute("SELECT * FROM sites ORDER BY created")]
            rooms = [dict(r) for r in db.execute("SELECT * FROM rooms ORDER BY created")]
            existing = {row["id"] for row in db.execute("SELECT id FROM photos")}
            for room in rooms:
                if room.get("cover_photo") and room["cover_photo"] not in existing:
                    room.update({"cover_photo": None, "cover_x": None, "cover_y": None, "cover_zoom": None})
            maps = [dict(r) for r in db.execute("SELECT * FROM maps ORDER BY created")]
            places = [dict(r) for r in db.execute("SELECT * FROM places ORDER BY code")]
            items = [dict(r) for r in db.execute("SELECT * FROM items ORDER BY name COLLATE NOCASE")]
            photos = {}
            for row in db.execute(
                "SELECT id, place_id FROM photos WHERE place_id IS NOT NULL ORDER BY created"
            ):
                photos.setdefault(row["place_id"], []).append(row["id"])
            for place in places:
                place["photos"] = photos.get(place["id"], [])
            detail_photos = {}
            for row in db.execute("SELECT id, item_id FROM photos WHERE item_id IS NOT NULL ORDER BY created"):
                detail_photos.setdefault(row["item_id"], []).append(row["id"])
            documents = {}
            for row in db.execute("SELECT id, item_id, kind, title, ext, size, created FROM documents ORDER BY created"):
                documents.setdefault(row["item_id"], []).append({key: row[key] for key in row.keys() if key != "item_id"})
            log = {}
            for row in db.execute("SELECT id, item_id, at, kind, text, who, day FROM item_log ORDER BY at DESC, id DESC"):
                log.setdefault(row["item_id"], []).append({key: row[key] for key in row.keys() if key != "item_id"})
            for item in items:
                item["photos"] = detail_photos.get(item["id"], [])
                item["passport"] = read_passport(item["passport"])
                item["next_service"] = next_service(item["passport"], item["created"])
                item["documents"] = documents.get(item["id"], [])
                item["log"] = log.get(item["id"], [])
            settings = {r["key"]: r["value"] for r in db.execute("SELECT * FROM settings")}
            failed = [
                dict(r)
                for r in db.execute(
                    "SELECT q, COUNT(*) AS times FROM events WHERE type = 'search' AND hits = 0 "
                    "GROUP BY lower(q) ORDER BY times DESC, MAX(at) DESC LIMIT 20"
                )
            ]
            recognized = {r["photo_id"]: r["instruction"] for r in db.execute("SELECT photo_id, instruction FROM recognitions")}
            spent = db.execute(
                "SELECT COALESCE(SUM(input_tokens), 0) AS i, COALESCE(SUM(output_tokens), 0) AS o FROM api_usage"
            ).fetchone()
            counts = {
                r["type"]: r["n"]
                for r in db.execute("SELECT type, COUNT(*) AS n FROM events GROUP BY type")
            }
            achievements = self._achievements(db, maps, places, items, counts)
        return {
            "achievements": achievements,
            "sites": sites,
            "rooms": rooms,
            "maps": maps,
            "places": places,
            "items": items,
            "settings": settings,
            "failed_searches": failed,
            "event_counts": counts,
            "recognized_photos": recognized,
            "trash_count": trash_count,
            "api_cost_usd": round(recognition.estimate_cost_usd(spent["i"], spent["o"]), 2),
            "preferences": self.preferences(),
        }

    # Anpassungen der Oberfläche

    def preferences(self):
        """Gespeicherte Anpassungen, ergänzt um Standardwerte. Unbekanntes oder Kaputtes fällt weg."""
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key = 'ui_preferences'").fetchone()
        try:
            stored = json.loads(row["value"]) if row else {}
        except ValueError:
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        result = json.loads(json.dumps(PREFERENCE_DEFAULTS))
        dashboard = stored.get("dashboard") if isinstance(stored.get("dashboard"), dict) else {}
        hidden = dashboard.get("hidden_rooms")
        if isinstance(hidden, list):
            result["dashboard"]["hidden_rooms"] = [h for h in hidden if isinstance(h, str) and 0 < len(h) <= 40][:500]
        for section in DASHBOARD_SECTIONS:
            if isinstance(dashboard.get(section), bool):
                result["dashboard"][section] = dashboard[section]
        for key, allowed in (("photo_look", PHOTO_LOOKS), ("chat", CHAT_CHOICES), ("label_size", LABEL_SIZES), ("checkin_days", CHECKIN_DAYS)):
            if stored.get(key) in allowed:
                result[key] = stored[key]
        try:
            result["checkin_next"] = clean_date(stored.get("checkin_next"), "Nächste Nachfrage")
        except ApiError:
            pass
        return result

    def set_preferences(self, body):
        """Ändert nur, was mitkommt. Prüft jeden Wert, bevor er gespeichert wird."""
        if not isinstance(body, dict):
            raise ApiError(400, "Ungültige Daten")
        current = self.preferences()
        for key, allowed in (("photo_look", PHOTO_LOOKS), ("chat", CHAT_CHOICES), ("label_size", LABEL_SIZES), ("checkin_days", CHECKIN_DAYS)):
            if key in body:
                if body[key] not in allowed or isinstance(body[key], bool):
                    raise ApiError(400, "Ungültige Auswahl")
                current[key] = body[key]
        if "checkin_next" in body:
            # Die nächste Nachfrage gilt für alle Geräte, damit nicht jedes Telefon einzeln fragt.
            current["checkin_next"] = clean_date(body["checkin_next"], "Nächste Nachfrage")
        if "dashboard" in body:
            dashboard = body["dashboard"]
            if not isinstance(dashboard, dict):
                raise ApiError(400, "Ungültige Daten")
            for section in DASHBOARD_SECTIONS:
                if section in dashboard:
                    if not isinstance(dashboard[section], bool):
                        raise ApiError(400, "Ungültige Daten")
                    current["dashboard"][section] = dashboard[section]
            if "hidden_rooms" in dashboard:
                hidden = dashboard["hidden_rooms"]
                if not isinstance(hidden, list) or len(hidden) > 500 or not all(isinstance(h, str) and 0 < len(h) <= 40 for h in hidden):
                    raise ApiError(400, "Ungültige Räume")
                current["dashboard"]["hidden_rooms"] = list(dict.fromkeys(hidden))
        self.set_setting("ui_preferences", json.dumps(current, ensure_ascii=False))
        return current

    @staticmethod
    def _achievements(db, maps, places, items, counts):
        room_of = {map_["id"]: map_["room_id"] for map_ in maps}
        open_rooms = {room_of[p["map_id"]] for p in places if not p["surveyed"]}
        all_rooms = {room_of[p["map_id"]] for p in places}
        surveyed = sum(1 for p in places if p["surveyed"])
        values = {
            "surveyed": surveyed,
            "items": len(items),
            "finds": counts.get("found", 0),
            "rooms_done": len(all_rooms - open_rooms),
            "all_done": 1 if surveyed >= 3 and surveyed == len(places) else 0,
            "moves": counts.get("moved", 0),
            "merges": counts.get("merged", 0),
            "sorted_out": counts.get("sorted_out", 0),
            "care": counts.get("cared", 0) + counts.get("checked", 0) + counts.get("checked_item", 0),
            "repairs": counts.get("repaired", 0),
            "services": counts.get("serviced", 0),
            "lends": counts.get("lent", 0),
        }
        earned = {row["key"]: row["at"] for row in db.execute("SELECT * FROM achievements")}
        now = time.time()
        for key, _, metric, goal in MILESTONES:
            if key not in earned and values[metric] >= goal:
                db.execute("INSERT INTO achievements (key, at) VALUES (?, ?)", (key, now))
                earned[key] = now
        levels = []
        for group, weights in LEVEL_POINTS.items():
            points = sum(values[metric] * weight for metric, weight in weights.items())
            level = level_of(points)
            key = f"level:{group}:{level}"
            # Eine neue Stufe wird einmal festgehalten, damit die App sie einmal feiert.
            if level and key not in earned:
                db.execute("INSERT INTO achievements (key, at) VALUES (?, ?)", (key, now))
                earned[key] = now
            levels.append({
                "group": group, "label": L(*LEVEL_GROUPS[group]), "points": points, "level": level, "title": level_title(level),
                "floor": level_floor(level), "next": level_floor(level + 1),
            })
        badges = [
            {"key": key, "title": milestone_title(key, title), "at": earned[key]}
            for key, title, _, _ in MILESTONES if key in earned
        ]
        reached = []
        for key, at in earned.items():
            parts = key.split(":")
            if len(parts) == 3 and parts[0] == "level" and parts[1] in LEVEL_GROUPS and parts[2].isdigit():
                level = int(parts[2])
                reached.append({
                    "key": key, "level": True, "at": at,
                    "title": L(f"{LEVEL_GROUPS[parts[1]][0]}: Stufe {level} · {level_title(level)}",
                               f"{LEVEL_GROUPS[parts[1]][1]}: level {level} · {level_title(level)}"),
                })
        return {
            "earned": sorted(badges + reached, key=lambda entry: entry["at"]),
            "levels": levels,
            "total": sum(entry["level"] for entry in levels),
        }

    # Häuser und Grundstücke

    def create_site(self, body):
        record = {
            "id": new_id(),
            "name": clean_text(body.get("name"), "Name", 60, required=True),
            "created": time.time(),
        }
        with self.connect() as db:
            try:
                db.execute("INSERT INTO sites (id, name, created) VALUES (:id, :name, :created)", record)
            except sqlite3.IntegrityError:
                raise ApiError(409, "Diesen Namen gibt es schon")
        return record

    def update_site(self, site_id, body):
        fields = map_position(body)
        if "name" in body or not fields:
            fields["name"] = clean_text(body.get("name"), "Name", 60, required=True)
        try:
            return self._update("sites", site_id, fields)
        except sqlite3.IntegrityError:
            raise ApiError(409, "Diesen Namen gibt es schon")

    def delete_site(self, site_id):
        with self.connect() as db:
            if db.execute("SELECT COUNT(*) FROM sites").fetchone()[0] <= 1:
                raise ApiError(409, "Das letzte Haus oder Grundstück bleibt erhalten")
        return self._move_to_trash("site", site_id)

    # Räume und Bereiche

    def create_room(self, body):
        site_id = clean_text(body.get("site_id"), "Haus oder Grundstück", 40, required=True)
        name = clean_text(body.get("name"), "Name", 60, required=True)
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM sites WHERE id = ?", (site_id,)).fetchone():
                raise ApiError(404, "Haus oder Grundstück nicht gefunden")
            record = {
                "id": new_id(),
                "site_id": site_id,
                "name": name,
                "code": self._free_room_code(db, name),
                "plan_photo": None,
                "created": time.time(),
            }
            try:
                db.execute(
                    "INSERT INTO rooms (id, site_id, name, code, plan_photo, created) "
                    "VALUES (:id, :site_id, :name, :code, :plan_photo, :created)",
                    record,
                )
            except sqlite3.IntegrityError:
                raise ApiError(409, "Diesen Raum gibt es hier schon")
        return record

    @staticmethod
    def _free_room_code(db, name):
        taken = {row["code"] for row in db.execute("SELECT code FROM rooms")}
        base = "".join(code_words(name)) or "R"
        for length in range(1, min(len(base), 6) + 1):
            if base[:length] not in taken:
                return base[:length]
        number = 2
        while f"{base[0]}{number}" in taken:
            number += 1
        return f"{base[0]}{number}"

    def update_room(self, room_id, body):
        fields = map_position(body)
        if "site_id" in body:
            site_id = clean_text(body["site_id"], "Haus oder Grundstück", 40, required=True)
            with self.connect() as db:
                if not db.execute("SELECT 1 FROM sites WHERE id = ?", (site_id,)).fetchone():
                    raise ApiError(404, "Haus oder Grundstück nicht gefunden")
            fields["site_id"] = site_id
        if "name" in body:
            fields["name"] = clean_text(body["name"], "Name", 60, required=True)
        old_cover = None
        if any(key in body for key in ("cover_photo", "cover_icon", "cover_x", "cover_y", "cover_zoom")):
            fields.update(self._clean_cover(body))
            if "cover_photo" in fields:
                with self.connect() as db:
                    row = db.execute("SELECT cover_photo FROM rooms WHERE id = ?", (room_id,)).fetchone()
                    old_cover = row["cover_photo"] if row else None
        old_plan = None
        if "plan_photo" in body:
            fields["plan_photo"] = self._clean_photo(body["plan_photo"])
            with self.connect() as db:
                row = db.execute("SELECT plan_photo FROM rooms WHERE id = ?", (room_id,)).fetchone()
                old_plan = row["plan_photo"] if row else None
                if fields["plan_photo"] is None:
                    # Ohne Plan haben auch die Standorte keine Bedeutung mehr.
                    db.execute("UPDATE maps SET plan_x = NULL, plan_y = NULL WHERE room_id = ?", (room_id,))
        try:
            record = self._update("rooms", room_id, fields)
        except sqlite3.IntegrityError:
            raise ApiError(409, "Diesen Raum gibt es hier schon")
        if old_plan and old_plan != record["plan_photo"]:
            self._forget_photo(old_plan)
        if old_cover and old_cover != record["cover_photo"]:
            self._forget_photo(old_cover)
        return record

    def _clean_cover(self, body):
        """Foto mit Ausschnitt (Mittelpunkt x, y und Vergrößerung) oder ein Symbol, nie beides."""
        fields = {}
        if "cover_icon" in body:
            icon = body["cover_icon"]
            if icon is not None and icon not in COVER_ICONS:
                raise ApiError(400, "Unbekanntes Symbol")
            fields["cover_icon"] = icon
        if "cover_photo" in body:
            fields["cover_photo"] = self._clean_photo(body["cover_photo"])
        for key in ("cover_x", "cover_y"):
            if key in body:
                fields[key] = clean_fraction(body[key], "Ausschnitt")
        if "cover_zoom" in body:
            zoom = body["cover_zoom"]
            if not isinstance(zoom, (int, float)) or isinstance(zoom, bool) or not 1 <= zoom <= COVER_ZOOM_MAX:
                raise ApiError(400, "Ungültige Vergrößerung")
            fields["cover_zoom"] = float(zoom)
        if fields.get("cover_photo"):
            fields["cover_icon"] = None
        elif fields.get("cover_icon"):
            fields.update({"cover_photo": None, "cover_x": None, "cover_y": None, "cover_zoom": None})
        return fields

    def delete_room(self, room_id):
        return self._move_to_trash("room", room_id)

    @staticmethod
    def _photo_in_use(db, photo_id):
        """Gehört das Foto noch einem Schrank, einem Raumplan, einem Titelbild oder einem Platz?"""
        return bool(
            db.execute("SELECT 1 FROM maps WHERE photo = ?", (photo_id,)).fetchone()
            or db.execute("SELECT 1 FROM rooms WHERE plan_photo = ? OR cover_photo = ?", (photo_id, photo_id)).fetchone()
            or db.execute("SELECT 1 FROM photos WHERE id = ? AND (place_id IS NOT NULL OR item_id IS NOT NULL)", (photo_id,)).fetchone()
        )

    def _forget_photo(self, photo_id):
        with self.connect() as db:
            if self._photo_in_use(db, photo_id):
                return
            rows = db.execute("SELECT id, ext FROM photos WHERE id = ?", (photo_id,)).fetchall()
            db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        self._remove_photo_files(rows)

    # Schränke und Regale

    def create_map(self, body):
        room_id = clean_text(body.get("room_id"), "Raum", 40, required=True)
        name = clean_text(body.get("name"), "Name", 60, required=True)
        photo = self._clean_photo(body.get("photo"))
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM rooms WHERE id = ?", (room_id,)).fetchone():
                raise ApiError(404, "Raum nicht gefunden")
            taken = {r["code"] for r in db.execute("SELECT code FROM maps WHERE room_id = ?", (room_id,))}
            base = short_code(name) or "S"
            code = base
            number = 2
            while code in taken:
                code = f"{base[:4]}{number}"
                number += 1
            record = {
                "id": new_id(), "room_id": room_id, "name": name, "code": code, "photo": photo,
                "plan_x": None, "plan_y": None, "created": time.time(),
            }
            db.execute(
                "INSERT INTO maps (id, room_id, name, code, photo, plan_x, plan_y, created) "
                "VALUES (:id, :room_id, :name, :code, :photo, :plan_x, :plan_y, :created)",
                record,
            )
        return record

    def update_map(self, map_id, body):
        fields = {}
        old_photo = None
        with self.connect() as db:
            current = db.execute("SELECT * FROM maps WHERE id = ?", (map_id,)).fetchone()
            if not current:
                raise ApiError(404, "Schrank nicht gefunden")
            if "room_id" in body and body["room_id"] != current["room_id"]:
                room_id = clean_text(body["room_id"], "Raum", 40, required=True)
                if not db.execute("SELECT 1 FROM rooms WHERE id = ?", (room_id,)).fetchone():
                    raise ApiError(404, "Raum nicht gefunden")
                # Die Adressen der Plätze bleiben, das Kürzel des Schranks darf im neuen Raum nur nicht doppelt sein.
                code, number = current["code"], 2
                while db.execute("SELECT 1 FROM maps WHERE room_id = ? AND code = ?", (room_id, code)).fetchone():
                    code = f"{current['code'][:4]}{number}"
                    number += 1
                fields.update({"room_id": room_id, "code": code, "plan_x": None, "plan_y": None})
            old_photo = current["photo"]
        if "name" in body:
            fields["name"] = clean_text(body["name"], "Name", 60, required=True)
        if "photo" in body:
            fields["photo"] = self._clean_photo(body["photo"])
        if "plan_x" in body or "plan_y" in body:
            x, y = body.get("plan_x"), body.get("plan_y")
            if x is None and y is None:
                fields["plan_x"] = fields["plan_y"] = None
            else:
                fields["plan_x"] = clean_fraction(x, "Standort")
                fields["plan_y"] = clean_fraction(y, "Standort")
        record = self._update("maps", map_id, fields)
        if "photo" in fields and old_photo and old_photo != fields["photo"]:
            self._forget_photo(old_photo)
        return record

    def delete_map(self, map_id):
        return self._move_to_trash("map", map_id)

    def _clean_photo(self, photo_id):
        if photo_id is None:
            return None
        if not isinstance(photo_id, str) or not PHOTO_ID.match(photo_id):
            raise ApiError(400, "Ungültige Foto-Kennung")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM photos WHERE id = ?", (photo_id,)).fetchone():
                raise ApiError(400, "Foto nicht gefunden")
        return photo_id

    # Plätze

    def create_place(self, body):
        map_id = clean_text(body.get("map_id"), "Karte", 40, required=True)
        with self.connect() as db:
            # Sofort schreibend sperren, damit zwei gleichzeitige Anfragen nicht dieselbe Nummer wählen.
            db.execute("BEGIN IMMEDIATE")
            parent = db.execute(
                "SELECT m.code, r.code AS room_code FROM maps m JOIN rooms r ON r.id = m.room_id WHERE m.id = ?",
                (map_id,),
            ).fetchone()
            if not parent:
                raise ApiError(404, "Schrank nicht gefunden")
            record = {
                "id": new_id(),
                "map_id": map_id,
                "code": self._free_place_code(db, f"{parent['room_code']}-{parent['code']}"),
                "label": clean_text(body.get("label"), "Bezeichnung", 80),
                "x": clean_fraction(body.get("x"), "x"),
                "y": clean_fraction(body.get("y"), "y"),
                "w": clean_fraction(body.get("w"), "Breite"),
                "h": clean_fraction(body.get("h"), "Höhe"),
                "surveyed": 0,
                "created": time.time(),
            }
            db.execute(
                "INSERT INTO places (id, map_id, code, label, x, y, w, h, surveyed, created) VALUES "
                "(:id, :map_id, :code, :label, :x, :y, :w, :h, :surveyed, :created)",
                record,
            )
            map_photo = db.execute("SELECT photo FROM maps WHERE id = ?", (map_id,)).fetchone()["photo"]
        if body.get("use_map_photo") and map_photo:
            # Ein Foto vom ganzen Bereich ist zugleich das Foto vom Inhalt.
            path = self.photo_path(map_photo)
            if path and path.exists():
                self.add_photo(path.read_bytes(), record["id"])
        return record

    @staticmethod
    def _free_place_code(db, prefix, reserved=()):
        """Die kleinste freie Nummer: Was gelöscht ist, auch im Papierkorb, gibt seine Nummer wieder frei."""
        number = 1
        while True:
            code = f"{prefix}-{number:02d}"
            if code not in reserved and not db.execute("SELECT 1 FROM places WHERE code = ?", (code,)).fetchone():
                return code
            number += 1

    def update_place(self, place_id, body):
        fields = {}
        if "label" in body:
            fields["label"] = clean_text(body["label"], "Bezeichnung", 80)
        for key in ("x", "y", "w", "h"):
            if key in body:
                fields[key] = clean_fraction(body[key], key)
        checked = False
        if "surveyed" in body:
            fields["surveyed"] = 1 if body["surveyed"] else 0
            fields["surveyed_at"] = time.time() if body["surveyed"] else None
            with self.connect() as db:
                row = db.execute("SELECT surveyed FROM places WHERE id = ?", (place_id,)).fetchone()
            # Einen schon erfassten Platz noch einmal durchsehen ist Inventarpflege.
            checked = bool(body["surveyed"] and row and row["surveyed"])
        record = self._update("places", place_id, fields)
        if checked:
            self._events(["checked"], place_id=place_id)
        return record

    def delete_place(self, place_id):
        return self._move_to_trash("place", place_id)

    # Inhalte

    def create_item(self, body):
        place_id = clean_text(body.get("place_id"), "Platz", 40, required=True)
        now = time.time()
        record = {
            "id": new_id(),
            "place_id": place_id,
            "name": clean_text(body.get("name"), "Name", 120, required=True),
            "synonyms": clean_text(body.get("synonyms"), "Auch genannt", 200),
            "fill": self._clean_fill(body.get("fill", "ok")),
            "scale": self._clean_scale(body.get("scale", "fill")),
            "quantity": clean_quantity(body.get("quantity", 1)),
            "note": clean_text(body.get("note"), "Notiz", 200),
            "details": clean_details(body.get("details")),
            "created": now,
            "updated": now,
            "last_seen": now,
            "missing": 0,
        }
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM places WHERE id = ?", (place_id,)).fetchone():
                raise ApiError(404, "Platz nicht gefunden")
            db.execute(
                "INSERT INTO items (id, place_id, name, synonyms, fill, scale, quantity, note, details, missing, last_seen, created, updated) "
                "VALUES (:id, :place_id, :name, :synonyms, :fill, :scale, :quantity, :note, :details, :missing, :last_seen, :created, :updated)",
                record,
            )
        return record

    def update_item(self, item_id, body):
        with self.connect() as db:
            before = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not before:
            raise ApiError(404, "Eintrag nicht gefunden")
        fields = {"updated": time.time()}
        if "name" in body:
            fields["name"] = clean_text(body["name"], "Name", 120, required=True)
        if "synonyms" in body:
            fields["synonyms"] = clean_text(body["synonyms"], "Auch genannt", 200)
        if "note" in body:
            fields["note"] = clean_text(body["note"], "Notiz", 200)
        if "details" in body:
            fields["details"] = clean_details(body["details"])
        if "fill" in body:
            fields["fill"] = self._clean_fill(body["fill"])
        if "scale" in body:
            fields["scale"] = self._clean_scale(body["scale"])
        if "quantity" in body:
            fields["quantity"] = clean_quantity(body["quantity"])
        if "place_id" in body:
            place_id = clean_text(body["place_id"], "Platz", 40, required=True)
            with self.connect() as db:
                if not db.execute("SELECT 1 FROM places WHERE id = ?", (place_id,)).fetchone():
                    raise ApiError(404, "Platz nicht gefunden")
            fields["place_id"] = place_id
        changes_away = any(key in body for key in ("away", "away_to", "away_due"))
        current = before
        if "passport" in body or changes_away:
            if "passport" in body:
                passport = clean_passport(body["passport"], read_passport(current["passport"]))
                fields["passport"] = json.dumps(passport, ensure_ascii=False, sort_keys=True) if passport else ""
        if changes_away:
            away = clean_text(body["away"], "Wo es gerade ist", 80) if "away" in body else current["away"]
            if not away and ("away_to" in body or "away_due" in body) and "away" not in body:
                raise ApiError(400, "Es ist gerade nicht woanders")
            # Bleibt es bei derselben Sache und Person, bleibt der Rest stehen. Sonst beginnt ein neuer Abschnitt.
            same_place = "away" not in body or away == current["away"]
            away_to = " ".join(clean_text(body["away_to"], "Bei wem", 60).split()) if "away_to" in body else (current["away_to"] if same_place else "")
            same_person = same_place and away_to == current["away_to"]
            away_due = clean_date(body["away_due"], "Zurück bis") if "away_due" in body else (current["away_due"] if same_person else "")
            if not away:
                away_to = away_due = ""
            fields.update({"away": away, "away_to": away_to, "away_due": away_due})
            moved = (away, fields["away_to"]) != (current["away"], current["away_to"])
            if moved:
                fields["away_since"] = time.time() if away else None
            if not away and current["away"]:
                fields["missing"] = 0
                fields["last_seen"] = time.time()
        record = self._update("items", item_id, fields)
        if changes_away and moved:
            with self.connect() as db:
                if away:
                    self._log(db, item_id, "weg", away, fields["away_to"])
                else:
                    self._log(db, item_id, "zurueck", current["away"], current["away_to"])
        # Für die Meilensteine: Umräumen, Pflegen, Reparieren und Verleihen zählen wie Sammeln.
        events = []
        if record["place_id"] != before["place_id"]:
            events.append("moved")
        if record["scale"] == "state" and before["fill"] in ("wenig", "leer") and record["fill"] in ("ok", "voll"):
            events.append("repaired")
        if any(record[key] != before[key] for key in ("name", "synonyms", "note", "details", "passport", "quantity")):
            events.append("cared")
        if changes_away and moved and away and (away in LENT_WORDS or fields["away_to"]):
            events.append("lent")
        self._events(events, item_id, record["place_id"])
        return record

    def _events(self, kinds, item_id=None, place_id=None):
        if not kinds:
            return
        with self.connect() as db:
            db.executemany(
                "INSERT INTO events (at, type, item_id, place_id) VALUES (?, ?, ?, ?)",
                [(time.time(), kind, item_id, place_id) for kind in kinds],
            )

    @staticmethod
    def _log(db, item_id, kind, text="", who="", day=""):
        """Eine Zeile im Verlauf eines Eintrags. Pro Eintrag bleiben die letzten LOG_KEEP Zeilen."""
        db.execute(
            "INSERT INTO item_log (item_id, at, kind, text, who, day) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, time.time(), kind, text, who, day),
        )
        db.execute(
            "DELETE FROM item_log WHERE item_id = ? AND id NOT IN "
            "(SELECT id FROM item_log WHERE item_id = ? ORDER BY at DESC, id DESC LIMIT ?)",
            (item_id, item_id, LOG_KEEP),
        )

    def service_done(self, item_id, body):
        """Wartung erledigt: Datum im Steckbrief setzen und im Verlauf festhalten."""
        day = clean_date(body.get("date"), "Datum") or time.strftime("%Y-%m-%d")
        note = clean_text(body.get("note"), "Notiz", 200)
        with self.connect() as db:
            row = db.execute("SELECT passport FROM items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                raise ApiError(404, "Eintrag nicht gefunden")
            passport = read_passport(row["passport"])
            if (passport.get("service_last") or "") <= day:
                passport["service_last"] = day
            db.execute(
                "UPDATE items SET passport = ?, updated = ? WHERE id = ?",
                (json.dumps(passport, ensure_ascii=False, sort_keys=True), time.time(), item_id),
            )
            self._log(db, item_id, "wartung", note, day=day)
        self._events(["serviced"], item_id)
        return self._update("items", item_id, {})

    def add_log(self, item_id, body):
        text = clean_text(body.get("text"), "Notiz", 200, required=True)
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
                raise ApiError(404, "Eintrag nicht gefunden")
            self._log(db, item_id, "notiz", " ".join(text.split()))
        self._events(["cared"], item_id)
        return {"ok": True}

    def delete_log(self, log_id):
        if not isinstance(log_id, str) or not log_id.isdigit() or len(log_id) > 12:
            raise ApiError(404, "Nicht gefunden")
        with self.connect() as db:
            if not db.execute("DELETE FROM item_log WHERE id = ?", (int(log_id),)).rowcount:
                raise ApiError(404, "Nicht gefunden")
        return {"ok": True}

    # Dokumente am Steckbrief

    def add_document(self, item_id, data, kind=None, name=None):
        kind = kind or "sonstiges"
        if kind not in DOCUMENT_KINDS:
            raise ApiError(400, "Unbekannte Art von Dokument")
        if not data:
            raise ApiError(400, "Die Datei ist leer")
        ext = sniff_document_ext(data[:16])
        if not ext:
            raise ApiError(415, "Nur PDF-Dateien oder JPEG-, PNG- und WebP-Bilder sind erlaubt")
        document_id = new_id()
        record = {
            "id": document_id, "item_id": item_id, "kind": kind, "title": document_title(name, kind),
            "ext": ext, "size": len(data), "created": time.time(),
        }
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
                raise ApiError(404, "Eintrag nicht gefunden")
            if db.execute("SELECT COUNT(*) FROM documents WHERE item_id = ?", (item_id,)).fetchone()[0] >= MAX_DOCUMENTS_PER_ITEM:
                raise ApiError(409, "An diesem Eintrag hängen schon zu viele Dokumente")
            temporary = self.document_dir / f".{document_id}.tmp"
            temporary.write_bytes(data)
            temporary.replace(self.document_dir / f"{document_id}{ext}")
            db.execute(
                "INSERT INTO documents (id, item_id, kind, title, ext, size, created) "
                "VALUES (:id, :item_id, :kind, :title, :ext, :size, :created)",
                record,
            )
        self._events(["cared"], item_id)
        return record

    def document(self, document_id):
        """Datei und Angaben zu einem Dokument, oder None."""
        if not isinstance(document_id, str) or not PHOTO_ID.match(document_id):
            return None
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not row or row["ext"] not in DOCUMENT_TYPES:
            return None
        path = self.document_dir / f"{document_id}{row['ext']}"
        return (dict(row), path) if path.exists() else None

    def update_document(self, document_id, body):
        fields = {}
        if "title" in body:
            fields["title"] = " ".join(clean_text(body["title"], "Titel", 120, required=True).split())
        if "kind" in body:
            if body["kind"] not in DOCUMENT_KINDS:
                raise ApiError(400, "Unbekannte Art von Dokument")
            fields["kind"] = body["kind"]
        if not PHOTO_ID.match(document_id or ""):
            raise ApiError(404, "Dokument nicht gefunden")
        return self._update("documents", document_id, fields)

    def delete_document(self, document_id):
        return self._move_to_trash("document", document_id)

    def _remove_document_files(self, rows):
        for row in rows:
            if PHOTO_ID.match(row["id"]) and row["ext"] in DOCUMENT_TYPES:
                (self.document_dir / f"{row['id']}{row['ext']}").unlink(missing_ok=True)

    def mark_item(self, item_id, found):
        fields = {"missing": 0 if found else 1}
        if found:
            fields["last_seen"] = time.time()
        record = self._update("items", item_id, fields)
        self.log_event("found" if found else "missing", item_id=item_id, place_id=record["place_id"])
        return record

    def confirm_item(self, item_id):
        """Auf Nachfrage bestätigt: Es liegt noch da. Zählt als Inventarpflege, nicht als Fund."""
        record = self._update("items", item_id, {"missing": 0, "last_seen": time.time()})
        self._events(["checked_item"], item_id, record["place_id"])
        return record

    def add_word(self, item_id, word):
        word = clean_text(word, "Suchwort", 60, required=True)
        with self.connect() as db:
            row = db.execute("SELECT synonyms FROM items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise ApiError(404, "Eintrag nicht gefunden")
        words = [w.strip() for w in row["synonyms"].split(",") if w.strip()]
        if normalize_name(word) in {normalize_name(w) for w in words}:
            return self._update("items", item_id, {})
        text = ", ".join([*words, word])
        if len(text) > 200:
            raise ApiError(400, "Zu viele Suchwörter bei diesem Eintrag")
        return self._update("items", item_id, {"synonyms": text, "updated": time.time()})

    def move_items(self, item_ids, place_id):
        """Verlegt Einträge an einen Platz. Gleichnamige Einträge dort werden zusammengeführt."""
        if not isinstance(item_ids, list) or not item_ids or not all(isinstance(i, str) for i in item_ids):
            raise ApiError(400, "Einträge fehlen")
        place_id = clean_text(place_id, "Platz", 40, required=True)
        now = time.time()
        moved = merged = 0
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM places WHERE id = ?", (place_id,)).fetchone():
                raise ApiError(404, "Platz nicht gefunden")
            for item_id in item_ids:
                item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
                if not item:
                    raise ApiError(404, "Eintrag nicht gefunden")
                twin = next((
                    row for row in db.execute("SELECT * FROM items WHERE place_id = ? AND id != ?", (place_id, item_id))
                    if normalize_name(row["name"]) == normalize_name(item["name"])
                ), None)
                if twin:
                    notes = [text for text in (twin["note"], item["note"]) if text]
                    words = [w.strip() for text in (twin["synonyms"], item["synonyms"]) for w in text.split(",") if w.strip()]
                    details = "\n".join(text for text in (twin["details"], item["details"]) if text)
                    try:
                        details = clean_details(details)
                    except ApiError:
                        details = "\n".join(details.split("\n")[:DETAIL_LINES_MAX])
                    # Der Steckbrief des Ziels gilt, Lücken füllt der verlegte Eintrag.
                    passport = {**read_passport(item["passport"]), **read_passport(twin["passport"])}
                    db.execute(
                        "UPDATE items SET note = ?, synonyms = ?, details = ?, passport = ?, quantity = ?, missing = 0, last_seen = ?, updated = ? WHERE id = ?",
                        (" · ".join(dict.fromkeys(notes))[:200], ", ".join(dict.fromkeys(words))[:200], details,
                         json.dumps(passport, ensure_ascii=False, sort_keys=True) if passport else "",
                         min(QUANTITY_MAX, twin["quantity"] + item["quantity"]), now, now, twin["id"]),
                    )
                    if item["away"] and not twin["away"]:
                        db.execute(
                            "UPDATE items SET away = ?, away_to = ?, away_due = ?, away_since = ? WHERE id = ?",
                            (item["away"], item["away_to"], item["away_due"], item["away_since"], twin["id"]),
                        )
                    db.execute("UPDATE photos SET item_id = ? WHERE item_id = ?", (twin["id"], item_id))
                    db.execute("UPDATE documents SET item_id = ? WHERE item_id = ?", (twin["id"], item_id))
                    db.execute("UPDATE item_log SET item_id = ? WHERE item_id = ?", (twin["id"], item_id))
                    db.execute("INSERT INTO events (at, type, item_id, place_id) VALUES (?, 'merged', ?, ?)", (now, twin["id"], place_id))
                    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
                    merged += 1
                else:
                    db.execute(
                        "UPDATE items SET place_id = ?, missing = 0, last_seen = ?, updated = ? WHERE id = ?",
                        (place_id, now, now, item_id),
                    )
                    if item["place_id"] != place_id:
                        db.execute("INSERT INTO events (at, type, item_id, place_id) VALUES (?, 'moved', ?, ?)", (now, item_id, place_id))
                    moved += 1
        return {"moved": moved, "merged": merged}

    def delete_item(self, item_id):
        trash_id = self._move_to_trash("item", item_id)
        self._events(["sorted_out"], item_id)
        return trash_id

    BATCH_FIELDS = ("name", "note", "synonyms", "fill", "scale", "quantity", "place_id")

    def batch_items(self, body):
        """Schnellbearbeitung: Änderungen an vielen Einträgen auf einmal. Gelöschtes kommt in den Papierkorb.
        Alles wird vorher geprüft, damit kein halber Auftrag ausgeführt wird."""
        if not isinstance(body, dict):
            raise ApiError(400, "Ungültige Daten")
        updates = body.get("updates") or []
        deletes = body.get("delete") or []
        if not isinstance(updates, list) or not isinstance(deletes, list) or len(updates) + len(deletes) > 2000:
            raise ApiError(400, "Ungültige Daten")
        with self.connect() as db:
            known = {row["id"] for row in db.execute("SELECT id FROM items")}
            places = {row["id"] for row in db.execute("SELECT id FROM places")}
        if not all(isinstance(item_id, str) and item_id in known for item_id in deletes):
            raise ApiError(404, "Eintrag nicht gefunden")
        doomed = set(deletes)
        checked = []
        for update in updates:
            if not isinstance(update, dict) or update.get("id") not in known:
                raise ApiError(404, "Eintrag nicht gefunden")
            if update["id"] in doomed:
                continue
            change = {key: update[key] for key in self.BATCH_FIELDS if key in update}
            if "name" in change:
                clean_text(change["name"], "Name", 120, required=True)
            if "note" in change:
                clean_text(change["note"], "Notiz", 200)
            if "synonyms" in change:
                clean_text(change["synonyms"], "Auch genannt", 200)
            if "fill" in change:
                self._clean_fill(change["fill"])
            if "scale" in change:
                self._clean_scale(change["scale"])
            if "quantity" in change:
                clean_quantity(change["quantity"])
            if "place_id" in change and change["place_id"] not in places:
                raise ApiError(404, "Platz nicht gefunden")
            if change:
                checked.append((update["id"], change))
        for item_id, change in checked:
            self.update_item(item_id, change)
        for item_id in dict.fromkeys(deletes):
            self.delete_item(item_id)
        return {"updated": len(checked), "deleted": len(doomed)}

    @staticmethod
    def _clean_scale(value):
        if value not in SCALES:
            raise ApiError(400, "Unbekannte Skala")
        return value

    @staticmethod
    def _clean_fill(value):
        if value not in FILL_LEVELS:
            raise ApiError(400, "Unbekannter Füllstand")
        return value

    # Fotos

    def add_photo(self, data, place_id=None, item_id=None):
        ext = sniff_image_ext(data[:16])
        if not ext:
            raise ApiError(415, "Nur JPEG-, PNG- oder WebP-Bilder sind erlaubt")
        if place_id and item_id:
            raise ApiError(400, "Ein Foto gehört entweder zu einem Platz oder zu einem Eintrag")
        photo_id = new_id()
        with self.connect() as db:
            if place_id and not db.execute("SELECT 1 FROM places WHERE id = ?", (place_id,)).fetchone():
                raise ApiError(404, "Platz nicht gefunden")
            if item_id and not db.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone():
                raise ApiError(404, "Eintrag nicht gefunden")
            (self.photo_dir / f"{photo_id}{ext}").write_bytes(data)
            db.execute(
                "INSERT INTO photos (id, ext, place_id, item_id, created) VALUES (?, ?, ?, ?, ?)",
                (photo_id, ext, place_id, item_id, time.time()),
            )
        return {"id": photo_id}

    def photo_path(self, photo_id):
        if not PHOTO_ID.match(photo_id):
            return None
        with self.connect() as db:
            row = db.execute("SELECT ext FROM photos WHERE id = ?", (photo_id,)).fetchone()
        return self.photo_dir / f"{photo_id}{row['ext']}" if row else None

    def delete_photo(self, photo_id):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM photos WHERE id = ?", (photo_id,)).fetchone():
                raise ApiError(404, "Foto nicht gefunden")
            if db.execute("SELECT 1 FROM maps WHERE photo = ?", (photo_id,)).fetchone():
                raise ApiError(409, "Das Foto gehört zu einem Schrank")
            if db.execute("SELECT 1 FROM rooms WHERE plan_photo = ?", (photo_id,)).fetchone():
                raise ApiError(409, "Das Foto gehört zu einem Raumplan")
        return self._move_to_trash("photo", photo_id)

    # Papierkorb

    @staticmethod
    def _rows(db, table, column, values):
        values = [value for value in values if value]
        if not values:
            return []
        marks = ", ".join("?" for _ in values)
        return [dict(row) for row in db.execute(f"SELECT * FROM {table} WHERE {column} IN ({marks})", values)]

    def _snapshot(self, db, kind, record_id):
        """Alles, was mit diesem Eintrag verschwinden würde, einschließlich der Fotos."""
        ids = lambda rows, column="id": [row[column] for row in rows]  # noqa: E731
        sites = self._rows(db, "sites", "id", [record_id]) if kind == "site" else []
        rooms = self._rows(db, "rooms", "id", [record_id]) if kind == "room" else self._rows(db, "rooms", "site_id", ids(sites))
        maps = self._rows(db, "maps", "id", [record_id]) if kind == "map" else self._rows(db, "maps", "room_id", ids(rooms))
        places = self._rows(db, "places", "id", [record_id]) if kind == "place" else self._rows(db, "places", "map_id", ids(maps))
        items = self._rows(db, "items", "id", [record_id]) if kind == "item" else self._rows(db, "items", "place_id", ids(places))
        if kind in ("photo", "document"):
            photos = self._rows(db, "photos", "id", [record_id])
        else:
            photos = self._rows(db, "photos", "place_id", ids(places))
            photos += self._rows(db, "photos", "item_id", ids(items))
            known = set(ids(photos))
            extra = ids(maps, "photo") + ids(rooms, "plan_photo") + ids(rooms, "cover_photo")
            photos += [row for row in self._rows(db, "photos", "id", extra) if row["id"] not in known]
        documents = (self._rows(db, "documents", "id", [record_id]) if kind == "document"
                     else self._rows(db, "documents", "item_id", ids(items)))
        return {
            "sites": sites, "rooms": rooms, "maps": maps, "places": places, "items": items, "photos": photos,
            "recognitions": self._rows(db, "recognitions", "photo_id", ids(photos)),
            "documents": documents, "item_log": self._rows(db, "item_log", "item_id", ids(items)),
        }

    @staticmethod
    def _describe(db, kind, row):
        """Name und Herkunft für die Anzeige im Papierkorb."""
        path = []
        place_id = row.get("place_id") if kind in ("item", "photo") else None
        if kind in ("photo", "document") and row.get("item_id"):
            owner = db.execute("SELECT name, place_id FROM items WHERE id = ?", (row["item_id"],)).fetchone()
            if owner:
                path.append(owner["name"])
                place_id = owner["place_id"]
        if place_id:
            place = db.execute("SELECT * FROM places WHERE id = ?", (place_id,)).fetchone()
            if place:
                path.insert(0, place["label"] or place["code"])
                row_map = place["map_id"]
            else:
                row_map = None
        elif kind == "place":
            row_map = row["map_id"]
        else:
            row_map = None
        room_id = row["room_id"] if kind == "map" else None
        if row_map:
            map_row = db.execute("SELECT name, room_id FROM maps WHERE id = ?", (row_map,)).fetchone()
            if map_row:
                path.insert(0, map_row["name"])
                room_id = map_row["room_id"]
        site_id = row["site_id"] if kind == "room" else None
        if room_id:
            room = db.execute("SELECT name, site_id FROM rooms WHERE id = ?", (room_id,)).fetchone()
            if room:
                path.insert(0, room["name"])
                site_id = room["site_id"]
        if site_id and db.execute("SELECT COUNT(*) FROM sites").fetchone()[0] > 1:
            site = db.execute("SELECT name FROM sites WHERE id = ?", (site_id,)).fetchone()
            if site:
                path.insert(0, site["name"])
        if kind == "place":
            label = row["label"] or row["code"]
        elif kind == "photo":
            label = "Foto"
        elif kind == "document":
            label = row["title"]
        else:
            label = row["name"]
        return label, " › ".join(path)

    def _move_to_trash(self, kind, record_id):
        table = TRASH_TABLES[kind]
        with self.connect() as db:
            data = self._snapshot(db, kind, record_id)
            if not data[table]:
                raise ApiError(404, "Nicht gefunden")
            label, detail = self._describe(db, kind, data[table][0])
            trash_id = new_id()
            db.execute(
                "INSERT INTO trash (id, kind, label, detail, created, data) VALUES (?, ?, ?, ?, ?, ?)",
                (trash_id, kind, label, detail, time.time(), json.dumps(data, ensure_ascii=False)),
            )
            db.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            db.executemany("DELETE FROM photos WHERE id = ?", [(row["id"],) for row in data["photos"]])
        return trash_id

    def list_trash(self):
        self.purge_trash()
        now = time.time()
        entries = []
        with self.connect() as db:
            for row in db.execute("SELECT * FROM trash ORDER BY created DESC").fetchall():
                data = json.loads(row["data"])
                parent = TRASH_PARENTS.get(row["kind"])
                if row["kind"] == "photo" and data["photos"][0].get("item_id"):
                    parent = None  # Ein Detailfoto kehrt nur zu seinem Eintrag zurück, ein Dokument ebenso.
                parent_missing = False
                if parent:
                    value = data[TRASH_TABLES[row["kind"]]][0][parent[0]]
                    parent_missing = not (value and db.execute(
                        f"SELECT 1 FROM {parent[1]} WHERE id = ?", (value,)
                    ).fetchone())
                entries.append({
                    "id": row["id"],
                    "kind": row["kind"],
                    "label": row["label"],
                    "detail": row["detail"],
                    "created": row["created"],
                    "days_left": max(1, int((row["created"] + TRASH_DAYS * 86400 - now) // 86400) + 1),
                    "counts": {name: len(data.get(name, [])) for name in ("rooms", "maps", "places", "items", "photos", "documents")},
                    "parent_table": parent[1] if parent else None,
                    "parent_missing": parent_missing,
                })
        return {"entries": entries, "days": TRASH_DAYS}

    def restore_trash(self, trash_id, parent_id=None):
        with self.connect() as db:
            entry = db.execute("SELECT * FROM trash WHERE id = ?", (trash_id,)).fetchone()
            if not entry:
                raise ApiError(404, "Das liegt nicht mehr im Papierkorb")
            kind = entry["kind"]
            data = json.loads(entry["data"])
            top = data[TRASH_TABLES[kind]][0]
            if kind == "photo" and top.get("item_id"):
                if not db.execute("SELECT 1 FROM items WHERE id = ?", (top["item_id"],)).fetchone():
                    raise ApiError(409, "Den Eintrag zu diesem Detailfoto gibt es nicht mehr.")
            elif kind == "document":
                if not db.execute("SELECT 1 FROM items WHERE id = ?", (top["item_id"],)).fetchone():
                    raise ApiError(409, "Den Eintrag zu diesem Dokument gibt es nicht mehr.")
            elif kind in TRASH_PARENTS:
                column, table = TRASH_PARENTS[kind]
                exists = lambda value: value and db.execute(f"SELECT 1 FROM {table} WHERE id = ?", (value,)).fetchone()  # noqa: E731
                if not exists(top[column]):
                    if not exists(parent_id):
                        raise ApiError(409, "Der ursprüngliche Ort existiert nicht mehr. Wähle einen anderen aus.")
                    top[column] = parent_id
            photos = [row for row in data["photos"] if (self.photo_dir / f"{row['id']}{row['ext']}").exists()]
            present = {row["id"] for row in photos}
            for row in data["sites"]:
                row["name"] = self._free_name(db, "sites", row["name"])
            for row in data["rooms"]:
                row["name"] = self._free_name(db, "rooms", row["name"], "site_id", row["site_id"])
                if db.execute("SELECT 1 FROM rooms WHERE code = ?", (row["code"],)).fetchone():
                    row["code"] = self._free_room_code(db, row["name"])
                if row.get("plan_photo") not in present:
                    row["plan_photo"] = None
                if row.get("cover_photo") and row["cover_photo"] not in present:
                    row["cover_photo"] = None
            for row in data["maps"]:
                code, number = row["code"], 2
                while db.execute("SELECT 1 FROM maps WHERE room_id = ? AND code = ?", (row["room_id"], code)).fetchone():
                    code = f"{row['code'][:4]}{number}"
                    number += 1
                row["code"] = code
                if row.get("photo") not in present:
                    row["photo"] = None
            # Eine Adresse, die inzwischen neu vergeben ist, bekommt die nächste freie Nummer an ihrem Schrank.
            maps_now = {row["id"]: row for row in data["maps"]}
            rooms_now = {row["id"]: row["code"] for row in data["rooms"]}
            kept = {row["code"] for row in data["places"]
                    if not db.execute("SELECT 1 FROM places WHERE code = ?", (row["code"],)).fetchone()}
            for row in data["places"]:
                if row["code"] in kept:
                    continue
                map_ = maps_now.get(row["map_id"]) or db.execute(
                    "SELECT room_id, code FROM maps WHERE id = ?", (row["map_id"],)).fetchone()
                room_code = rooms_now.get(map_["room_id"]) or db.execute(
                    "SELECT code FROM rooms WHERE id = ?", (map_["room_id"],)).fetchone()["code"]
                row["code"] = self._free_place_code(db, f"{room_code}-{map_['code']}", kept)
                kept.add(row["code"])
            data["photos"] = photos
            data["recognitions"] = [row for row in data["recognitions"] if row["photo_id"] in present]
            data["documents"] = [
                row for row in data.get("documents", [])
                if row.get("ext") in DOCUMENT_TYPES and (self.document_dir / f"{row['id']}{row['ext']}").exists()
            ]
            try:
                for table in ("sites", "rooms", "maps", "places", "items", "photos", "recognitions", "documents", "item_log"):
                    columns = {info["name"] for info in db.execute(f"PRAGMA table_info({table})")}
                    for row in data.get(table, []):
                        names = [name for name in row if name in columns]
                        db.execute(
                            f"INSERT INTO {table} ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})",
                            [row[name] for name in names],
                        )
            except sqlite3.IntegrityError:
                db.rollback()
                raise ApiError(409, "Das passt nicht mehr zum Bestand")
            db.execute("DELETE FROM trash WHERE id = ?", (trash_id,))
            return {"href": self._href_of(db, kind, top)}

    @staticmethod
    def _free_name(db, table, name, column=None, value=None):
        where = f" AND {column} = ?" if column else ""
        extra = (value,) if column else ()
        candidate, number = name, 2
        while db.execute(f"SELECT 1 FROM {table} WHERE name = ?{where}", (candidate, *extra)).fetchone():
            candidate = f"{name} ({number})"
            number += 1
        return candidate

    @staticmethod
    def _href_of(db, kind, top):
        if kind == "room":
            return f"#/raum/{top['id']}"
        if kind == "map":
            return f"#/karte/{top['id']}"
        if kind == "place":
            return f"#/p/{top['code']}"
        if kind == "document":
            return f"#/steckbrief/{top['item_id']}"
        if kind in ("item", "photo"):
            place = db.execute("SELECT code FROM places WHERE id = ?", (top["place_id"],)).fetchone()
            return f"#/p/{place['code']}" if place else "#/"
        return "#/"

    def _discard_trash(self, entries):
        for entry in entries:
            data = json.loads(entry["data"])
            self._remove_photo_files(data["photos"])
            self._remove_document_files(data.get("documents", []))

    def purge_trash(self, older_than_days=TRASH_DAYS):
        """Löscht endgültig, was länger als die Frist im Papierkorb liegt."""
        limit = time.time() - older_than_days * 86400
        with self.connect() as db:
            entries = db.execute("SELECT * FROM trash WHERE created < ?", (limit,)).fetchall()
            if entries:
                db.execute("DELETE FROM trash WHERE created < ?", (limit,))
        self._discard_trash(entries)

    def delete_trash(self, trash_id=None):
        """Löscht einen Eintrag endgültig, ohne Angabe den ganzen Papierkorb."""
        with self.connect() as db:
            if trash_id is None:
                entries = db.execute("SELECT * FROM trash").fetchall()
                db.execute("DELETE FROM trash")
            else:
                entries = db.execute("SELECT * FROM trash WHERE id = ?", (trash_id,)).fetchall()
                if not entries:
                    raise ApiError(404, "Das liegt nicht mehr im Papierkorb")
                db.execute("DELETE FROM trash WHERE id = ?", (trash_id,))
        self._discard_trash(entries)

    def _remove_photo_files(self, rows):
        for row in rows:
            (self.photo_dir / f"{row['id']}{row['ext']}").unlink(missing_ok=True)

    # Erkennung

    def saved_recognition(self, photo_id, instruction):
        """Liefert das gespeicherte Ergebnis, aber nur für denselben Hinweis."""
        with self.connect() as db:
            row = db.execute(
                "SELECT result FROM recognitions WHERE photo_id = ? AND instruction = ?", (photo_id, instruction)
            ).fetchone()
        return json.loads(row["result"]) if row else None

    def save_recognition(self, photo_id, instruction, result, usage):
        with self.connect() as db:
            db.execute(
                "INSERT INTO recognitions (photo_id, result, instruction, created) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(photo_id) DO UPDATE SET result = excluded.result, "
                "instruction = excluded.instruction, created = excluded.created",
                (photo_id, json.dumps(result, ensure_ascii=False), instruction, time.time()),
            )
            if usage:
                db.execute(
                    "INSERT INTO api_usage (at, input_tokens, output_tokens) VALUES (?, ?, ?)",
                    (time.time(), usage["input_tokens"], usage["output_tokens"]),
                )

    # Sonstiges

    def keep_unreadable_answer(self, answer):
        # Nur die letzte. So lässt sich nachvollziehen, woran eine Auswertung gescheitert ist.
        path = self.data_dir / "letzte-unlesbare-chat-antwort.txt"
        path.touch(mode=0o600, exist_ok=True)
        path.write_text(answer)

    def add_usage(self, usage):
        with self.connect() as db:
            db.execute(
                "INSERT INTO api_usage (at, input_tokens, output_tokens) VALUES (?, ?, ?)",
                (time.time(), usage["input_tokens"], usage["output_tokens"]),
            )

    # Auswertung

    def report(self):
        state = self.state()
        now = time.time()
        rooms = {room["id"]: room for room in state["rooms"]}
        sites = {site["id"]: site for site in state["sites"]}
        maps = {map_["id"]: map_ for map_ in state["maps"]}
        places = {place["id"]: place for place in state["places"]}
        several_sites = len(sites) > 1

        def place_name(place):
            return place["label"] or L(f"Platz {int(place['code'].split('-')[-1])}", f"Spot {int(place['code'].split('-')[-1])}")

        def path(place):
            map_ = maps[place["map_id"]]
            room = rooms[map_["room_id"]]
            parts = [sites[room["site_id"]]["name"]] if several_sites else []
            return " › ".join([*parts, room["name"], map_["name"], place_name(place)])

        def item_view(item, **extra):
            place = places[item["place_id"]]
            return {"id": item["id"], "name": item["name"], "code": place["code"], "where": path(place), **extra}

        with self.connect() as db:
            finds = {
                row["item_id"]: row["n"]
                for row in db.execute(
                    "SELECT item_id, COUNT(*) AS n FROM events WHERE type = 'found' AND item_id IS NOT NULL GROUP BY item_id"
                )
            }
            searches = db.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN hits = 0 THEN 1 ELSE 0 END), 0) AS misses "
                "FROM events WHERE type = 'search'"
            ).fetchone()
        dismissed = set(json.loads(state["settings"].get("dismissed_recommendations", "[]")))
        items_at = {}
        for item in state["items"]:
            items_at.setdefault(item["place_id"], []).append(item)

        room_stats = []
        for room in state["rooms"]:
            room_places = [p for p in state["places"] if maps[p["map_id"]]["room_id"] == room["id"]]
            done = sum(1 for p in room_places if p["surveyed"])
            room_stats.append({
                "id": room["id"],
                "name": room["name"],
                "site": sites[room["site_id"]]["name"],
                "places": len(room_places),
                "surveyed": done,
                "items": sum(len(items_at.get(p["id"], [])) for p in room_places),
            })

        fill = {level: 0 for level in FILL_LEVELS}
        condition = {level: 0 for level in FILL_LEVELS}
        for item in state["items"]:
            counts = condition if item["scale"] == "state" else fill
            counts[item["fill"]] = counts.get(item["fill"], 0) + 1

        groups = {}
        for item in state["items"]:
            groups.setdefault(normalize_name(item["name"]), []).append(item)
        duplicates = [group for group in groups.values() if len({i["place_id"] for i in group}) > 1]
        duplicates.sort(key=lambda group: -len(group))

        open_places = [p for p in state["places"] if not p["surveyed"]]
        low = [i for i in state["items"] if runs_low(i)]
        missing = [i for i in state["items"] if i["missing"]]
        searchable = [normalize_name(f"{i['name']} {i['synonyms']} {i['note']}") for i in state["items"]]
        failed = [
            row for row in state["failed_searches"]
            if normalize_name(row["q"]) and not any(normalize_name(row["q"]) in text for text in searchable)
        ]
        top_items = sorted(
            (i for i in state["items"] if finds.get(i["id"])), key=lambda i: -finds[i["id"]]
        )
        stale = [
            p for p in state["places"]
            if p["surveyed"] and (p["surveyed_at"] or p["created"]) < now - STALE_DAYS * 86400
        ]

        recommendations = []

        def recommend(rec_id, kind, title, why, **data):
            if rec_id not in dismissed:
                recommendations.append({"id": rec_id, "kind": kind, "title": title, "why": why, **data})

        if open_places:
            with_photo = [p for p in open_places if p["photos"] and not items_at.get(p["id"])]
            target = (with_photo or open_places)[0]
            recommend(
                f"continue:{len(open_places)}", "continue",
                L(f"{len(open_places)} von {len(state['places'])} Plätzen {'ist' if len(open_places) == 1 else 'sind'} noch nicht bestätigt",
                  f"{len(open_places)} of {len(state['places'])} spots {'is' if len(open_places) == 1 else 'are'} not confirmed yet"),
                L("Erst wenn alles bestätigt ist, kann die Suche sicher sagen, dass etwas nicht vorhanden ist.",
                  "Only when everything is confirmed can search say for sure that something isn't there."),
                code=target["code"], where=path(target),
            )
        for item in missing[:MAX_PER_KIND]:
            recommend(
                f"missing:{item['id']}", "missing", L(f"„{item['name']}“ lag zuletzt nicht dort", f"“{item['name']}” wasn't there last time"),
                L("Der Eintrag zeigt vermutlich auf den falschen Platz. Sieh nach und korrigiere ihn.",
                  "The item probably points to the wrong spot. Check and correct it."),
                item=item_view(item),
            )
        away = [i for i in state["items"] if i["away"]]
        if away:
            recommend(
                f"away:{len(away)}", "away",
                L(f"„{away[0]['name']}“ ist gerade woanders" if len(away) == 1 else f"{len(away)} Dinge sind gerade woanders",
                  f"“{away[0]['name']}” is elsewhere right now" if len(away) == 1 else f"{len(away)} things are elsewhere right now"),
                L("Ist etwas zurück, gib es hier frei. Dann zeigt die Suche wieder den richtigen Platz.",
                  "When something is back, release it here. Search then shows the right spot again."),
                items=[item_view(i, away=i["away"], since=i["away_since"]) for i in away[:MAX_PER_KIND * 2]],
            )
        for group in duplicates[:MAX_PER_KIND]:
            recommend(
                f"duplicate:{normalize_name(group[0]['name'])}:{len(group)}", "duplicate",
                L(f"„{group[0]['name']}“ liegt an {len({i['place_id'] for i in group})} Plätzen",
                  f"“{group[0]['name']}” is in {len({i['place_id'] for i in group})} spots"),
                L("Verstreuter Bestand führt zu Doppelkäufen. An einem Platz siehst du sofort, wie viel da ist.",
                  "Scattered stock leads to buying twice. In one spot you see at once how much there is."),
                items=[item_view(i) for i in group],
            )
        for row in failed[:MAX_PER_KIND]:
            recommend(
                f"failed:{normalize_name(row['q'])}", "failed",
                L(f"„{row['q']}“ wurde gesucht und nicht gefunden ({row['times']}-mal)",
                  f"“{row['q']}” was searched for and not found ({row['times']} {'time' if row['times'] == 1 else 'times'})"),
                L("Oft heißt das Ding im Inventar nur anders. Speichere das Wort beim passenden Eintrag.",
                  "Often the thing just has another name in the inventory. Save the word with the matching item."),
                word=row["q"],
            )
        if low:
            recommend(
                f"shopping:{len(low)}", "shopping",
                L("Eine Sache geht zur Neige" if len(low) == 1 else f"{len(low)} Dinge gehen zur Neige",
                  "One thing is running low" if len(low) == 1 else f"{len(low)} things are running low"),
                L("Diese Einträge sind als wenig oder leer markiert.", "These items are marked low or empty."),
                items=[item_view(i, fill=i["fill"]) for i in low],
            )
        for item in [i for i in top_items if finds[i["id"]] >= FREQUENT_FINDS][:3]:
            recommend(
                f"frequent:{item['id']}", "frequent",
                L(f"„{item['name']}“ brauchst du oft ({finds[item['id']]}-mal gefunden)", f"You often need “{item['name']}” (found {finds[item['id']]} times)"),
                L("Häufig Genutztes gehört griffnah. Liegt es dort schon, blende diesen Hinweis einfach aus.",
                  "Things you use often belong within reach. If it's there already, just hide this tip."),
                item=item_view(item),
            )
        for place in state["places"]:
            count = len(items_at.get(place["id"], []))
            if count >= OVERFULL_ITEMS:
                recommend(
                    f"overfull:{place['id']}", "overfull", L(f"{path(place)} hat {count} Einträge", f"{path(place)} has {count} items"),
                    L("In so einem Platz wird wieder gewühlt. Lässt er sich aufteilen, markiere im Schrank einen zweiten.",
                      "A spot like this means rummaging again. If it can be split, mark a second one in the cabinet."),
                    map_id=place["map_id"],
                )
        if stale:
            recommend(
                f"stale:{len(stale)}", "stale",
                L(f"{len(stale)} {'Platz wurde' if len(stale) == 1 else 'Plätze wurden'} seit über {STALE_DAYS} Tagen nicht geprüft",
                  f"{len(stale)} {'spot has' if len(stale) == 1 else 'spots have'} not been checked for over {STALE_DAYS} days"),
                L("Bestände veralten. Eine Stichprobe genügt, du musst nicht alles neu erfassen.",
                  "Stock goes out of date. A spot-check is enough, you don't have to record everything again."),
                code=stale[0]["code"], where=path(stale[0]),
            )
        for room in state["rooms"]:
            room_maps = [m for m in state["maps"] if m["room_id"] == room["id"]]
            unplaced = [m for m in room_maps if m["plan_x"] is None]
            if room["plan_photo"] and unplaced:
                recommend(
                    f"unplaced:{room['id']}:{len(unplaced)}", "unplaced",
                    f"{len(unplaced)} {'Schrank fehlt' if len(unplaced) == 1 else 'Schränke fehlen'} im Raumplan von {room['name']}",
                    "Mit Standort zeigt die Suche auch, wo im Raum du nachsehen musst.",
                    room_id=room["id"],
                )

        summary = self.analysis_summary(state, finds)
        counts = state["event_counts"]
        return {
            "totals": {
                "sites": len(sites),
                "rooms": len(rooms),
                "maps": len(maps),
                "places": len(places),
                "surveyed": len(places) - len(open_places),
                "items": len(state["items"]),
                "low": len(low),
            },
            "rooms": room_stats,
            "fill": fill,
            "condition": condition,
            "top_items": [item_view(i, finds=finds[i["id"]]) for i in top_items[:5]],
            "search": {
                "searches": searches["n"],
                "misses": searches["misses"],
                "found": counts.get("found", 0),
                "missing": counts.get("missing", 0),
            },
            "ai": {
                "recognitions": counts.get("recognize", 0),
                "chat_answers": counts.get("chat_answer", 0),
                "analyses": counts.get("analysis", 0),
                "cost_usd": state["api_cost_usd"],
            },
            "recommendations": recommendations,
            "dismissed_count": len(dismissed),
            "analysis": self.latest_analysis(),
            "analysis_prompt": recognition.analysis_chat_prompt(summary),
            "analysis_retry": recognition.ANALYSIS_RETRY,
            "analysis_estimate_usd": recognition.estimate_analysis_cost_usd(summary),
        }

    def dismiss_recommendation(self, rec_id):
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key = 'dismissed_recommendations'").fetchone()
        dismissed = json.loads(row["value"]) if row else []
        if rec_id and rec_id not in dismissed:
            dismissed.append(clean_text(rec_id, "Empfehlung", 200))
        self.set_setting("dismissed_recommendations", json.dumps(dismissed))

    def restore_recommendations(self):
        self.set_setting("dismissed_recommendations", "[]")

    def analysis_summary(self, state=None, finds=None):
        """Das, was bei einer KI-Analyse den Mac verlässt: Texte und Zahlen, keine Fotos."""
        state = state or self.state()
        if finds is None:
            with self.connect() as db:
                finds = {
                    row["item_id"]: row["n"]
                    for row in db.execute(
                        "SELECT item_id, COUNT(*) AS n FROM events WHERE type = 'found' AND item_id IS NOT NULL GROUP BY item_id"
                    )
                }
        rooms = {room["id"]: room for room in state["rooms"]}
        maps = {map_["id"]: map_ for map_ in state["maps"]}
        codes = {place["id"]: place["code"] for place in state["places"]}
        return {
            "places": [
                {
                    "code": place["code"],
                    "name": place["label"],
                    "cabinet": maps[place["map_id"]]["name"],
                    "room": rooms[maps[place["map_id"]]["room_id"]]["name"],
                    "confirmed": bool(place["surveyed"]),
                }
                for place in state["places"]
            ],
            "items": [
                {
                    "ref": item["id"][:8],
                    "name": item["name"],
                    "also_known_as": item["synonyms"],
                    "note": item["note"],
                    "fill": item["fill"],
                    "is_device": item["scale"] == "state",
                    "place": codes[item["place_id"]],
                    "times_found": finds.get(item["id"], 0),
                    "last_time_not_there": bool(item["missing"]),
                    "away": item["away"],
                }
                for item in state["items"]
            ],
            "failed_searches": [{"q": row["q"], "times": row["times"]} for row in state["failed_searches"]],
        }

    def save_analysis(self, result, source):
        with self.connect() as db:
            db.execute(
                "INSERT INTO analyses (created, source, result) VALUES (?, ?, ?)",
                (time.time(), source, json.dumps(result, ensure_ascii=False)),
            )

    def _resolve_action(self, action):
        """Prüft einen Vorschlag gegen den Bestand. Der Knopftext kommt aus den echten Daten, nicht von der KI."""
        kind = action.get("type")
        if kind == "none":
            return None
        with self.connect() as db:
            items = []
            for ref in action.get("refs", []):
                if not re.fullmatch(r"[0-9a-f]{8,32}", ref):
                    return None
                rows = db.execute("SELECT id, name FROM items WHERE id LIKE ?", (ref + "%",)).fetchall()
                if len(rows) != 1:
                    return None
                items.append(dict(rows[0]))
            place = db.execute("SELECT id, code, label FROM places WHERE code = ?", (action.get("place_code", ""),)).fetchone()
        if not items:
            return None
        names = ", ".join(f"„{item['name']}“" for item in items)
        if kind == "add_word" and len(items) == 1 and action.get("word"):
            return {"kind": kind, "items": items, "word": action["word"],
                    "text": f"„{action['word']}“ als Suchwort bei {names} speichern"}
        if kind == "rename" and len(items) == 1 and action.get("new_name"):
            return {"kind": kind, "items": items, "new_name": action["new_name"],
                    "text": f"{names} in „{action['new_name']}“ umbenennen"}
        if kind == "move" and place:
            return {"kind": kind, "items": items, "place_id": place["id"],
                    "text": f"{names} nach {place['code']} verlegen"}
        return None

    def latest_analysis(self):
        with self.connect() as db:
            row = db.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        status = json.loads(row["status"])
        views = []
        for index, entry in enumerate(json.loads(row["result"])["recommendations"]):
            resolved = self._resolve_action(entry["action"])
            views.append({
                "index": index,
                "title": entry["title"],
                "why": entry["why"],
                "action_text": resolved["text"] if resolved else None,
                "status": status.get(str(index)),
            })
        return {"created": row["created"], "source": row["source"], "recommendations": views}

    def _set_analysis_status(self, index, value):
        with self.connect() as db:
            row = db.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                raise ApiError(404, "Es gibt noch keine Analyse")
            entries = json.loads(row["result"])["recommendations"]
            if not 0 <= index < len(entries):
                raise ApiError(404, "Diese Empfehlung gibt es nicht")
            status = json.loads(row["status"])
            if status.get(str(index)):
                raise ApiError(409, "Diese Empfehlung ist schon erledigt")
            status[str(index)] = value
            db.execute("UPDATE analyses SET status = ? WHERE id = ?", (json.dumps(status), row["id"]))
            return entries[index]

    def apply_analysis(self, index):
        with self.connect() as db:
            row = db.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            raise ApiError(404, "Es gibt noch keine Analyse")
        entries = json.loads(row["result"])["recommendations"]
        if not 0 <= index < len(entries):
            raise ApiError(404, "Diese Empfehlung gibt es nicht")
        if json.loads(row["status"]).get(str(index)):
            raise ApiError(409, "Diese Empfehlung ist schon erledigt")
        resolved = self._resolve_action(entries[index]["action"])
        if not resolved:
            raise ApiError(409, "Das passt nicht mehr zum Bestand")
        if resolved["kind"] == "add_word":
            self.add_word(resolved["items"][0]["id"], resolved["word"])
        elif resolved["kind"] == "rename":
            self.update_item(resolved["items"][0]["id"], {"name": resolved["new_name"]})
        else:
            self.move_items([item["id"] for item in resolved["items"]], resolved["place_id"])
        self._set_analysis_status(index, "applied")

    def dismiss_analysis(self, index):
        self._set_analysis_status(index, "dismissed")

    def log_event(self, event_type, q=None, hits=None, item_id=None, place_id=None):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events (at, type, q, hits, item_id, place_id) VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), event_type, q, hits, item_id, place_id),
            )

    def set_setting(self, key, value):
        with self.connect() as db:
            db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def add_session(self, token):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE created < ?", (time.time() - SESSION_DAYS * 86400,))
            db.execute(
                "INSERT INTO sessions (token_hash, created) VALUES (?, ?)",
                (hashlib.sha256(token.encode()).hexdigest(), time.time()),
            )

    def has_session(self, token):
        with self.connect() as db:
            return bool(
                db.execute(
                    "SELECT 1 FROM sessions WHERE token_hash = ? AND created >= ?",
                    (hashlib.sha256(token.encode()).hexdigest(), time.time() - SESSION_DAYS * 86400),
                ).fetchone()
            )

    def export_csv(self):
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(L(
            ["Name", "Auch genannt", "Füllstand oder Zustand", "Notiz", "Adresse", "Platz", "Schrank", "Raum", "Haus oder Grundstück", "Gerade woanders", "Inhalt",
             "Bei wem", "Zurück bis", "Hersteller", "Modell", "Seriennummer", "Kaufdatum", "Garantie bis", "Nächste Wartung", "Dokumente", "Anzahl"],
            ["Name", "Also called", "Stock level or condition", "Note", "Address", "Spot", "Cabinet", "Room", "House or property", "Elsewhere right now", "Contents",
             "With whom", "Back by", "Maker", "Model", "Serial number", "Purchase date", "Warranty until", "Next maintenance", "Documents", "Quantity"],
        ))
        with self.connect() as db:
            rows = db.execute(
                "SELECT i.name, i.synonyms, i.fill, i.note, p.code, p.label, m.name AS map_name, "
                "r.name AS room_name, s.name AS site_name, i.away, replace(i.details, char(10), ' | ') AS details, "
                "i.away_to, i.away_due, i.passport, i.created, i.scale, i.quantity, "
                "(SELECT COUNT(*) FROM documents d WHERE d.item_id = i.id) AS documents "
                "FROM items i JOIN places p ON p.id = i.place_id JOIN maps m ON m.id = p.map_id "
                "JOIN rooms r ON r.id = m.room_id JOIN sites s ON s.id = r.site_id "
                "ORDER BY i.name COLLATE NOCASE"
            ).fetchall()
        for row in rows:
            passport = read_passport(row["passport"])
            values = list(tuple(row)[:13])
            if row["scale"] == "state":
                values[2] = level_word(row)
            values = [*values, *(passport.get(key, "") for key in ("maker", "model", "serial", "bought", "warranty")),
                      next_service(passport, row["created"]), row["documents"] or "", row["quantity"]]
            writer.writerow([csv_safe(value) for value in values])
        return "﻿" + buffer.getvalue()

    def _write_backup(self, target):
        with tempfile.TemporaryDirectory() as tmp:
            copy_path = Path(tmp) / "inventar.sqlite"
            source = self.connect()
            copy = sqlite3.connect(copy_path)
            with copy:
                source.backup(copy)
            copy.close()
            source.close()
            with zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as archive:
                archive.write(copy_path, "inventar.sqlite")
                for path in sorted(self.photo_dir.iterdir()):
                    archive.write(path, f"fotos/{path.name}")
                for path in sorted(self.document_dir.iterdir()):
                    if BACKUP_DOCUMENT.match(f"dokumente/{path.name}"):
                        archive.write(path, f"dokumente/{path.name}")

    def backup_zip(self):
        output = io.BytesIO()
        self._write_backup(output)
        return output.getvalue()

    @property
    def backup_dir(self):
        return self.data_dir / BACKUP_FOLDER

    def _fingerprint(self):
        """Ändert sich nur, wenn sich am Inventar selbst etwas geändert hat."""
        digest = hashlib.sha256()
        with self.connect() as db:
            for table in ("sites", "rooms", "maps", "places", "items", "photos", "trash", "achievements", "documents", "item_log"):
                for row in db.execute(f"SELECT * FROM {table} ORDER BY 1"):
                    digest.update(repr(tuple(row)).encode())
        for path in sorted(self.photo_dir.iterdir()):
            digest.update(path.name.encode())
        for path in sorted(self.document_dir.iterdir()):
            digest.update(path.name.encode())
        return digest.hexdigest()

    def backup_settings(self):
        with self.connect() as db:
            rows = {r["key"]: r["value"] for r in db.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'backup_%'"
            )}
        interval = int(rows.get("backup_interval") or BACKUP_INTERVAL_DEFAULT)
        keep = int(rows.get("backup_keep") or BACKUP_KEEP_DEFAULT)
        return {
            "target": rows.get("backup_mirror", ""),
            "interval": interval if interval in BACKUP_INTERVALS else BACKUP_INTERVAL_DEFAULT,
            "keep": min(max(keep, BACKUP_KEEP_MIN), BACKUP_KEEP_MAX),
            "last": float(rows["backup_last"]) if rows.get("backup_last") else None,
            "fingerprint": rows.get("backup_fingerprint"),
            "error": rows.get("backup_error", ""),
            "target_at": float(rows["backup_target_at"]) if rows.get("backup_target_at") else None,
            "target_error": rows.get("backup_target_error", ""),
            "target_via": rows.get("backup_target_via", ""),
        }

    def _read_keep(self):
        """Wie backup_settings, aber auch vor dem Anlegen der Tabellen nutzbar."""
        try:
            with self.connect() as db:
                row = db.execute("SELECT value FROM settings WHERE key = 'backup_keep'").fetchone()
            return min(max(int(row["value"]), BACKUP_KEEP_MIN), BACKUP_KEEP_MAX) if row else BACKUP_KEEP_DEFAULT
        except (sqlite3.Error, ValueError):
            return BACKUP_KEEP_DEFAULT

    def _is_empty(self):
        with self.connect() as db:
            # Auch der Papierkorb zählt: Daten darin sollen wiederherstellbar bleiben.
            return not db.execute("SELECT 1 FROM rooms LIMIT 1").fetchone() and not db.execute("SELECT 1 FROM trash LIMIT 1").fetchone()

    def _backup_name(self):
        stamp = time.time()
        while True:
            name = f"findling-{time.strftime('%Y-%m-%d-%H%M%S', time.localtime(stamp))}.zip"
            if not (self.backup_dir / name).exists():
                return name
            stamp += 1

    def create_backup(self, label=None):
        """Legt einen Stand an, räumt alte Stände weg und bringt ihn zum Speicherort."""
        self.backup_dir.mkdir(exist_ok=True)
        name = self._backup_name()
        temporary = self.backup_dir / f".{name}.tmp"
        try:
            self._write_backup(temporary)
            temporary.replace(self.backup_dir / name)
        finally:
            temporary.unlink(missing_ok=True)
        self.set_setting("backup_fingerprint", self._fingerprint())
        self.set_setting("backup_last", str(time.time()))
        self._prune_backups(self.backup_dir, self.backup_settings()["keep"])
        self.sync_target()
        return name

    def auto_backup(self):
        """Sichert im eingestellten Takt, aber nur, wenn sich seit dem letzten Stand etwas geändert hat.
        Danach bekommt der Speicherort, was ihm fehlt, auch wenn er zuletzt nicht erreichbar war."""
        try:
            created = None
            if not self._is_empty():
                settings = self.backup_settings()
                due = not settings["last"] or time.time() - settings["last"] >= settings["interval"] * 3600 - 300
                if due and settings["fingerprint"] != self._fingerprint():
                    created = self.create_backup()
                    self.set_setting("backup_error", "")
                    return created
            self.sync_target()
            return created
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            self.set_setting("backup_error", str(error)[:200])
            return None

    @staticmethod
    def _backup_files(folder):
        """Alle Sicherungen eines Ordners, die neueste zuerst. Andere Dateien bleiben unberührt."""
        try:
            files = [p for p in folder.iterdir() if BACKUP_NAME.match(p.name) and p.is_file() and not p.is_symlink()]
        except OSError:
            return []
        return sorted(files, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)

    @staticmethod
    def _prune_backups(folder, keep=BACKUP_KEEP_DEFAULT):
        """Behält die letzten Stände (keep) und die beiden letzten Sicherungen vor einem Update."""
        files = Store._backup_files(folder)
        before = [p for p in files if BACKUP_NAME.match(p.name).group(2)]
        regular = [p for p in files if not BACKUP_NAME.match(p.name).group(2)]
        for path in regular[keep:] + before[BACKUP_KEEP_BEFORE_UPDATE:]:
            path.unlink(missing_ok=True)

    def _write_mirror_conf(self, target, keep):
        conf = self.data_dir / MIRROR_CONF
        if not target:
            conf.unlink(missing_ok=True)
            return
        temporary = self.data_dir / f".{MIRROR_CONF}.tmp"
        temporary.write_text(f"{target}\n{keep}\n")
        temporary.replace(conf)

    def sync_target(self):
        """Bringt die letzten Stände an den Speicherort und hält dort dieselbe Zahl vor."""
        settings = self.backup_settings()
        target, keep = settings["target"], settings["keep"]
        if self.mirror_helper:
            # In Home Assistant darf die App /share nur lesen. Das Kopieren übernimmt der Kopierdienst.
            self._write_mirror_conf(target, keep)
            if target:
                self.set_setting("backup_target_via", "dienst")
            return
        if not target:
            return
        folder = Path(target)
        try:
            if not folder.is_dir():
                raise FileNotFoundError("Der Speicherort ist nicht erreichbar")
            files = self._backup_files(self.backup_dir)
            regular = [p for p in files if not BACKUP_NAME.match(p.name).group(2)][:keep]
            before = [p for p in files if BACKUP_NAME.match(p.name).group(2)][:BACKUP_KEEP_BEFORE_UPDATE]
            for source in regular + before:
                destination = folder / source.name
                if destination.is_file() and destination.stat().st_size == source.stat().st_size:
                    continue
                temporary = folder / f".{source.name}.tmp"
                try:
                    shutil.copy2(source, temporary)
                    temporary.replace(destination)
                finally:
                    temporary.unlink(missing_ok=True)
            self._prune_backups(folder, keep)
            self.set_setting("backup_target_at", str(time.time()))
            self.set_setting("backup_target_error", "")
            self.set_setting("backup_target_via", "app")
        except PermissionError as error:
            self.set_setting("backup_target_error", f"Keine Schreibrechte am Speicherort: {error}"[:200])
        except OSError as error:
            self.set_setting("backup_target_error", f"Speicherort nicht erreichbar: {error}"[:200])

    def _drop_foreign_target(self):
        """Ein Speicherort aus einer Sicherung, den es auf diesem Gerät nicht gibt, wird nicht übernommen."""
        target = self.backup_settings()["target"]
        if not target:
            return
        try:
            self._clean_target(target)
        except ApiError:
            self.set_setting("backup_mirror", "")
            self.set_setting("backup_target_error", "")

    def _helper_status(self):
        """Liest die Meldung des Kopierdienstes: „ok <Zeit>“ oder „fehler <Zeit> <Text>“."""
        try:
            parts = (self.data_dir / MIRROR_STATUS).read_text(encoding="utf-8", errors="replace").strip().split(" ", 2)
            at = float(parts[1]) if len(parts) > 1 else None
            if parts[0] == "ok":
                return at, ""
            return at, (parts[2] if len(parts) > 2 else "Unbekannter Fehler")[:200]
        except (OSError, ValueError, IndexError):
            return None, "Der Kopierdienst hat sich noch nicht gemeldet"

    def target_backups(self, target=None):
        target = target if target is not None else self.backup_settings()["target"]
        if not target:
            return []
        entries = []
        for path in self._backup_files(Path(target)):
            try:
                info = path.stat()
            except OSError:
                continue
            entries.append({"name": path.name, "size": info.st_size, "created": info.st_mtime,
                            "before_version": BACKUP_NAME.match(path.name).group(2)})
        return entries

    def list_backups(self):
        settings = self.backup_settings()
        entries = []
        for path in self._backup_files(self.backup_dir):
            info = path.stat()
            entries.append({"name": path.name, "size": info.st_size, "created": info.st_mtime,
                            "before_version": BACKUP_NAME.match(path.name).group(2)})
        target_at, target_error = settings["target_at"], settings["target_error"]
        if settings["target"] and settings["target_via"] == "dienst":
            target_at, target_error = self._helper_status()
        return {
            "backups": entries,
            "error": settings["error"],
            "last": settings["last"],
            "next": settings["last"] + settings["interval"] * 3600 if settings["last"] else None,
            "interval": settings["interval"],
            "intervals": list(BACKUP_INTERVALS),
            "keep": settings["keep"],
            "keep_range": [BACKUP_KEEP_MIN, BACKUP_KEEP_MAX],
            "target": settings["target"],
            "target_at": target_at,
            "target_error": target_error,
            "target_backups": self.target_backups(settings["target"]),
            "target_root": str(self.target_root) if self.target_root else "",
            "empty": self._is_empty(),
            "folder": str(self.backup_dir),
        }

    def _clean_target(self, value):
        value = clean_text(value, "Speicherort", 500)
        if not value:
            return ""
        folder = Path(value).expanduser()
        if self.target_root:
            root = Path(self.target_root).resolve()
            resolved = folder.resolve()
            if root not in resolved.parents:
                raise ApiError(400, f"Wähle einen Ordner unter {self.target_root}")
            folder = resolved
        if not folder.is_dir():
            raise ApiError(400, "Diesen Ordner gibt es nicht")
        if Path(self.data_dir).resolve() in [folder.resolve(), *folder.resolve().parents]:
            raise ApiError(400, "Der Speicherort muss außerhalb der App-Daten liegen")
        if not self.mirror_helper:
            try:
                with tempfile.NamedTemporaryFile(dir=folder):
                    pass
            except OSError:
                raise ApiError(400, "In diesen Ordner darf die App nicht schreiben")
        return str(folder)

    def set_backup_settings(self, body):
        if not isinstance(body, dict):
            raise ApiError(400, "Ungültige Daten")
        changes = {}
        if "target" in body or "mirror" in body:
            changes["backup_mirror"] = self._clean_target(body.get("target", body.get("mirror")))
        if "interval" in body:
            if body["interval"] not in BACKUP_INTERVALS:
                raise ApiError(400, "Ungültiger Takt")
            changes["backup_interval"] = str(body["interval"])
        if "keep" in body:
            keep = body["keep"]
            if not isinstance(keep, int) or isinstance(keep, bool) or not BACKUP_KEEP_MIN <= keep <= BACKUP_KEEP_MAX:
                raise ApiError(400, f"Zwischen {BACKUP_KEEP_MIN} und {BACKUP_KEEP_MAX} Stände")
            changes["backup_keep"] = str(keep)
        for key, value in changes.items():
            self.set_setting(key, value)
        if "backup_mirror" in changes:
            self.set_setting("backup_target_error", "")
            self.set_setting("backup_target_at", "")
            self.set_setting("backup_target_via", "")
        self._prune_backups(self.backup_dir, self.backup_settings()["keep"])
        self.sync_target()
        return self.list_backups()

    def target_folders(self):
        """Ordner, die als Speicherort in Frage kommen. In Home Assistant: alles unter /share, zwei Ebenen tief."""
        if not self.target_root:
            return []
        root = Path(self.target_root)
        found = []
        try:
            for first in sorted(root.iterdir()):
                if first.name.startswith(".") or not first.is_dir():
                    continue
                found.append(str(first))
                try:
                    for second in sorted(first.iterdir()):
                        if not second.name.startswith(".") and second.is_dir():
                            found.append(str(second))
                except OSError:
                    continue
        except OSError:
            return []
        return found[:200]

    def restore_backup(self, name, source="local"):
        """Spielt einen Stand ein, auch direkt vom Speicherort. Vorher wird der aktuelle Stand gesichert."""
        if not BACKUP_NAME.match(name or ""):
            raise ApiError(404, "Diese Sicherung gibt es nicht")
        if source == "target":
            target = self.backup_settings()["target"]
            if not target:
                raise ApiError(404, "Es ist kein Speicherort eingerichtet")
            path = Path(target) / name
            if path.is_symlink():
                raise ApiError(404, "Diese Sicherung gibt es nicht")
        else:
            path = self.backup_dir / name
        if not path.is_file():
            raise ApiError(404, "Diese Sicherung gibt es nicht")
        return self._restore_file(path)

    def restore_upload(self, chunks):
        """Übernimmt eine hochgeladene Sicherung, zum Beispiel vom Umzug von einem anderen Rechner."""
        self.backup_dir.mkdir(exist_ok=True)
        temporary = self.backup_dir / f".upload-{new_id()}.tmp"
        try:
            with temporary.open("wb") as output:
                for chunk in chunks:
                    output.write(chunk)
            result = self._restore_file(temporary)
            stamp = int(time.time())
            while True:
                # Die Sicherung vor dem Einspielen trägt oft dieselbe Sekunde, sie darf nicht überschrieben werden.
                target = self.backup_dir / f"findling-{time.strftime('%Y-%m-%d-%H%M%S', time.localtime(stamp))}.zip"
                if not target.exists():
                    break
                stamp += 1
            temporary.replace(target)
            return result
        finally:
            temporary.unlink(missing_ok=True)

    def _restore_file(self, path):
        with tempfile.TemporaryDirectory(dir=self.data_dir) as tmp:
            folder = Path(tmp)
            try:
                with zipfile.ZipFile(path) as archive:
                    infos = archive.infolist()
                    if len(infos) > MAX_BACKUP_ENTRIES or sum(info.file_size for info in infos) > MAX_BACKUP_UPLOAD * 2:
                        raise ApiError(400, "Diese Sicherung ist zu groß")
                    # Nur bekannte Namen werden entpackt, sonst könnte eine Datei Pfade außerhalb erreichen.
                    members = [
                        m for m in archive.namelist()
                        if m == "inventar.sqlite" or BACKUP_PHOTO.match(m) or BACKUP_DOCUMENT.match(m)
                    ]
                    if "inventar.sqlite" not in members:
                        raise ApiError(400, "Das ist keine gültige Sicherung")
                    for member in members:
                        archive.extract(member, folder)
            except zipfile.BadZipFile:
                raise ApiError(400, "Die Sicherung ist beschädigt")
            check = sqlite3.connect(f"{(folder / 'inventar.sqlite').resolve().as_uri()}?immutable=1", uri=True)
            try:
                healthy = check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                has_tables = check.execute("SELECT 1 FROM sqlite_master WHERE name = 'places'").fetchone()
            except sqlite3.Error:
                healthy = has_tables = False
            finally:
                check.close()
            if not healthy or not has_tables:
                raise ApiError(400, "Die Sicherung ist beschädigt")
            # Eine frisch eingerichtete, leere App muss vorher nicht gesichert werden.
            safety = None if self._is_empty() else self.create_backup()
            with self.connect() as db:
                sessions = [tuple(row) for row in db.execute("SELECT token_hash, created FROM sessions")]
                device = [tuple(row) for row in db.execute(
                    f"SELECT key, value FROM settings WHERE key IN ({', '.join('?' for _ in BACKUP_SETTING_KEYS)})",
                    BACKUP_SETTING_KEYS,
                )]
            source = sqlite3.connect(folder / "inventar.sqlite")
            target = self.connect()
            try:
                source.backup(target)
            finally:
                source.close()
                target.close()
            restored = folder / "fotos"
            names = {p.name for p in restored.iterdir()} if restored.exists() else set()
            for existing in self.photo_dir.iterdir():
                if existing.name not in names:
                    existing.unlink(missing_ok=True)
            for filename in names:
                shutil.copy2(restored / filename, self.photo_dir / filename)
            restored = folder / "dokumente"
            names = {p.name for p in restored.iterdir()} if restored.exists() else set()
            for existing in self.document_dir.iterdir():
                if existing.name not in names:
                    existing.unlink(missing_ok=True)
            for filename in names:
                shutil.copy2(restored / filename, self.document_dir / filename)
        self._prepare()
        self.set_setting("app_version", APP_VERSION)
        with self.connect() as db:
            db.executemany("INSERT OR IGNORE INTO sessions (token_hash, created) VALUES (?, ?)", sessions)
            db.execute("DELETE FROM settings WHERE key = 'backup_fingerprint'")
            # Hat dieses Gerät Speicherort, Takt oder Aufbewahrung schon festgelegt, bleibt das.
            # Sonst gelten die Werte aus der Sicherung, etwa nach einem Verlust auf einem frischen Gerät.
            if device:
                keys = [key for key, _ in device]
                db.execute(f"DELETE FROM settings WHERE key IN ({', '.join('?' for _ in keys)})", keys)
                db.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", device)
        self._drop_foreign_target()
        return {"safety": safety}

    # Massenimport

    def import_table(self, raw, apply=False):
        """Prüft eine Tabelle und übernimmt sie auf Wunsch. Mit einem Fehler wird nichts übernommen."""
        records, columns, ignored = read_import_table(raw)
        result = self._import(records, apply=False)
        result.update({"ignored": ignored, "columns": columns, "applied": False, "backup": None})
        if not apply or result["errors"]:
            return result
        # Vor einem großen Import den alten Stand sichern, damit er sich zurückholen lässt.
        try:
            result["backup"] = None if self._is_empty() else self.create_backup()
        except (OSError, sqlite3.Error, zipfile.BadZipFile):
            raise ApiError(500, "Die Sicherung vor dem Import ist fehlgeschlagen. Es wurde nichts übernommen.")
        result.update(self._import(records, apply=True))
        result["applied"] = True
        return result

    def _import(self, records, apply):
        now = time.time()
        counts = {"rows": len(records), "sites": 0, "rooms": 0, "maps": 0, "places": 0, "items_new": 0, "items_updated": 0}
        errors = []
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            sites = {normalize_name(row["name"]): row["id"] for row in db.execute("SELECT id, name FROM sites ORDER BY created DESC")}
            default_site = db.execute("SELECT id FROM sites ORDER BY created LIMIT 1").fetchone()["id"]
            rooms = {(row["site_id"], normalize_name(row["name"])): dict(row) for row in db.execute("SELECT id, site_id, name, code FROM rooms")}
            maps = {(row["room_id"], normalize_name(row["name"])): dict(row) for row in db.execute("SELECT id, room_id, name, code FROM maps ORDER BY created DESC")}
            places = {(row["map_id"], normalize_name(row["label"])): row["id"] for row in db.execute("SELECT id, map_id, label FROM places ORDER BY created DESC")}
            by_code = {row["code"].upper(): row["id"] for row in db.execute("SELECT id, code FROM places")}
            items = {(row["place_id"], normalize_name(row["name"])): dict(row) for row in db.execute("SELECT * FROM items ORDER BY created DESC")}
            created_items, updated_items = set(), set()
            new_places = {}

            def find_place(cells):
                code = cells.get("code", "")
                if code and code.upper() in by_code:
                    return by_code[code.upper()]
                if code and not (cells.get("room") or cells.get("map")):
                    raise ApiError(400, f"Die Adresse {code[:20]} gibt es nicht")
                room_name = clean_text(cells.get("room"), "Raum", 60, required=True)
                map_name = clean_text(cells.get("map"), "Schrank oder Regal", 60, required=True)
                site_name = clean_text(cells.get("site"), "Haus oder Grundstück", 60)
                site_id = default_site
                if site_name:
                    site_id = sites.get(normalize_name(site_name))
                    if not site_id:
                        site_id = new_id()
                        db.execute("INSERT INTO sites (id, name, created) VALUES (?, ?, ?)", (site_id, site_name, now))
                        sites[normalize_name(site_name)] = site_id
                        counts["sites"] += 1
                room = rooms.get((site_id, normalize_name(room_name)))
                if not room:
                    room = {"id": new_id(), "site_id": site_id, "name": room_name, "code": self._free_room_code(db, room_name)}
                    db.execute(
                        "INSERT INTO rooms (id, site_id, name, code, plan_photo, created) VALUES (?, ?, ?, ?, NULL, ?)",
                        (room["id"], site_id, room_name, room["code"], now),
                    )
                    rooms[(site_id, normalize_name(room_name))] = room
                    counts["rooms"] += 1
                map_ = maps.get((room["id"], normalize_name(map_name)))
                if not map_:
                    taken = {row["code"] for row in db.execute("SELECT code FROM maps WHERE room_id = ?", (room["id"],))}
                    base = short_code(map_name) or "S"
                    code, number = base, 2
                    while code in taken:
                        code = f"{base[:4]}{number}"
                        number += 1
                    map_ = {"id": new_id(), "room_id": room["id"], "name": map_name, "code": code}
                    db.execute(
                        "INSERT INTO maps (id, room_id, name, code, photo, plan_x, plan_y, created) VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?)",
                        (map_["id"], room["id"], map_name, code, now),
                    )
                    maps[(room["id"], normalize_name(map_name))] = map_
                    counts["maps"] += 1
                label = clean_text(cells.get("place"), "Platz", 80)
                place_id = places.get((map_["id"], normalize_name(label)))
                if not place_id:
                    place_id = new_id()
                    code = self._free_place_code(db, f"{room['code']}-{map_['code']}")
                    # Erst als ganzer Schrank. Am Ende verteilt ein Raster die neuen Plätze, die Rahmen lassen sich später anpassen.
                    db.execute(
                        "INSERT INTO places (id, map_id, code, label, x, y, w, h, surveyed, created, surveyed_at) "
                        "VALUES (?, ?, ?, ?, 0, 0, 1, 1, 1, ?, ?)",
                        (place_id, map_["id"], code, label, now, now),
                    )
                    places[(map_["id"], normalize_name(label))] = place_id
                    by_code[code.upper()] = place_id
                    new_places.setdefault(map_["id"], []).append(place_id)
                    counts["places"] += 1
                return place_id

            def item_fields(cells, existing):
                fields = {}
                level = cells.get("fill", "")
                scale = None
                if level:
                    found = IMPORT_LEVELS.get(normalize_name(level))
                    if not found:
                        raise ApiError(400, f"Unbekannter Füllstand oder Zustand: {level[:30]}")
                    fields["fill"], scale = found
                device = normalize_name(cells.get("device", ""))
                if device in IMPORT_YES:
                    scale = "state"
                elif device in IMPORT_NO:
                    scale = "fill"
                elif device:
                    raise ApiError(400, "Gerät: bitte ja oder nein eintragen")
                if scale:
                    fields["scale"] = scale
                if cells.get("quantity"):
                    fields["quantity"] = clean_quantity(cells["quantity"].replace("x", "").replace("×", "").strip())
                if cells.get("note"):
                    fields["note"] = clean_text(cells["note"], "Notiz", 200)
                if cells.get("synonyms"):
                    fields["synonyms"] = clean_text(cells["synonyms"], "Auch genannt", 200)
                if cells.get("details"):
                    fields["details"] = clean_details(re.split(r"\s*\|\s*|\n", cells["details"]))
                change = {key: cells[key] for key in ("maker", "model", "serial") if cells.get(key)}
                for key, label in (("bought", "Kaufdatum"), ("warranty", "Garantie bis")):
                    if cells.get(key):
                        change[key] = import_date(cells[key], label)
                if change:
                    passport = clean_passport(change, read_passport(existing["passport"]) if existing else {})
                    fields["passport"] = json.dumps(passport, ensure_ascii=False, sort_keys=True)
                return fields

            for line, cells in records:
                try:
                    name = clean_text(cells.get("name"), "Name", 120, required=True)
                    place_id = find_place(cells)
                    key = (place_id, normalize_name(name))
                    existing = items.get(key)
                    fields = item_fields(cells, existing)
                    if existing:
                        fields["updated"] = now
                        db.execute(
                            f"UPDATE items SET {', '.join(f'{column} = ?' for column in fields)} WHERE id = ?",
                            (*fields.values(), existing["id"]),
                        )
                        existing.update(fields)
                        if existing["id"] not in created_items:
                            updated_items.add(existing["id"])
                    else:
                        record = {
                            "id": new_id(), "place_id": place_id, "name": name, "synonyms": "", "fill": "ok", "scale": "fill", "quantity": 1,
                            "note": "", "details": "", "passport": "", "missing": 0, "last_seen": now, "created": now, "updated": now,
                            **fields,
                        }
                        db.execute(
                            f"INSERT INTO items ({', '.join(record)}) VALUES ({', '.join('?' for _ in record)})",
                            tuple(record.values()),
                        )
                        items[key] = record
                        created_items.add(record["id"])
                except ApiError as error:
                    errors.append({"line": line, "message": error.message})
                    if len(errors) >= IMPORT_MAX_ERRORS:
                        break
            for ids in new_places.values():
                columns = math.ceil(math.sqrt(len(ids)))
                rows = math.ceil(len(ids) / columns)
                for index, place_id in enumerate(ids):
                    db.execute(
                        "UPDATE places SET x = ?, y = ?, w = ?, h = ? WHERE id = ?",
                        ((index % columns) / columns + 0.01, (index // columns) / rows + 0.01,
                         1 / columns - 0.02, 1 / rows - 0.02, place_id),
                    )
            counts["items_new"] = len(created_items)
            counts["items_updated"] = len(updated_items)
            if apply and not errors:
                db.commit()
            else:
                db.rollback()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
        return {**counts, "errors": errors}

    # Teilen

    def shopping_list(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key = 'shopping_extra'").fetchone()
        return json.loads(row["value"]) if row else []

    def add_to_shopping(self, name):
        name = clean_text(name, "Name", 120, required=True)
        extra = self.shopping_list()
        if normalize_name(name) not in {normalize_name(entry) for entry in extra}:
            extra.append(name)
            self.set_setting("shopping_extra", json.dumps(extra, ensure_ascii=False))
        return extra

    def remove_from_shopping(self, name):
        extra = [entry for entry in self.shopping_list() if entry != name]
        self.set_setting("shopping_extra", json.dumps(extra, ensure_ascii=False))
        return extra

    def shopping_pdf(self):
        """Die Mitbringliste als PDF zum Ansehen, Drucken oder Weitergeben vom Telefon aus."""
        with self.connect() as db:
            low = db.execute(
                "SELECT name, fill, note FROM items WHERE fill IN ('wenig', 'leer') AND scale != 'state' ORDER BY name COLLATE NOCASE"
            ).fetchall()
        fill_word = {"wenig": L("wenig", "low"), "leer": L("leer", "empty")}
        entries = [(row["name"], ", ".join(filter(None, (fill_word[row["fill"]], row["note"])))) for row in low]
        entries += [(name, "") for name in self.shopping_list()]
        width = PDF_W - 2 * PDF_MARGIN
        stand = time.strftime(L("%d.%m.%Y, %H:%M", "%d/%m/%Y, %H:%M"))
        pages, ops, y = [], [], 0.0

        def text(x, top, size, value, bold=False, gray=0.0):
            ops.append(b"%.2f g BT /%s %d Tf %.2f %.2f Td (" % (gray, b"F2" if bold else b"F1", size, x, PDF_H - top)
                       + pdf_text(value) + b") Tj ET")

        def new_page():
            nonlocal ops, y
            if ops:
                pages.append(ops)
            ops, y = [], PDF_MARGIN

        new_page()
        text(PDF_MARGIN, y + 22, 24, L("Mitbringliste", "Shopping list"), bold=True)
        text(PDF_MARGIN, y + 42, 10, L(f"Stand {stand} · aus findling", f"As of {stand} · from findling"), gray=0.45)
        y += 70
        if not entries:
            text(PDF_MARGIN, y + 12, 12, L("Gerade fehlt nichts.", "Nothing is missing right now."), gray=0.4)
        for name, detail in entries:
            if y + 34 > PDF_H - PDF_MARGIN - 24:
                new_page()
            ops.append(b"0.3 G 0.8 w %.2f %.2f 11 11 re S" % (PDF_MARGIN, PDF_H - y - 13))
            text(PDF_MARGIN + 22, y + 11, 13, pdf_fit(name, 13, width - 22))
            y += 17
            if detail:
                text(PDF_MARGIN + 22, y + 9, 9, pdf_fit(detail, 9, width - 22), gray=0.45)
                y += 13
            y += 9
        pages.append(ops)
        for number, page in enumerate(pages, 1):
            if len(pages) > 1:
                footer = L(f"Seite {number} von {len(pages)}", f"Page {number} of {len(pages)}")
                page.append(b"0.5 g BT /F1 8 Tf %.2f %.2f Td (" % (PDF_MARGIN, 24) + pdf_text(footer) + b") Tj ET")
        return pdf_document(pages)

    def share_html(self):
        """Der Bestand als eine einzige Datei: lesbar auch ohne Skript, mit Suche, wo Skripte laufen."""
        state = self.state()
        esc = html.escape
        rooms = {room["id"]: room for room in state["rooms"]}
        sites = {site["id"]: site for site in state["sites"]}
        maps = {map_["id"]: map_ for map_ in state["maps"]}
        places = {place["id"]: place for place in state["places"]}

        def where(item):
            place = places[item["place_id"]]
            map_ = maps[place["map_id"]]
            room = rooms[map_["room_id"]]
            parts = [sites[room["site_id"]]["name"]] if len(sites) > 1 else []
            return " › ".join([*parts, room["name"], map_["name"], place["label"] or place["code"]])

        low = [item for item in state["items"] if runs_low(item)]
        rows = []
        for item in state["items"]:
            extra = []
            if item["fill"] in ("wenig", "leer"):
                extra.append(level_word(item))
            if item["away"]:
                away = f"{item['away']} ({item['away_to']})" if item["away_to"] else item["away"]
                extra.append(L(f"gerade: {away}", f"currently: {away}"))
            contents = item["details"].replace("\n", " · ")
            passport = item["passport"]
            device = " · ".join(passport[key] for key in ("maker", "model") if passport.get(key))
            search = " ".join((item["name"], item["synonyms"], item["note"], contents, device, where(item))).lower()
            rows.append(
                f'<li data-s="{esc(search)}"><strong>{esc(quantity_name(item))}</strong>'
                + (f" <em>{esc(', '.join(extra))}</em>" if extra else "")
                + (f'<br><small>{esc(item["note"])}</small>' if item["note"] else "")
                + (f"<br><small>{esc(device)}</small>" if device else "")
                + (f'<br><small>{L("Inhalt", "Contents")}: {esc(contents)}</small>' if contents else "")
                + f"<br><small>{esc(where(item))} · {esc(places[item['place_id']]['code'])}</small></li>"
            )
        fill_word = {"wenig": L("wenig", "low"), "leer": L("leer", "empty")}
        wanted = [f"{esc(item['name'])} ({esc(fill_word[item['fill']])})" for item in low] + [esc(entry) for entry in self.shopping_list()]
        shopping = (
            f"<h2>{L('Bitte mitbringen', 'Please bring')}</h2><ul>" + "".join(f"<li>{entry}</li>" for entry in wanted) + "</ul>"
            if wanted else ""
        )
        surveyed = sum(1 for place in state["places"] if place["surveyed"])
        stand = time.strftime(L("%d.%m.%Y, %H:%M", "%d/%m/%Y, %H:%M"))
        intro = L(
            f"Stand {stand}. {len(state['items'])} Einträge, {surveyed} von {len(state['places'])} Plätzen vollständig erfasst. "
            "Fehlt etwas hier, kann es trotzdem vorhanden sein, solange nicht alles erfasst ist.",
            f"As of {stand}. {len(state['items'])} items, {surveyed} of {len(state['places'])} spots fully recorded. "
            "If something is missing here, it may still exist as long as not everything is recorded.",
        )
        return f"""<!doctype html>
<html lang="{LANGUAGE}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>findling, {L("Stand", "as of")} {esc(stand)}</title>
<style>
body{{margin:0 auto;max-width:640px;padding:16px;background:#1d201f;color:#f1f3f1;font:16px/1.4 -apple-system,Segoe UI,Roboto,Arial,sans-serif}}
h1{{font-size:1.5rem;margin:.2em 0}}h2{{font-size:1.1rem;margin:1.2em 0 .4em}}
ul{{list-style:none;margin:0;padding:0}}li{{padding:10px 0;border-top:1px solid #3f4141}}
small{{color:#a3a9a6}}em{{color:#26ff00;font-style:normal;font-size:.85em}}
input{{box-sizing:border-box;width:100%;padding:12px;background:#282b2a;border:1px solid #3f4141;border-radius:10px;color:inherit;font:inherit}}
input:focus{{outline:2px solid #26ff00}}
</style></head><body>
<h1>findling</h1>
<p><em>{L("Hab ich. Weiß ich. Find ich.", "Got it. Know it. Find it.")}</em></p>
<p><small>{esc(intro)}</small></p>
{shopping}
<h2>{L("Bestand", "Inventory")}</h2>
<input id="q" type="search" placeholder="{L("Suchen", "Search")}" aria-label="{L("Suchen", "Search")}" hidden>
<ul id="list">{"".join(rows)}</ul>
<script>
var q=document.getElementById('q'),rows=document.querySelectorAll('#list li');q.hidden=false;
q.addEventListener('input',function(){{var t=q.value.toLowerCase().split(/\\s+/).filter(Boolean);
rows.forEach(function(r){{var s=r.getAttribute('data-s');r.hidden=!t.every(function(w){{return s.indexOf(w)>=0}})}})}});
</script>
</body></html>
"""

    def _update(self, table, record_id, fields):
        with self.connect() as db:
            if fields:
                assignments = ", ".join(f"{name} = ?" for name in fields)
                db.execute(
                    f"UPDATE {table} SET {assignments} WHERE id = ?",
                    (*fields.values(), record_id),
                )
            row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()
        if not row:
            raise ApiError(404, "Eintrag nicht gefunden")
        return dict(row)


class PinGuard:
    """Bremst das Durchprobieren der PIN."""

    def __init__(self):
        self.lock = threading.Lock()
        self.failures = 0
        self.locked_until = 0.0

    def check(self, supplied, pin):
        with self.lock:
            if time.time() < self.locked_until:
                raise ApiError(429, "Zu viele Versuche, bitte eine Minute warten")
            if hmac.compare_digest(str(supplied).encode(), pin.encode()):
                self.failures = 0
                return True
            self.failures += 1
            if self.failures >= MAX_PIN_FAILURES:
                self.failures = 0
                self.locked_until = time.time() + PIN_LOCK_SECONDS
            return False


class Handler(BaseHTTPRequestHandler):
    server_version = "findling"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = SOCKET_TIMEOUT_SECONDS  # Hängende Verbindungen sollen keine Fäden binden.

    @property
    def store(self):
        return self.server.store

    def log_message(self, format, *args):
        if self.server.verbose:
            super().log_message(format, *args)

    # Eingang

    def do_GET(self):
        self.dispatch("GET")

    def do_HEAD(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PATCH(self):
        self.dispatch("PATCH")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def dispatch(self, method):
        self.body_read = False
        try:
            self.check_client()
            path = urlparse(self.path).path
            if self.server.gate_only:
                self.handle_gate(path)
            elif path.startswith("/api/"):
                self.handle_api(method, path)
            elif path == CERT_DOWNLOAD and method == "GET":
                self.send_certificate()
            elif path.startswith("/fotos/") and method == "GET":
                self.require_auth()
                self.send_photo(path[len("/fotos/"):])
            elif method == "GET":
                self.send_static(path)
            else:
                raise ApiError(405, "Nicht erlaubt")
            # Ungelesene Daten würden sonst als Anfang der nächsten Anfrage gelten.
            if not self.body_read:
                self.read_body(MAX_JSON_BYTES)
        except ApiError as error:
            self.close_connection = True
            self.send_json({"error": error.message}, error.status)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception as error:  # Der Server soll bei einem Fehler weiterlaufen.
            self.log_error("Fehler: %r", error)
            self.close_connection = True
            self.send_json({"error": "Interner Fehler"}, 500)

    def check_client(self):
        if self.server.ingress_peer:
            # Hinter dem Ingress prüft Home Assistant die Anmeldung. Das gilt nur für genau diesen Absender.
            if self.client_address[0] != self.server.ingress_peer:
                raise ApiError(403, "Anfrage abgelehnt")
            return
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if host not in self.server.allowed_hosts:
            raise ApiError(403, "Unbekannter Rechnername")

    def handle_gate(self, path):
        """Der unverschlüsselte Eingang gibt nur das Zertifikat heraus und leitet sonst auf HTTPS um."""
        if path == CERT_DOWNLOAD and self.command in ("GET", "HEAD"):
            return self.send_certificate()
        self.send_bytes(b"", "text/plain; charset=utf-8", {"Location": f"{self.server.gate_target}/"}, status=308)

    def require_auth(self):
        if self.server.pin and not self.is_authenticated():
            raise ApiError(401, "PIN erforderlich")

    def is_authenticated(self):
        if not self.server.pin:
            return True
        jar = cookies.SimpleCookie(self.headers.get("Cookie") or "")
        morsel = jar.get(SESSION_COOKIE)
        return bool(morsel and self.store.has_session(morsel.value))

    def body_chunks(self, limit):
        """Liefert den Rumpf stückweise. Hinter dem Ingress kommt er oft ohne Längenangabe."""
        self.body_read = True
        encoding = (self.headers.get("Transfer-Encoding") or "").strip().lower()
        declared = self.headers.get("Content-Length")
        if encoding:
            # Beide Angaben zugleich oder andere Kodierungen sind der klassische Weg, Anfragen zu schmuggeln.
            if encoding != "chunked" or declared is not None:
                raise ApiError(400, "Ungültige Anfrage")
            yield from self._chunked_body(limit)
            return
        try:
            length = int(declared or 0)
        except ValueError:
            raise ApiError(400, "Ungültige Länge")
        if length < 0 or length > limit:
            raise ApiError(413, "Die Daten sind zu groß")
        while length > 0:
            chunk = self.rfile.read(min(length, 1024 * 1024))
            if not chunk:
                raise ApiError(400, "Die Daten kamen nicht vollständig an")
            length -= len(chunk)
            yield chunk

    def _chunked_body(self, limit):
        total = 0
        while True:
            line = self.rfile.readline(1024)
            try:
                size = int(line.split(b";")[0].strip(), 16)
            except ValueError:
                raise ApiError(400, "Ungültige Anfrage")
            if size < 0:
                raise ApiError(400, "Ungültige Anfrage")
            if size == 0:
                while self.rfile.readline(1024) not in (b"\r\n", b"\n", b""):
                    pass
                return
            total += size
            if total > limit:
                raise ApiError(413, "Die Daten sind zu groß")
            left = size
            while left > 0:
                chunk = self.rfile.read(min(left, 1024 * 1024))
                if not chunk:
                    raise ApiError(400, "Die Daten kamen nicht vollständig an")
                left -= len(chunk)
                yield chunk
            self.rfile.readline(8)

    def read_body(self, limit):
        return b"".join(self.body_chunks(limit))

    def read_json(self):
        try:
            body = json.loads(self.read_body(MAX_JSON_BYTES) or b"{}")
        except ValueError:
            raise ApiError(400, "Ungültiges JSON")
        if not isinstance(body, dict):
            raise ApiError(400, "Ungültige Daten")
        return body

    # API

    def handle_api(self, method, path):
        # Eigener Kopf: Fremde Webseiten können ihn ohne CORS-Freigabe nicht setzen.
        if method != "GET" and self.headers.get("X-Werkstatt") != "1":
            raise ApiError(403, "Anfrage abgelehnt")

        if path == "/api/session" and method == "GET":
            return self.send_json(
                {"pin_required": bool(self.server.pin), "authenticated": self.is_authenticated()}
            )
        if path == "/api/login" and method == "POST":
            return self.login()

        self.require_auth()
        parts = path.strip("/").split("/")[1:]
        resource = parts[0] if parts else ""
        record_id = parts[1] if len(parts) > 1 else None
        action = parts[2] if len(parts) > 2 else None
        store = self.store

        if resource == "state" and method == "GET":
            state = store.state()
            state["server"] = self.server.info()
            state["shopping_extra"] = store.shopping_list()
            state["recognition"] = {
                "installed": recognition.sdk_installed(),
                "configured": recognition.is_configured(store.data_dir),
                "can_set_key": self.is_admin_client() and not self.server.ha,
                "chat_prompt": recognition.chat_prompt(),
                "chat_retry": recognition.chat_retry(),
            }
            return self.send_json(state)
        if resource == "export.csv" and method == "GET":
            return self.send_bytes(
                store.export_csv().encode("utf-8"),
                "text/csv; charset=utf-8",
                {"Content-Disposition": 'attachment; filename="findling-bestand.csv"'},
            )
        if resource == "backup.zip" and method == "GET":
            stamp = time.strftime("%Y-%m-%d")
            return self.send_bytes(
                store.backup_zip(),
                "application/zip",
                {"Content-Disposition": f'attachment; filename="findling-sicherung-{stamp}.zip"'},
            )
        if resource == "convert-image" and method == "POST":
            return self.send_bytes(heic_to_jpeg(self.read_body(MAX_PHOTO_BYTES)), "image/jpeg")
        if resource == "backups":
            return self.handle_backups(method, record_id, action)
        if resource == "share.html" and method == "GET":
            stamp = time.strftime("%Y-%m-%d")
            return self.send_bytes(
                store.share_html().encode("utf-8"),
                "text/html; charset=utf-8",
                {"Content-Disposition": f'attachment; filename="findling-bestand-{stamp}.html"'},
            )
        if resource == "import-vorlage.csv" and method == "GET":
            return self.send_bytes(
                import_template().encode("utf-8"), "text/csv; charset=utf-8",
                {"Content-Disposition": f'attachment; filename="findling-{L("importvorlage", "import-template")}.csv"'},
            )
        if resource == "import" and method == "POST":
            apply = "apply=1" in urlparse(self.path).query.split("&")
            return self.send_json(store.import_table(self.read_body(MAX_IMPORT_BYTES), apply))
        if resource == "mitbringliste.pdf" and method == "GET":
            stamp = time.strftime("%Y-%m-%d")
            name = L("mitbringliste", "shopping-list")
            return self.send_bytes(
                store.shopping_pdf(), "application/pdf",
                {"Content-Disposition": f'inline; filename="findling-{name}-{stamp}.pdf"'}, csp=DOCUMENT_CSP_PDF,
            )
        if resource == "preferences" and method == "PATCH":
            return self.send_json(store.set_preferences(self.read_json()))
        if resource == "shopping" and method == "POST":
            return self.send_json({"extra": store.add_to_shopping(self.read_json().get("name"))})
        if resource == "shopping" and method == "DELETE":
            return self.send_json({"extra": store.remove_from_shopping(self.read_json().get("name"))})
        if resource == "trash":
            if method == "GET" and not record_id:
                return self.send_json(store.list_trash())
            if method == "POST" and record_id and action == "restore":
                return self.send_json(store.restore_trash(record_id, self.read_json().get("parent_id")))
            if method == "DELETE":
                store.delete_trash(record_id)
                return self.send_json({"ok": True})
            raise ApiError(404, "Unbekannte Adresse")
        if resource == "report" and method == "GET":
            return self.send_json(store.report())
        if resource == "report" and method == "POST" and record_id == "dismiss":
            store.dismiss_recommendation(self.read_json().get("id"))
            return self.send_json({"ok": True})
        if resource == "report" and method == "POST" and record_id == "restore":
            self.read_json()
            store.restore_recommendations()
            return self.send_json({"ok": True})
        if resource == "analysis" and method == "POST":
            return self.handle_analysis(record_id, action)
        if resource == "items" and method == "POST" and record_id == "batch":
            return self.send_json(store.batch_items(self.read_json()))
        if resource == "items" and method == "POST" and record_id == "move":
            body = self.read_json()
            return self.send_json(store.move_items(body.get("item_ids"), body.get("place_id")))
        if resource == "items" and method == "POST" and action == "word":
            return self.send_json(store.add_word(record_id, self.read_json().get("word")))
        if resource == "items" and method == "POST" and action == "service":
            return self.send_json(store.service_done(record_id, self.read_json()))
        if resource == "items" and method == "POST" and action == "log":
            return self.send_json(store.add_log(record_id, self.read_json()), 201)
        if resource == "items" and method == "POST" and action == "documents":
            query = dict(p.split("=", 1) for p in urlparse(self.path).query.split("&") if "=" in p)
            name = unquote(self.headers.get("X-Datei-Name") or "")[:300]
            data = self.read_body(MAX_DOCUMENT_BYTES)
            return self.send_json(store.add_document(record_id, data, query.get("kind"), name), 201)
        if resource == "log" and method == "DELETE" and record_id:
            return self.send_json(store.delete_log(record_id))
        if resource == "documents" and record_id and not action:
            if method == "GET":
                return self.send_document(record_id)
            if method == "PATCH":
                return self.send_json(store.update_document(record_id, self.read_json()))
            if method == "DELETE":
                return self.send_json({"ok": True, "trash_id": store.delete_document(record_id)})
        if resource == "photos" and method == "POST" and action == "recognize":
            return self.recognize(record_id)
        if resource == "photos" and method == "POST" and action == "chat-answer":
            return self.import_chat_answer(record_id)
        if resource == "recognition-key":
            return self.handle_recognition_key(method)
        if resource == "photos" and method == "POST":
            query = dict(p.split("=", 1) for p in urlparse(self.path).query.split("&") if "=" in p)
            data = self.read_body(MAX_PHOTO_BYTES)
            return self.send_json(store.add_photo(data, query.get("place_id"), query.get("item_id")), 201)
        if resource == "photos" and method == "DELETE" and record_id:
            return self.send_json({"ok": True, "trash_id": store.delete_photo(record_id)})
        if resource == "settings" and method == "PATCH":
            body = self.read_json()
            base_url = clean_text(body.get("base_url"), "Adresse", 200, required=True).rstrip("/")
            if not re.match(r"^https?://[^\s/]+$", base_url):
                raise ApiError(400, "Die Adresse muss wie http://rechner.local:8787 aussehen")
            store.set_setting("base_url", base_url)
            return self.send_json({"ok": True})
        if resource == "events" and method == "POST":
            body = self.read_json()
            q = clean_text(body.get("q"), "Suchbegriff", 120, required=True)
            hits = body.get("hits")
            if not isinstance(hits, int) or isinstance(hits, bool):
                raise ApiError(400, "Ungültige Trefferzahl")
            store.log_event("search", q=q, hits=hits)
            return self.send_json({"ok": True}, 201)

        handlers = {
            "sites": (store.create_site, store.update_site, store.delete_site),
            "rooms": (store.create_room, store.update_room, store.delete_room),
            "maps": (store.create_map, store.update_map, store.delete_map),
            "places": (store.create_place, store.update_place, store.delete_place),
            "items": (store.create_item, store.update_item, store.delete_item),
        }
        if resource in handlers:
            create, update, delete = handlers[resource]
            if method == "POST" and not record_id:
                return self.send_json(create(self.read_json()), 201)
            if resource == "items" and method == "POST" and action == "still-there":
                return self.send_json(store.confirm_item(record_id))
            if resource == "items" and method == "POST" and action in ("found", "missing"):
                return self.send_json(store.mark_item(record_id, action == "found"))
            if method == "PATCH" and record_id and not action:
                return self.send_json(update(record_id, self.read_json()))
            if method == "DELETE" and record_id and not action:
                return self.send_json({"ok": True, "trash_id": delete(record_id)})
        raise ApiError(404, "Unbekannte Adresse")

    def recognize(self, photo_id):
        # Jede Abfrage kostet Geld. Sie läuft nur hier, also nur auf ausdrücklichen Tipp in der App,
        # und ein schon erkanntes Foto wird mit demselben Hinweis ohne "force" nicht noch einmal geschickt.
        body = self.read_json()
        instruction = clean_text(body.get("instruction"), "Hinweis", MAX_INSTRUCTION)
        path = self.store.photo_path(photo_id or "")
        if not path or not path.exists():
            raise ApiError(404, "Foto nicht gefunden")
        cached = None if body.get("force") else self.store.saved_recognition(photo_id, instruction)
        if cached:
            return self.send_json({**cached, "from_cache": True})
        try:
            result = self.server.recognizer(path, self.store.data_dir, instruction)
        except recognition.RecognitionError as error:
            raise ApiError(error.status, error.message)
        usage = result.pop("usage", None)
        self.store.save_recognition(photo_id, instruction, result, usage)
        self.store.log_event("recognize", hits=len(result["items"]))
        self.send_json({**result, "from_cache": False})

    def import_chat_answer(self, photo_id):
        # Die kostenlose Übergabe: keine API, keine Kosten. Der Mensch hat den Chat selbst bedient.
        body = self.read_json()
        instruction = clean_text(body.get("instruction"), "Hinweis", MAX_INSTRUCTION)
        answer = clean_text(body.get("answer"), "Antwort", MAX_CHAT_ANSWER, required=True)
        path = self.store.photo_path(photo_id or "")
        if not path or not path.exists():
            raise ApiError(404, "Foto nicht gefunden")
        try:
            result = recognition.parse_chat_answer(answer)
        except recognition.RecognitionError as error:
            self.store.keep_unreadable_answer(answer)
            raise ApiError(error.status, error.message)
        self.store.save_recognition(photo_id, instruction, result, None)
        self.store.log_event("chat_answer", hits=len(result["items"]))
        self.send_json({**result, "from_cache": False})

    def handle_analysis(self, record_id, action):
        body = self.read_json()
        store = self.store
        if record_id is None:
            # Kostenpflichtig. Läuft nur hier, also nur auf ausdrücklichen Tipp in der App.
            try:
                result = self.server.analyzer(store.analysis_summary(), store.data_dir)
            except recognition.RecognitionError as error:
                raise ApiError(error.status, error.message)
            usage = result.pop("usage", None)
            if usage:
                store.add_usage(usage)
            store.save_analysis(recognition.clean_analysis(result), "api")
            store.log_event("analysis")
            return self.send_json({"ok": True})
        if record_id == "chat-answer":
            answer = clean_text(body.get("answer"), "Antwort", MAX_CHAT_ANSWER, required=True)
            try:
                result = recognition.parse_analysis_answer(answer)
            except recognition.RecognitionError as error:
                store.keep_unreadable_answer(answer)
                raise ApiError(error.status, error.message)
            store.save_analysis(result, "chat")
            store.log_event("analysis_chat")
            return self.send_json({"ok": True})
        if not record_id.isdigit() or action not in ("apply", "dismiss"):
            raise ApiError(404, "Unbekannte Adresse")
        if action == "apply":
            store.apply_analysis(int(record_id))
        else:
            store.dismiss_analysis(int(record_id))
        return self.send_json({"ok": True})

    def handle_backups(self, method, name, action):
        store = self.store
        if method == "GET" and not name:
            info = store.list_backups()
            if self.server.ha:
                info.update({"folder": ""})
            if not self.is_admin_client():
                info.update({"target": "", "target_backups": [], "folder": ""})
            return self.send_json({**info, "local": self.is_admin_client(), "ha": self.server.ha})
        if method == "POST" and not name:
            self.read_json()
            return self.send_json({"name": store.create_backup()}, 201)
        # Das greift tief ein oder schreibt in fremde Ordner, deshalb nur für Berechtigte.
        if not self.is_admin_client():
            raise ApiError(403, "Das geht nur am Mac selbst oder angemeldet in Home Assistant")
        if method == "POST" and name == "upload":
            return self.send_json(store.restore_upload(self.body_chunks(MAX_BACKUP_UPLOAD)))
        if method == "GET" and name == "ordner":
            return self.send_json({"folders": store.target_folders(), "root": str(store.target_root or "")})
        if method == "POST" and action == "restore":
            body = self.read_json()
            source = body.get("source", "local") if isinstance(body, dict) else "local"
            return self.send_json(store.restore_backup(name, "target" if source == "target" else "local"))
        if method == "PATCH" and not name:
            return self.send_json(store.set_backup_settings(self.read_json()))
        raise ApiError(404, "Unbekannte Adresse")

    def handle_recognition_key(self, method):
        # Der Schlüssel soll nicht unverschlüsselt durchs WLAN gehen, deshalb nur am Mac selbst.
        if not self.is_admin_client() or self.server.ha:
            raise ApiError(403, "Den Schlüssel kannst du nur am Mac selbst ändern")
        if method == "POST":
            key = clean_text(self.read_json().get("key"), "Schlüssel", 300, required=True)
            try:
                recognition.save_key(self.store.data_dir, key)
            except recognition.RecognitionError as error:
                raise ApiError(error.status, error.message)
            return self.send_json({"ok": True})
        if method == "DELETE":
            recognition.remove_key(self.store.data_dir)
            return self.send_json({"ok": True})
        raise ApiError(405, "Nicht erlaubt")

    def is_admin_client(self):
        """Am Mac selbst, oder in Home Assistant angemeldet und über den Ingress gekommen."""
        return bool(self.server.ingress_peer) or self.client_address[0] in ("127.0.0.1", "::1")

    def login(self):
        body = self.read_json()
        if not self.server.pin:
            return self.send_json({"ok": True})
        if not self.server.guard.check(body.get("pin", ""), self.server.pin):
            print(f"Falsche PIN von {self.client_address[0]}", file=sys.stderr, flush=True)
            raise ApiError(401, "PIN falsch")
        token = secrets.token_urlsafe(32)
        self.store.add_session(token)
        secure = "; Secure" if self.server.tls else ""
        cookie = f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_DAYS * 86400}{secure}"
        self.send_json({"ok": True}, extra_headers={"Set-Cookie": cookie})

    # Antworten

    def send_json(self, payload, status=200, extra_headers=None):
        self.send_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            extra_headers,
            status,
        )

    def send_bytes(self, data, content_type, extra_headers=None, status=200, cache="no-store", csp=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        # Der Ingress zeigt die App in einem Rahmen von Home Assistant, sonst darf sie niemand einbetten.
        framed = bool(self.server.ingress_peer)
        self.send_header("X-Frame-Options", "SAMEORIGIN" if framed else "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        # Die Kamera nur für diese App selbst, zum Scannen der Etiketten.
        self.send_header("Permissions-Policy", "camera=(self), microphone=(), geolocation=(), payment=(), usb=()")
        self.send_header(
            "Content-Security-Policy",
            csp or "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; "
            "manifest-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
            f"frame-ancestors {chr(39) + 'self' + chr(39) if framed else chr(39) + 'none' + chr(39)}",
        )
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def send_certificate(self):
        # Öffentlich: Ein Telefon braucht das Zertifikat, bevor es der Verbindung trauen kann.
        path = zugang.certificate_paths(self.store.data_dir)["ca"]
        if not self.server.lan or not path.exists():
            raise ApiError(404, "Nicht gefunden")
        self.send_bytes(
            path.read_bytes(), "application/x-x509-ca-cert",
            {"Content-Disposition": 'attachment; filename="findling-zertifikat.crt"'},
        )

    def send_photo(self, photo_name):
        path = self.store.photo_path(photo_name)
        if not path or not path.exists():
            raise ApiError(404, "Foto nicht gefunden")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_bytes(path.read_bytes(), content_type, cache="private, max-age=31536000, immutable")

    def send_document(self, document_id):
        """Liefert ein Dokument zum Ansehen im Browser. Die Art steht fest, nie geraten aus dem Inhalt."""
        found = self.store.document(document_id)
        if not found:
            raise ApiError(404, "Dokument nicht gefunden")
        row, path = found
        ascii_name = re.sub(r"[^A-Za-z0-9 ._-]", "_", row["title"])[:80].strip() or "dokument"
        disposition = "attachment" if "download=1" in urlparse(self.path).query else "inline"
        headers = {"Content-Disposition": f"{disposition}; filename=\"{ascii_name}{row['ext']}\"; filename*=UTF-8''{quote(row['title'] + row['ext'])}"}
        csp = DOCUMENT_CSP_PDF if row["ext"] == ".pdf" else DOCUMENT_CSP_IMAGE
        self.send_bytes(path.read_bytes(), DOCUMENT_TYPES[row["ext"]], headers, cache="private, no-cache", csp=csp)

    def send_static(self, path):
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (STATIC_DIR / relative).resolve()
        if STATIC_DIR not in target.parents or not target.is_file():
            raise ApiError(404, "Nicht gefunden")
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        body = target.read_bytes()
        if relative == "index.html":
            body = body.replace(b'<html lang="de">', f'<html lang="{LANGUAGE}">'.encode(), 1)
        self.send_bytes(body, content_type)


class InventoryServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, pin=None, verbose=False, ingress_peer=None, guard=None, ha=False):
        super().__init__(address, Handler)
        self.store = store
        self.pin = pin
        self.verbose = verbose
        self.ingress_peer = ingress_peer
        self.ha = ha
        self.tls = False
        self.gate_only = False
        self.gate_target = None
        self.guard = guard or PinGuard()
        self.slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        self.recognizer = recognition.recognize_photo
        self.analyzer = recognition.analyze_inventory
        self.lan = bool(pin)
        self.hostname = local_hostname()
        self.allowed_hosts = {"localhost", "127.0.0.1", "::1"}
        if self.lan and not ha:
            self.allowed_hosts |= {self.hostname.lower(), lan_ip(), zugang.STABLE_NAME}
        self.stable_name = False
        self.http_port = address[1]
        self.https_port = None
        self.public_host = None
        self.label_url = None

    def process_request(self, request, client_address):
        # Eine feste Obergrenze: Zu viele Verbindungen dürfen nicht beliebig viele Fäden erzeugen.
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        # Browser und Telefone trennen Verbindungen oft einfach. Das ist kein Fehler der App.
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError, ssl.SSLError)):
            return
        super().handle_error(request, client_address)

    def enable_tls(self, cert, key):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert, key)
        # Der Handschlag läuft im Faden der Anfrage, damit ein Gerät, das hängt, nicht alle aufhält.
        self.socket = context.wrap_socket(self.socket, server_side=True, do_handshake_on_connect=False)
        self.tls = True

    def info(self):
        port = self.http_port
        if self.ha:
            direct = bool(self.https_port)
            host = self.public_host
            return {
                "lan": direct,
                "ha": True,
                "ingress": bool(self.ingress_peer),
                "suggested_base": f"http://{host}:{port}" if direct else None,
                "https_base": f"https://{host}:{self.https_port}" if direct else None,
                "certificate": CERT_DOWNLOAD if direct else None,
                "stable_name": True,
                "label_url": self.label_url,
            }
        host = zugang.STABLE_NAME if self.stable_name else self.hostname
        return {
            "lan": self.lan,
            "ha": False,
            "ingress": False,
            "suggested_base": f"http://{host}:{port}" if self.lan else f"http://localhost:{port}",
            "https_base": f"https://{host}:{self.https_port}" if self.https_port else None,
            "certificate": CERT_DOWNLOAD if self.https_port else None,
            "stable_name": self.stable_name,
            "label_url": None,
        }


def local_hostname():
    try:
        name = subprocess.run(
            ["/usr/sbin/scutil", "--get", "LocalHostName"], capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        name = ""
    name = name or socket.gethostname().split(".")[0]
    return f"{name}.local"


def lan_ip():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))  # Sendet nichts, ermittelt nur die eigene Netzadresse.
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def load_or_create_pin(data_dir):
    pin_file = Path(data_dir) / "pin.txt"
    if pin_file.exists():
        return pin_file.read_text().strip()
    pin = f"{secrets.randbelow(1_000_000):06d}"
    pin_file.write_text(pin + "\n")
    pin_file.chmod(0o600)
    return pin


def start_backup_timer(store):
    def loop():
        while True:
            store.auto_backup()
            time.sleep(BACKUP_CHECK_SECONDS)

    threading.Thread(target=loop, daemon=True).start()


def start_https(server, store, pin, args):
    """Ein zweiter Eingang mit HTTPS. Ohne ihn bleibt das Telefon auf das Heimnetz beschränkt."""
    paths = zugang.ensure_certificate(args.data, (server.hostname.lower(),))
    if not paths:
        return
    try:
        secure = InventoryServer(("0.0.0.0", args.port + 1), store, pin, args.verbose)
        secure.enable_tls(str(paths["cert"]), str(paths["key"]))
    except (OSError, ssl.SSLError) as error:
        print(f"HTTPS nicht verfügbar: {error}")
        return
    secure.stable_name = server.stable_name
    secure.http_port = args.port
    secure.https_port = args.port + 1
    server.https_port = args.port + 1
    threading.Thread(target=secure.serve_forever, daemon=True).start()


def read_app_options(path):
    """Liest die Einstellungen aus Home Assistant. Unbrauchbares führt zum sicheren Standard."""
    try:
        with open(path, encoding="utf-8") as handle:
            options = json.load(handle)
    except (OSError, ValueError):
        options = {}
    return options if isinstance(options, dict) else {}


def ingress_slug():
    """Home Assistant nennt den Container nach der App, daraus ergibt sich ihre Adresse."""
    name = socket.gethostname().replace("-", "_")
    return name if re.fullmatch(r"[a-z0-9_]{1,64}", name) else "local_findling"


def set_language(language):
    global LANGUAGE
    LANGUAGE = language if language in LANGUAGES else "de"
    recognition.set_language(LANGUAGE)


def run_home_assistant(args):
    options = read_app_options(args.options)
    set_language(str(options.get("language") or "de"))
    store = Store(args.data)
    store.target_root = Path(getattr(args, "share", "/share"))
    store.mirror_helper = True
    # Den Auftrag für den Kopierdienst gleich beim Start erneuern.
    try:
        store.sync_target()
    except (OSError, sqlite3.Error) as error:
        say(f"Speicherort für Sicherungen nicht vorbereitet: {error}")
    options = read_app_options(args.options)
    key = str(options.get("anthropic_api_key") or "").strip()
    if key:
        try:
            recognition.save_key(args.data, key)
        except recognition.RecognitionError as error:
            say(f"API-Schlüssel nicht übernommen: {error.message}")
    else:
        recognition.remove_key(args.data)
    guard = PinGuard()
    ingress = InventoryServer(("0.0.0.0", args.ingress_port), store, None, args.verbose, args.ingress_peer, guard, ha=True)
    hostname = str(options.get("hostname") or "homeassistant.local").strip().lower()
    if not HOST_NAME.match(hostname):
        say("Der Rechnername ist ungültig, nutze homeassistant.local.")
        hostname = "homeassistant.local"
    qr_base = str(options.get("qr_base_url") or "http://homeassistant.local:8123").strip().rstrip("/")
    if not re.fullmatch(r"https?://[^\s/\"'<>]+", qr_base):
        say("Die Adresse für QR-Codes ist ungültig, nutze die Standardadresse.")
        qr_base = "http://homeassistant.local:8123"
    ingress.public_host = hostname
    ingress.label_url = f"{qr_base}/app/{ingress_slug()}/p/{{code}}"
    start_backup_timer(store)
    if options.get("direct_access") is True:
        pin = str(options.get("pin") or "")
        if len(pin) < MIN_DIRECT_PIN:
            say(f"Direktzugang bleibt aus: Die PIN braucht mindestens {MIN_DIRECT_PIN} Zeichen.")
        else:
            start_direct_access(ingress, store, pin, guard, hostname, args)
    say(f"findling läuft. Geschützter Zugang über Home Assistant auf Port {args.ingress_port}.")
    try:
        ingress.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ingress.server_close()


def start_direct_access(ingress, store, pin, guard, hostname, args):
    """Für die Kopie unterwegs: HTTPS mit PIN, dazu ein Eingang, der nur das Zertifikat herausgibt."""
    paths = zugang.ensure_certificate(args.data, (hostname,))
    if not paths:
        say("Direktzugang bleibt aus: Das Zertifikat konnte nicht angelegt werden.")
        return
    hosts = {hostname, "localhost"}
    try:
        secure = InventoryServer(("0.0.0.0", args.direct_port), store, pin, args.verbose, None, guard, ha=True)
        secure.enable_tls(str(paths["cert"]), str(paths["key"]))
        gate = InventoryServer(("0.0.0.0", args.gate_port), store, pin, args.verbose, None, guard, ha=True)
    except (OSError, ssl.SSLError) as error:
        say(f"Direktzugang bleibt aus: {error}")
        return
    label = f"https://{hostname}:{args.direct_port}/#/p/{{code}}"
    for server in (secure, gate):
        server.allowed_hosts = hosts
        server.public_host = hostname
        server.http_port = args.gate_port
        server.https_port = args.direct_port
        server.label_url = label
    gate.gate_only = True
    gate.gate_target = f"https://{hostname}:{args.direct_port}"
    ingress.http_port = args.gate_port
    ingress.https_port = args.direct_port
    ingress.label_url = label
    threading.Thread(target=secure.serve_forever, daemon=True).start()
    threading.Thread(target=gate.serve_forever, daemon=True).start()
    say(f"Direktzugang ist an: https://{hostname}:{args.direct_port}")


def main():
    parser = argparse.ArgumentParser(description="findling starten")
    parser.add_argument("--lan", action="store_true", help="auch im Heimnetz erreichbar machen, mit PIN")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data", default=str(DEFAULT_DATA_DIR), help="Ordner für Datenbank und Fotos")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--ha", action="store_true", help="als App in Home Assistant laufen")
    parser.add_argument("--options", default="/data/options.json", help=argparse.SUPPRESS)
    parser.add_argument("--ingress-port", type=int, default=8099, help=argparse.SUPPRESS)
    parser.add_argument("--ingress-peer", default=INGRESS_PEER, help=argparse.SUPPRESS)
    parser.add_argument("--gate-port", type=int, default=8787, help=argparse.SUPPRESS)
    parser.add_argument("--direct-port", type=int, default=8788, help=argparse.SUPPRESS)
    parser.add_argument("--share", default="/share", help=argparse.SUPPRESS)
    parser.add_argument("--lang", default="de", choices=LANGUAGES, help="Sprache der Oberfläche: de oder en")
    args = parser.parse_args()
    if args.ha:
        if args.data == str(DEFAULT_DATA_DIR):
            args.data = "/data"
        run_home_assistant(args)
        return

    set_language(args.lang)
    store = Store(args.data)
    pin = load_or_create_pin(args.data) if args.lan else None
    server = InventoryServer(("0.0.0.0" if args.lan else "127.0.0.1", args.port), store, pin, args.verbose)
    start_backup_timer(store)
    name = None
    if args.lan:
        name = zugang.StableName(args.port, lan_ip)
        server.stable_name = name.start()
        start_https(server, store, pin, args)

    print(f"Daten liegen in: {args.data}")
    print(f"Auf diesem Rechner: http://localhost:{args.port}")
    if args.lan:
        print(f"Im Heimnetz, zum Beispiel am Telefon: {server.info()['suggested_base']}")
        if server.https_port:
            print(f"Für unterwegs einrichten: {server.info()['https_base']}")
        print(f"PIN: {pin}")
    print("Beenden mit Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if name:
            name.stop()
        server.server_close()


if __name__ == "__main__":
    main()
