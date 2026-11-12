"""Tests für den Server. Start: python3 tests/test_server.py"""
import argparse
import base64
import http.client
import io
import json
import os
import re
import shutil
import socket
import ssl
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "findling" / "app"
sys.path.insert(0, str(APP))

import recognition
import server as server_module
import zugang
from server import InventoryServer, Store

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


class Client:
    def __init__(self, port, host="localhost"):
        self.base = f"http://127.0.0.1:{port}"
        self.host = host
        self.cookie = None

    def request(self, method, path, body=None, raw=None, marker=True):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Host", self.host)
        if marker:
            request.add_header("X-Werkstatt", "1")
        if self.cookie:
            request.add_header("Cookie", self.cookie)
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        payload = response.read()
        if response.headers.get("Set-Cookie"):
            self.cookie = response.headers["Set-Cookie"].split(";")[0]
        return response.status if hasattr(response, "status") else response.code, payload, response.headers

    def json(self, method, path, body=None):
        status, payload, _ = self.request(method, path, body)
        return status, json.loads(payload)


class ServerCase(unittest.TestCase):
    pin = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.server = InventoryServer(("127.0.0.1", 0), self.store, self.pin)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = Client(self.server.server_address[1])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def site_id(self):
        return self.client.json("GET", "/api/state")[1]["sites"][0]["id"]

    def make_room(self, name="Werkstatt"):
        status, room = self.client.json("POST", "/api/rooms", {"site_id": self.site_id(), "name": name})
        self.assertEqual(status, 201)
        return room

    def make_place(self, name="Regal 2", label="Schublade", room=None):
        room = room or self.make_room()
        status, map_record = self.client.json("POST", "/api/maps", {"room_id": room["id"], "name": name})
        self.assertEqual(status, 201)
        status, place = self.client.json("POST", "/api/places", {
            "map_id": map_record["id"], "label": label, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2,
        })
        self.assertEqual(status, 201)
        return map_record, place


class InventoryTests(ServerCase):
    def add_place(self, map_id):
        status, place = self.client.json("POST", "/api/places", {
            "map_id": map_id, "label": "", "x": 0, "y": 0, "w": 0.1, "h": 0.1,
        })
        self.assertEqual(status, 201)
        return place

    def test_place_codes_count_up(self):
        room = self.make_room()
        map_record, first = self.make_place(room=room)
        self.assertEqual(first["code"], "W-R2-01")
        self.assertEqual(self.add_place(map_record["id"])["code"], "W-R2-02")

    def test_a_new_cabinet_with_the_old_name_starts_again_at_one(self):
        room = self.make_room()
        map_record, _ = self.make_place(name="Regal 1", room=room)
        for _ in range(2):
            self.add_place(map_record["id"])
        self.client.json("DELETE", f"/api/maps/{map_record['id']}")
        again, first = self.make_place(name="Regal 1", room=room)
        self.assertEqual(again["code"], map_record["code"])
        codes = [first["code"]] + [self.add_place(again["id"])["code"] for _ in range(2)]
        self.assertEqual(codes, ["W-R1-01", "W-R1-02", "W-R1-03"])

    def test_a_deleted_place_frees_its_number(self):
        map_record, _ = self.make_place()
        second = self.add_place(map_record["id"])
        self.add_place(map_record["id"])
        self.client.json("DELETE", f"/api/places/{second['id']}")
        self.assertEqual(self.add_place(map_record["id"])["code"], "W-R2-02")
        self.assertEqual(self.add_place(map_record["id"])["code"], "W-R2-04")

    def test_places_created_at_the_same_time_get_different_numbers(self):
        map_record, _ = self.make_place()
        port = self.server.server_address[1]
        results = []

        def create():
            status, place = Client(port).json("POST", "/api/places", {
                "map_id": map_record["id"], "label": "", "x": 0, "y": 0, "w": 0.1, "h": 0.1,
            })
            results.append((status, place.get("code")))

        threads = [threading.Thread(target=create) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([status for status, _ in results], [201] * 8)
        self.assertEqual(sorted(code for _, code in results), [f"W-R2-{n:02d}" for n in range(2, 10)])

    def test_codes_stay_unique_across_rooms_and_houses(self):
        garage = self.make_room("Garage")
        gartenhaus = self.make_room("Gartenhaus")
        self.assertEqual((garage["code"], gartenhaus["code"]), ("G", "GA"))
        _, other = self.client.json("POST", "/api/sites", {"name": "Ferienhaus"})
        _, second = self.client.json("POST", "/api/rooms", {"site_id": other["id"], "name": "Garage"})
        self.assertEqual(second["code"], "GAR")
        _, a = self.client.json("POST", "/api/maps", {"room_id": garage["id"], "name": "Regal"})
        _, b = self.client.json("POST", "/api/maps", {"room_id": garage["id"], "name": "Rolle"})
        self.assertEqual((a["code"], b["code"]), ("R", "R2"))

    def test_same_room_name_is_refused_within_one_house_only(self):
        self.make_room("Garage")
        status, _ = self.client.json("POST", "/api/rooms", {"site_id": self.site_id(), "name": "Garage"})
        self.assertEqual(status, 409)

    def test_deleting_a_room_removes_everything_in_it(self):
        room = self.make_room()
        map_record, place = self.make_place(room=room)
        status, payload, _ = self.client.request("POST", f"/api/photos?place_id={place['id']}", raw=JPEG)
        photo = json.loads(payload)["id"]
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack"})
        self.assertEqual(self.client.json("DELETE", f"/api/rooms/{room['id']}")[0], 200)
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual((state["rooms"], state["maps"], state["places"], state["items"]), ([], [], [], []))
        self.assertEqual(self.client.request("GET", f"/fotos/{photo}")[0], 404)

    def test_last_house_cannot_be_deleted(self):
        self.assertEqual(self.client.json("DELETE", f"/api/sites/{self.site_id()}")[0], 409)
        _, other = self.client.json("POST", "/api/sites", {"name": "Ferienhaus"})
        self.assertEqual(self.client.json("DELETE", f"/api/sites/{other['id']}")[0], 200)

    def test_item_lifecycle_and_state(self):
        _, place = self.make_place()
        status, item = self.client.json("POST", "/api/items", {
            "place_id": place["id"], "name": "Lack anthrazit", "fill": "wenig", "note": "RAL 7016",
        })
        self.assertEqual(status, 201)
        self.client.json("POST", f"/api/items/{item['id']}/missing")
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["items"][0]["missing"], 1)
        self.client.json("POST", f"/api/items/{item['id']}/found")
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["items"][0]["missing"], 0)
        self.assertEqual(state["event_counts"], {"missing": 1, "found": 1})

    def test_invalid_input_is_rejected(self):
        _, place = self.make_place()
        status, _ = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": " "})
        self.assertEqual(status, 400)
        status, _ = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "x", "fill": "halb"})
        self.assertEqual(status, 400)
        status, _ = self.client.json("POST", "/api/maps", {"room_id": "gibt-es-nicht", "name": "R"})
        self.assertEqual(status, 404)

    def test_failed_searches_are_collected(self):
        self.client.json("POST", "/api/events", {"q": "Winkelverbinder", "hits": 0})
        self.client.json("POST", "/api/events", {"q": "Lack", "hits": 2})
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual([row["q"] for row in state["failed_searches"]], ["Winkelverbinder"])

    def test_photo_upload_checks_content_and_delete_removes_file(self):
        _, place = self.make_place()
        status, _, _ = self.client.request("POST", f"/api/photos?place_id={place['id']}", raw=b"<svg></svg>")
        self.assertEqual(status, 415)
        status, payload, _ = self.client.request("POST", f"/api/photos?place_id={place['id']}", raw=JPEG)
        self.assertEqual(status, 201)
        photo_id = json.loads(payload)["id"]
        status, body, headers = self.client.request("GET", f"/fotos/{photo_id}")
        self.assertEqual((status, body, headers["Content-Type"]), (200, JPEG, "image/jpeg"))
        self.client.json("DELETE", f"/api/photos/{photo_id}")
        self.assertEqual(self.client.request("GET", f"/fotos/{photo_id}")[0], 404)

    def test_csv_export_neutralises_formulas(self):
        _, place = self.make_place()
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "=HYPERLINK(1)"})
        status, payload, _ = self.client.request("GET", "/api/export.csv")
        self.assertEqual(status, 200)
        self.assertIn("'=HYPERLINK(1)", payload.decode("utf-8-sig"))

    def test_backup_contains_database_and_photos(self):
        self.client.request("POST", "/api/photos", raw=JPEG)
        status, payload, _ = self.client.request("GET", "/api/backup.zip")
        self.assertEqual(status, 200)
        names = zipfile.ZipFile(io.BytesIO(payload)).namelist()
        self.assertIn("inventar.sqlite", names)
        self.assertEqual(sum(name.startswith("fotos/") for name in names), 1)

    def test_writes_without_marker_header_are_rejected(self):
        status, _, _ = self.client.request("POST", "/api/events", {"q": "x", "hits": 0}, marker=False)
        self.assertEqual(status, 403)

    def test_unknown_host_is_rejected(self):
        client = Client(self.server.server_address[1], host="evil.example")
        self.assertEqual(client.request("GET", "/api/state")[0], 403)

    def test_static_files_cannot_escape_their_folder(self):
        status, _, _ = self.client.request("GET", "/../server.py")
        self.assertEqual(status, 404)
        status, _, _ = self.client.request("GET", "/%2e%2e/server.py")
        self.assertEqual(status, 404)


class FloorPlanTests(ServerCase):
    def upload(self):
        return json.loads(self.client.request("POST", "/api/photos", raw=JPEG)[1])["id"]

    def test_plan_and_positions_are_stored(self):
        room = self.make_room()
        map_record, _ = self.make_place(room=room)
        photo = self.upload()
        self.assertEqual(self.client.json("PATCH", f"/api/rooms/{room['id']}", {"plan_photo": photo})[0], 200)
        status, updated = self.client.json("PATCH", f"/api/maps/{map_record['id']}", {"plan_x": 0.25, "plan_y": 0.5})
        self.assertEqual((status, updated["plan_x"], updated["plan_y"]), (200, 0.25, 0.5))
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["rooms"][0]["plan_photo"], photo)
        self.assertEqual(state["maps"][0]["plan_y"], 0.5)

    def test_position_can_be_removed_and_is_validated(self):
        map_record, _ = self.make_place()
        path = f"/api/maps/{map_record['id']}"
        self.assertEqual(self.client.json("PATCH", path, {"plan_x": 2, "plan_y": 0.5})[0], 400)
        self.assertEqual(self.client.json("PATCH", path, {"plan_x": 0.5})[0], 400)
        self.client.json("PATCH", path, {"plan_x": 0.5, "plan_y": 0.5})
        _, updated = self.client.json("PATCH", path, {"plan_x": None, "plan_y": None})
        self.assertIsNone(updated["plan_x"])

    def test_replacing_a_plan_removes_the_old_photo(self):
        room = self.make_room()
        first, second = self.upload(), self.upload()
        self.client.json("PATCH", f"/api/rooms/{room['id']}", {"plan_photo": first})
        self.client.json("PATCH", f"/api/rooms/{room['id']}", {"plan_photo": second})
        self.assertEqual(self.client.request("GET", f"/fotos/{first}")[0], 404)
        self.assertEqual(self.client.request("GET", f"/fotos/{second}")[0], 200)

    def test_plan_photo_cannot_be_deleted_directly(self):
        room = self.make_room()
        photo = self.upload()
        self.client.json("PATCH", f"/api/rooms/{room['id']}", {"plan_photo": photo})
        self.assertEqual(self.client.json("DELETE", f"/api/photos/{photo}")[0], 409)

    def test_removing_a_plan_clears_positions_and_photo(self):
        room = self.make_room()
        map_record, _ = self.make_place(room=room)
        photo = self.upload()
        self.client.json("PATCH", f"/api/rooms/{room['id']}", {"plan_photo": photo})
        self.client.json("PATCH", f"/api/maps/{map_record['id']}", {"plan_x": 0.5, "plan_y": 0.5})
        self.assertEqual(self.client.json("PATCH", f"/api/rooms/{room['id']}", {"plan_photo": None})[0], 200)
        _, state = self.client.json("GET", "/api/state")
        self.assertIsNone(state["rooms"][0]["plan_photo"])
        self.assertIsNone(state["maps"][0]["plan_x"])
        self.assertEqual(self.client.request("GET", f"/fotos/{photo}")[0], 404)

    def test_existing_database_is_upgraded_without_losing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            old = sqlite3.connect(Path(folder) / "inventar.sqlite")
            old.execute(
                "CREATE TABLE maps (id TEXT PRIMARY KEY, room TEXT NOT NULL, room_code TEXT NOT NULL, "
                "name TEXT NOT NULL, code TEXT NOT NULL, photo TEXT, created REAL NOT NULL, UNIQUE (room_code, code))"
            )
            old.execute(
                "CREATE TABLE places (id TEXT PRIMARY KEY, map_id TEXT NOT NULL REFERENCES maps(id) ON DELETE CASCADE, "
                "code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL, w REAL NOT NULL, "
                "h REAL NOT NULL, surveyed INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL)"
            )
            old.execute("INSERT INTO maps VALUES ('m1', 'Werkstatt', 'W', 'Regal', 'R', NULL, 1.0)")
            old.execute("INSERT INTO places VALUES ('p1', 'm1', 'W-R-01', 'Fach', 0, 0, 0.1, 0.1, 0, 1.0)")
            old.commit()
            old.close()
            store = Store(folder)
            state = store.state()
            self.assertEqual(state["maps"][0]["name"], "Regal")
            self.assertEqual(state["rooms"][0]["name"], "Werkstatt")
            self.assertEqual(state["rooms"][0]["code"], "W")
            self.assertEqual(state["places"][0]["code"], "W-R-01")
            self.assertEqual(state["maps"][0]["room_id"], state["rooms"][0]["id"])
            # Die Verknüpfung der Plätze muss nach dem Umbau weiter greifen.
            store.delete_map("m1")
            self.assertEqual(store.state()["places"], [])


class RecognitionEndpointTests(ServerCase):
    def upload(self):
        _, place = self.make_place()
        _, payload, _ = self.client.request("POST", f"/api/photos?place_id={place['id']}", raw=JPEG)
        return json.loads(payload)["id"]

    def test_suggestions_are_returned_but_not_saved(self):
        photo_id = self.upload()
        self.server.recognizer = lambda path, data_dir, instruction: {"items": [{"name": "Lack"}], "not_recognized": ""}
        status, result = self.client.json("POST", f"/api/photos/{photo_id}/recognize", {})
        self.assertEqual((status, result["items"][0]["name"]), (200, "Lack"))
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["items"], [])
        self.assertEqual(state["event_counts"]["recognize"], 1)

    def test_a_recognized_photo_is_not_sent_again_unless_asked(self):
        photo_id = self.upload()
        calls = []

        def recognizer(path, data_dir, instruction):
            calls.append(path)
            return {"items": [], "not_recognized": "", "usage": {"input_tokens": 1000000, "output_tokens": 1000000}}

        self.server.recognizer = recognizer
        path = f"/api/photos/{photo_id}/recognize"
        self.assertFalse(self.client.json("POST", path, {})[1]["from_cache"])
        self.assertTrue(self.client.json("POST", path, {})[1]["from_cache"])
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.client.json("POST", path, {"force": True})[1]["from_cache"])
        self.assertEqual(len(calls), 2)
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["recognized_photos"], {photo_id: ""})
        self.assertEqual(state["api_cost_usd"], 48.0)

    def test_changed_instruction_asks_again_and_same_one_is_free(self):
        photo_id = self.upload()
        calls = []

        def recognizer(path, data_dir, instruction):
            calls.append(instruction)
            return {"items": [], "not_recognized": instruction}

        self.server.recognizer = recognizer
        path = f"/api/photos/{photo_id}/recognize"
        self.assertFalse(self.client.json("POST", path, {})[1]["from_cache"])
        status, result = self.client.json("POST", path, {"instruction": " nur das Holz "})
        self.assertEqual((status, result["from_cache"], result["not_recognized"]), (200, False, "nur das Holz"))
        self.assertTrue(self.client.json("POST", path, {"instruction": "nur das Holz"})[1]["from_cache"])
        self.assertEqual(calls, ["", "nur das Holz"])
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["recognized_photos"], {photo_id: "nur das Holz"})

    def test_too_long_instruction_costs_nothing(self):
        photo_id = self.upload()
        calls = []
        self.server.recognizer = lambda path, data_dir, instruction: calls.append(path)
        status, _ = self.client.json("POST", f"/api/photos/{photo_id}/recognize", {"instruction": "x" * 301})
        self.assertEqual((status, calls), (400, []))

    def test_nothing_is_sent_when_a_photo_is_uploaded(self):
        calls = []
        self.server.recognizer = lambda path, data_dir, instruction: calls.append(path)
        self.upload()
        self.client.json("GET", "/api/state")
        self.assertEqual(calls, [])

    def test_recognition_errors_reach_the_client(self):
        photo_id = self.upload()

        def fail(path, data_dir, instruction):
            raise recognition.RecognitionError(503, "Keine Verbindung")

        self.server.recognizer = fail
        status, result = self.client.json("POST", f"/api/photos/{photo_id}/recognize", {})
        self.assertEqual((status, result["error"]), (503, "Keine Verbindung"))

    def test_unknown_photo_is_rejected(self):
        status, _ = self.client.json("POST", f"/api/photos/{'0' * 32}/recognize", {})
        self.assertEqual(status, 404)

    def test_key_is_stored_privately_never_returned_and_not_backed_up(self):
        secret = "test-key-0123456789"
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.assertEqual(self.client.json("POST", "/api/recognition-key", {"key": secret})[0], 200)
        path = Path(self.tmp.name) / recognition.KEY_FILE_NAME
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        status, payload, _ = self.client.request("GET", "/api/state")
        self.assertNotIn(secret, payload.decode())
        self.assertTrue(json.loads(payload)["recognition"]["configured"])
        _, backup, _ = self.client.request("GET", "/api/backup.zip")
        self.assertNotIn(recognition.KEY_FILE_NAME, zipfile.ZipFile(io.BytesIO(backup)).namelist())
        self.assertEqual(self.client.json("DELETE", "/api/recognition-key")[0], 200)
        self.assertFalse(path.exists())

    def test_unread_request_body_does_not_break_the_next_request(self):
        photo_id = self.upload()
        self.server.recognizer = lambda path, data_dir, instruction: {"items": [], "not_recognized": ""}
        headers = {"Host": "localhost", "X-Werkstatt": "1", "Content-Type": "application/json"}
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1])
        connection.request("POST", f"/api/photos/{photo_id}/recognize", body="{}", headers=headers)
        response = connection.getresponse()
        response.read()
        connection.request("GET", "/api/session", headers=headers)
        self.assertEqual(connection.getresponse().status, 200)
        connection.close()

    def test_invalid_key_is_rejected(self):
        self.assertEqual(self.client.json("POST", "/api/recognition-key", {"key": "a b"})[0], 400)


class ChatHandoverTests(ServerCase):
    ANSWER = """Hier ist die Liste:

```json
{"items": [
  {"name": "Lack anthrazit", "also_known_as": ["Farbe"], "details": "RAL 7016", "amount": "ca. 2 Dosen",
   "fill": "voll", "certainty": "sicher"},
  {"name": "Spax", "fill": "fast leer", "certainty": "vielleicht"},
  {"name": "   "}, "Unsinn"
], "not_recognized": "eine Tüte"}
```

Sag Bescheid, wenn du mehr brauchst."""

    def upload(self):
        return json.loads(self.client.request("POST", "/api/photos", raw=JPEG)[1])["id"]

    def test_answer_is_saved_without_any_api_call(self):
        photo = self.upload()
        calls = []
        self.server.recognizer = lambda path, data_dir, instruction: calls.append(path)
        status, result = self.client.json("POST", f"/api/photos/{photo}/chat-answer", {
            "instruction": "nur Lack", "answer": self.ANSWER,
        })
        self.assertEqual((status, calls), (200, []))
        self.assertEqual([item["name"] for item in result["items"]], ["Lack anthrazit", "Spax", "Unsinn"])
        self.assertEqual(result["not_recognized"], "eine Tüte")
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["recognized_photos"], {photo: "nur Lack"})
        self.assertEqual(state["api_cost_usd"], 0)
        self.assertEqual(state["event_counts"]["chat_answer"], 1)
        _, again = self.client.json("POST", f"/api/photos/{photo}/recognize", {"instruction": "nur Lack"})
        self.assertTrue(again["from_cache"])
        self.assertEqual(calls, [])

    def test_unknown_values_become_safe_defaults(self):
        items = recognition.parse_chat_answer(self.ANSWER)["items"]
        self.assertEqual((items[1]["fill"], items[1]["certainty"], items[1]["also_known_as"]), ("unklar", "unsicher", []))

    def test_plain_json_without_code_block_is_read(self):
        result = recognition.parse_chat_answer('Gern: {"items": [{"name": "Holz"}], "not_recognized": ""} Fertig.')
        self.assertEqual(result["items"][0]["name"], "Holz")

    def test_unreadable_answers_are_refused_and_nothing_is_saved(self):
        photo = self.upload()
        for answer in ("Das ist eine Schublade mit Schrauben.", '{"items": [oops]}', '{"foo": 1}', "[1]", ""):
            status, _ = self.client.json("POST", f"/api/photos/{photo}/chat-answer", {"answer": answer})
            self.assertEqual(status, 400, answer)
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["recognized_photos"], {})

    def names(self, answer):
        return [item["name"] for item in recognition.parse_chat_answer(answer)["items"]]

    def test_answers_as_chats_really_write_them(self):
        lack = '{"name": "Lack", "also_known_as": [], "details": "", "amount": "", "fill": "ok", "certainty": "sicher"}'
        holz = '{"name": "Holz", "also_known_as": [], "details": "", "amount": "", "fill": "ok", "certainty": "sicher"}'
        expected = ["Lack", "Holz"]
        cases = {
            "Codeblock": f'```json\n{{"items": [{lack}, {holz}], "not_recognized": ""}}\n```',
            "Grossgeschrieben": f'```JSON\n{{"items": [{lack}, {holz}]}}\n```',
            "Kopfzeile der Oberfläche": f'json\nCopy code\n{{"items": [{lack}, {holz}]}}',
            "Text davor und danach": f'Gern! Hier:\n{{"items": [{lack}, {holz}]}}\nViel Erfolg [1]!',
            "nur eine Liste": f"[{lack}, {holz}]",
            "zwei Codeblöcke": f'```json\n{{"items": [{lack}]}}\n```\nUnd:\n```json\n{{"items": [{holz}]}}\n```',
            "einzelne Objekte": f"{lack}\n{holz}",
            "eine Ebene tiefer": f'{{"ergebnis": {{"items": [{lack}, {holz}]}}}}',
            "deutscher Schlüssel": '{"eintraege": [{"Bezeichnung": "Lack"}, {"Name": "Holz"}]}',
            "nur Wörter": '{"items": ["Lack", "Holz"]}',
            "Komma am Ende": '{"items": [{"name": "Lack",}, {"name": "Holz",},],}',
            "Kommentar": '{"items": [\n// erster\n{"name": "Lack"},\n{"name": "Holz"}\n]}',
            "typografische Anführungszeichen": '{\u201citems\u201d: [{\u201cname\u201d: \u201cLack\u201d}, {\u201cname\u201d: \u201cHolz\u201d}]}',
            "einfache Anführungszeichen": "{'items': [{'name': 'Lack', 'details': None}, {'name': 'Holz'}]}",
            "unsichtbare Zeichen": '\ufeff{"items":\u00a0[{"name": "Lack"},\u200b {"name": "Holz"}]}',
            "Windows-Zeilen": '{\r\n"items": [\r\n{"name": "Lack"},\r\n{"name": "Holz"}\r\n]\r\n}',
            "abgeschnitten": '{"items": [{"name": "Lack", "details": ""}, {"name": "Holz", "details": ""}, {"na',
            "Stichpunkte": "Das sehe ich:\n\n- **Lack**\n- Holz\n",
            "nummeriert": "1. Lack\n2. Holz",
            "Tabelle": "| Name | Details |\n|---|---|\n| Lack | RAL |\n| Holz | Fichte |",
            "Tabelle ohne Kopf": "| Lack | RAL |\n| Holz | Fichte |",
        }
        for label, answer in cases.items():
            with self.subTest(label):
                self.assertEqual(self.names(answer), expected)

    def test_inner_quotes_do_not_lose_the_item(self):
        answer = '{"items": [\n{"name": "Rohr 1/2" Zoll", "details": "Messing"},\n{"name": "Holz", "details": ""}\n]}'
        items = recognition.parse_chat_answer(answer)["items"]
        self.assertEqual(items[0]["name"], 'Rohr 1/2" Zoll')
        self.assertEqual(items[0]["details"], "Messing")
        self.assertEqual(items[1]["name"], "Holz")

    def test_values_are_tidied_up(self):
        item = recognition.parse_chat_answer(
            '{"items": [{"Name": "Mutter M8", "Menge": 35, "Füllstand": "Wenig", "Sicherheit": "hoch", "Synonyme": "Sechskant, Mutter", "Notiz": ["verzinkt", "DIN 934"]}], "nicht_erkannt": "Tüte"}'
        )
        self.assertEqual(item["not_recognized"], "Tüte")
        first = item["items"][0]
        self.assertEqual((first["amount"], first["fill"], first["certainty"]), ("35", "wenig", "sicher"))
        self.assertEqual(first["also_known_as"], ["Sechskant", "Mutter"])
        self.assertEqual(first["details"], "verzinkt, DIN 934")

    def test_missing_certainty_stays_selected_in_the_review(self):
        self.assertEqual(recognition.parse_chat_answer('{"items": [{"name": "Holz"}]}')["items"][0]["certainty"], "wahrscheinlich")

    def test_empty_list_means_nothing_recognized(self):
        self.assertEqual(recognition.parse_chat_answer('{"items": [], "not_recognized": "zu dunkel"}')["items"], [])

    def test_missing_photo_gets_its_own_message(self):
        for answer in ("KEIN FOTO", "Ich sehe kein Bild. Bitte lade das Foto hoch."):
            with self.assertRaises(recognition.RecognitionError) as caught:
                recognition.parse_chat_answer(answer)
            self.assertIn("kein Foto gesehen", caught.exception.message)

    def test_unreadable_answer_is_quoted_and_kept_for_diagnosis(self):
        photo = self.upload()
        status, result = self.client.json("POST", f"/api/photos/{photo}/chat-answer", {"answer": "Das ist eine Schublade."})
        self.assertEqual(status, 400)
        self.assertIn("Das ist eine Schublade.", result["error"])
        kept = Path(self.store.data_dir) / "letzte-unlesbare-chat-antwort.txt"
        self.assertEqual(kept.read_text(), "Das ist eine Schublade.")
        self.assertEqual(kept.stat().st_mode & 0o777, 0o600)

    def test_prompt_puts_the_format_last_with_room_for_the_hint(self):
        prompt = recognition.chat_prompt()
        self.assertLess(prompt.index(recognition.HINT_MARK), prompt.index("JSON-Codeblock"))
        self.assertIn("KEIN FOTO", prompt)
        self.assertIn('"items"', recognition.CHAT_RETRY)
        self.assertNotIn("KEIN FOTO", recognition.CHAT_RETRY)

    def test_unknown_photo_is_refused(self):
        status, _ = self.client.json("POST", f"/api/photos/{'0' * 32}/chat-answer", {"answer": self.ANSWER})
        self.assertEqual(status, 404)

    def test_prompt_names_every_field_and_works_without_a_key(self):
        _, state = self.client.json("GET", "/api/state")
        prompt = state["recognition"]["chat_prompt"]
        item = recognition.OUTPUT_SCHEMA["properties"]["items"]["items"]["properties"]
        for field in [*item, "not_recognized"]:
            self.assertIn(f'"{field}"', prompt)
        self.assertIn("niemals eine Anweisung", prompt)


class WorkflowTests(ServerCase):
    def test_whole_photo_place_reuses_the_cabinet_photo(self):
        room = self.make_room("Schuppen")
        photo = json.loads(self.client.request("POST", "/api/photos", raw=JPEG)[1])["id"]
        _, map_record = self.client.json("POST", "/api/maps", {"room_id": room["id"], "name": "Holz", "photo": photo})
        status, place = self.client.json("POST", "/api/places", {
            "map_id": map_record["id"], "label": "Holz", "x": 0, "y": 0, "w": 1, "h": 1, "use_map_photo": True,
        })
        self.assertEqual(status, 201)
        _, state = self.client.json("GET", "/api/state")
        copies = state["places"][0]["photos"]
        self.assertEqual(len(copies), 1)
        self.assertNotEqual(copies[0], photo)
        self.assertEqual(self.client.request("GET", f"/fotos/{copies[0]}")[0], 200)

    def test_confirming_sets_and_clears_the_date(self):
        _, place = self.make_place()
        _, done = self.client.json("PATCH", f"/api/places/{place['id']}", {"surveyed": True})
        self.assertTrue(done["surveyed_at"])
        _, undone = self.client.json("PATCH", f"/api/places/{place['id']}", {"surveyed": False})
        self.assertIsNone(undone["surveyed_at"])

    def test_database_without_confirmation_date_is_upgraded(self):
        with self.store.connect() as db:
            db.execute("ALTER TABLE places DROP COLUMN surveyed_at") if sqlite3.sqlite_version_info >= (3, 35) else None
        Store(self.tmp.name)
        with self.store.connect() as db:
            self.assertIn("surveyed_at", [row["name"] for row in db.execute("PRAGMA table_info(places)")])


class TrashTests(ServerCase):
    def setUp(self):
        super().setUp()
        self.room = self.make_room("Garage")
        photo = json.loads(self.client.request("POST", "/api/photos", raw=JPEG)[1])["id"]
        _, self.map = self.client.json("POST", "/api/maps", {"room_id": self.room["id"], "name": "Regal", "photo": photo})
        self.map_photo = photo
        _, self.place = self.client.json("POST", "/api/places", {
            "map_id": self.map["id"], "label": "Fach", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2,
        })
        self.place_photo = json.loads(self.client.request("POST", f"/api/photos?place_id={self.place['id']}", raw=JPEG)[1])["id"]
        _, self.item = self.client.json("POST", "/api/items", {"place_id": self.place["id"], "name": "Lack", "note": "RAL 7016", "fill": "wenig"})
        self.server.recognizer = lambda path, data_dir, instruction: {"items": [], "not_recognized": ""}
        self.client.json("POST", f"/api/photos/{self.place_photo}/recognize", {})

    def state(self):
        return self.client.json("GET", "/api/state")[1]

    def trash(self):
        return self.client.json("GET", "/api/trash")[1]["entries"]

    def delete(self, path):
        status, result = self.client.json("DELETE", path)
        self.assertEqual(status, 200)
        return result["trash_id"]

    def restore(self, trash_id, **body):
        return self.client.json("POST", f"/api/trash/{trash_id}/restore", body)

    def test_cabinet_comes_back_completely(self):
        before = self.state()
        trash_id = self.delete(f"/api/maps/{self.map['id']}")
        gone = self.state()
        self.assertEqual((gone["maps"], gone["places"], gone["items"], gone["trash_count"]), ([], [], [], 1))
        self.assertEqual(self.client.request("GET", f"/fotos/{self.map_photo}")[0], 404)
        entry = self.trash()[0]
        self.assertEqual((entry["kind"], entry["label"], entry["detail"], entry["days_left"]), ("map", "Regal", "Garage", 30))
        self.assertEqual((entry["counts"]["places"], entry["counts"]["items"], entry["counts"]["photos"]), (1, 1, 2))
        status, result = self.restore(trash_id)
        self.assertEqual((status, result["href"]), (200, f"#/karte/{self.map['id']}"))
        after = self.state()
        for key in ("maps", "places", "items", "recognized_photos"):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(after["trash_count"], 0)
        self.assertEqual(self.client.request("GET", f"/fotos/{self.map_photo}")[0], 200)
        self.assertEqual(self.client.request("GET", f"/fotos/{self.place_photo}")[0], 200)

    def test_every_kind_can_be_restored(self):
        _, other = self.client.json("POST", "/api/sites", {"name": "Ferienhaus"})
        _, far = self.client.json("POST", "/api/rooms", {"site_id": other["id"], "name": "Keller"})
        for path, check in (
            (f"/api/items/{self.item['id']}", "items"),
            (f"/api/photos/{self.place_photo}", None),
            (f"/api/places/{self.place['id']}", "places"),
            (f"/api/rooms/{self.room['id']}", "rooms"),
            (f"/api/sites/{other['id']}", "sites"),
        ):
            with self.subTest(path):
                before = self.state()
                trash_id = self.delete(path)
                self.assertEqual(self.restore(trash_id)[0], 200)
                after = self.state()
                self.assertEqual(after["items"], before["items"])
                self.assertEqual(after["rooms"], before["rooms"])
                self.assertEqual(after["sites"], before["sites"])
                self.assertEqual(after["places"], before["places"])
        self.assertEqual(far["name"], "Keller")

    def test_item_whose_place_is_gone_needs_a_new_one(self):
        item_trash = self.delete(f"/api/items/{self.item['id']}")
        map_trash = self.delete(f"/api/maps/{self.map['id']}")
        entry = next(e for e in self.trash() if e["id"] == item_trash)
        self.assertTrue(entry["parent_missing"])
        self.assertEqual(entry["parent_table"], "places")
        self.assertEqual(self.restore(item_trash)[0], 409)
        self.assertEqual(self.restore(map_trash)[0], 200)
        self.assertEqual(self.restore(item_trash)[0], 200)
        self.assertEqual(self.state()["items"][0]["note"], "RAL 7016")

    def test_item_can_move_to_another_place_on_restore(self):
        _, place = self.client.json("POST", "/api/places", {"map_id": self.map["id"], "label": "B", "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1})
        item_trash = self.delete(f"/api/items/{self.item['id']}")
        self.delete(f"/api/places/{self.place['id']}")
        self.assertEqual(self.restore(item_trash, parent_id=place["id"])[0], 200)
        self.assertEqual(self.state()["items"][0]["place_id"], place["id"])

    def test_room_with_a_taken_name_and_code_keeps_its_addresses(self):
        trash_id = self.delete(f"/api/rooms/{self.room['id']}")
        new = self.make_room("Garage")
        self.assertEqual(new["code"], self.room["code"])
        self.assertEqual(self.restore(trash_id)[0], 200)
        state = self.state()
        self.assertEqual(sorted(room["name"] for room in state["rooms"]), ["Garage", "Garage (2)"])
        self.assertEqual(len({room["code"] for room in state["rooms"]}), 2)
        self.assertEqual(state["places"][0]["code"], self.place["code"])

    def test_foreign_files_in_the_backup_folder_are_ignored(self):
        folder = self.store.backup_dir
        folder.mkdir(exist_ok=True)
        self.store.create_backup()
        foreign = folder / "fremd-2026-01-01.zip"
        foreign.write_bytes(next(folder.glob("findling-*.zip")).read_bytes())
        names = [entry["name"] for entry in self.client.json("GET", "/api/backups")[1]["backups"]]
        self.assertNotIn(foreign.name, names)
        self.assertNotEqual(self.client.json("POST", f"/api/backups/{foreign.name}/restore", {})[0], 200)
        self.assertTrue(foreign.exists())

    def test_number_is_free_again_while_in_trash(self):
        trash_id = self.delete(f"/api/places/{self.place['id']}")
        _, fresh = self.client.json("POST", "/api/places", {"map_id": self.map["id"], "label": "", "x": 0, "y": 0, "w": 0.1, "h": 0.1})
        self.assertEqual(fresh["code"], self.place["code"])
        status, result = self.restore(trash_id)
        self.assertEqual(status, 200)
        codes = sorted(place["code"] for place in self.state()["places"])
        self.assertEqual(codes, [self.place["code"], self.place["code"][:-2] + "02"])
        self.assertEqual(result["href"], f"#/p/{codes[1]}")
        self.assertEqual(self.state()["items"][0]["place_id"], self.place["id"])

    def test_cabinet_comes_back_next_to_its_replacement(self):
        trash_id = self.delete(f"/api/maps/{self.map['id']}")
        _, again = self.client.json("POST", "/api/maps", {"room_id": self.room["id"], "name": self.map["name"]})
        _, fresh = self.client.json("POST", "/api/places", {"map_id": again["id"], "label": "", "x": 0, "y": 0, "w": 0.1, "h": 0.1})
        self.assertEqual(fresh["code"], self.place["code"])
        self.assertEqual(self.restore(trash_id)[0], 200)
        state = self.state()
        back = next(m for m in state["maps"] if m["id"] == self.map["id"])
        moved = next(p for p in state["places"] if p["id"] == self.place["id"])
        self.assertNotEqual(back["code"], again["code"])
        self.assertEqual(moved["code"], f"{self.room['code']}-{back['code']}-01")
        self.assertEqual(len({p["code"] for p in state["places"]}), 2)
        self.assertEqual(state["items"][0]["place_id"], self.place["id"])

    def old_photo_file(self, photo):
        return Path(self.store.data_dir) / "fotos" / f"{photo}.jpg"

    def test_after_30_days_everything_is_deleted_for_good(self):
        fresh = self.delete(f"/api/items/{self.item['id']}")
        old = self.delete(f"/api/maps/{self.map['id']}")
        self.assertTrue(self.old_photo_file(self.map_photo).exists())
        with self.store.connect() as db:
            db.execute("UPDATE trash SET created = created - ? WHERE id = ?", (29 * 86400, fresh))
            db.execute("UPDATE trash SET created = created - ? WHERE id = ?", (30 * 86400 + 60, old))
        entries = self.trash()
        self.assertEqual([e["id"] for e in entries], [fresh])
        self.assertEqual(entries[0]["days_left"], 1)
        self.assertFalse(self.old_photo_file(self.map_photo).exists())
        self.assertFalse(self.old_photo_file(self.place_photo).exists())
        self.assertEqual(self.restore(old)[0], 404)

    def test_expired_entries_also_go_at_startup(self):
        self.delete(f"/api/items/{self.item['id']}")
        with self.store.connect() as db:
            db.execute("UPDATE trash SET created = 1000")
        Store(self.tmp.name)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM trash").fetchone()[0], 0)

    def test_final_delete_and_empty(self):
        one = self.delete(f"/api/maps/{self.map['id']}")
        self.assertEqual(self.client.json("DELETE", f"/api/trash/{one}")[0], 200)
        self.assertFalse(self.old_photo_file(self.map_photo).exists())
        self.assertEqual(self.client.json("DELETE", f"/api/trash/{one}")[0], 404)
        room_trash = self.delete(f"/api/rooms/{self.room['id']}")
        self.assertTrue(room_trash)
        self.assertEqual(self.client.json("DELETE", "/api/trash")[0], 200)
        self.assertEqual(self.trash(), [])

    def test_last_house_and_cabinet_photo_rules_still_hold(self):
        self.assertEqual(self.client.json("DELETE", f"/api/sites/{self.site_id()}")[0], 409)
        self.assertEqual(self.client.json("DELETE", f"/api/photos/{self.map_photo}")[0], 409)
        self.assertEqual(self.client.json("DELETE", f"/api/items/{'0' * 32}")[0], 404)
        self.assertEqual(self.trash(), [])


class BackupTests(ServerCase):
    def make_item(self, name="Lack"):
        _, place = self.make_place()
        return self.client.json("POST", "/api/items", {"place_id": place["id"], "name": name})[1]

    def names(self):
        return [entry["name"] for entry in self.client.json("GET", "/api/backups")[1]["backups"]]

    def age_last_backup(self, hours):
        last = float(self.store.backup_settings()["last"])
        self.store.set_setting("backup_last", str(last - hours * 3600))

    def test_backup_follows_the_interval_and_only_when_something_changed(self):
        self.make_item()
        first = self.store.auto_backup()
        self.assertTrue(first)
        self.assertIsNone(self.store.auto_backup())  # Takt noch nicht erreicht.
        self.age_last_backup(25)
        self.assertIsNone(self.store.auto_backup())  # Takt erreicht, aber nichts geändert.
        self.client.json("POST", "/api/items", {
            "place_id": self.client.json("GET", "/api/state")[1]["places"][0]["id"], "name": "Spax",
        })
        self.assertTrue(self.store.auto_backup())
        self.assertEqual(len(self.names()), 2)

    def test_interval_can_be_set_to_six_hours(self):
        self.make_item()
        self.store.auto_backup()
        status, info = self.client.json("PATCH", "/api/backups", {"interval": 6})
        self.assertEqual((status, info["interval"]), (200, 6))
        self.client.json("POST", "/api/items", {
            "place_id": self.client.json("GET", "/api/state")[1]["places"][0]["id"], "name": "Spax",
        })
        self.age_last_backup(5)
        self.assertIsNone(self.store.auto_backup())
        self.age_last_backup(1.1)
        self.assertTrue(self.store.auto_backup())
        self.assertTrue(info["next"])

    def test_invalid_settings_are_refused(self):
        for body in ({"interval": 5}, {"interval": "24"}, {"keep": 2}, {"keep": 31}, {"keep": True}, {"target": "/gibt/es/nicht"}):
            with self.subTest(body):
                self.assertEqual(self.client.json("PATCH", "/api/backups", body)[0], 400)

    def test_restore_brings_back_data_and_photos_and_keeps_the_login(self):
        item = self.make_item("Lack")
        place_id = item["place_id"]
        photo = json.loads(self.client.request("POST", f"/api/photos?place_id={place_id}", raw=JPEG)[1])["id"]
        name = self.client.json("POST", "/api/backups", {})[1]["name"]
        self.client.json("DELETE", f"/api/items/{item['id']}")
        self.client.json("DELETE", f"/api/trash")
        self.client.json("DELETE", f"/api/photos/{photo}")
        self.client.json("DELETE", "/api/trash")
        later = json.loads(self.client.request("POST", f"/api/photos?place_id={place_id}", raw=JPEG)[1])["id"]
        self.store.add_session("mein-token")
        status, result = self.client.json("POST", f"/api/backups/{name}/restore", {})
        self.assertEqual(status, 200)
        self.assertTrue(result["safety"].endswith(".zip"))
        state = self.client.json("GET", "/api/state")[1]
        self.assertEqual([entry["name"] for entry in state["items"]], ["Lack"])
        self.assertEqual(self.client.request("GET", f"/fotos/{photo}")[0], 200)
        self.assertEqual(self.client.request("GET", f"/fotos/{later}")[0], 404)
        self.assertTrue(self.store.has_session("mein-token"))
        self.assertIn(result["safety"], self.names())

    def test_broken_or_invented_backups_are_refused(self):
        self.make_item()
        self.assertEqual(self.client.json("POST", "/api/backups/../../inventar.sqlite/restore", {})[0], 404)
        self.assertEqual(self.client.json("POST", "/api/backups/findling-2020-01-01.zip/restore", {})[0], 404)
        self.store.backup_dir.mkdir(exist_ok=True)
        (self.store.backup_dir / "findling-2020-01-02.zip").write_bytes(b"kein zip")
        self.assertEqual(self.client.json("POST", "/api/backups/findling-2020-01-02.zip/restore", {})[0], 400)
        evil = self.store.backup_dir / "findling-2020-01-03.zip"
        with zipfile.ZipFile(evil, "w") as archive:
            archive.writestr("../boese.txt", "x")
        self.assertEqual(self.client.json("POST", f"/api/backups/{evil.name}/restore", {})[0], 400)
        self.assertFalse((Path(self.store.data_dir) / "boese.txt").exists())
        self.assertEqual(len(self.client.json("GET", "/api/state")[1]["items"]), 1)

    def test_empty_app_is_not_backed_up(self):
        self.assertIsNone(self.store.auto_backup())
        self.assertEqual(self.names(), [])

    def test_newest_backup_comes_first_even_within_a_day(self):
        self.make_item()
        daily = self.store.auto_backup()
        os.utime(self.store.backup_dir / daily, (1000, 1000))
        manual = self.client.json("POST", "/api/backups", {})[1]["name"]
        self.assertEqual(self.names(), [manual, daily])

    def test_only_the_last_backups_are_kept(self):
        folder = self.store.backup_dir
        folder.mkdir(exist_ok=True)
        for day in range(1, 13):
            path = folder / f"findling-2026-01-{day:02d}-1200.zip"
            path.write_bytes(b"x")
            os.utime(path, (day * 86400, day * 86400))
        for n, version in enumerate(("0.1.0", "0.1.1", "0.2.0")):
            path = folder / f"findling-2026-01-0{n + 1}-vor-{version}.zip"
            path.write_bytes(b"x")
            os.utime(path, (n * 86400, n * 86400))
        (folder / "notizen.txt").write_text("bleibt")
        Store._prune_backups(folder, 7)
        kept = sorted(path.name for path in folder.iterdir())
        regular = [name for name in kept if name.endswith("-1200.zip")]
        self.assertEqual(regular, [f"findling-2026-01-{day:02d}-1200.zip" for day in range(6, 13)])
        self.assertEqual([name for name in kept if "-vor-" in name], ["findling-2026-01-02-vor-0.1.1.zip", "findling-2026-01-03-vor-0.2.0.zip"])
        self.assertIn("notizen.txt", kept)

    def test_fewer_backups_are_kept_after_changing_the_setting(self):
        self.make_item()
        for _ in range(5):
            self.client.json("POST", "/api/backups", {})
        self.assertEqual(len(self.names()), 5)
        self.assertEqual(self.client.json("PATCH", "/api/backups", {"keep": 3})[0], 200)
        self.assertEqual(len(self.names()), 3)

    def test_second_folder_receives_a_copy(self):
        self.make_item()
        with tempfile.TemporaryDirectory() as mirror:
            self.assertEqual(self.client.json("PATCH", "/api/backups", {"mirror": mirror})[0], 200)
            name = self.client.json("POST", "/api/backups", {})[1]["name"]
            self.assertTrue((Path(mirror) / name).exists())
        self.assertEqual(self.client.json("PATCH", "/api/backups", {"mirror": "/gibt/es/nicht"})[0], 400)

    def test_storage_location_keeps_the_same_number_and_reports_success(self):
        self.make_item()
        with tempfile.TemporaryDirectory() as target:
            (Path(target) / "fremde-datei.zip").write_bytes(b"bleibt")
            info = self.client.json("PATCH", "/api/backups", {"target": target, "keep": 3})[1]
            self.assertEqual(info["target"], str(Path(target)))
            for _ in range(5):
                self.client.json("POST", "/api/backups", {})
            info = self.client.json("GET", "/api/backups")[1]
            self.assertEqual(len(info["target_backups"]), 3)
            self.assertEqual({e["name"] for e in info["target_backups"]}, {e["name"] for e in info["backups"]})
            self.assertTrue(info["target_at"])
            self.assertEqual(info["target_error"], "")
            self.assertTrue((Path(target) / "fremde-datei.zip").exists())
            self.assertFalse([p for p in Path(target).iterdir() if p.name.endswith(".tmp")])

    def test_missing_storage_location_is_reported_and_caught_up_later(self):
        self.make_item()
        with tempfile.TemporaryDirectory() as parent:
            target = Path(parent) / "nas"
            target.mkdir()
            self.client.json("PATCH", "/api/backups", {"target": str(target)})
            target.rmdir()  # Das Netzlaufwerk ist weg.
            name = self.client.json("POST", "/api/backups", {})[1]["name"]
            info = self.client.json("GET", "/api/backups")[1]
            self.assertIn("nicht erreichbar", info["target_error"])
            target.mkdir()  # Wieder da: Der nächste Durchlauf holt die Kopie nach, ohne neuen Stand.
            self.assertIsNone(self.store.auto_backup())
            self.assertTrue((target / name).exists())
            self.assertEqual(self.client.json("GET", "/api/backups")[1]["target_error"], "")

    def test_backup_from_the_storage_location_restores_a_new_install(self):
        self.make_item("Bohrmaschine")
        with tempfile.TemporaryDirectory() as target:
            self.client.json("PATCH", "/api/backups", {"target": target, "interval": 12, "keep": 5})
            name = self.client.json("POST", "/api/backups", {})[1]["name"]
            # Neuer Server, gleiche Freigabe: Speicherort eintragen, Sicherung von dort einspielen.
            with tempfile.TemporaryDirectory() as fresh:
                store = Store(fresh)
                self.assertTrue(store.list_backups()["empty"])
                store.set_backup_settings({"target": target})
                self.assertEqual([e["name"] for e in store.list_backups()["target_backups"]], [name])
                result = store.restore_backup(name, "target")
                self.assertIsNone(result["safety"])  # Eine leere App braucht vorher keine Sicherung.
                state = store.state()
                self.assertEqual([item["name"] for item in state["items"]], ["Bohrmaschine"])
                # Der Speicherort, den das neue Gerät gewählt hat, bleibt. Takt und Aufbewahrung kommen aus der Sicherung.
                settings = store.backup_settings()
                self.assertEqual((settings["target"], settings["interval"], settings["keep"]), (str(Path(target)), 12, 5))
            with self.assertRaises(server_module.ApiError):
                self.store.restore_backup("../" + name, "target")

    def test_restore_from_the_storage_location_needs_one(self):
        self.make_item()
        self.assertEqual(self.client.json("POST", "/api/backups/findling-2026-01-01.zip/restore", {"source": "target"})[0], 404)

    def test_key_pin_and_certificate_stay_out_of_backups(self):
        self.make_item()
        (Path(self.store.data_dir) / "anthropic-key.txt").write_text("geheim")
        (Path(self.store.data_dir) / "pin.txt").write_text("123456")
        name = self.store.create_backup()
        with zipfile.ZipFile(self.store.backup_dir / name) as archive:
            self.assertEqual({n.split("/")[0] for n in archive.namelist()}, {"inventar.sqlite"})


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        site = self.store.state()["sites"][0]["id"]
        room = self.store.create_room({"site_id": site, "name": "Garage"})
        map_record = self.store.create_map({"room_id": room["id"], "name": "Regal"})
        self.place = self.store.create_place({"map_id": map_record["id"], "label": "A", "x": 0, "y": 0, "w": 0.1, "h": 0.1})
        self.store.create_item({"place_id": self.place["id"], "name": "Lack"})
        self.photo = self.store.add_photo(JPEG, self.place["id"])["id"]

    def backups(self):
        folder = Path(self.tmp.name) / "sicherungen"
        return sorted(p.name for p in folder.iterdir() if p.suffix == ".zip") if folder.exists() else []

    def pretend_old_version(self, version="0.1.0"):
        self.store.set_setting("app_version", version)

    def test_same_version_makes_no_backup(self):
        Store(self.tmp.name)
        self.assertEqual(self.backups(), [])

    def test_new_version_saves_the_old_data_first(self):
        self.pretend_old_version()
        again = Store(self.tmp.name)
        names = self.backups()
        self.assertEqual(len(names), 1)
        self.assertIn(f"-vor-{server_module.APP_VERSION}.zip", names[0])
        self.assertEqual(again.list_backups()["backups"][0]["before_version"], server_module.APP_VERSION)
        Store(self.tmp.name)
        self.assertEqual(len(self.backups()), 1)

    def test_version_0_1_0_without_marker_is_saved_too(self):
        with self.store.connect() as db:
            db.execute("DELETE FROM settings WHERE key = 'app_version'")
        Store(self.tmp.name)
        self.assertEqual(len(self.backups()), 1)

    def test_backup_holds_the_state_before_the_database_changes(self):
        if sqlite3.sqlite_version_info < (3, 35):
            self.skipTest("SQLite zu alt")
        with self.store.connect() as db:
            db.execute("ALTER TABLE items DROP COLUMN away")
            db.execute("ALTER TABLE items DROP COLUMN away_since")
        self.pretend_old_version()
        again = Store(self.tmp.name)
        with again.connect() as db:
            self.assertIn("away", [row["name"] for row in db.execute("PRAGMA table_info(items)")])
        name = self.backups()[0]
        with zipfile.ZipFile(Path(self.tmp.name) / "sicherungen" / name) as archive:
            archive.extract("inventar.sqlite", self.tmp.name + "/auszug")
            self.assertIn(f"fotos/{self.photo}.jpg", archive.namelist())
        old = sqlite3.connect(self.tmp.name + "/auszug/inventar.sqlite")
        self.assertNotIn("away", [row[1] for row in old.execute("PRAGMA table_info(items)")])
        self.assertEqual(old.execute("SELECT name FROM items").fetchall(), [("Lack",)])
        old.close()

    def test_update_backup_can_be_restored(self):
        self.pretend_old_version()
        again = Store(self.tmp.name)
        again.delete_item(again.state()["items"][0]["id"])
        again.delete_trash()
        result = again.restore_backup(self.backups()[0])
        self.assertTrue(result["safety"])
        state = again.state()
        self.assertEqual([item["name"] for item in state["items"]], ["Lack"])
        self.assertEqual(state["settings"]["app_version"], server_module.APP_VERSION)

    def test_data_only_in_the_trash_is_still_saved(self):
        self.store.delete_room(self.store.state()["rooms"][0]["id"])
        self.pretend_old_version()
        again = Store(self.tmp.name)
        self.assertEqual(len(self.backups()), 1)
        (Path(self.tmp.name) / "sicherungen" / self.backups()[0]).unlink()
        with again.connect() as db:
            db.execute("DELETE FROM settings WHERE key = 'backup_fingerprint'")
        self.assertTrue(again.auto_backup())

    def test_empty_app_needs_no_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            fresh = Store(folder)
            fresh.set_setting("app_version", "0.0.1")
            Store(folder)
            self.assertFalse((Path(folder) / "sicherungen").exists())

    def test_failed_backup_is_reported_but_the_app_still_starts(self):
        self.pretend_old_version()
        original = Store._write_backup
        Store._write_backup = lambda store, target: (_ for _ in ()).throw(OSError("Platte voll"))
        self.addCleanup(lambda: setattr(Store, "_write_backup", original))
        again = Store(self.tmp.name)
        self.assertIn("Platte voll", again.list_backups()["error"])
        self.assertEqual(len(again.state()["items"]), 1)

    def test_odd_backup_names_stay_refused(self):
        for name in ("findling-2026-01-01-vor-../../x.zip", "findling-2026-01-01-vor-0.1.zip", "findling-2026-01-01-vor-a.b.c.zip"):
            with self.assertRaises(server_module.ApiError):
                self.store.restore_backup(name)

    def test_package_and_program_have_the_same_version(self):
        config = APP.parent / "config.yaml"
        if not config.exists():
            self.skipTest("Kein Paketordner")
        self.assertIn(f'version: "{server_module.APP_VERSION}"', config.read_text())


class PreferenceTests(ServerCase):
    def test_defaults_come_with_the_state(self):
        prefs = self.client.json("GET", "/api/state")[1]["preferences"]
        self.assertEqual(prefs["photo_look"], "gruen")
        self.assertEqual(prefs["dashboard"], {"hidden_rooms": [], "progress": True, "minimap": True, "rooms": True, "low": True, "watch": True, "checkin": True})

    def test_changes_are_checked_and_merged(self):
        status, prefs = self.client.json("PATCH", "/api/preferences", {"photo_look": "blau", "dashboard": {"minimap": False, "hidden_rooms": ["a1", "a1", "b2"]}})
        self.assertEqual(status, 200)
        self.assertEqual((prefs["photo_look"], prefs["dashboard"]["minimap"], prefs["dashboard"]["rooms"]), ("blau", False, True))
        self.assertEqual(prefs["dashboard"]["hidden_rooms"], ["a1", "b2"])
        self.assertEqual(self.client.json("PATCH", "/api/preferences", {"chat": "claude"})[1]["photo_look"], "blau")
        for body in ({"photo_look": "pink"}, {"chat": "gemini"}, {"label_size": "xxl"}, {"dashboard": {"minimap": "nein"}},
                     {"dashboard": {"hidden_rooms": "a1"}}, {"dashboard": {"hidden_rooms": ["x" * 41]}}, ["kein", "objekt"]):
            with self.subTest(body):
                self.assertEqual(self.client.json("PATCH", "/api/preferences", body)[0], 400)

    def test_broken_stored_value_falls_back_to_defaults(self):
        self.store.set_setting("ui_preferences", "{kaputt")
        self.assertEqual(self.store.preferences()["photo_look"], "gruen")
        self.store.set_setting("ui_preferences", json.dumps({"photo_look": "rosa", "dashboard": {"rooms": False, "fremd": 1}}))
        prefs = self.store.preferences()
        self.assertEqual((prefs["photo_look"], prefs["dashboard"]["rooms"]), ("gruen", False))
        self.assertNotIn("fremd", prefs["dashboard"])

    def test_preferences_and_backup_settings_come_back_on_a_fresh_device(self):
        room = self.make_room()
        self.make_place(room=room)
        self.client.json("PATCH", "/api/preferences", {"photo_look": "violett", "label_size": "size-l", "dashboard": {"hidden_rooms": [room["id"]], "low": False}})
        self.client.json("PATCH", "/api/backups", {"interval": 6, "keep": 12})
        name = self.client.json("POST", "/api/backups", {})[1]["name"]
        archive = self.store.backup_dir / name
        with tempfile.TemporaryDirectory() as fresh:
            store = Store(fresh)
            store.restore_upload([archive.read_bytes()])
            prefs = store.preferences()
            self.assertEqual((prefs["photo_look"], prefs["label_size"], prefs["dashboard"]["low"]), ("violett", "size-l", False))
            self.assertEqual(prefs["dashboard"]["hidden_rooms"], [room["id"]])
            settings = store.backup_settings()
            self.assertEqual((settings["interval"], settings["keep"]), (6, 12))

    def test_a_device_keeps_its_own_backup_settings_and_drops_foreign_targets(self):
        room = self.make_room()
        self.make_place(room=room)
        with tempfile.TemporaryDirectory() as target:
            self.client.json("PATCH", "/api/backups", {"target": target, "interval": 6})
            data = self.store.backup_zip()
        with tempfile.TemporaryDirectory() as fresh:
            store = Store(fresh)
            store.restore_upload([data])
            # Den Ordner der Sicherung gibt es hier nicht mehr: Er wird nicht übernommen, der Takt schon.
            self.assertEqual((store.backup_settings()["target"], store.backup_settings()["interval"]), ("", 6))
        with tempfile.TemporaryDirectory() as fresh:
            store = Store(fresh)
            store.set_backup_settings({"interval": 168})
            store.restore_upload([data])
            self.assertEqual(store.backup_settings()["interval"], 168)


class QuickEditTests(ServerCase):
    def setUp(self):
        super().setUp()
        self.map, self.place = self.make_place()
        self.other = self.client.json("POST", "/api/places", {"map_id": self.map["id"], "label": "B", "x": 0, "y": 0, "w": 0.1, "h": 0.1})[1]
        self.items = [self.client.json("POST", "/api/items", {"place_id": self.place["id"], "name": name})[1] for name in ("Lack", "Leim", "Spax")]

    def test_many_changes_in_one_go(self):
        lack, leim, spax = self.items
        status, result = self.client.json("POST", "/api/items/batch", {
            "updates": [
                {"id": lack["id"], "name": "Lack anthrazit", "fill": "wenig", "note": "RAL 7016"},
                {"id": leim["id"], "place_id": self.other["id"]},
                {"id": spax["id"], "fill": "leer"},
            ],
            "delete": [spax["id"]],
        })
        self.assertEqual((status, result), (200, {"updated": 2, "deleted": 1}))
        items = {item["id"]: item for item in self.client.json("GET", "/api/state")[1]["items"]}
        self.assertEqual((items[lack["id"]]["name"], items[lack["id"]]["fill"], items[lack["id"]]["note"]), ("Lack anthrazit", "wenig", "RAL 7016"))
        self.assertEqual(items[leim["id"]]["place_id"], self.other["id"])
        self.assertNotIn(spax["id"], items)
        self.assertEqual(self.client.json("GET", "/api/state")[1]["trash_count"], 1)

    def test_nothing_happens_if_one_change_is_wrong(self):
        lack, leim, _ = self.items
        for body in (
            {"updates": [{"id": lack["id"], "fill": "wenig"}, {"id": leim["id"], "fill": "halb"}]},
            {"updates": [{"id": lack["id"], "fill": "wenig"}, {"id": leim["id"], "name": "  "}]},
            {"updates": [{"id": lack["id"], "fill": "wenig"}, {"id": leim["id"], "place_id": "gibt-es-nicht"}]},
            {"updates": [{"id": lack["id"], "fill": "wenig"}], "delete": ["gibt-es-nicht"]},
            {"updates": "kaputt"},
        ):
            with self.subTest(body):
                self.assertIn(self.client.json("POST", "/api/items/batch", body)[0], (400, 404))
                items = {item["id"]: item for item in self.client.json("GET", "/api/state")[1]["items"]}
                self.assertEqual(items[lack["id"]]["fill"], "ok")
                self.assertEqual(len(items), 3)


class LanguageTests(ServerCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(server_module.set_language, "de")

    def test_german_is_the_default(self):
        self.assertIn(b'<html lang="de">', self.client.request("GET", "/")[1])
        self.assertIn("Hinweis", recognition.chat_prompt())

    def test_english_page_texts_and_prompt(self):
        server_module.set_language("en")
        self.assertIn(b'<html lang="en">', self.client.request("GET", "/")[1])
        self.assertIn(b"Spot", self.client.request("GET", "/lang/en.js")[1])
        state = self.client.json("GET", "/api/state")[1]
        self.assertIn("You help inventory", state["recognition"]["chat_prompt"])
        self.assertIn("The app couldn't read", state["recognition"]["chat_retry"])
        levels = state["achievements"]["levels"]
        self.assertEqual([entry["label"] for entry in levels], ["Recording", "Sorting", "Care", "Using"])
        self.assertEqual(levels[0]["title"], "Newcomer")
        csv_text = self.client.request("GET", "/api/export.csv")[1].decode("utf-8-sig")
        self.assertTrue(csv_text.startswith("Name;Also called;Stock level"))

    def test_english_recommendations_and_share_file(self):
        server_module.set_language("en")
        _, place = self.make_place()
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack", "fill": "wenig"})
        report = self.client.json("GET", "/api/report")[1]
        titles = [rec["title"] for rec in report["recommendations"]]
        self.assertIn("One thing is running low", titles)
        self.assertTrue(any("not confirmed yet" in title for title in titles))
        html_page = self.client.request("GET", "/api/share.html")[1].decode()
        self.assertIn('<html lang="en">', html_page)
        self.assertIn("Please bring", html_page)
        self.assertIn("Lack (low)", html_page)

    def test_english_chat_answers_are_understood(self):
        answer = '{"items": [{"name": "Wood glue", "fill": "low", "certainty": "likely"}], "not_recognized": ""}'
        items = recognition.parse_chat_answer(answer)["items"] if hasattr(recognition, "parse_chat_answer") else None
        if items is None:
            self.skipTest("Kein öffentlicher Parser")
        self.assertEqual((items[0]["fill"], items[0]["certainty"]), ("wenig", "wahrscheinlich"))
        with self.assertRaises(recognition.RecognitionError):
            recognition.parse_chat_answer("NO PHOTO")

    def test_home_assistant_option_sets_the_language(self):
        with tempfile.TemporaryDirectory() as folder:
            options = Path(folder) / "options.json"
            options.write_text(json.dumps({"language": "en"}))
            server_module.set_language(str(server_module.read_app_options(str(options)).get("language")))
            self.assertEqual(server_module.LANGUAGE, "en")
        server_module.set_language("fr")
        self.assertEqual(server_module.LANGUAGE, "de")


class FrontendSourceTests(unittest.TestCase):
    """Fehler, die erst im Browser auffallen würden: ein Wert, der sich beim Anlegen selbst braucht."""

    def test_no_top_level_constant_refers_to_itself(self):
        source = (APP / "static" / "app.js").read_text(encoding="utf-8")
        for match in re.finditer(r"^const (\w+) = (.+);$", source, re.M):
            name, value = match.groups()
            # Texte in Anführungszeichen zählen nicht.
            code = re.sub(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'", '""', value)
            self.assertIsNone(re.search(rf"\b{name}\b", code), match.group(0))

    def test_locale_is_set_for_both_languages(self):
        source = (APP / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('const LOCALE = LANG === "en" ? "en-GB" : "de-DE";', source)


class DetailModeTests(ServerCase):
    def upload(self, query=""):
        status, body = self.client.request("POST", f"/api/photos{query}", raw=JPEG)[:2]
        return status, json.loads(body)

    def bitbox(self):
        _, place = self.make_place()
        return self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Bitbox"})[1], place

    def item_in_state(self, item_id):
        return next((item for item in self.client.json("GET", "/api/state")[1]["items"] if item["id"] == item_id), None)

    def test_contents_are_cleaned_and_saved(self):
        box, _ = self.bitbox()
        status, saved = self.client.json("PATCH", f"/api/items/{box['id']}", {"details": ["Bit T20", "  bit   t20 ", "", "PH2", "Innensechskant 4 mm"]})
        self.assertEqual(status, 200)
        self.assertEqual(saved["details"], "Bit T20\nPH2\nInnensechskant 4 mm")
        self.assertEqual(self.client.json("PATCH", f"/api/items/{box['id']}", {"details": "Bit T25\nBit T30"})[1]["details"], "Bit T25\nBit T30")

    def test_invalid_contents_are_refused(self):
        box, _ = self.bitbox()
        for details in (["x" * 81], [f"Teil {n}" for n in range(151)], [3], {"a": 1}):
            with self.subTest(details=str(details)[:30]):
                self.assertEqual(self.client.json("PATCH", f"/api/items/{box['id']}", {"details": details})[0], 400)

    def test_detail_photo_belongs_to_the_item_not_the_place(self):
        box, place = self.bitbox()
        status, photo = self.upload(f"?item_id={box['id']}")
        self.assertEqual(status, 201)
        state = self.client.json("GET", "/api/state")[1]
        self.assertEqual(next(i for i in state["items"] if i["id"] == box["id"])["photos"], [photo["id"]])
        self.assertEqual(next(p for p in state["places"] if p["id"] == place["id"])["photos"], [])
        self.assertEqual(self.upload("?item_id=" + "0" * 32)[0], 404)
        self.assertEqual(self.upload(f"?item_id={box['id']}&place_id={place['id']}")[0], 400)

    def test_item_goes_to_the_trash_with_its_detail_photos_and_comes_back(self):
        box, _ = self.bitbox()
        photo = self.upload(f"?item_id={box['id']}")[1]["id"]
        self.client.json("PATCH", f"/api/items/{box['id']}", {"details": ["Bit T20"]})
        trash_id = self.client.json("DELETE", f"/api/items/{box['id']}")[1]["trash_id"]
        self.assertEqual(self.client.request("GET", f"/fotos/{photo}")[0], 404)
        self.assertEqual(self.client.json("POST", f"/api/trash/{trash_id}/restore", {})[0], 200)
        back = self.item_in_state(box["id"])
        self.assertEqual((back["photos"], back["details"]), ([photo], "Bit T20"))
        self.assertEqual(self.client.request("GET", f"/fotos/{photo}")[0], 200)

    def test_single_detail_photo_returns_only_to_its_item(self):
        box, _ = self.bitbox()
        photo = self.upload(f"?item_id={box['id']}")[1]["id"]
        trash_id = self.client.json("DELETE", f"/api/photos/{photo}")[1]["trash_id"]
        entry = next(e for e in self.client.json("GET", "/api/trash")[1]["entries"] if e["id"] == trash_id)
        self.assertFalse(entry["parent_missing"])
        self.assertIn("Bitbox", entry["detail"] + entry["label"])
        self.assertEqual(self.client.json("POST", f"/api/trash/{trash_id}/restore", {})[0], 200)
        self.assertEqual(self.item_in_state(box["id"])["photos"], [photo])

    def test_merging_twins_keeps_contents_and_photos(self):
        box, place = self.bitbox()
        _, other = self.make_place(label="Fach B", room=self.make_room("Garage"))
        twin = self.client.json("POST", "/api/items", {"place_id": other["id"], "name": "Bitbox", "details": ["PH2"]})[1]
        photo = self.upload(f"?item_id={box['id']}")[1]["id"]
        self.client.json("PATCH", f"/api/items/{box['id']}", {"details": ["Bit T20", "PH2"]})
        self.assertEqual(self.client.json("POST", "/api/items/move", {"item_ids": [box["id"]], "place_id": other["id"]})[1]["merged"], 1)
        merged = self.item_in_state(twin["id"])
        self.assertEqual((merged["details"], merged["photos"]), ("PH2\nBit T20", [photo]))

    def test_contents_appear_in_table_and_share_file(self):
        box, _ = self.bitbox()
        self.client.json("PATCH", f"/api/items/{box['id']}", {"details": ["Bit T20", "PH2"]})
        self.assertIn("Bit T20 | PH2", self.client.request("GET", "/api/export.csv")[1].decode("utf-8"))


PDF = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n%%EOF\n"


class PassportTests(ServerCase):
    """Steckbrief: Angaben, Dokumente, Verleih, Wartung und Verlauf je Eintrag."""

    def drill(self, name="Akkuschrauber", place=None):
        place = place or self.make_place()[1]
        return self.client.json("POST", "/api/items", {"place_id": place["id"], "name": name})[1]

    def item_in_state(self, item_id):
        return next((item for item in self.client.json("GET", "/api/state")[1]["items"] if item["id"] == item_id), None)

    def add_document(self, item_id, data=PDF, kind="anleitung", name=None):
        request = urllib.request.Request(
            f"{self.client.base}/api/items/{item_id}/documents?kind={kind}", data=data, method="POST",
            headers={"X-Werkstatt": "1", "Host": "localhost", **({"X-Datei-Name": name} if name else {})},
        )
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        return response.status if hasattr(response, "status") else response.code, json.loads(response.read())

    def test_passport_is_optional_and_quick_entry_stays_unchanged(self):
        item = self.drill()
        self.assertEqual(self.item_in_state(item["id"])["passport"], {})
        self.assertEqual(self.item_in_state(item["id"])["documents"], [])
        self.assertEqual(self.item_in_state(item["id"])["log"], [])

    def test_passport_is_cleaned_merged_and_can_be_cleared(self):
        item = self.drill()
        status, saved = self.client.json("PATCH", f"/api/items/{item['id']}", {"passport": {
            "maker": "  Bosch  ", "model": "GSR 18V-55", "serial": "SN 123", "bought": "2024-03-01",
            "warranty": "2027-03-01", "link": "https://www.bosch-diy.com", "service_months": 12,
            "usage": "Akku einrasten lassen.\r\nDrehmoment wählen.", "accessories": "2 Akkus, Ladegerät, Koffer",
        }})
        self.assertEqual(status, 200)
        passport = self.item_in_state(item["id"])["passport"]
        self.assertEqual(passport["maker"], "Bosch")
        self.assertEqual(passport["usage"], "Akku einrasten lassen.\nDrehmoment wählen.")
        self.client.json("PATCH", f"/api/items/{item['id']}", {"passport": {"price": "129 €", "serial": ""}})
        passport = self.item_in_state(item["id"])["passport"]
        self.assertEqual((passport["price"], passport["model"]), ("129 €", "GSR 18V-55"))
        self.assertNotIn("serial", passport)

    def test_invalid_passport_values_are_refused(self):
        item = self.drill()
        for passport in (
            {"link": "javascript:alert(1)"}, {"link": "data:text/html,x"}, {"link": "https://a.de/\"><script>"},
            {"bought": "2024-02-30"}, {"bought": "01.03.2024"}, {"warranty": "0001-01-01"},
            {"service_months": 0.5}, {"service_months": 241}, {"service_months": True}, {"service_months": "12"},
            {"maker": "x" * 61}, {"usage": "x" * 3001}, {"unbekannt": "x"}, {"maker": 3}, "Bosch",
        ):
            with self.subTest(passport=str(passport)[:40]):
                self.assertEqual(self.client.json("PATCH", f"/api/items/{item['id']}", {"passport": passport})[0], 400)
        self.assertEqual(self.item_in_state(item["id"])["passport"], {})

    def test_next_service_counts_from_last_service_purchase_or_creation(self):
        item = self.drill()
        self.client.json("PATCH", f"/api/items/{item['id']}", {"passport": {"service_months": 6, "bought": "2024-08-31"}})
        self.assertEqual(self.item_in_state(item["id"])["next_service"], "2025-02-28")
        status, _ = self.client.json("POST", f"/api/items/{item['id']}/service", {"date": "2025-03-10", "note": "Kohlen getauscht"})
        self.assertEqual(status, 200)
        state = self.item_in_state(item["id"])
        self.assertEqual((state["passport"]["service_last"], state["next_service"]), ("2025-03-10", "2025-09-10"))
        self.assertEqual((state["log"][0]["kind"], state["log"][0]["text"], state["log"][0]["day"]), ("wartung", "Kohlen getauscht", "2025-03-10"))
        # Eine nachgetragene ältere Wartung verschiebt den letzten Termin nicht zurück.
        self.client.json("POST", f"/api/items/{item['id']}/service", {"date": "2024-12-01"})
        self.assertEqual(self.item_in_state(item["id"])["passport"]["service_last"], "2025-03-10")
        self.assertEqual(self.client.json("POST", f"/api/items/{item['id']}/service", {"date": "morgen"})[0], 400)
        self.assertEqual(self.client.json("POST", f"/api/items/{'0' * 32}/service", {})[0], 404)
        self.assertEqual(server_module.next_service({"service_months": 1}, 0), "1970-02-01")

    def test_lending_records_whom_and_until_when_and_keeps_a_history(self):
        item = self.drill()
        status, saved = self.client.json("PATCH", f"/api/items/{item['id']}", {"away": "Verliehen", "away_to": " Nachbar  Max ", "away_due": "2026-12-01"})
        self.assertEqual(status, 200)
        self.assertEqual((saved["away"], saved["away_to"], saved["away_due"]), ("Verliehen", "Nachbar Max", "2026-12-01"))
        self.assertIsNotNone(saved["away_since"])
        # Nur das Datum ändern legt keine neue Zeile an, ein anderer Entleiher schon.
        self.client.json("PATCH", f"/api/items/{item['id']}", {"away_due": "2026-12-15"})
        self.client.json("PATCH", f"/api/items/{item['id']}", {"away": "Verliehen", "away_to": "Erika"})
        state = self.item_in_state(item["id"])
        self.assertEqual((state["away_to"], state["away_due"]), ("Erika", ""))
        status, back = self.client.json("PATCH", f"/api/items/{item['id']}", {"away": ""})
        self.assertEqual((back["away"], back["away_to"], back["away_due"], back["away_since"]), ("", "", "", None))
        log = [(entry["kind"], entry["who"]) for entry in self.item_in_state(item["id"])["log"]]
        self.assertEqual(log, [("zurueck", "Erika"), ("weg", "Erika"), ("weg", "Nachbar Max")])

    def test_invalid_lending_values_are_refused(self):
        item = self.drill()
        self.assertEqual(self.client.json("PATCH", f"/api/items/{item['id']}", {"away_to": "Max"})[0], 400)
        self.assertEqual(self.client.json("PATCH", f"/api/items/{item['id']}", {"away": "Verliehen", "away_due": "bald"})[0], 400)
        self.assertEqual(self.client.json("PATCH", f"/api/items/{item['id']}", {"away": "Verliehen", "away_to": "x" * 61})[0], 400)
        self.assertEqual(self.item_in_state(item["id"])["away"], "")

    def test_notes_in_the_history_can_be_added_and_removed(self):
        item = self.drill()
        self.assertEqual(self.client.json("POST", f"/api/items/{item['id']}/log", {"text": "Bohrfutter klemmt"})[0], 201)
        self.assertEqual(self.client.json("POST", f"/api/items/{item['id']}/log", {"text": ""})[0], 400)
        entry = self.item_in_state(item["id"])["log"][0]
        self.assertEqual((entry["kind"], entry["text"]), ("notiz", "Bohrfutter klemmt"))
        for bad in ("abc", "1%20OR%201=1", "9" * 20):
            self.assertEqual(self.client.json("DELETE", f"/api/log/{bad}")[0], 404)
        self.assertEqual(self.client.json("DELETE", f"/api/log/{entry['id']}")[0], 200)
        self.assertEqual(self.item_in_state(item["id"])["log"], [])

    def test_history_keeps_only_the_newest_lines(self):
        item = self.drill()
        keep, server_module.LOG_KEEP = server_module.LOG_KEEP, 3
        try:
            for number in range(5):
                self.client.json("POST", f"/api/items/{item['id']}/log", {"text": f"Notiz {number}"})
        finally:
            server_module.LOG_KEEP = keep
        self.assertEqual([entry["text"] for entry in self.item_in_state(item["id"])["log"]], ["Notiz 4", "Notiz 3", "Notiz 2"])

    def test_documents_are_checked_and_served_safely(self):
        item = self.drill()
        status, document = self.add_document(item["id"], name="Bedienungsanleitung%20GSR_18V.pdf")
        self.assertEqual(status, 201)
        self.assertEqual((document["title"], document["kind"], document["ext"]), ("Bedienungsanleitung GSR 18V", "anleitung", ".pdf"))
        status, payload, headers = self.client.request("GET", f"/api/documents/{document['id']}")
        self.assertEqual((status, payload), (200, PDF))
        self.assertEqual(headers["Content-Type"], "application/pdf")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertTrue(headers["Content-Disposition"].startswith("inline;"))
        self.assertNotIn("script-src", headers["Content-Security-Policy"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertTrue(self.client.request("GET", f"/api/documents/{document['id']}?download=1")[2]["Content-Disposition"].startswith("attachment;"))
        status, image = self.add_document(item["id"], data=JPEG, kind="rechnung")
        self.assertEqual((status, image["title"]), (201, "Rechnung"))
        self.assertIn("sandbox", self.client.request("GET", f"/api/documents/{image['id']}")[2]["Content-Security-Policy"])
        for data in (b"<html><script>alert(1)</script></html>", b"<svg onload=alert(1)>", b"", b"PK\x03\x04zip"):
            with self.subTest(data=data[:10]):
                self.assertIn(self.add_document(item["id"], data=data)[0], (400, 415))
        self.assertEqual(self.add_document(item["id"], kind="boese")[0], 400)
        self.assertEqual(self.add_document("0" * 32)[0], 404)
        for bad in ("../inventar.sqlite", "0" * 32, document["id"] + ".pdf"):
            self.assertEqual(self.client.request("GET", f"/api/documents/{bad}")[0], 404)
        self.assertEqual(len(self.item_in_state(item["id"])["documents"]), 2)

    def test_document_title_and_kind_can_be_changed(self):
        item = self.drill()
        document = self.add_document(item["id"])[1]
        status, saved = self.client.json("PATCH", f"/api/documents/{document['id']}", {"title": "Garantiekarte", "kind": "garantie"})
        self.assertEqual((status, saved["title"], saved["kind"]), (200, "Garantiekarte", "garantie"))
        self.assertEqual(self.client.json("PATCH", f"/api/documents/{document['id']}", {"kind": "boese"})[0], 400)
        self.assertEqual(self.client.json("PATCH", f"/api/documents/{document['id']}", {"title": ""})[0], 400)

    def test_documents_per_item_are_limited(self):
        item = self.drill()
        limit, server_module.MAX_DOCUMENTS_PER_ITEM = server_module.MAX_DOCUMENTS_PER_ITEM, 2
        try:
            self.add_document(item["id"])
            self.add_document(item["id"])
            self.assertEqual(self.add_document(item["id"])[0], 409)
        finally:
            server_module.MAX_DOCUMENTS_PER_ITEM = limit

    def test_item_goes_to_the_trash_with_documents_and_history_and_comes_back(self):
        item = self.drill()
        document = self.add_document(item["id"])[1]
        self.client.json("PATCH", f"/api/items/{item['id']}", {"passport": {"maker": "Bosch"}, "away": "Verliehen", "away_to": "Max"})
        trash_id = self.client.json("DELETE", f"/api/items/{item['id']}")[1]["trash_id"]
        self.assertEqual(self.client.request("GET", f"/api/documents/{document['id']}")[0], 404)
        entry = next(e for e in self.client.json("GET", "/api/trash")[1]["entries"] if e["id"] == trash_id)
        self.assertEqual(entry["counts"]["documents"], 1)
        self.assertEqual(self.client.json("POST", f"/api/trash/{trash_id}/restore", {})[0], 200)
        back = self.item_in_state(item["id"])
        self.assertEqual(([d["id"] for d in back["documents"]], back["passport"], back["away_to"]), ([document["id"]], {"maker": "Bosch"}, "Max"))
        self.assertEqual(len(back["log"]), 1)
        self.assertEqual(self.client.request("GET", f"/api/documents/{document['id']}")[0], 200)

    def test_single_document_returns_only_to_its_item(self):
        item = self.drill()
        document = self.add_document(item["id"], name="Rechnung Baumarkt.pdf")[1]
        trash_id = self.client.json("DELETE", f"/api/documents/{document['id']}")[1]["trash_id"]
        entry = next(e for e in self.client.json("GET", "/api/trash")[1]["entries"] if e["id"] == trash_id)
        self.assertEqual((entry["kind"], entry["label"], entry["parent_missing"]), ("document", "Rechnung Baumarkt", False))
        self.assertIn("Akkuschrauber", entry["detail"])
        status, result = self.client.json("POST", f"/api/trash/{trash_id}/restore", {})
        self.assertEqual((status, result["href"]), (200, f"#/steckbrief/{item['id']}"))
        # Ohne den Eintrag kann das Dokument nicht zurück. Endgültig gelöscht ist auch die Datei weg.
        trash_id = self.client.json("DELETE", f"/api/documents/{document['id']}")[1]["trash_id"]
        self.client.json("DELETE", f"/api/items/{item['id']}")
        self.assertEqual(self.client.json("POST", f"/api/trash/{trash_id}/restore", {})[0], 409)
        self.client.json("DELETE", "/api/trash")
        self.assertEqual(list(self.store.document_dir.iterdir()), [])

    def test_merging_twins_keeps_documents_history_and_passport(self):
        item = self.drill()
        _, other = self.make_place(label="Fach B", room=self.make_room("Garage"))
        twin = self.drill(place=other)
        document = self.add_document(item["id"])[1]
        self.client.json("PATCH", f"/api/items/{item['id']}", {"passport": {"maker": "Bosch", "serial": "A1"}})
        self.client.json("PATCH", f"/api/items/{twin['id']}", {"passport": {"maker": "Makita"}})
        self.client.json("POST", f"/api/items/{item['id']}/log", {"text": "Neuer Akku"})
        self.assertEqual(self.client.json("POST", "/api/items/move", {"item_ids": [item["id"]], "place_id": other["id"]})[1]["merged"], 1)
        merged = self.item_in_state(twin["id"])
        self.assertEqual(merged["passport"], {"maker": "Makita", "serial": "A1"})
        self.assertEqual(([d["id"] for d in merged["documents"]], merged["log"][0]["text"]), ([document["id"]], "Neuer Akku"))

    def test_backup_carries_documents_and_restores_them(self):
        item = self.drill()
        document = self.add_document(item["id"])[1]
        backup = self.store.backup_zip()
        self.assertIn(f"dokumente/{document['id']}.pdf", zipfile.ZipFile(io.BytesIO(backup)).namelist())
        self.client.json("DELETE", f"/api/items/{item['id']}")
        self.client.json("DELETE", "/api/trash")
        self.assertEqual(list(self.store.document_dir.iterdir()), [])
        # Fremde Namen in der Sicherung werden nicht entpackt.
        buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(backup)) as source, zipfile.ZipFile(buffer, "w") as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
            target.writestr("dokumente/../../boese.pdf", PDF)
            target.writestr("dokumente/boese.html", b"<script>")
        self.store.restore_upload([buffer.getvalue()])
        self.assertEqual(self.client.request("GET", f"/api/documents/{document['id']}")[1], PDF)
        self.assertEqual(sorted(p.name for p in self.store.document_dir.iterdir()), [f"{document['id']}.pdf"])
        self.assertFalse((Path(self.tmp.name).parent / "boese.pdf").exists())

    def test_passport_appears_in_table_and_share_file(self):
        item = self.drill()
        self.client.json("PATCH", f"/api/items/{item['id']}", {
            "passport": {"maker": "Bosch", "model": "GSR 18V-55", "serial": "SN-77", "bought": "2024-01-15", "service_months": 12},
            "away": "Verliehen", "away_to": "Max", "away_due": "2026-12-01",
        })
        self.add_document(item["id"])
        table = self.client.request("GET", "/api/export.csv")[1].decode("utf-8")
        row = next(line for line in table.splitlines() if line.startswith("Akkuschrauber"))
        for value in ("Max", "2026-12-01", "Bosch", "GSR 18V-55", "SN-77", "2024-01-15", "2025-01-15", ";1"):
            self.assertIn(value, row)
        self.assertIn("Bosch · GSR 18V-55", self.client.request("GET", "/api/share.html")[1].decode("utf-8"))


class ShoppingPdfTests(ServerCase):
    def test_shopping_list_comes_as_a_pdf_to_view_and_share(self):
        _, place = self.make_place()
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Spax 4 x 40 (Teilgewinde)", "fill": "leer", "note": "Torx, 200 Stück"})
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack", "fill": "voll"})
        self.client.json("POST", "/api/shopping", {"name": "Holzleim 750 g für 12 €"})
        status, payload, headers = self.client.request("GET", "/api/mitbringliste.pdf")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/pdf")
        self.assertTrue(headers["Content-Disposition"].startswith("inline;"))
        self.assertNotIn("script-src", headers["Content-Security-Policy"])
        self.assertTrue(payload.startswith(b"%PDF-1.4") and payload.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"Spax 4 x 40 \\(Teilgewinde\\)", payload)
        self.assertIn("Holzleim 750 g für 12 €".encode("cp1252"), payload)
        self.assertIn(b"leer, Torx, 200 St", payload)
        self.assertNotIn(b"Lack", payload)

    def test_long_shopping_list_gets_more_pages(self):
        for number in range(60):
            self.client.json("POST", "/api/shopping", {"name": f"Wunsch {number}"})
        payload = self.client.request("GET", "/api/mitbringliste.pdf")[1]
        self.assertGreaterEqual(payload.count(b"/Type /Page "), 2)
        self.assertIn(b"Seite 1 von", payload)


class DeviceConditionTests(ServerCase):
    """Geräte haben statt Füllstand einen Zustand auf derselben Skala und landen nie auf der Mitbringliste."""

    def test_scale_is_saved_and_checked(self):
        _, place = self.make_place()
        status, drill = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Bohrmaschine", "scale": "state", "fill": "leer"})
        self.assertEqual((status, drill["scale"], drill["fill"]), (201, "state", "leer"))
        paint = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack"})[1]
        self.assertEqual(paint["scale"], "fill")
        self.assertEqual(self.client.json("PATCH", f"/api/items/{paint['id']}", {"scale": "gerät"})[0], 400)
        self.assertEqual(self.client.json("PATCH", f"/api/items/{paint['id']}", {"scale": "state"})[1]["scale"], "state")
        self.assertEqual(self.client.json("POST", "/api/items/batch", {"updates": [{"id": paint["id"], "scale": "fill"}]})[0], 200)
        self.assertEqual(self.client.json("POST", "/api/items/batch", {"updates": [{"id": paint["id"], "scale": "x"}]})[0], 400)

    def test_broken_devices_stay_off_the_shopping_list_but_show_their_condition(self):
        _, place = self.make_place()
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Bohrmaschine", "scale": "state", "fill": "leer"})
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Holzleim", "fill": "wenig"})
        pdf = self.client.request("GET", "/api/mitbringliste.pdf")[1]
        self.assertIn(b"Holzleim", pdf)
        self.assertNotIn(b"Bohrmaschine", pdf)
        share = self.client.request("GET", "/api/share.html")[1].decode("utf-8")
        shopping = share.split("<h2>Bitte mitbringen</h2>")[1].split("</ul>")[0]
        self.assertIn("Holzleim", shopping)
        self.assertNotIn("Bohrmaschine", shopping)
        self.assertIn("<strong>Bohrmaschine</strong> <em>kaputt</em>", share)
        table = self.client.request("GET", "/api/export.csv")[1].decode("utf-8")
        self.assertIn("Bohrmaschine;;kaputt;", table)
        self.assertIn("Holzleim;;wenig;", table)
        report = self.client.json("GET", "/api/report")[1]
        self.assertEqual((report["fill"]["wenig"], report["fill"]["leer"], report["condition"]["leer"]), (1, 0, 1))
        shopping_rec = next(rec for rec in report["recommendations"] if rec["kind"] == "shopping")
        self.assertEqual([item["name"] for item in shopping_rec["items"]], ["Holzleim"])


class ImportTests(ServerCase):
    """Massenimport: Vorlage, Prüfung ohne Änderung, Übernahme alles oder nichts."""

    def send(self, text, apply=False, encoding="utf-8"):
        status, payload, _ = self.client.request("POST", "/api/import" + ("?apply=1" if apply else ""), raw=text.encode(encoding))
        return status, json.loads(payload)

    def state(self):
        return self.client.json("GET", "/api/state")[1]

    def test_template_can_be_imported_unchanged(self):
        status, template, headers = self.client.request("GET", "/api/import-vorlage.csv")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        text = template.decode("utf-8-sig")
        self.assertTrue(text.startswith("Haus oder Grundstück;Raum;Schrank oder Regal;Platz;Name;Anzahl;Gerät"))
        status, check = self.send(text)
        self.assertEqual(status, 200)
        self.assertEqual((check["errors"], check["applied"]), ([], False))
        self.assertEqual((check["rooms"], check["maps"], check["places"], check["items_new"]), (2, 4, 5, 5))
        self.assertEqual(self.state()["items"], [])  # Die Prüfung ändert nichts.
        status, done = self.send(text, apply=True)
        self.assertEqual((status, done["applied"]), (200, True))
        items = {item["name"]: item for item in self.state()["items"]}
        drill = items["Akkuschrauber"]
        self.assertEqual((drill["scale"], drill["fill"], drill["passport"]["maker"], drill["passport"]["bought"]), ("state", "ok", "Bosch", "2024-03-01"))
        self.assertEqual(items["Bitbox"]["details"], "Bit T20\nBit T25\nPH2")
        self.assertEqual((items["Rasenmäher"]["scale"], items["Rasenmäher"]["fill"]), ("state", "wenig"))
        self.assertEqual((items["Holzschrauben 4 x 40"]["scale"], items["Holzschrauben 4 x 40"]["fill"]), ("fill", "wenig"))
        self.assertEqual((items["Schraubzwinge 300 mm"]["quantity"], items["Bitbox"]["quantity"]), (4, 1))
        places = self.state()["places"]
        self.assertTrue(all(place["surveyed"] for place in places))
        self.assertTrue(all(0 <= place["x"] and place["x"] + place["w"] <= 1 and place["y"] + place["h"] <= 1 for place in places))

    def test_second_import_updates_instead_of_duplicating(self):
        text = "Raum;Schrank;Platz;Name;Füllstand\nKeller;Regal;Fach 1;Farbe weiß;voll\n"
        self.send(text, apply=True)
        status, done = self.send("Raum;Schrank;Platz;Name;Füllstand\nkeller;REGAL;fach 1;Farbe Weiß;leer\nKeller;Regal;Fach 2;Pinsel;\n", apply=True)
        self.assertEqual((status, done["items_new"], done["items_updated"], done["rooms"], done["places"]), (200, 1, 1, 0, 1))
        items = {item["name"]: item for item in self.state()["items"]}
        self.assertEqual((len(items), items["Farbe weiß"]["fill"], items["Pinsel"]["fill"]), (2, "leer", "ok"))

    def test_one_bad_row_changes_nothing_and_names_the_line(self):
        text = "Raum;Schrank;Name;Zustand;Kaufdatum\nKeller;Regal;Bohrer;ok;\nKeller;Regal;Säge;halb voll;\nKeller;Regal;;ok;\nKeller;Regal;Hobel;ok;31.02.2024\n"
        status, done = self.send(text, apply=True)
        self.assertEqual((status, done["applied"]), (200, False))
        self.assertEqual([error["line"] for error in done["errors"]], [3, 4, 5])
        self.assertIn("halb voll", done["errors"][0]["message"])
        self.assertEqual((self.state()["rooms"], self.state()["items"]), ([], []))

    def test_own_export_can_be_read_back_with_addresses(self):
        _, place = self.make_place()
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Kreissäge", "scale": "state", "fill": "leer"})
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "-Profil", "fill": "wenig"})
        export = self.client.request("GET", "/api/export.csv")[1].decode("utf-8-sig")
        export = export.replace(";kaputt;", ";in Ordnung;")
        status, done = self.send(export, apply=True)
        self.assertEqual((status, done["errors"], done["items_new"], done["items_updated"]), (200, [], 0, 2))
        self.assertIn("Gerade woanders", done["ignored"])
        items = {item["name"]: item for item in self.state()["items"]}
        self.assertEqual((items["Kreissäge"]["fill"], items["-Profil"]["fill"], len(items)), ("ok", "wenig", 2))

    def test_excel_style_files_and_sites_are_understood(self):
        text = "Haus oder Grundstück,Raum,Schrank oder Regal,Name,Gerät,Zustand\nFerienhaus,Schuppen,Regal,Heckenschere,ja,defekt\n"
        status, done = self.send(text, apply=True, encoding="cp1252")
        self.assertEqual((status, done["sites"], done["errors"]), (200, 1, []))
        state = self.state()
        self.assertIn("Ferienhaus", [site["name"] for site in state["sites"]])
        self.assertEqual((state["items"][0]["scale"], state["items"][0]["fill"]), ("state", "leer"))

    def test_invalid_tables_are_refused(self):
        for text in ("", "Foo;Bar\n1;2\n", "Name\nBohrer\n", "Raum;Schrank;Name\n" + "Keller;Regal;Ding\n" * 5001):
            with self.subTest(text=text[:20]):
                self.assertEqual(self.send(text)[0], 400)
        self.assertEqual(self.send("Raum;Schrank;Name;Gerät\nKeller;Regal;Ding;vielleicht\n")[1]["errors"][0]["line"], 2)
        with self.assertRaises(server_module.ApiError) as raised:
            server_module.read_import_table(b"Raum;Schrank;Name\n" + b"x" * (server_module.MAX_IMPORT_BYTES + 10))
        self.assertEqual(raised.exception.status, 413)
        self.assertEqual(self.client.request("POST", "/api/import", raw=b"Raum;Schrank;Name\nA;B;C\n", marker=False)[0], 403)

    def test_backup_is_taken_before_an_import_changes_data(self):
        _, place = self.make_place()
        self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack"})
        done = self.send("Raum;Schrank;Name\nKeller;Regal;Dübel\n", apply=True)[1]
        self.assertTrue(done["backup"])
        self.assertIn(done["backup"], [entry["name"] for entry in self.client.json("GET", "/api/backups")[1]["backups"]])


class CareMilestoneTests(ServerCase):
    """Belohnt wird auch Ordnen, Aussortieren, Pflegen, Reparieren, Warten und Benutzen, nicht nur Sammeln."""

    def earned(self):
        return {entry["key"] for entry in self.client.json("GET", "/api/state")[1]["achievements"]["earned"]}

    def test_care_and_use_earn_milestones(self):
        _, place = self.make_place()
        _, other = self.make_place(name="Regal 3", label="Fach", room=self.make_room("Garage"))
        drill = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Bohrmaschine", "scale": "state", "fill": "leer"})[1]
        glue = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Leim"})[1]
        self.client.json("POST", "/api/items", {"place_id": other["id"], "name": "Leim"})
        waste = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Alte Dose"})[1]
        self.assertFalse(self.earned() & {"first_move", "first_merge", "first_care", "first_repair", "first_lend", "first_sorted_out", "first_service"})
        self.client.json("PATCH", f"/api/items/{drill['id']}", {"fill": "ok"})
        self.client.json("PATCH", f"/api/items/{drill['id']}", {"note": "Kohlen neu"})
        self.client.json("POST", f"/api/items/{drill['id']}/service", {})
        self.client.json("PATCH", f"/api/items/{drill['id']}", {"away": "Verliehen", "away_to": "Max"})
        self.client.json("POST", "/api/items/move", {"item_ids": [glue["id"]], "place_id": other["id"]})
        self.client.json("PATCH", f"/api/items/{drill['id']}", {"place_id": other["id"]})
        self.client.json("DELETE", f"/api/items/{waste['id']}")
        earned = self.earned()
        for key in ("first_move", "first_merge", "first_care", "first_repair", "first_lend", "first_sorted_out", "first_service"):
            self.assertIn(key, earned)

    def test_nothing_counts_without_a_real_change(self):
        _, place = self.make_place()
        item = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack", "note": "weiß"})[1]
        self.client.json("PATCH", f"/api/items/{item['id']}", {"note": "weiß", "place_id": place["id"], "fill": "ok"})
        self.client.json("POST", "/api/items/move", {"item_ids": [item["id"]], "place_id": place["id"]})
        self.assertFalse(self.earned() & {"first_move", "first_care", "first_repair"})

    def test_rechecking_a_recorded_spot_is_care(self):
        _, place = self.make_place()
        self.client.json("PATCH", f"/api/places/{place['id']}", {"surveyed": True})
        self.assertNotIn("first_care", self.earned())
        self.client.json("PATCH", f"/api/places/{place['id']}", {"surveyed": True})
        self.assertIn("first_care", self.earned())

    def test_care_and_use_earn_points_for_their_levels(self):
        _, place = self.make_place()
        item = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Säge", "scale": "state", "fill": "leer"})[1]
        self.client.json("PATCH", f"/api/items/{item['id']}", {"fill": "ok"})
        self.client.json("POST", f"/api/items/{item['id']}/service", {})
        self.client.json("POST", f"/api/items/{item['id']}/found")
        levels = {entry["group"]: entry["points"] for entry in self.client.json("GET", "/api/state")[1]["achievements"]["levels"]}
        self.assertEqual((levels["pflegen"], levels["nutzen"]), (10, 2))


class CheckinTests(ServerCase):
    """Kurz nachgefragt: bestätigen, Takt und Pause für alle Geräte."""

    def test_still_there_confirms_without_counting_as_a_find(self):
        _, place = self.make_place()
        item = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack"})[1]
        self.client.json("POST", f"/api/items/{item['id']}/missing")
        status, saved = self.client.json("POST", f"/api/items/{item['id']}/still-there")
        self.assertEqual((status, saved["missing"]), (200, 0))
        self.assertGreaterEqual(saved["last_seen"], item["last_seen"])
        counts = self.client.json("GET", "/api/state")[1]["event_counts"]
        self.assertEqual((counts.get("checked_item"), counts.get("found")), (1, None))
        self.assertIn("first_care", {entry["key"] for entry in self.client.json("GET", "/api/state")[1]["achievements"]["earned"]})
        self.assertEqual(self.client.json("POST", f"/api/items/{'0' * 32}/still-there")[0], 404)

    def test_interval_and_pause_are_saved_for_all_devices(self):
        prefs = self.client.json("GET", "/api/state")[1]["preferences"]
        self.assertEqual((prefs["checkin_days"], prefs["checkin_next"], prefs["dashboard"]["checkin"]), (90, "", True))
        status, prefs = self.client.json("PATCH", "/api/preferences", {"checkin_days": 30, "checkin_next": "2026-12-01"})
        self.assertEqual((status, prefs["checkin_days"], prefs["checkin_next"]), (200, 30, "2026-12-01"))
        for body in ({"checkin_days": 7}, {"checkin_days": True}, {"checkin_next": "morgen"}, {"checkin_next": "2026-02-30"}):
            with self.subTest(body=body):
                self.assertEqual(self.client.json("PATCH", "/api/preferences", body)[0], 400)
        self.assertEqual(self.client.json("GET", "/api/state")[1]["preferences"]["checkin_next"], "2026-12-01")


class QuantityTests(ServerCase):
    """Manches hat man mehrfach: Anzahl je Eintrag."""

    def test_quantity_is_saved_checked_and_shown(self):
        _, place = self.make_place()
        status, clamp = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Schraubzwinge", "quantity": 3})
        self.assertEqual((status, clamp["quantity"]), (201, 3))
        self.assertEqual(self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack"})[1]["quantity"], 1)
        for bad in (0, -1, 10000, 2.5, True, "drei", None):
            with self.subTest(bad=bad):
                self.assertEqual(self.client.json("PATCH", f"/api/items/{clamp['id']}", {"quantity": bad})[0], 400)
        self.assertEqual(self.client.json("PATCH", f"/api/items/{clamp['id']}", {"quantity": 5})[1]["quantity"], 5)
        table = self.client.request("GET", "/api/export.csv")[1].decode("utf-8-sig")
        self.assertTrue(table.splitlines()[0].endswith(";Anzahl"))
        self.assertTrue(next(line for line in table.splitlines() if line.startswith("Schraubzwinge")).endswith(";5"))
        self.assertIn("<strong>5× Schraubzwinge</strong>", self.client.request("GET", "/api/share.html")[1].decode("utf-8"))

    def test_merging_twins_adds_up_the_pieces(self):
        _, place = self.make_place()
        _, other = self.make_place(label="Fach B", room=self.make_room("Garage"))
        moved = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Zwinge", "quantity": 2})[1]
        twin = self.client.json("POST", "/api/items", {"place_id": other["id"], "name": "Zwinge", "quantity": 3})[1]
        self.client.json("POST", "/api/items/move", {"item_ids": [moved["id"]], "place_id": other["id"]})
        state = self.client.json("GET", "/api/state")[1]
        self.assertEqual([item["quantity"] for item in state["items"] if item["id"] == twin["id"]], [5])

    def test_import_reads_the_quantity(self):
        text = "Raum;Schrank;Name;Anzahl\nKeller;Regal;Zwinge;4\nKeller;Regal;Leim;\nKeller;Regal;Pinsel;3x\n"
        status, done = self.client.request("POST", "/api/import?apply=1", raw=text.encode())[:2]
        self.assertEqual(status, 200)
        items = {item["name"]: item["quantity"] for item in self.client.json("GET", "/api/state")[1]["items"]}
        self.assertEqual(items, {"Zwinge": 4, "Leim": 1, "Pinsel": 3})
        bad = "Raum;Schrank;Name;Anzahl\nKeller;Regal;Zwinge;viele\n"
        self.assertEqual(json.loads(self.client.request("POST", "/api/import", raw=bad.encode())[1])["errors"][0]["line"], 2)


class RoomCoverTests(ServerCase):
    def upload(self, place_id=None):
        query = f"?place_id={place_id}" if place_id else ""
        return json.loads(self.client.request("POST", f"/api/photos{query}", raw=JPEG)[1])["id"]

    def test_cover_photo_with_crop_or_an_icon(self):
        room = self.make_room()
        photo = self.upload()
        status, saved = self.client.json("PATCH", f"/api/rooms/{room['id']}", {"cover_photo": photo, "cover_x": 0.2, "cover_y": 0.7, "cover_zoom": 2.5})
        self.assertEqual(status, 200)
        self.assertEqual((saved["cover_photo"], saved["cover_x"], saved["cover_y"], saved["cover_zoom"], saved["cover_icon"]), (photo, 0.2, 0.7, 2.5, None))
        saved = self.client.json("PATCH", f"/api/rooms/{room['id']}", {"cover_icon": "garten"})[1]
        self.assertEqual((saved["cover_icon"], saved["cover_photo"], saved["cover_zoom"]), ("garten", None, None))
        # Das ersetzte, eigens hochgeladene Foto wird nicht mehr gebraucht und verschwindet.
        self.assertEqual(self.client.request("GET", f"/fotos/{photo}")[0], 404)
        saved = self.client.json("PATCH", f"/api/rooms/{room['id']}", {"cover_icon": None, "cover_photo": None})[1]
        self.assertEqual((saved["cover_icon"], saved["cover_photo"]), (None, None))

    def test_invalid_cover_values_are_refused(self):
        room = self.make_room()
        for body in ({"cover_icon": "rakete"}, {"cover_zoom": 5}, {"cover_zoom": 0.5}, {"cover_zoom": True}, {"cover_x": 1.5}, {"cover_photo": "0" * 32}):
            with self.subTest(body):
                self.assertIn(self.client.json("PATCH", f"/api/rooms/{room['id']}", body)[0], (400, 404))

    def test_a_cabinet_photo_used_as_cover_survives_a_new_cabinet_photo(self):
        room = self.make_room()
        first = self.upload()
        cabinet = self.client.json("POST", "/api/maps", {"room_id": room["id"], "name": "Regal", "photo": first})[1]
        self.client.json("PATCH", f"/api/rooms/{room['id']}", {"cover_photo": first, "cover_x": 0.5, "cover_y": 0.5, "cover_zoom": 1})
        self.client.json("PATCH", f"/api/maps/{cabinet['id']}", {"photo": self.upload()})
        self.assertEqual(self.client.request("GET", f"/fotos/{first}")[0], 200)
        self.assertEqual(next(r for r in self.client.json("GET", "/api/state")[1]["rooms"] if r["id"] == room["id"])["cover_photo"], first)

    def test_cover_falls_back_when_its_photo_goes_to_the_trash(self):
        room = self.make_room()
        _, place = self.make_place(room=room)
        photo = self.upload(place["id"])
        self.client.json("PATCH", f"/api/rooms/{room['id']}", {"cover_photo": photo, "cover_x": 0.5, "cover_y": 0.5, "cover_zoom": 1.5})
        self.assertEqual(self.client.json("DELETE", f"/api/photos/{photo}")[0], 200)
        state = self.client.json("GET", "/api/state")[1]
        self.assertIsNone(next(r for r in state["rooms"] if r["id"] == room["id"])["cover_photo"])

    def test_server_and_interface_offer_the_same_icons(self):
        source = (APP / "static" / "app.js").read_text(encoding="utf-8")
        listed = re.search(r"const COVER_ICONS = \[(.*?)\];", source, re.S).group(1)
        self.assertEqual(tuple(re.findall(r'\["([a-z]+)", T\(', listed)), server_module.COVER_ICONS)
        for name in server_module.COVER_ICONS:
            self.assertRegex(source, rf"\n  {name}: \[")

    def test_room_with_own_cover_comes_back_from_the_trash(self):
        room = self.make_room()
        photo = self.upload()
        self.client.json("PATCH", f"/api/rooms/{room['id']}", {"cover_photo": photo, "cover_x": 0.3, "cover_y": 0.4, "cover_zoom": 2})
        status, trashed = self.client.json("DELETE", f"/api/rooms/{room['id']}")
        self.assertEqual(status, 200)
        entry = self.client.json("GET", "/api/trash")[1]["entries"][0]
        self.assertEqual(self.client.json("POST", f"/api/trash/{entry['id']}/restore", {})[0], 200)
        back = next(r for r in self.client.json("GET", "/api/state")[1]["rooms"] if r["id"] == room["id"])
        self.assertEqual((back["cover_photo"], back["cover_zoom"]), (photo, 2.0))
        self.assertEqual(self.client.request("GET", f"/fotos/{photo}")[0], 200)


class ScannerTests(ServerCase):
    def test_qr_reader_is_served_and_camera_is_allowed_for_the_app_only(self):
        status, body, headers = self.client.request("GET", "/vendor/jsQR.js")
        self.assertEqual(status, 200)
        self.assertIn(b"jsQR", body[:2000])
        policy = headers["Permissions-Policy"]
        self.assertIn("camera=(self)", policy)
        self.assertIn("microphone=()", policy)
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])

    def test_license_of_the_qr_reader_ships_with_it(self):
        status, body, _ = self.client.request("GET", "/vendor/jsQR-LICENSE.txt")
        self.assertEqual(status, 200)
        self.assertIn(b"Apache License", body)


class MirrorHelperTests(unittest.TestCase):
    """Der Kopierdienst aus dem Home-Assistant-Paket, hier mit Ordnern im Temp-Verzeichnis."""

    def setUp(self):
        self.script = APP.parent / "spiegel.sh"
        if not self.script.exists() or not shutil.which("realpath"):
            self.skipTest("Kein Paketordner oder kein realpath")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.data, self.share = base / "data", base / "share"
        (self.data / "sicherungen").mkdir(parents=True)
        (self.share / "nas").mkdir(parents=True)

    def run_once(self, target, keep=3):
        (self.data / "spiegel.conf").write_text(f"{target}\n{keep}\n")
        env = {**os.environ, "SPIEGEL_DATA": str(self.data), "SPIEGEL_SHARE": str(self.share)}
        subprocess.run(["/bin/sh", str(self.script), "einmal"], env=env, check=True, timeout=30)
        return (self.data / "spiegel-status").read_text().strip()

    def backup(self, name, when):
        path = self.data / "sicherungen" / name
        path.write_bytes(name.encode())
        os.utime(path, (when, when))
        return path

    def test_copies_the_last_backups_and_keeps_only_that_many(self):
        for day in range(1, 6):
            self.backup(f"findling-2026-01-0{day}-120000.zip", day * 86400)
        self.backup("findling-2026-01-01-vor-0.2.0.zip", 1000)
        (self.data / "sicherungen" / "inventar.sqlite").write_text("nicht kopieren")
        old = self.share / "nas" / "findling-2025-12-01-120000.zip"
        old.write_text("alt")
        os.utime(old, (10, 10))
        (self.share / "nas" / "eigene.txt").write_text("bleibt")
        self.assertTrue(self.run_once(self.share / "nas").startswith("ok "))
        names = sorted(p.name for p in (self.share / "nas").iterdir())
        self.assertEqual(names, ["eigene.txt", "findling-2026-01-01-vor-0.2.0.zip", "findling-2026-01-03-120000.zip",
                                 "findling-2026-01-04-120000.zip", "findling-2026-01-05-120000.zip"])
        copy = self.share / "nas" / "findling-2026-01-05-120000.zip"
        self.assertEqual(copy.read_bytes(), b"findling-2026-01-05-120000.zip")
        self.assertEqual(int(copy.stat().st_mtime), 5 * 86400)
        self.assertEqual(copy.stat().st_mode & 0o777, 0o644)

    def test_refuses_targets_outside_share_and_never_follows_links(self):
        self.backup("findling-2026-01-01-120000.zip", 86400)
        secret = Path(self.tmp.name) / "geheim.txt"
        secret.write_text("geheim")
        (self.data / "sicherungen" / "findling-2026-01-02-120000.zip").symlink_to(secret)
        outside = Path(self.tmp.name) / "draussen"
        outside.mkdir()
        (self.share / "umweg").symlink_to(outside)
        for target in (outside, self.share / "nas" / ".." / "..", self.share / "umweg", "/etc", ""):
            with self.subTest(str(target)):
                self.assertTrue(self.run_once(target).startswith("fehler "))
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.run_once(self.share / "nas")[:2], "ok")
        self.assertEqual([p.name for p in (self.share / "nas").iterdir()], ["findling-2026-01-01-120000.zip"])

    def test_bad_keep_values_change_nothing(self):
        self.backup("findling-2026-01-01-120000.zip", 86400)
        for keep in ("2", "31", "x", "3; rm -rf /"):
            with self.subTest(keep):
                self.assertTrue(self.run_once(self.share / "nas", keep).startswith("fehler "))
        self.assertEqual(list((self.share / "nas").iterdir()), [])


class AppArmorProfileTests(unittest.TestCase):
    def profile(self):
        path = APP.parent / "apparmor.txt"
        if not path.exists():
            self.skipTest("Kein Paketordner")
        return path.read_text()

    def test_profile_is_enforced_and_has_one_top_level_profile(self):
        text = self.profile()
        self.assertNotIn("complain", text)
        self.assertEqual(len(re.findall(r"^profile ", text, re.M)), 1)
        self.assertEqual(text.count("{"), text.count("}"))

    def test_app_profile_allows_what_python_needs(self):
        child = self.profile().split("profile findling_app", 1)[1]
        for rule in ("/opt/findling/** mr,", "/usr/lib/** mr,", "/data/** rwkm,", "/tmp/** rwkm,", "network inet stream,", "/usr/bin/openssl rix,"):
            self.assertIn(rule, child)
        self.assertNotIn("capability", child)
        self.assertNotRegex(child, r"(?m)^\s*file,")
        self.assertNotRegex(child, r"/opt/findling/\*\* [^,]*w")

    def test_app_may_only_read_share_and_the_helper_is_started(self):
        child = self.profile().split("profile findling_app", 1)[1]
        self.assertIn("/share/** r,", child)
        self.assertNotRegex(child, r"/share[^,]* [^,]*[wakl]")
        base = APP.parent
        self.assertIn("/bin/sh /spiegel.sh &", (base / "run.sh").read_text())
        self.assertIn("COPY spiegel.sh /spiegel.sh", (base / "Dockerfile").read_text())
        config = (base / "config.yaml").read_text()
        self.assertIn("map:\n  - type: share\n    read_only: false", config)


class ManageTests(ServerCase):
    def upload(self, query=""):
        return json.loads(self.client.request("POST", f"/api/photos{query}", raw=JPEG)[1])["id"]

    def test_place_frame_can_be_moved_and_resized(self):
        _, place = self.make_place()
        status, updated = self.client.json("PATCH", f"/api/places/{place['id']}", {"x": 0.3, "y": 0.4, "w": 0.2, "h": 0.25})
        self.assertEqual((status, updated["x"], updated["h"]), (200, 0.3, 0.25))
        self.assertEqual(updated["code"], place["code"])

    def test_cabinet_photo_can_be_replaced(self):
        room = self.make_room()
        first, second = self.upload(), self.upload()
        _, map_record = self.client.json("POST", "/api/maps", {"room_id": room["id"], "name": "Regal", "photo": first})
        status, updated = self.client.json("PATCH", f"/api/maps/{map_record['id']}", {"photo": second})
        self.assertEqual((status, updated["photo"]), (200, second))
        self.assertEqual(self.client.request("GET", f"/fotos/{first}")[0], 404)
        self.assertEqual(self.client.request("GET", f"/fotos/{second}")[0], 200)

    def test_cabinet_moves_to_another_room_and_keeps_addresses(self):
        garage = self.make_room("Garage")
        keller = self.make_room("Keller")
        map_record, place = self.make_place("Regal", "A", garage)
        self.client.json("PATCH", f"/api/maps/{map_record['id']}", {"plan_x": 0.5, "plan_y": 0.5})
        self.client.json("POST", "/api/maps", {"room_id": keller["id"], "name": "Regal"})
        status, moved = self.client.json("PATCH", f"/api/maps/{map_record['id']}", {"room_id": keller["id"]})
        self.assertEqual((status, moved["room_id"], moved["plan_x"]), (200, keller["id"], None))
        self.assertNotEqual(moved["code"], "R")
        state = self.client.json("GET", "/api/state")[1]
        self.assertEqual(state["places"][0]["code"], place["code"])
        self.assertEqual(self.client.json("PATCH", f"/api/maps/{map_record['id']}", {"room_id": "x"})[0], 404)

    def test_room_moves_to_another_house(self):
        room = self.make_room("Garage")
        _, other = self.client.json("POST", "/api/sites", {"name": "Ferienhaus"})
        _, moved = self.client.json("PATCH", f"/api/rooms/{room['id']}", {"site_id": other["id"]})
        self.assertEqual(moved["site_id"], other["id"])
        self.assertEqual(self.client.json("PATCH", f"/api/rooms/{room['id']}", {"site_id": "x"})[0], 404)
        _, twin = self.client.json("POST", "/api/rooms", {"site_id": self.site_id(), "name": "Garage"})
        self.assertEqual(self.client.json("PATCH", f"/api/rooms/{twin['id']}", {"site_id": other["id"]})[0], 409)

    def test_item_can_be_away_and_come_back(self):
        _, place = self.make_place()
        _, item = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Bohrmaschine"})
        _, away = self.client.json("PATCH", f"/api/items/{item['id']}", {"away": "verliehen an Max"})
        self.assertEqual(away["away"], "verliehen an Max")
        self.assertTrue(away["away_since"])
        report = self.client.json("GET", "/api/report")[1]
        rec = next(r for r in report["recommendations"] if r["kind"] == "away")
        self.assertEqual(rec["items"][0]["away"], "verliehen an Max")
        self.assertIn("verliehen an Max", self.store.export_csv())
        _, back = self.client.json("PATCH", f"/api/items/{item['id']}", {"away": ""})
        self.assertIsNone(back["away_since"])
        self.assertTrue(back["last_seen"])
        trash = self.client.json("DELETE", f"/api/items/{item['id']}")[1]["trash_id"]
        self.assertEqual(self.client.json("POST", f"/api/trash/{trash}/restore", {})[0], 200)

    def test_database_without_away_column_is_upgraded(self):
        if sqlite3.sqlite_version_info < (3, 35):
            self.skipTest("SQLite zu alt")
        with self.store.connect() as db:
            db.execute("ALTER TABLE items DROP COLUMN away")
            db.execute("ALTER TABLE items DROP COLUMN away_since")
        Store(self.tmp.name)
        with self.store.connect() as db:
            self.assertIn("away", [row["name"] for row in db.execute("PRAGMA table_info(items)")])


class ShareTests(ServerCase):
    def setUp(self):
        super().setUp()
        _, self.place = self.make_place()

    def test_shopping_extras_are_kept_without_duplicates(self):
        self.client.json("POST", "/api/shopping", {"name": "Holzleim"})
        self.client.json("POST", "/api/shopping", {"name": "holzleim"})
        self.assertEqual(self.client.json("GET", "/api/state")[1]["shopping_extra"], ["Holzleim"])
        self.client.json("DELETE", "/api/shopping", {"name": "Holzleim"})
        self.assertEqual(self.client.json("GET", "/api/state")[1]["shopping_extra"], [])
        self.assertEqual(self.client.json("POST", "/api/shopping", {"name": ""})[0], 400)

    def test_shared_file_is_complete_and_escaped(self):
        self.client.json("POST", "/api/items", {"place_id": self.place["id"], "name": "Lack <script>alert(1)</script>", "fill": "wenig", "note": 'RAL "7016"'})
        self.client.json("POST", "/api/shopping", {"name": "Holzleim"})
        status, body, headers = self.client.request("GET", "/api/share.html")
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertNotIn("<script>alert", text)
        self.assertIn("&lt;script&gt;alert", text)
        self.assertIn("Bitte mitbringen", text)
        self.assertIn("Holzleim", text)
        self.assertIn(self.place["code"], text)
        self.assertNotIn("/fotos/", text)
        self.assertIn("kann es trotzdem vorhanden sein", text)


def raw_request(port, payload):
    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
        connection.sendall(payload)
        answer = b""
        while True:
            try:
                part = connection.recv(65536)
            except socket.timeout:
                break
            if not part:
                break
            answer += part
            if b"\r\n\r\n" in answer:
                head, _, body = answer.partition(b"\r\n\r\n")
                length = re.search(rb"content-length: (\d+)", head.lower())
                if length and len(body) >= int(length.group(1)):
                    break
    return answer


class IngressTests(unittest.TestCase):
    def start(self, peer="127.0.0.1"):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.server = InventoryServer(("127.0.0.1", 0), self.store, None, False, peer, None, ha=True)
        self.server.public_host = "homeassistant.local"
        self.server.label_url = "http://homeassistant.local:8123/app/local_findling/p/{code}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        return Client(self.server.server_address[1], host="172.30.33.1:8099")

    def test_only_the_supervisor_gets_in(self):
        client = self.start(peer="172.30.32.2")
        self.assertEqual(client.request("GET", "/api/state")[0], 403)
        self.assertEqual(client.request("GET", "/")[0], 403)

    def test_any_host_header_works_behind_ingress_and_no_pin_is_needed(self):
        client = self.start()
        status, state = client.json("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(state["server"]["ingress"])
        self.assertIn("/p/{code}", state["server"]["label_url"])
        self.assertFalse(state["recognition"]["can_set_key"])

    def test_writes_still_need_the_marker(self):
        client = self.start()
        self.assertEqual(client.request("POST", "/api/sites", {"name": "X"}, marker=False)[0], 403)

    def test_chunked_bodies_as_sent_by_the_ingress_proxy(self):
        client = self.start()
        site = client.json("GET", "/api/state")[1]["sites"][0]["id"]
        port = self.server.server_address[1]
        body = json.dumps({"site_id": site, "name": "Garage"}).encode()
        middle = len(body) // 2
        chunks = b"%x\r\n%s\r\n%x\r\n%s\r\n0\r\n\r\n" % (middle, body[:middle], len(body) - middle, body[middle:])
        answer = raw_request(port, (
            b"POST /api/rooms HTTP/1.1\r\nHost: x\r\nX-Werkstatt: 1\r\nContent-Type: application/json\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n" + chunks
        ))
        self.assertIn(b" 201 ", answer.split(b"\r\n")[0])
        self.assertEqual(client.json("GET", "/api/state")[1]["rooms"][0]["name"], "Garage")
        chunked_photo = b"%x\r\n%s\r\n0\r\n\r\n" % (len(JPEG), JPEG)
        answer = raw_request(port, (
            b"POST /api/photos HTTP/1.1\r\nHost: x\r\nX-Werkstatt: 1\r\nTransfer-Encoding: chunked\r\n\r\n" + chunked_photo
        ))
        self.assertIn(b" 201 ", answer.split(b"\r\n")[0])

    def test_request_smuggling_and_broken_chunks_are_refused(self):
        self.start()
        port = self.server.server_address[1]
        for payload in (
            b"POST /api/sites HTTP/1.1\r\nHost: x\r\nX-Werkstatt: 1\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
            b"POST /api/sites HTTP/1.1\r\nHost: x\r\nX-Werkstatt: 1\r\nTransfer-Encoding: gzip\r\n\r\n",
            b"POST /api/sites HTTP/1.1\r\nHost: x\r\nX-Werkstatt: 1\r\nTransfer-Encoding: chunked\r\n\r\nzz\r\n",
            b"POST /api/sites HTTP/1.1\r\nHost: x\r\nX-Werkstatt: 1\r\nTransfer-Encoding: chunked\r\n\r\n-5\r\n",
        ):
            self.assertIn(b" 400 ", raw_request(port, payload).split(b"\r\n")[0], payload)

    def test_oversized_chunked_body_is_stopped(self):
        self.start()
        port = self.server.server_address[1]
        answer = raw_request(port, (
            b"POST /api/sites HTTP/1.1\r\nHost: x\r\nX-Werkstatt: 1\r\nTransfer-Encoding: chunked\r\n\r\n%x\r\n" % (5 * 1024 * 1024)
        ))
        self.assertIn(b" 413 ", answer.split(b"\r\n")[0])

    def test_frame_headers_allow_only_home_assistant(self):
        client = self.start()
        headers = client.request("GET", "/")[2]
        self.assertEqual(headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("frame-ancestors 'self'", headers["Content-Security-Policy"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("unsafe", headers["Content-Security-Policy"])

    def test_backup_can_be_uploaded_and_replaces_the_data(self):
        client = self.start()
        site = client.json("GET", "/api/state")[1]["sites"][0]["id"]
        client.json("POST", "/api/rooms", {"site_id": site, "name": "Vom Mac"})
        data = self.store.backup_zip()
        client.json("DELETE", f"/api/rooms/{client.json('GET', '/api/state')[1]['rooms'][0]['id']}")
        self.assertEqual(client.json("GET", "/api/state")[1]["rooms"], [])
        status, _, _ = client.request("POST", "/api/backups/upload", raw=data)
        self.assertEqual(status, 200)
        self.assertEqual(client.json("GET", "/api/state")[1]["rooms"][0]["name"], "Vom Mac")
        self.assertEqual(client.request("POST", "/api/backups/upload", raw=b"kein zip")[0], 400)
        names = [p.name for p in self.store.backup_dir.iterdir()]
        self.assertFalse([name for name in names if name.endswith(".tmp")])

    def test_storage_location_in_home_assistant_lies_under_share_and_goes_to_the_helper(self):
        client = self.start()
        outside_data = tempfile.TemporaryDirectory()
        self.addCleanup(outside_data.cleanup)
        share = Path(outside_data.name).resolve() / "share"
        (share / "nas" / "findling").mkdir(parents=True)
        (share / ".versteckt").mkdir()
        self.store.target_root = share
        self.store.mirror_helper = True
        with tempfile.TemporaryDirectory() as outside:
            self.assertEqual(client.json("PATCH", "/api/backups", {"target": outside})[0], 400)
        self.assertEqual(client.json("PATCH", "/api/backups", {"target": str(share)})[0], 400)
        self.assertEqual(client.json("PATCH", "/api/backups", {"target": str(share / "nas" / ".." / "..")})[0], 400)
        folders = client.json("GET", "/api/backups/ordner")[1]["folders"]
        self.assertEqual(folders, [str(share / "nas"), str(share / "nas" / "findling")])
        status, info = client.json("PATCH", "/api/backups", {"target": str(share / "nas" / "findling"), "keep": 4})
        self.assertEqual(status, 200)
        conf = (Path(self.tmp.name) / "spiegel.conf").read_text().splitlines()
        self.assertEqual(conf, [str(share / "nas" / "findling"), "4"])
        self.assertEqual(info["target_error"], "Der Kopierdienst hat sich noch nicht gemeldet")
        (Path(self.tmp.name) / "spiegel-status").write_text("ok 1700000000\n")
        info = client.json("GET", "/api/backups")[1]
        self.assertEqual((info["target_at"], info["target_error"]), (1700000000.0, ""))
        (Path(self.tmp.name) / "spiegel-status").write_text("fehler 1700000100 Keine Schreibrechte am Speicherort\n")
        self.assertEqual(client.json("GET", "/api/backups")[1]["target_error"], "Keine Schreibrechte am Speicherort")
        client.json("PATCH", "/api/backups", {"target": ""})
        self.assertFalse((Path(self.tmp.name) / "spiegel.conf").exists())
        self.assertEqual(client.json("POST", "/api/recognition-key", {"key": "x" * 20})[0], 403)


class HardeningTests(ServerCase):
    pin = "12345678"

    def test_direct_clients_are_not_admins(self):
        # Der Test läuft über 127.0.0.1, darum wird der Absender hier nachgestellt.
        original = self.server.RequestHandlerClass.is_admin_client
        self.server.RequestHandlerClass.is_admin_client = lambda handler: False
        self.addCleanup(lambda: setattr(self.server.RequestHandlerClass, "is_admin_client", original))
        self.client.json("POST", "/api/login", {"pin": self.pin})
        self.assertEqual(self.client.json("POST", "/api/backups/x.zip/restore", {})[0], 403)
        self.assertEqual(self.client.request("POST", "/api/backups/upload", raw=b"x")[0], 403)

    def test_sessions_expire(self):
        self.store.add_session("alt")
        self.assertTrue(self.store.has_session("alt"))
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET created = 1000")
        self.assertFalse(self.store.has_session("alt"))

    def test_unknown_hosts_are_refused(self):
        client = Client(self.server.server_address[1], host="boese.example")
        self.assertEqual(client.request("GET", "/")[0], 403)

    def test_cookie_is_protected(self):
        status, _, headers = self.client.request("POST", "/api/login", {"pin": self.pin})
        self.assertEqual(status, 200)
        cookie = headers["Set-Cookie"]
        for part in ("HttpOnly", "SameSite=Strict", "Max-Age=2592000"):
            self.assertIn(part, cookie)
        self.assertNotIn("Secure", cookie)

    def test_security_headers_on_direct_access(self):
        headers = self.client.request("GET", "/")[2]
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn("Permissions-Policy", headers)

    def test_connection_limit_holds(self):
        self.assertEqual(server_module.MAX_CONNECTIONS, 64)
        slots = self.server.slots
        for _ in range(64):
            self.assertTrue(slots.acquire(blocking=False))
        try:
            with socket.create_connection(("127.0.0.1", self.server.server_address[1]), timeout=5) as connection:
                connection.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
                try:
                    self.assertEqual(connection.recv(100), b"")
                except ConnectionResetError:
                    pass  # Auch ein hartes Trennen weist die Verbindung ab.
        finally:
            for _ in range(64):
                slots.release()


class HomeAssistantStartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_gate_only_gives_certificate_and_redirects(self):
        store = Store(self.tmp.name)
        gate = InventoryServer(("127.0.0.1", 0), store, "12345678", False, None, None, ha=True)
        gate.gate_only = True
        gate.gate_target = "https://homeassistant.local:8788"
        gate.allowed_hosts = {"localhost"}
        threading.Thread(target=gate.serve_forever, daemon=True).start()
        self.addCleanup(gate.server_close)
        self.addCleanup(gate.shutdown)
        port = gate.server_address[1]
        answer = raw_request(port, b"GET /api/state HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b" 308 ", answer.split(b"\r\n")[0])
        self.assertIn(b"Location: https://homeassistant.local:8788/", answer)
        answer = raw_request(port, b"POST /api/login HTTP/1.1\r\nHost: localhost\r\nX-Werkstatt: 1\r\nContent-Length: 2\r\n\r\n{}")
        self.assertIn(b" 308 ", answer.split(b"\r\n")[0])
        self.assertNotIn(b"Set-Cookie", answer)
        answer = raw_request(port, b"GET /findling-zertifikat.crt HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b" 404 ", answer.split(b"\r\n")[0])

    def run_app(self, options):
        import server as module
        path = Path(self.tmp.name) / "options.json"
        path.write_text(json.dumps(options))
        started = []
        args = argparse.Namespace(data=self.tmp.name, options=str(path), ingress_port=0, ingress_peer="127.0.0.1", gate_port=0, direct_port=0, verbose=False)
        original_forever = module.InventoryServer.serve_forever
        module.InventoryServer.serve_forever = lambda server: started.append(server)
        original_timer = module.start_backup_timer
        module.start_backup_timer = lambda store: None
        original_direct = module.start_direct_access
        module.start_direct_access = lambda *a: started.append("direkt")
        try:
            module.run_home_assistant(args)
        finally:
            module.InventoryServer.serve_forever = original_forever
            module.start_backup_timer = original_timer
            module.start_direct_access = original_direct
        return started

    def test_direct_access_needs_a_long_pin(self):
        self.assertNotIn("direkt", self.run_app({"direct_access": True, "pin": "1234"}))
        self.assertIn("direkt", self.run_app({"direct_access": True, "pin": "12345678"}))
        self.assertNotIn("direkt", self.run_app({"direct_access": False, "pin": "12345678"}))
        self.assertNotIn("direkt", self.run_app({}))

    def test_key_follows_the_option_and_has_tight_rights(self):
        key_file = Path(self.tmp.name) / recognition.KEY_FILE_NAME
        self.run_app({"anthropic_api_key": "sk-ant-testschluessel-123"})
        self.assertEqual(key_file.stat().st_mode & 0o777, 0o600)
        self.run_app({"anthropic_api_key": ""})
        self.assertFalse(key_file.exists())

    def test_bad_values_fall_back_safely(self):
        server = self.run_app({"hostname": "bad host\r\nX: y", "qr_base_url": "javascript:alert(1)"})[0]
        self.assertEqual(server.public_host, "homeassistant.local")
        self.assertTrue(server.label_url.startswith("http://homeassistant.local:8123/app/"))


class AccessTests(unittest.TestCase):
    def test_certificate_is_limited_and_its_authority_key_is_gone(self):
        if not shutil.which("openssl"):
            self.skipTest("openssl fehlt")
        with tempfile.TemporaryDirectory() as folder:
            paths = zugang.ensure_certificate(folder)
            self.assertTrue(paths)
            self.assertFalse((paths["folder"] / "ca.key").exists())
            self.assertEqual(paths["key"].stat().st_mode & 0o777, 0o600)
            text = subprocess.run(["openssl", "x509", "-in", str(paths["ca"]), "-noout", "-text"], capture_output=True, text=True).stdout
            self.assertIn("Name Constraints", text)
            again = zugang.ensure_certificate(folder)
            self.assertEqual(again["cert"].read_bytes(), paths["cert"].read_bytes())
            store = Store(folder)
            server = InventoryServer(("127.0.0.1", 0), store)
            server.enable_tls(str(paths["cert"]), str(paths["key"]))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            context = ssl.create_default_context(cafile=str(paths["ca"]))
            connection = http.client.HTTPSConnection("localhost", server.server_address[1], context=context, timeout=10)
            connection.request("GET", "/api/session")
            self.assertEqual(connection.getresponse().status, 200)
            connection.close()
            wrong = ssl.create_default_context()
            connection = http.client.HTTPSConnection("localhost", server.server_address[1], context=wrong, timeout=10)
            with self.assertRaises(ssl.SSLError):
                connection.request("GET", "/api/session")
            connection.close()

    def test_certificate_download_is_public_only_in_the_home_network(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            server = InventoryServer(("127.0.0.1", 0), store, pin="123456")
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            client = Client(server.server_address[1])
            self.assertEqual(client.request("GET", "/findling-zertifikat.crt")[0], 404)
            if zugang.ensure_certificate(folder):
                status, body, headers = client.request("GET", "/findling-zertifikat.crt")
                self.assertEqual((status, headers["Content-Type"]), (200, "application/x-x509-ca-cert"))
                self.assertIn(b"BEGIN CERTIFICATE", body)
            self.assertEqual(client.request("GET", "/api/state")[0], 401)


class MilestoneTests(ServerCase):
    def earned(self):
        return [entry["key"] for entry in self.client.json("GET", "/api/state")[1]["achievements"]["earned"]]

    def test_milestones_come_with_progress_and_stay(self):
        self.assertEqual(self.earned(), [])
        _, place = self.make_place()
        _, item = self.client.json("POST", "/api/items", {"place_id": place["id"], "name": "Lack"})
        self.client.json("PATCH", f"/api/places/{place['id']}", {"surveyed": True})
        self.assertEqual(set(self.earned()), {"first_place", "room_done"})
        self.client.json("POST", f"/api/items/{item['id']}/found")
        self.assertIn("first_find", self.earned())
        before = self.earned()
        self.client.json("PATCH", f"/api/places/{place['id']}", {"surveyed": False})
        self.client.json("DELETE", f"/api/items/{item['id']}")
        # Was erreicht ist, bleibt. Das Aussortieren zählt dabei selbst als Meilenstein.
        self.assertEqual(self.earned(), [*before, "first_sorted_out"])

    def test_levels_grow_without_limit_and_show_how_far_it_is(self):
        _, place = self.make_place()
        for index in range(4):
            self.client.json("POST", "/api/items", {"place_id": place["id"], "name": f"Ding {index}"})
        levels = {entry["group"]: entry for entry in self.client.json("GET", "/api/state")[1]["achievements"]["levels"]}
        self.assertEqual(set(levels), {"erfassen", "ordnen", "pflegen", "nutzen"})
        self.assertEqual((levels["erfassen"]["points"], levels["erfassen"]["level"], levels["erfassen"]["next"]), (4, 0, 15))
        # Jede Stufe braucht mehr als die vorige, und es geht immer weiter.
        floors = [server_module.level_floor(level) for level in range(1, 40)]
        steps = [b - a for a, b in zip(floors, floors[1:])]
        self.assertTrue(all(later > earlier for earlier, later in zip(steps, steps[1:])))
        self.assertEqual(server_module.level_of(server_module.level_floor(25)), 25)
        self.assertEqual(server_module.level_of(server_module.level_floor(25) - 1), 24)

    def test_a_new_level_is_celebrated_once(self):
        _, place = self.make_place()
        for index in range(15):
            self.client.json("POST", "/api/items", {"place_id": place["id"], "name": f"Ding {index}"})
        state = self.client.json("GET", "/api/state")[1]
        reached = [entry for entry in state["achievements"]["earned"] if entry.get("level")]
        self.assertEqual([entry["key"] for entry in reached], ["level:erfassen:1"])
        self.assertIn("Stufe 1", reached[0]["title"])
        self.assertEqual(state["achievements"]["total"], 1)

    def test_all_done_needs_a_real_inventory(self):
        room = self.make_room()
        _, first = self.make_place("Regal", "A", room)
        self.client.json("PATCH", f"/api/places/{first['id']}", {"surveyed": True})
        self.assertNotIn("all_done", self.earned())
        for name in ("B", "C"):
            _, other = self.make_place("Regal " + name, name, room)
            self.client.json("PATCH", f"/api/places/{other['id']}", {"surveyed": True})
        self.assertIn("all_done", self.earned())


class MinimapTests(ServerCase):
    def test_positions_of_rooms_and_houses_are_stored(self):
        room = self.make_room()
        status, updated = self.client.json("PATCH", f"/api/rooms/{room['id']}", {"map_x": 0.25, "map_y": 0.75})
        self.assertEqual((status, updated["map_x"], updated["map_y"], updated["name"]), (200, 0.25, 0.75, "Werkstatt"))
        site = self.site_id()
        status, moved = self.client.json("PATCH", f"/api/sites/{site}", {"map_x": 0.5, "map_y": 0.5})
        self.assertEqual((status, moved["map_x"], moved["name"]), (200, 0.5, "Mein Zuhause"))
        _, state = self.client.json("GET", "/api/state")
        self.assertEqual(state["rooms"][0]["map_y"], 0.75)
        self.assertEqual(state["sites"][0]["map_y"], 0.5)

    def test_positions_are_validated(self):
        room = self.make_room()
        path = f"/api/rooms/{room['id']}"
        self.assertEqual(self.client.json("PATCH", path, {"map_x": 2, "map_y": 0.5})[0], 400)
        self.assertEqual(self.client.json("PATCH", path, {"map_x": 0.5})[0], 400)
        self.assertEqual(self.client.json("PATCH", f"/api/sites/{self.site_id()}", {})[0], 400)

    def test_database_without_positions_is_upgraded(self):
        if sqlite3.sqlite_version_info < (3, 35):
            self.skipTest("SQLite zu alt")
        with self.store.connect() as db:
            for table in ("sites", "rooms"):
                db.execute(f"ALTER TABLE {table} DROP COLUMN map_x")
                db.execute(f"ALTER TABLE {table} DROP COLUMN map_y")
        Store(self.tmp.name)
        room = self.make_room()
        self.assertEqual(self.client.json("PATCH", f"/api/rooms/{room['id']}", {"map_x": 0.1, "map_y": 0.2})[0], 200)


class ReportTests(ServerCase):
    def setUp(self):
        super().setUp()
        self.room = self.make_room()
        self.map, self.a = self.make_place("Regal", "A", self.room)
        _, self.b = self.client.json("POST", "/api/places", {
            "map_id": self.map["id"], "label": "B", "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1,
        })

    def add(self, place, name, **fields):
        return self.client.json("POST", "/api/items", {"place_id": place["id"], "name": name, **fields})[1]

    def report(self):
        status, report = self.client.json("GET", "/api/report")
        self.assertEqual(status, 200)
        return report

    def kinds(self):
        return [rec["kind"] for rec in self.report()["recommendations"]]

    def test_totals_and_rooms(self):
        self.add(self.a, "Lack", fill="wenig")
        self.client.json("PATCH", f"/api/places/{self.a['id']}", {"surveyed": True})
        report = self.report()
        self.assertEqual(report["totals"]["items"], 1)
        self.assertEqual(report["totals"]["surveyed"], 1)
        self.assertEqual(report["totals"]["low"], 1)
        self.assertEqual(report["rooms"][0]["surveyed"], 1)
        self.assertEqual(report["fill"]["wenig"], 1)

    def test_recommendations_follow_the_data(self):
        self.assertEqual(self.kinds(), ["continue"])
        first = self.add(self.a, "Spax 4x40")
        self.add(self.b, "spax 4x40")
        self.assertIn("duplicate", self.kinds())
        self.client.json("POST", f"/api/items/{first['id']}/missing")
        self.assertIn("missing", self.kinds())
        self.client.json("POST", "/api/events", {"q": "Flex", "hits": 0})
        rec = next(r for r in self.report()["recommendations"] if r["kind"] == "failed")
        self.assertEqual(rec["word"], "Flex")
        self.client.json("POST", f"/api/items/{first['id']}/word", {"word": "Flex"})
        self.assertNotIn("failed", self.kinds())

    def test_frequent_needs_enough_finds(self):
        item = self.add(self.a, "Zange")
        for _ in range(2):
            self.client.json("POST", f"/api/items/{item['id']}/found")
        self.assertNotIn("frequent", self.kinds())
        self.client.json("POST", f"/api/items/{item['id']}/found")
        self.assertIn("frequent", self.kinds())

    def test_stale_places_are_reported(self):
        self.client.json("PATCH", f"/api/places/{self.a['id']}", {"surveyed": True})
        self.assertNotIn("stale", self.kinds())
        with self.store.connect() as db:
            db.execute("UPDATE places SET surveyed_at = 1000 WHERE id = ?", (self.a["id"],))
        self.assertIn("stale", self.kinds())

    def test_dismiss_and_restore(self):
        rec = self.report()["recommendations"][0]
        self.client.json("POST", "/api/report/dismiss", {"id": rec["id"]})
        report = self.report()
        self.assertEqual((report["recommendations"], report["dismissed_count"]), ([], 1))
        self.client.json("POST", "/api/report/restore", {})
        self.assertEqual(len(self.report()["recommendations"]), 1)

    def test_move_merges_same_names_and_keeps_notes(self):
        first = self.add(self.a, "Spax", note="4x40", synonyms="Schraube")
        second = self.add(self.b, "SPAX", note="5x60", synonyms="Holzschraube")
        other = self.add(self.a, "Lack")
        status, result = self.client.json("POST", "/api/items/move", {
            "item_ids": [first["id"], other["id"]], "place_id": self.b["id"],
        })
        self.assertEqual((status, result), (200, {"moved": 1, "merged": 1}))
        _, state = self.client.json("GET", "/api/state")
        items = {item["id"]: item for item in state["items"]}
        self.assertEqual(len(items), 2)
        self.assertEqual(items[second["id"]]["note"], "5x60 · 4x40")
        self.assertIn("Schraube", items[second["id"]]["synonyms"])
        self.assertEqual(items[other["id"]]["place_id"], self.b["id"])

    def test_move_rejects_unknown_targets(self):
        item = self.add(self.a, "Lack")
        self.assertEqual(self.client.json("POST", "/api/items/move", {"item_ids": [item["id"]], "place_id": "x"})[0], 404)
        self.assertEqual(self.client.json("POST", "/api/items/move", {"item_ids": [], "place_id": self.b["id"]})[0], 400)

    def analysis(self, *actions):
        return {"recommendations": [
            {"title": f"Vorschlag {i}", "why": "weil", "action": action} for i, action in enumerate(actions)
        ]}

    def action(self, kind="none", refs=(), word="", new_name="", place_code=""):
        return {"type": kind, "refs": list(refs), "word": word, "new_name": new_name, "place_code": place_code}

    def test_report_never_calls_the_paid_analysis(self):
        calls = []
        self.server.analyzer = lambda summary, data_dir: calls.append(summary)
        self.add(self.a, "Lack")
        self.report()
        self.client.json("GET", "/api/state")
        self.assertEqual(calls, [])

    def test_paid_analysis_runs_once_per_request_and_counts_cost(self):
        calls = []

        def analyzer(summary, data_dir):
            calls.append(summary)
            return {**self.analysis(self.action()), "usage": {"input_tokens": 1000000, "output_tokens": 0}}

        self.server.analyzer = analyzer
        item = self.add(self.a, "Lack")
        self.assertEqual(self.client.json("POST", "/api/analysis", {})[0], 200)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["items"][0]["ref"], item["id"][:8])
        self.assertNotIn("photos", json.dumps(calls[0]))
        report = self.report()
        self.assertEqual(report["ai"]["cost_usd"], 4.0)
        self.assertEqual(report["analysis"]["source"], "api")
        self.assertIsNone(report["analysis"]["recommendations"][0]["action_text"])

    def test_chat_answer_is_free_and_actions_apply_after_confirmation(self):
        lack = self.add(self.a, "Lack")
        flex = self.add(self.a, "Winkelschleifer")
        schraube = self.add(self.a, "Schraube")
        answer = "```json\n" + json.dumps(self.analysis(
            self.action("add_word", [flex["id"][:8]], word="Flex"),
            self.action("rename", [schraube["id"][:8]], new_name="Spax 4x40"),
            self.action("move", [lack["id"][:8]], place_code=self.b["code"]),
            self.action("move", ["deadbeef"], place_code=self.b["code"]),
            self.action("move", ["%"], place_code=self.b["code"]),
            self.action("delete_all", [lack["id"][:8]]),
        )) + "\n```"
        calls = []
        self.server.analyzer = lambda summary, data_dir: calls.append(summary)
        self.assertEqual(self.client.json("POST", "/api/analysis/chat-answer", {"answer": answer})[0], 200)
        self.assertEqual(calls, [])
        recs = self.report()["analysis"]["recommendations"]
        self.assertIn("Flex", recs[0]["action_text"])
        self.assertIn(self.b["code"], recs[2]["action_text"])
        self.assertEqual([rec["action_text"] for rec in recs[3:]], [None, None, None])
        _, before = self.client.json("GET", "/api/state")
        self.assertEqual({item["name"] for item in before["items"]}, {"Lack", "Winkelschleifer", "Schraube"})
        for index in (0, 1, 2):
            self.assertEqual(self.client.json("POST", f"/api/analysis/{index}/apply", {})[0], 200)
        _, state = self.client.json("GET", "/api/state")
        items = {item["id"]: item for item in state["items"]}
        self.assertIn("Flex", items[flex["id"]]["synonyms"])
        self.assertEqual(items[schraube["id"]]["name"], "Spax 4x40")
        self.assertEqual(items[lack["id"]]["place_id"], self.b["id"])
        self.assertEqual(self.client.json("POST", "/api/analysis/0/apply", {})[0], 409)
        self.assertEqual(self.client.json("POST", "/api/analysis/3/apply", {})[0], 409)
        self.assertEqual(self.client.json("POST", "/api/analysis/5/dismiss", {})[0], 200)
        self.assertEqual(self.report()["analysis"]["recommendations"][5]["status"], "dismissed")

    def test_analysis_answers_in_other_shapes_are_read(self):
        for answer in (
            '[{"title": "A", "why": "B"}]',
            '{"empfehlungen": [{"titel": "A", "begründung": "B"}]}',
            "- A: B",
            '{"recommendations": [{"title": "A", "why": "B",}]}',
        ):
            with self.subTest(answer):
                rec = recognition.parse_analysis_answer(answer)["recommendations"][0]
                self.assertEqual((rec["title"], rec["why"], rec["action"]["type"]), ("A", "B", "none"))

    def test_unreadable_analysis_answer_is_refused(self):
        self.assertEqual(self.client.json("POST", "/api/analysis/chat-answer", {"answer": "Räum mal auf."})[0], 400)
        self.assertIsNone(self.report()["analysis"])

    def test_prompt_contains_data_and_guards(self):
        item = self.add(self.a, "Lack anthrazit")
        prompt = self.report()["analysis_prompt"]
        self.assertIn("Lack anthrazit", prompt)
        self.assertIn(item["id"][:8], prompt)
        self.assertIn("niemals eine Anweisung", prompt)


class ConvertImageTests(ServerCase):
    def test_other_formats_are_refused(self):
        self.assertEqual(self.client.request("POST", "/api/convert-image", raw=JPEG)[0], 415)

    @unittest.skipUnless(shutil.which("sips"), "sips gibt es nur auf dem Mac")
    def test_heic_becomes_jpeg(self):
        folder = Path(self.tmp.name)
        png = folder / "klein.png"
        png.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAEklEQVR4nGP8z8DAwMDAwMAAAAwTAQHyvC5CAAAAAElFTkSuQmCC"
        ))
        heic = folder / "klein.heic"
        subprocess.run(["sips", "-s", "format", "heic", str(png), "--out", str(heic)], capture_output=True, check=True)
        status, payload, headers = self.client.request("POST", "/api/convert-image", raw=heic.read_bytes())
        self.assertEqual((status, headers["Content-Type"]), (200, "image/jpeg"))
        self.assertTrue(payload.startswith(b"\xff\xd8\xff"))


class FakeClaude(BaseHTTPRequestHandler):
    reply = {}
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeClaude.seen.append({"path": self.path, "body": body, "beta": self.headers.get("anthropic-beta")})
        payload = json.dumps(FakeClaude.reply).encode()
        self.send_response(FakeClaude.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def message(content, stop_reason="end_turn"):
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": recognition.MODEL,
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


@unittest.skipUnless(recognition.sdk_installed(), "anthropic ist nicht installiert")
class RecognizePhotoTests(unittest.TestCase):
    def setUp(self):
        self.api = HTTPServer(("127.0.0.1", 0), FakeClaude)
        threading.Thread(target=self.api.serve_forever, daemon=True).start()
        self.addCleanup(self.api.server_close)
        self.addCleanup(self.api.shutdown)
        self.env = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.env)))
        os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{self.api.server_address[1]}"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.photo = Path(self.tmp.name) / "foto.jpg"
        self.photo.write_bytes(JPEG)
        FakeClaude.seen = []
        FakeClaude.status = 200

    def run_recognition(self):
        return recognition.recognize_photo(self.photo, self.tmp.name)

    def test_request_shape_and_result(self):
        expected = {"items": [{
            "name": "Lack anthrazit", "also_known_as": ["Farbe"], "details": "RAL 7016",
            "fill": "unklar", "certainty": "sicher",
        }], "not_recognized": ""}
        FakeClaude.reply = message([{"type": "text", "text": json.dumps(expected)}])
        result = self.run_recognition()
        self.assertEqual(result.pop("usage"), {"input_tokens": 1, "output_tokens": 1})
        self.assertEqual(result, expected)
        sent = FakeClaude.seen[0]
        self.assertTrue(sent["path"].startswith("/v1/messages"))
        self.assertEqual(sent["body"]["model"], "claude-opus-5-5")
        self.assertEqual(sent["body"]["fallbacks"], "default")
        self.assertIn("server-side-fallback-2026-07-01", sent["beta"])
        self.assertEqual(sent["body"]["output_config"]["format"]["type"], "json_schema")
        image = sent["body"]["messages"][0]["content"][0]
        self.assertEqual(image["source"]["media_type"], "image/jpeg")

    def test_instruction_reaches_the_request_only_when_given(self):
        FakeClaude.reply = message([{"type": "text", "text": '{"items": [], "not_recognized": ""}'}])
        recognition.recognize_photo(self.photo, self.tmp.name, "nur die M8-Muttern zählen")
        self.run_recognition()
        with_hint, without = (seen["body"]["messages"][0]["content"][1]["text"] for seen in FakeClaude.seen)
        self.assertIn("Hinweis: nur die M8-Muttern zählen", with_hint)
        self.assertNotIn("Hinweis", without)

    def test_refusal_is_reported(self):
        FakeClaude.reply = message([], stop_reason="refusal")
        with self.assertRaises(recognition.RecognitionError) as caught:
            self.run_recognition()
        self.assertEqual(caught.exception.status, 422)

    def test_truncated_answer_is_reported(self):
        FakeClaude.reply = message([{"type": "text", "text": '{"items": ['}], stop_reason="max_tokens")
        with self.assertRaises(recognition.RecognitionError):
            self.run_recognition()

    def test_rejected_key_is_reported_without_leaking_it(self):
        FakeClaude.status = 401
        FakeClaude.reply = {"type": "error", "error": {"type": "authentication_error", "message": "invalid"}}
        with self.assertRaises(recognition.RecognitionError) as caught:
            self.run_recognition()
        self.assertEqual(caught.exception.status, 502)
        self.assertNotIn("test-key", caught.exception.message)


class PinTests(ServerCase):
    pin = "123456"

    def test_data_needs_pin_but_app_shell_does_not(self):
        self.assertEqual(self.client.request("GET", "/api/state")[0], 401)
        self.assertEqual(self.client.request("GET", "/fotos/" + "0" * 32)[0], 401)
        self.assertEqual(self.client.json("GET", "/api/session")[1]["authenticated"], False)

    def test_login(self):
        self.assertEqual(self.client.json("POST", "/api/login", {"pin": "000000"})[0], 401)
        self.assertEqual(self.client.json("POST", "/api/login", {"pin": "123456"})[0], 200)
        self.assertEqual(self.client.request("GET", "/api/state")[0], 200)

    def test_home_network_name_is_accepted(self):
        client = Client(self.server.server_address[1], host=f"{self.server.hostname}:8787")
        self.assertEqual(client.request("GET", "/api/session")[0], 200)

    def test_repeated_wrong_pins_lock_login(self):
        for _ in range(10):
            self.client.json("POST", "/api/login", {"pin": "000000"})
        self.assertEqual(self.client.json("POST", "/api/login", {"pin": "123456"})[0], 429)


if __name__ == "__main__":
    unittest.main()
