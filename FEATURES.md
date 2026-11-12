# Funktionen von findling 1.1.0

## Aufbau und Erfassung

- Haus oder Grundstück › Raum oder Bereich › Schrank › Platz › Inhalt, auf Wunsch mit Raumplan.
- Schrank fotografieren und jeden Platz antippen. Plätze bekommen eine kurze Adresse.
- Geführter Ablauf mit dem Kamera-Button: Er fotografiert je nach Ansicht den Schrank, den nächsten offenen Platz oder den Inhalt.
- „Neu reingekommen“ auf der Startseite: Foto, Name, Lagerplatz, fertig. Für Kauf, Geschenk oder Fund, auf Wunsch gleich mit Kassenbon oder Rechnung.
- Massenimport: Vorlage herunterladen, in einer Tabellenkalkulation ausfüllen, einlesen. Vorschau mit Fehlern je Zeile, übernommen wird alles oder nichts, vorher wird gesichert.
- Schnellbearbeitung: viele Einträge in einer Liste ändern, verschieben oder löschen.
- Anzahl je Eintrag für alles, was mehrfach vorhanden ist.

## Erkennung

- Inhalte lassen sich aus dem Foto erkennen, immer nur auf ausdrücklichen Tipp.
- Kostenlos per Übergabe an den eigenen Chat (Auftrag kopieren, Antwort einfügen) oder mit eigenem API-Schlüssel.
- Detailmodus: Ein Eintrag wie eine Bitbox bekommt Detailfotos und eine durchsuchbare Teileliste.

## Finden

- Suche über Namen, Notizen, Teile, Hersteller, Modell und Seriennummer.
- QR-Etiketten für jeden Platz, Scanner in der App (live oder per Foto), Code auch zum Eintippen.
- Karte der Standorte und Räume auf der Startseite, Titelbild je Raum.

## Steckbrief und Pflege

- Steckbrief je Eintrag: Hersteller, Modell, Seriennummer, Kauf, Preis, Händler, Garantie, Zubehör, Bedienung, Wartungshinweise. Alles freiwillig und jederzeit später.
- Dokumente am Steckbrief: Anleitung, Rechnung oder Garantie als PDF oder Foto.
- Füllstand für Material, Gerätezustand für Geräte (ausgezeichnet, in Ordnung, zu überprüfen, kaputt).
- Wartung mit festem Takt und nächstem Termin.
- Verleihen mit Name und Rückgabedatum, Erinnerung an das Zubehör bei der Rückgabe.
- Verlauf je Eintrag, eigene Notizen inklusive.
- „Im Blick“: Verliehenes, überfällige Rückgaben, anstehende Wartung, auslaufende Garantie.
- „Kurz nachgefragt“: In unregelmäßigen Abständen fragt die Pixelfigur, ob etwas lange nicht Bestätigtes noch da ist.

## Teilen und Drucken

- Mitbringliste für alles, was zur Neige geht, als PDF zum Teilen. „Besorgt“ fragt gleich nach dem Lagerplatz.
- Etiketten und Inventar als PDF, Steckbrief als PDF mit Zubehör-Checkliste.
- Bestand als Tabelle und als eigenständige Datei zum Weitergeben.

## Überblick

- Auswertung mit Kennzahlen, Diagrammen und Empfehlungen.
- Stufen für Erfassen, Ordnen, Pflegen und Benutzen. Punkte gibt es auch fürs Umräumen, Aussortieren, Reparieren und Wiederfinden. Nach Pausen geht nichts verloren. Jede Stufe hat ihre eigene Farbe.
- Dashboard anpassbar, einheitlicher Fotolook in wählbarer Farbe.
- Deutsch und Englisch.

## Sicherheit und Daten

- Betrieb im eigenen Heimnetz hinter der Anmeldung von Home Assistant, ohne offene Ports.
- Automatische Sicherungen mit einstellbarem Takt und Aufbewahrung, auf Wunsch auf ein Netzlaufwerk. Einspielen direkt auf dem Startbildschirm.
- Vor jedem Update und vor jedem Import wird der Stand gesichert.
- Papierkorb mit 30 Tagen Frist.
- Erzwungenes AppArmor-Profil, eigener Benutzer ohne Root-Rechte, strenge Content Security Policy.
- Freiwilliger Direktzugang per HTTPS und PIN für die Kopie auf dem Telefon, standardmäßig aus.
