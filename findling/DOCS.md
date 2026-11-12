# findling

Dein Zeug. Dein System. Hab ich. Weiß ich. Find ich.

## Benutzung

Öffne findling über die Seitenleiste. Die Anmeldung von Home Assistant genügt, ein eigenes Passwort gibt es dort nicht. Nur Administratoren sehen die App.

## Einstellungen

- **Sprache:** Deutsch (de) oder Englisch (en). Gilt nach einem Neustart der App, auch für die Erkennung. Deine eigenen Namen und Notizen bleiben, wie du sie eingegeben hast.
- **Adresse von Home Assistant:** So erreicht dein Telefon Home Assistant im Heimnetz. Daraus entstehen die QR-Codes. Lege sie fest, bevor du Etiketten druckst.
- **API-Schlüssel (freiwillig):** Für die automatische Erkennung per Claude. Jeder Abruf kostet Guthaben und läuft nur auf deinen Tipp. Ohne Schlüssel gibt es die kostenlose Übergabe an deinen eigenen Chat.
- **Direktzugang:** Standardmäßig aus. Nur nötig für die Kopie auf dem Telefon für unterwegs. Dann auch eine PIN mit mindestens 8 Zeichen setzen, den Rechnernamen prüfen und unter „Netzwerk“ die Ports 8787 und 8788 eintragen. Gib diese Ports nie im Router für das Internet frei.

## Updates

Beim ersten Start einer neuen Version sichert findling den alten Stand automatisch. Deinstalliere die App nicht, wenn du deine Daten behalten willst.

## Sicherungen

findling sichert von selbst, Inventar und Fotos zusammen, sobald sich etwas geändert hat. Wie oft (alle 6 oder 12 Stunden, täglich, wöchentlich) und wie viele Stände bleiben (Standard: die letzten 7), stellst du unter „Einstellungen › Sicherungen“ ein.

**Netzlaufwerk als Speicherort:** In Home Assistant unter „Einstellungen › System › Speicher › Netzwerkspeicher hinzufügen“ ein Laufwerk mit der Verwendung „Freigabe“ einbinden. Es erscheint dann in findling als Speicherort. Dorthin kopiert ein kleiner Kopierdienst die letzten Stände. Die App selbst darf das Laufwerk nur lesen.

**Umzug oder neuer Server:** Auf dem Startbildschirm einer neuen Installation „Sicherung wählen“ oder „Vom Speicherort“ antippen. Damit ist findling sofort auf dem alten Stand.

Eine Sicherung enthält Inventar, Fotos und alle Anpassungen (Dashboard, Fotolook, Etikettengröße, Takt und Aufbewahrung). Nicht darin sind der API-Schlüssel und die PIN: Sie stehen in der Konfiguration der App in Home Assistant.

Der aktuelle Datenbestand ist außerdem in den Sicherungen von Home Assistant enthalten.

## Etiketten scannen

Der Kamera-Button unten rechts richtet sich nach der Ansicht: Auf dem Start und in den Übersichten öffnet er den Scanner, im Schrank fotografiert er den nächsten offenen Platz, auf einem Platz dessen Inhalt. Der Scanner ist dort über den kleinen QR-Knopf darüber erreichbar. Erkennt er ein Etikett, springt findling zum Platz. Ein Live-Bild gibt es nur, wenn Home Assistant über HTTPS läuft und der Browser die Kamera freigibt. Sonst tippst du auf „Etikett fotografieren“, löst aus und tippst „Foto verwenden“. Die Kamera erkennt den Code dabei nicht selbst, findling liest ihn erst aus dem fertigen Foto.
