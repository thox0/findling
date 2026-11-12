// Oberfläche von findling: suchen, dazu Haus > Raum > Schrank > Platz mit Inhalt und Etiketten.

// Sprache: Deutsch oder Englisch. Der Server setzt sie in <html lang>, aus den Einstellungen in Home Assistant.
import { EN, FILL_EN, PATTERNS_EN } from "./lang/en.js";

const LANG = document.documentElement.lang === "en" ? "en" : "de";
const LOCALE = LANG === "en" ? "en-GB" : "de-DE";

// Übersetzt einen Text der Oberfläche. Schlüssel ist der deutsche Text, {0}, {1} … werden mit args gefüllt.
function T(text, args) {
  let out = text;
  if (LANG === "en" && typeof text === "string") out = EN[text] ?? translatePattern(text) ?? text;
  if (args) out = out.replace(/\{(\d+)\}/g, (_, index) => String(args[Number(index)] ?? ""));
  return out;
}

function translatePattern(text) {
  for (const [source, target] of PATTERNS_EN) {
    const match = text.match(new RegExp(source));
    if (match) return target.replace(/\{(\d+)\}/g, (_, index) => T(match[Number(index) + 1] ?? ""));
  }
  return null;
}

// Füllstände bleiben als Daten deutsch, angezeigt wird die Übersetzung. Bei Geräten heißt dieselbe Stufe Zustand.
function fillLabel(level, item) {
  if (isDevice(item)) return STATE_LABELS[level] || level;
  return LANG === "en" ? FILL_EN[level] || level : level;
}

const FILL_LEVELS = ["voll", "ok", "wenig", "leer"];
const STATE_LABELS = { voll: T("ausgezeichnet"), ok: T("in Ordnung"), wenig: T("zu überprüfen"), leer: T("kaputt") };

function isDevice(item) {
  return item?.scale === "state";
}

// Beide Namen einer Stufe, für Auswahlen über Material und Geräte hinweg.
function bothLabels(level) {
  return `${fillLabel(level)} / ${STATE_LABELS[level]}`;
}

// Auf die Mitbringliste kommt nur Material, das zur Neige geht. Ein kaputtes Gerät kauft man nicht nach Liste.
function runsLow(item) {
  return !isDevice(item) && ["wenig", "leer"].includes(item.fill);
}

function needsCheck(item) {
  return isDevice(item) && ["wenig", "leer"].includes(item.fill);
}
const MAX_PHOTO_EDGE = 2048;
const ROOM_IDEAS = [T("Werkstatt"), "Garage", "Carport", T("Gartenhaus"), T("Keller"), T("Vorrat"), T("Dachboden"), T("Schuppen")];

// Startwortschatz, normalisiert. Fehlsuchen aus dem Alltag zeigen später, was fehlt.
const SYNONYM_GROUPS = [
  ["schraube", "schrauben", "spax", "holzschraube"],
  ["duebel", "wandduebel", "hohlraumduebel"],
  ["lack", "lacke", "farbe", "farben", "lackfarbe", "acryllack", "farbdose"],
  ["kleber", "klebstoff", "leim", "holzleim"],
  ["akkuschrauber", "bohrschrauber", "schrauber"],
  ["saege", "fuchsschwanz", "stichsaege"],
  ["schleifpapier", "sandpapier"],
  ["silikon", "dichtmasse", "fugenmasse", "acryl"],
  ["kabelbinder", "kabelstrapse"],
  ["klebeband", "tape", "kreppband", "malerband", "gewebeband"],
  ["winkel", "winkelverbinder"],
  ["rohrschelle", "schelle"],
  ["pinsel", "malerpinsel"],
  ["kriechoel", "rostloeser", "wd40"],
].map((group) => new Set(group));

const ICONS = {
  search: ["M21 21l-4.3-4.3", "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z"],
  plus: ["M12 5v14", "M5 12h14"],
  copy: ["M9 9h10v11H9z", "M5 15V4h10"],
  qr: ["M4 4h6v6H4z", "M14 4h6v6h-6z", "M4 14h6v6H4z", "M14 14h2v2h-2z", "M18 18h2v2h-2z", "M18 14h2", "M14 18v2", "M7 7h0.01", "M17 7h0.01", "M7 17h0.01"],
  camera: ["M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z", "M12 17a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"],
  printer: ["M6 9V3h12v6", "M6 18H4a1 1 0 0 1-1-1v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a1 1 0 0 1-1 1h-2", "M6 14h12v7H6z"],
  settings: ["M4 7h10", "M18 7h2", "M4 17h2", "M10 17h10", "M16 5v4", "M8 15v4"],
  check: ["M5 12.5l4.5 4.5L19 7.5"],
  back: ["M15 5l-7 7 7 7"],
  next: ["M9 5l7 7-7 7"],
  spark: ["M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z", "M19 16v4", "M17 18h4"],
  plan: ["M3 5l6-2 6 2 6-2v16l-6 2-6-2-6 2z", "M9 3v16", "M15 5v16"],
  trash: ["M4 7h16", "M9 7V4h6v3", "M6 7l1 13h10l1-13", "M10 11v5", "M14 11v5"],
  share: ["M12 15V4", "M8 8l4-4 4 4", "M5 12v7a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-7"],
  chart: ["M4 20V11", "M10 20V4", "M16 20v-6", "M3 20h18"],
  cabinet: ["M5 3h14a1 1 0 0 1 1 1v17H4V4a1 1 0 0 1 1-1z", "M4 12h16", "M10 7.5h4", "M10 16.5h4"],
  edit: ["M4 20h4L19 9l-4-4L4 16z", "M13.5 6.5l4 4"],
  lupe: ["M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "M15 15l6 6", "M10 7v6", "M7 10h6"],
  doc: ["M6 3h8l4 4v14H6z", "M14 3v4h4", "M9 12h6", "M9 16h6"],
  download: ["M12 4v11", "M7.5 10.5L12 15l4.5-4.5", "M5 19h14"],
  blick: ["M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"],
  werkzeug: ["M14.5 3.5a5 5 0 0 0-4.3 7.1l-6.4 6.4a2 2 0 0 0 2.9 2.9l6.4-6.4a5 5 0 0 0 7.1-4.3l-3 1.6-2.6-1.3-.6-2.6z"],
  werkzeugkasten: ["M3 9h18v10H3z", "M8.5 9V6.5a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1V9", "M3 13.5h18", "M10 12.5v2.5h4v-2.5"],
  auto: ["M5 11l1.6-4.2a2 2 0 0 1 1.9-1.3h7a2 2 0 0 1 1.9 1.3L19 11", "M4 11h16a1 1 0 0 1 1 1v5H3v-5a1 1 0 0 1 1-1z", "M5 17v2.5h3V17", "M16 17v2.5h3V17", "M6.5 14h1.5", "M16 14h1.5"],
  fahrrad: ["M6 19a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z", "M18 19a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z", "M6 15.5l3.5-6.5h6.5L18 15.5", "M9.5 9l3 6.5H6", "M8 6h3", "M15 6.5h2.5l-1.5 2.5"],
  garten: ["M12 21v-9", "M12 12c0-4.5 3-7 8-7 0 5-3 7-8 7z", "M12 15.5c0-3-2.5-5.5-6.5-5.5 0 3.5 2.5 5.5 6.5 5.5z", "M7 21h10"],
  haus: ["M3 11l9-7 9 7", "M5 9.5V20h14V9.5", "M10 20v-5.5h4V20"],
  keller: ["M3 5h5v4.5h4V14h4v4.5h5", "M3 20.5h18", "M17 5v5", "M14.5 7.5L17 10l2.5-2.5"],
  dachboden: ["M2.5 18.5L12 4l9.5 14.5z", "M12 15.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z", "M12 10.5v5", "M9.5 13h5"],
  kiste: ["M3 8l9-4 9 4v9l-9 4-9-4z", "M3 8l9 4 9-4", "M12 12v9", "M7.5 6l9 4"],
  regal: ["M4 3v18", "M20 3v18", "M4 8.5h16", "M4 14.5h16", "M4 20h16", "M6.5 8.5v-3h3v3", "M12 14.5v-4h2v4", "M15 14.5v-3h2.5v3"],
};

// Das Zeichen: ein Schrank mit zwei Schubladen, gebaut wie das Zeichen von jungkonzept:
// 20-mal-20-Raster, Treppenecken, die Öse rechts und der Fuß unten.
const LOGO = [
  "........########....",
  "........########....",
  "....######......##..",
  "....######......##..",
  "..####....####..##..",
  "..####....####..##..",
  "..##............####",
  "..##............####",
  "..##########..##..##",
  "..##########..##..##",
  "..##..........######",
  "..##..........######",
  "..##....####....##..",
  "..##....####....##..",
  "..####..........##..",
  "..####..........##..",
  "....##############..",
  "....##############..",
  "........####........",
  "........####........",
];
const LOGO_PIXELS = LOGO.flatMap((row, y) => [...row].flatMap((cell, x) => (cell === "#" ? [{ x, y }] : [])))
  .sort((a, b) => b.y - a.y || a.x - b.x); // Von unten nach oben: So füllt sich der Schrank mit dem Überblick.

const app = document.getElementById("app");
let data = null;
let searchQuery = "";
let onlyLow = false;
let searchLogTimer = null;
let openItem = null; // Der Eintrag, der gerade aufgeklappt ist.
let suggestions = null; // Offene Vorschläge der Erkennung: { placeId, items, notRecognized }
let recognizingPhoto = null;
// Was der Kamera-Button in der aktuellen Ansicht tut. Ohne Angabe scannt er Etiketten.
let pageCamera = null;
// Ein Foto, das der Kamera-Button im Schrank aufgenommen hat, wird auf dem Platz gleich erkannt.
let recognizeOnArrival = null;
const photoHints = {}; // Hinweise je Foto, die noch nicht abgeschickt sind.
let chatPhoto = null; // Das Foto, dessen Übergabe an den eigenen Chat gerade offen ist.
let detailSuggestions = null; // Vorschläge der Erkennung im Detailmodus: { itemId, lines }
let chatPromptBox = null;
const pendingHints = {}; // Hinweise für das nächste Foto eines Platzes.
let knownMilestones = null;
let offlineSince = null; // Gesetzt, wenn die Daten aus der Kopie auf dem Telefon kommen.
let editFrames = null; // Der Schrank, dessen Rahmen gerade angepasst werden.
let selecting = null; // Der Platz, dessen Einträge gerade ausgewählt werden.
const selectedItems = new Set();
const skippedInSeries = new Set();
const autoOpened = new Set(); // Plätze, deren gespeichertes Ergebnis schon einmal geöffnet wurde.
const chatAnswers = {}; // Schon eingefügte, noch nicht ausgewertete Antworten.
let planSelection = null; // Der Schrank, dessen Standort im Raumplan als Nächstes gesetzt wird.
let sitesOpen = false; // Bleibt beim Neuzeichnen aufgeklappt.
let analysisChatOpen = false; // Die Übergabe der KI-Analyse an den eigenen Chat.
let analysisBusy = false;
let reportRequest = 0;
const unselectedLabels = new Set();

// Hilfen

function h(tag, props, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") element.className = value;
    else if (key === "style") Object.assign(element.style, value);
    else if (key.startsWith("on")) element.addEventListener(key.slice(2), value);
    else if (key === "value") element.value = value;
    else if (key === "checked") element.checked = value;
    else element.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    element.append(child);
  }
  return element;
}

function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  for (const d of ICONS[name]) {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

function toast(message, action) {
  const box = document.getElementById("toast");
  box.replaceChildren(T(message));
  if (action) {
    box.append(h("button", {
      type: "button",
      class: "toast-action",
      onclick: () => { box.hidden = true; action.run(); },
    }, action.text));
  }
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { box.hidden = true; }, action ? 10000 : 3500);
}

// Gelöschtes landet im Papierkorb. Der Hinweis danach bietet an, es sofort zurückzuholen.
function deleteWithUndo(path, message, after = render) {
  let result;
  act(async () => {
    result = await api("DELETE", path);
  }, () => {
    after();
    toast(message, {
      text: T("Rückgängig"),
      run: () => act(() => api("POST", `api/trash/${result.trash_id}/restore`, {}), () => {
        toast(T("Wiederhergestellt"));
        render();
      }),
    });
  });
}

// Nimmt den Hinweis „wird geladen“ weg, sobald das Bild da ist.
function loaded() {
  document.getElementById("toast").hidden = true;
  render();
}

async function api(method, path, body, rawBody, extraHeaders = {}) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: { "X-Werkstatt": "1", ...(rawBody ? {} : { "Content-Type": "application/json" }), ...extraHeaders },
      body: rawBody || (body === undefined ? undefined : JSON.stringify(body)),
    });
  } catch {
    throw new Error(T("Das geht nur im Heimnetz. {0} ist gerade nicht erreichbar.", [onServer() ? T("Der Server") : T("Der Mac")]));
  }
  if (path === "api/state") {
    const stand = response.headers.get("X-Offline-Stand");
    offlineSince = stand === null ? null : Number(stand) || 0;
    document.body.classList.toggle("offline", offlineSince !== null);
  }
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401 && path !== "api/login") {
    renderLogin();
    throw new Error(T("PIN erforderlich"));
  }
  if (!response.ok) throw new Error(payload.error || T("Das hat nicht geklappt"));
  return payload;
}

// Führt eine Aktion aus, lädt danach die Daten neu und meldet Fehler sichtbar.
async function act(action, after = render) {
  try {
    await action();
    await reload();
    after();
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
  }
}

async function reload() {
  data = await api("GET", "api/state");
  applyPhotoLook();
  noteMilestones();
  prepareEnvironment();
  if (offlineSince === null) savePhotosForTravel();
}

let environmentReady = false;

// Einmal nach dem ersten Laden: Die Kopie für unterwegs oder die Anbindung an Home Assistant.
function prepareEnvironment() {
  if (environmentReady) return;
  environmentReady = true;
  if (data.server.ingress) {
    followIngressLinks();
    return;
  }
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
    navigator.serviceWorker.ready.then(() => savePhotosForTravel()).catch(() => {});
  }
}

// Etiketten zeigen auf /p/<Adresse>, der QR-Code im Steckbrief auf /s/<Eintrag>.
const LABEL_PATH = /^\/(p|s)\/([A-Za-z0-9-]{1,40})\/?$/;

function openLabelPath(path) {
  const match = LABEL_PATH.exec(path || "");
  if (match) location.hash = `#/${match[1]}/${match[2]}`;
}

// QR-Codes zeigen auf .../app/<slug>/p/<Adresse>. Home Assistant reicht das nicht an den Rahmen weiter,
// darum liest die App den Pfad selbst, und zwar nur von der eigenen Oberseite und nur diese eine Form.
function followIngressLinks() {
  try {
    const outer = /\/(?:app|hassio\/ingress)\/[^/]+(\/[ps]\/[A-Za-z0-9-]{1,40})\/?$/.exec(window.parent.location.pathname);
    if (outer) openLabelPath(outer[1]);
  } catch {
    // Ein fremder Rahmen darf nicht gelesen werden, das ist in Ordnung.
  }
  window.addEventListener("message", (event) => {
    if (event.source !== window.parent || event.origin !== location.origin) return;
    if (event.data?.type === "home-assistant/properties") openLabelPath(event.data.route?.path);
  });
  if (window.parent !== window) {
    window.parent.postMessage({ type: "home-assistant/subscribe-properties" }, location.origin);
  }
}

function savePhotosForTravel() {
  const worker = navigator.serviceWorker?.controller;
  if (!worker) return;
  const urls = [...data.maps.map((map) => map.photo), ...data.rooms.map((room) => room.plan_photo)]
    .filter(Boolean).map((photo) => `fotos/${photo}`);
  if (urls.length) worker.postMessage({ type: "photos", urls });
}

// Belohnung: kurze Rückmeldungen, die nichts blockieren

const cheers = [];
let cheerBusy = false;

function cheer(title, detail, big, tone) {
  cheers.push({ title, detail, big, tone });
  showNextCheer();
}

function showNextCheer() {
  if (cheerBusy || !cheers.length) return;
  cheerBusy = true;
  const { title, detail, big, tone } = cheers.shift();
  const box = h("div", { class: `cheer${big ? " big" : ""}`, role: "status" },
    logoMark(big ? 40 : 30, 100, "jubel"),
    h("div", {}, h("strong", {}, title), detail ? h("div", { class: "small" }, detail) : null));
  if (tone) {
    box.classList.add("toned");
    box.style.setProperty("--tone", tone);
  }
  document.body.append(box);
  try {
    navigator.vibrate?.(big ? [20, 40, 20] : 15);
  } catch {
    // Nicht jedes Gerät kann vibrieren.
  }
  setTimeout(() => {
    box.remove();
    cheerBusy = false;
    showNextCheer();
  }, big ? 2600 : 1800);
}

function noteMilestones() {
  const earned = data.achievements.earned;
  if (knownMilestones) {
    for (const entry of earned) {
      if (knownMilestones.has(entry.key)) continue;
      cheer(entry.level ? T("Neue Stufe") : T("Abzeichen"), entry.title, true, entry.level ? levelColor(Number(entry.key.split(":")[2])) : null);
      if (round) {
        round.earned.push(entry.title);
        saveRound();
      }
    }
  }
  knownMilestones = new Set(earned.map((entry) => entry.key));
}

// Eine Runde: alles zwischen Anfangen und „Fertig für heute“. Keine Serie, die bei einer Pause reißt.

const ROUND_KEY = "werkstatt-runde";
const PACE_KEY = "werkstatt-tempo";
const ROUND_IDLE_MS = 2 * 60 * 60 * 1000;
let round = loadRound();

function loadRound() {
  try {
    const stored = JSON.parse(localStorage.getItem(ROUND_KEY));
    return stored && Date.now() - stored.lastAt < ROUND_IDLE_MS ? stored : null;
  } catch {
    return null;
  }
}

function saveRound() {
  try {
    if (round) localStorage.setItem(ROUND_KEY, JSON.stringify(round));
    else localStorage.removeItem(ROUND_KEY);
  } catch {
    // Ohne Speicher gilt die Runde nur bis zum Neuladen.
  }
}

function ensureRound() {
  if (round && Date.now() - round.lastAt < ROUND_IDLE_MS) return;
  const now = Date.now();
  const cover = coverage();
  round = {
    startedAt: now, lastAt: now, surveyed: cover.done, items: data.items.length, percent: cover.percent, skipped: [], earned: [],
  };
  saveRound();
}

function roundFigures() {
  return {
    places: Math.max(0, coverage().done - round.surveyed),
    items: Math.max(0, data.items.length - round.items),
    minutes: Math.max(1, Math.round((round.lastAt - round.startedAt) / 60000)),
  };
}

function secondsPerPlace() {
  try {
    return Number(localStorage.getItem(PACE_KEY)) || null;
  } catch {
    return null;
  }
}

function notePace() {
  if (!round) return;
  const now = Date.now();
  const seconds = Math.min(900, Math.max(10, (now - round.lastAt) / 1000));
  round.lastAt = now;
  saveRound();
  const previous = secondsPerPlace();
  try {
    localStorage.setItem(PACE_KEY, String(previous ? previous * 0.7 + seconds * 0.3 : seconds));
  } catch {
    // Dann bleibt es ohne Zeitangabe.
  }
}

// Das Zeichen als SVG. Mit Fortschritt leuchtet nur der erreichte Anteil.
// Mit mood wird der Schrank zur kleinen Pixelfigur mit zwei Augen: „happy“ atmet, blinzelt, schaut sich
// um, winkt mit der Öse und trippelt. „jubel“ macht einen Freudensprung. Bewegt wird nur in ganzen Pixeln.
function logoPart(x, y) {
  if (x >= 10 && x <= 13 && y >= 4 && y <= 5) return "eye";
  if (x >= 16 && y >= 6 && y <= 11) return "ring";
  if (y >= 18) return "feet";
  return "body";
}

function logoMark(size, percent = 100, mood = "") {
  const on = Math.round((LOGO_PIXELS.length * percent) / 100);
  const svg = svgEl("svg", {
    class: `mark${mood ? ` figure ${mood}` : ""}`, width: size, height: size, viewBox: "0 0 20 20", "shape-rendering": "crispEdges", "aria-hidden": "true",
  });
  const groups = {};
  for (const part of ["feet", "body", "ring"]) {
    groups[part] = svgEl("g", { class: `part-${part}` });
    svg.append(groups[part]);
  }
  // Das Auge sitzt im Körper, damit es beim Atmen mitgeht.
  groups.eye = svgEl("g", { class: "part-eye" });
  groups.body.append(groups.eye);
  LOGO_PIXELS.forEach(({ x, y }, index) => {
    const part = logoPart(x, y);
    // Als Figur ist das Auge immer wach, auch wenn erst wenig erfasst ist.
    const lit = index < on || (mood && part === "eye");
    // Die obere Reihe des Auges ist das Lid: Fehlt sie kurz, blinzelt die Figur.
    const lid = part === "eye" && y === 4;
    groups[part].append(svgEl("rect", { x, y, width: 1, height: 1, class: `${lit ? "on" : "off"}${lid ? " lid" : ""}` }));
  });
  if (mood) {
    // Kleine Funken neben der Öse, nur beim Winken und beim Jubeln.
    const spark = svgEl("g", { class: "part-spark" });
    for (const [x, y] of [[18, 3], [19, 1], [16, 2]]) spark.append(svgEl("rect", { x, y, width: 1, height: 1, class: "on" }));
    svg.append(spark);
    // Jede Figur beginnt woanders im Ablauf, damit nicht alle gleichzeitig winken.
    svg.style.setProperty("--gesture-delay", `${-Math.round(Math.random() * 12000)}ms`);
  }
  return svg;
}

// Das Raster aus 400 Feldern, wie auf jungkonzept.de. Der Fortschritt bringt den Schrank zum Leuchten.
function logoPixels(percent = 100, waking = false) {
  const on = Math.round((LOGO_PIXELS.length * percent) / 100);
  const lit = new Map(LOGO_PIXELS.slice(0, on).map(({ x, y }, index) => [`${x}/${y}`, index]));
  const grid = h("div", { class: `pixels${waking ? " waking" : ""}`, "aria-hidden": "true" });
  for (let y = 0; y < 20; y += 1) {
    for (let x = 0; x < 20; x += 1) {
      const order = lit.get(`${x}/${y}`);
      const pixel = h("i", { class: order === undefined ? undefined : "on" });
      if (waking && order !== undefined) pixel.style.animationDelay = `${order * 7}ms`;
      grid.append(pixel);
    }
  }
  return h("div", {}, grid, h("div", { class: "pixels-note" }, h("span", {}, "20 × 20 px"), h("span", {}, `${on} / 400 leuchten`)));
}

function makerLine() {
  return h("a", { class: "maker", href: "https://jungkonzept.de/", target: "_blank", rel: "noopener noreferrer" }, T("eine entwicklung von jungkonzept.de"));
}

function brandHero() {
  return h("div", { class: "brand-hero" },
    logoPixels(100, true),
    h("p", { class: "brand-title" }, "findling"),
    h("p", { class: "brand-line" }, T("Dein Zeug. Dein System.")),
    h("p", { class: "brand-claim-big" }, T("Hab ich. Weiß ich. "), h("span", { class: "glow" }, T("Find ich."))));
}

function mapOf(place) {
  return data.maps.find((map) => map.id === place.map_id);
}

function roomOf(map) {
  return data.rooms.find((room) => room.id === map.room_id);
}

function mapsIn(room) {
  return data.maps.filter((map) => map.room_id === room.id);
}

function roomsIn(site) {
  return data.rooms.filter((room) => room.site_id === site.id);
}

function placeOf(item) {
  return data.places.find((place) => place.id === item.place_id);
}

function placesOf(map) {
  return data.places.filter((place) => place.map_id === map.id);
}

function itemsOf(place) {
  return data.items.filter((item) => item.place_id === place.id);
}

// Wo die Daten liegen: auf Home Assistant der Server, sonst der Mac.
function hostOn() {
  return onServer() ? T("dem Server") : T("dem Mac");
}

// Läuft die App auf Home Assistant (Server) oder auf dem Mac?
function onServer() {
  return Boolean(typeof data !== "undefined" && data && data.server && data.server.ha);
}

function hostWord() {
  return onServer() ? T("den Server") : T("den Mac");
}

function placeNumber(place) {
  return Number(place.code.split("-").pop());
}

function placeName(place) {
  return place.label || T("Platz {0}", [placeNumber(place)]);
}

function placePath(place) {
  const map = mapOf(place);
  const room = roomOf(map);
  const site = data.sites.length > 1 ? data.sites.find((candidate) => candidate.id === room.site_id).name : null;
  return [site, room.name, map.name, placeName(place)].filter(Boolean).join(" › ");
}

// Der nächste offene Platz: erst im selben Schrank, dann im selben Raum, dann irgendwo.
function nextOpenPlace(after) {
  const skipped = round ? round.skipped : [];
  const allOpen = data.places.filter((place) => !place.surveyed && (!after || place.id !== after.id));
  const open = allOpen.filter((place) => !skipped.includes(place.id));
  if (!after) return open[0] || allOpen[0] || null;
  const map = mapOf(after);
  return open.find((place) => place.map_id === map.id)
    || open.find((place) => mapOf(place).room_id === map.room_id)
    || open[0]
    || null;
}

function coverage() {
  const total = data.places.length;
  const done = data.places.filter((place) => place.surveyed).length;
  return { total, done, percent: total ? Math.round((done / total) * 100) : 0 };
}

function formatDate(seconds) {
  return seconds ? new Date(seconds * 1000).toLocaleDateString(LOCALE) : T("noch nie");
}

function formatDateTime(seconds) {
  return new Date(seconds * 1000).toLocaleString(LOCALE, { day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" });
}

function plural(count, one, many) {
  return `${count} ${count === 1 ? one : many}`;
}

// Liefert ein Bild, das der Browser anzeigen kann. iPhone-Fotos (HEIC) wandelt notfalls der Server um.
async function readableImage(file) {
  try {
    (await createImageBitmap(file)).close();
    return file;
  } catch {
    const response = await fetch("api/convert-image", { method: "POST", headers: { "X-Werkstatt": "1" }, body: file });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || T("Dieses Bild konnte nicht gelesen werden"));
    }
    return response.blob();
  }
}

// Fotos werden im Browser verkleinert. Das spart Platz und entfernt Metadaten wie den Aufnahmeort.
async function uploadPhoto(file, placeId, itemId) {
  const bitmap = await createImageBitmap(await readableImage(file));
  const scale = Math.min(1, MAX_PHOTO_EDGE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
  const query = placeId ? `?place_id=${encodeURIComponent(placeId)}` : itemId ? `?item_id=${encodeURIComponent(itemId)}` : "";
  return api("POST", `api/photos${query}`, undefined, blob);
}

function photoInput(onFile, many) {
  return h("input", {
    type: "file",
    accept: "image/*",
    multiple: many,
    onchange: (event) => {
      const files = [...event.target.files];
      event.target.value = "";
      if (!files.length) return;
      if (many) onFile(files);
      else onFile(files[0]);
    },
  });
}

function photoButton(text, className, onFile) {
  return h("label", { class: `button file-button ${className}` }, icon("camera"), text, photoInput(onFile));
}

// Suche

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function words(text) {
  return normalize(text).split(" ").filter(Boolean);
}

function editDistance(a, b, limit) {
  if (Math.abs(a.length - b.length) > limit) return limit + 1;
  let previous = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i += 1) {
    const current = [i];
    for (let j = 1; j <= b.length; j += 1) {
      current[j] = Math.min(
        previous[j] + 1,
        current[j - 1] + 1,
        previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
    previous = current;
  }
  return previous[b.length];
}

function synonymsOf(term) {
  const found = new Set();
  for (const group of SYNONYM_GROUPS) {
    if (group.has(term)) group.forEach((word) => found.add(word));
  }
  found.delete(term);
  return found;
}

// Bewertet einen Suchbegriff gegen die Wörter eines Feldes, 0 heißt kein Treffer.
function scoreTerm(term, fieldWords) {
  let best = 0;
  const synonyms = synonymsOf(term);
  // Maße wie M6 und M8 dürfen nicht als Tippfehler gelten.
  const limit = /\d/.test(term) ? 0 : term.length >= 8 ? 2 : term.length >= 4 ? 1 : 0;
  for (const word of fieldWords) {
    if (word === term) return 10;
    if (word.startsWith(term)) best = Math.max(best, 7);
    else if (term.length >= 3 && word.includes(term)) best = Math.max(best, 5);
    else if (synonyms.has(word)) best = Math.max(best, 4);
    else if (limit && editDistance(term, word, limit) <= limit) best = Math.max(best, 2);
  }
  return best;
}

function scoreItem(item, terms) {
  // Plätze werden getrennt gesucht. Sonst träfe „Lack“ alles, was in der „Schublade Lacke“ liegt.
  const nameWords = words(item.name);
  const passport = item.passport || {};
  const otherWords = words(`${item.synonyms} ${item.note} ${item.details || ""} ${passport.maker || ""} ${passport.model || ""} ${passport.serial || ""}`);
  let total = 0;
  for (const term of terms) {
    const score = Math.max(scoreTerm(term, nameWords) * 2, scoreTerm(term, otherWords));
    if (!score) return 0;
    total += score;
  }
  return total;
}

function searchItems(query, low) {
  const terms = words(query);
  const groups = new Map();
  for (const item of data.items) {
    if (low && !runsLow(item)) continue;
    const score = terms.length ? scoreItem(item, terms) : 1;
    if (!score) continue;
    const key = normalize(item.name);
    if (!groups.has(key)) groups.set(key, { name: item.name, score, items: [] });
    const group = groups.get(key);
    group.score = Math.max(group.score, score);
    group.items.push(item);
  }
  return [...groups.values()].sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, "de"));
}

function detailLines(item) {
  return (item.details || "").split("\n").filter(Boolean);
}

// Die Zeilen aus dem Inhalt, die zur Suche passen, etwa „Bit T20“ in einer Bitbox.
function detailHits(item, query) {
  const terms = words(query);
  if (!terms.length) return [];
  const matching = (line) => terms.filter((term) => scoreTerm(term, words(line)) >= 5).length;
  const lines = detailLines(item);
  const all = lines.filter((line) => matching(line) === terms.length);
  return all.length ? all : lines.filter((line) => matching(line) > 0);
}

function searchPlaces(query) {
  const terms = words(query);
  if (!terms.length) return [];
  return data.places.filter((place) =>
    terms.every((term) => scoreTerm(term, words(`${place.code} ${placeName(place)} ${mapOf(place).name}`))));
}

function searchRooms(query) {
  const terms = words(query);
  if (!terms.length) return [];
  return data.rooms.filter((room) => terms.every((term) => scoreTerm(term, words(room.name))));
}

// Bausteine

function shell(...content) {
  return [
    h("header", { class: "topbar" },
      h("a", { class: "brand", href: "#/", "aria-label": T("findling, zur Startseite") }, logoMark(28),
        // Name und Claim in einer Textzeile, damit beide auf derselben Grundlinie stehen.
        h("span", { class: "brand-text" }, h("span", { class: "brand-name" }, "findling"), h("span", { class: "brand-claim" }, T("Hab ich. Weiß ich. Find ich.")))),
      h("div", { class: "row tight" },
        h("a", { class: "icon-link", href: "#/teilen", "aria-label": T("Teilen und Mitbringliste"), title: T("Teilen und Mitbringliste") }, icon("share")),
        h("a", { class: "icon-link", href: "#/blick", "aria-label": T("Im Blick"), title: T("Im Blick") }, icon("blick")),
        h("a", { class: "icon-link", href: "#/auswertung", "aria-label": T("Auswertung"), title: T("Auswertung") }, icon("chart")),
        h("a", { class: "icon-link", href: "#/daten", "aria-label": T("Einstellungen"), title: T("Einstellungen") }, icon("settings")))),
    offlineSince !== null ? h("div", { class: "offline-bar", role: "status" },
      T("Unterwegs: Stand {0}. Ändern geht wieder im Heimnetz.", [offlineSince ? T("vom {0}", [formatDateTime(offlineSince / 1000)]) : T("der letzten Verbindung")])) : null,
    h("main", {}, content),
    cameraButtons(),
  ].filter(Boolean);
}

// Zentraler Kamera-Button. Auf Start und Übersichten scannt er Etiketten, in Schrank, Platz und
// Fotoserie fotografiert er den Inhalt für die Inventur. Scannen bleibt dort als kleiner Knopf daneben.
function cameraButtons() {
  if (location.hash.startsWith("#/scan") || location.hash.startsWith("#/bearbeiten")) return null;
  const scan = (small) => h("a", {
    class: `camera-fab${small ? " camera-fab-small" : ""}`,
    href: "#/scan",
    "aria-label": T("Etikett scannen"),
    title: T("Etikett scannen"),
  }, icon("qr"));
  const action = pageCamera;
  if (!action) return h("div", { class: "camera-dock" }, scan(false));
  return h("div", { class: "camera-dock" },
    scan(true),
    h("label", { class: "camera-fab camera-fab-wide", title: action.text },
      icon("camera"),
      h("span", {}, action.text),
      h("input", {
        type: "file",
        accept: "image/*",
        capture: "environment",
        "aria-label": action.text,
        onchange: (event) => {
          const file = event.target.files[0];
          event.target.value = "";
          if (file) action.onFile(file);
        },
      })));
}

function backLink(href, text) {
  return h("a", { class: "back", href }, icon("back"), text);
}

function placeBox(place, { isCurrent = false, link = true } = {}) {
  return h(link ? "a" : "div", {
    class: `box${isCurrent ? " current" : ""}`,
    href: link ? `#/p/${place.code}` : undefined,
    title: link ? placeName(place) : undefined,
    style: {
      left: `${place.x * 100}%`,
      top: `${place.y * 100}%`,
      width: `${place.w * 100}%`,
      height: `${place.h * 100}%`,
    },
  }, h("span", {}, String(placeNumber(place))));
}

function thumb(place) {
  const map = mapOf(place);
  return h("div", { class: "stage thumb" },
    map.photo ? h("img", { src: `fotos/${map.photo}`, alt: "" }) : null,
    placeBox(place, { isCurrent: true, link: false }));
}

function fillChip(fill, item) {
  return ["wenig", "leer"].includes(fill) ? h("span", { class: `fill fill-${fill}` }, fillLabel(fill, item)) : null;
}

// Kleiner Raumplan mit dem Standort eines Schranks, falls beides vorhanden ist.
function planThumb(map) {
  const plan = roomOf(map).plan_photo;
  if (!plan || map.plan_x === null) return null;
  return h("div", { class: "stage thumb" },
    h("img", { src: `fotos/${plan}`, alt: "" }),
    h("span", { class: "pin-dot", style: { left: `${map.plan_x * 100}%`, top: `${map.plan_y * 100}%` } }));
}

function roomHref(room) {
  return `#/raum/${room.id}`;
}

// Ansicht: Start

// Das Dashboard ist die Startseite. Was es zeigt, legt jede Person selbst fest (siehe viewDashboardSettings).
function dashboardPrefs() {
  return prefs().dashboard;
}

function dashboardRooms() {
  const hidden = new Set(dashboardPrefs().hidden_rooms);
  return data.rooms.filter((room) => !hidden.has(room.id));
}

function viewDashboard() {
  const dash = dashboardPrefs();
  const results = h("div", { id: "results" });
  const rest = h("div", { id: "home-rest" }, homeContent());
  const minimap = dash.minimap && dashboardRooms().length ? meshMap() : null;
  const hero = dash.progress && data.rooms.length ? homeHero() : null;
  const watch = dash.watch !== false ? watchCard() : null;
  const checkin = dash.checkin !== false && data.rooms.length ? checkinCard(Boolean(hero)) : null;
  if (checkin && hero) hero.classList.add("asking");
  const intakeLink = data.places.length && offlineSince === null ? h("a", { class: "intake-link", href: "#/eingang" },
    icon("camera"),
    h("span", { class: "grow" }, h("strong", {}, T("Neu reingekommen")), h("span", { class: "muted small block" }, T("Foto, Name, Lagerplatz. Für Kauf, Geschenk oder Fund."))),
    icon("next")) : null;
  const update = () => {
    renderResults(results);
    const searching = Boolean(searchQuery.trim()) || onlyLow;
    rest.hidden = searching;
    if (hero) hero.hidden = searching;
    if (watch) watch.hidden = searching;
    if (intakeLink) intakeLink.hidden = searching;
    if (checkin) checkin.hidden = searching;
    if (minimap) minimap.highlight(searching ? roomsWithHits(searchQuery.trim(), onlyLow) : null);
  };
  const input = h("input", {
    type: "search",
    class: "search-input",
    placeholder: T("Lack anthrazit, Spax 4 x 40 ..."),
    "aria-label": T("Suchbegriff"),
    value: searchQuery,
    autocomplete: "off",
    oninput: (event) => {
      searchQuery = event.target.value;
      update();
      scheduleSearchLog();
    },
  });
  const lowCount = data.items.filter(runsLow).length;

  app.replaceChildren(...shell(
    data.maps.length ? h("div", { class: "search-area" },
      h("h1", {}, T("Was suchst du?")),
      h("div", { class: "search-box" }, icon("search"), input),
      lowCount && dash.low ? h("button", {
        type: "button",
        class: "chip",
        "aria-pressed": String(onlyLow),
        onclick: () => { onlyLow = !onlyLow; viewDashboard(); },
      }, T("Nachkaufen ({0})", [lowCount])) : null) : null,
    hero,
    checkin,
    intakeLink,
    watch,
    minimap ? minimap.element : null,
    results,
    rest));
  update();
  if (data.maps.length && matchMedia("(min-width: 641px)").matches) input.focus();
}

// Der eine klare Einstieg: wie weit bin ich, und was kommt als Nächstes?
function homeHero() {
  const cover = coverage();
  const next = nextOpenPlace();
  if (!cover.total) {
    const room = data.rooms[0];
    return h("a", { class: "hero", href: `#/neu/${room.id}` },
      logoMark(60, 0),
      h("span", { class: "grow" },
        h("strong", {}, T("Ersten Schrank anlegen")),
        h("span", { class: "muted small block" }, T("In {0}. Ein Foto genügt.", [room.name]))),
      icon("next"));
  }
  if (!next) {
    return h("div", { class: "hero done" },
      logoMark(60, 100, "happy"),
      h("span", { class: "grow" },
        h("strong", {}, T("Alles erfasst")),
        h("span", { class: "muted small block" }, T("{0}, {1}. Die Suche ist jetzt vollständig.", [plural(cover.total, T("Platz"), T("Plätze")), plural(data.items.length, T("Eintrag"), T("Einträge"))]))));
  }
  const open = cover.total - cover.done;
  const pace = secondsPerPlace();
  const time = pace ? T(", bei deinem Tempo etwa {0} Minuten", [Math.max(1, Math.round((open * pace) / 60))]) : "";
  return h("a", { class: "hero", href: `#/p/${next.code}` },
    logoMark(60, cover.percent, "happy"),
    h("span", { class: "grow" },
      h("span", { class: "hero-percent block" }, T("Überblick {0} %", [cover.percent])),
      h("strong", {}, T("Weiter erfassen")),
      h("span", { class: "small block" }, placePath(next)),
      h("span", { class: "muted small block" }, T("Noch {0}{1}", [plural(open, T("Platz"), T("Plätze")), time]))),
    icon("next"));
}

function homeContent() {
  if (!data.rooms.length) return welcome();
  const several = data.sites.length > 1;
  const visible = new Set(dashboardRooms().map((room) => room.id));
  const hiddenCount = data.rooms.length - visible.size;
  return [
    dashboardPrefs().rooms ? data.sites.map((site) => [
      h("div", { class: "section-head room-head" }, h("h2", {}, several ? site.name : T("Räume und Bereiche"))),
      h("div", { class: "tiles" },
        roomsIn(site).filter((room) => visible.has(room.id)).map(roomTile),
        h("a", { class: "tile tile-add", href: `#/neuer-raum/${site.id}` }, icon("plus"), T("Raum oder Bereich"))),
    ]) : null,
    dashboardPrefs().rooms ? sitesSection() : null,
    data.trash_count ? h("a", { class: "trash-link small", href: "#/papierkorb" }, icon("trash"), T("Papierkorb ({0})", [data.trash_count])) : null,
    data.items.length ? h("a", { class: "trash-link small dashboard-link", href: "#/bearbeiten" }, icon("check"), T("Schnellbearbeitung")) : null,
    data.items.length ? h("a", { class: "trash-link small dashboard-link", href: "#/blick" }, icon("blick"), T("Im Blick")) : null,
    h("a", { class: "trash-link small dashboard-link", href: "#/dashboard" }, icon("plan"),
      hiddenCount ? T("Dashboard anpassen ({0} ausgeblendet)", [plural(hiddenCount, T("Bereich"), T("Bereiche"))]) : T("Dashboard anpassen")),
  ];
}

function viewDashboardSettings() {
  const dash = dashboardPrefs();
  const hidden = new Set(dash.hidden_rooms);
  const toggle = (label, hint, checked, onChange) => h("label", { class: "toggle-row" },
    h("span", { class: "grow" }, h("strong", {}, label), hint ? h("span", { class: "muted small block" }, hint) : null),
    h("input", { type: "checkbox", checked, onchange: (event) => onChange(event.target.checked) }));
  const section = (key, label, hint) => toggle(label, hint, dash[key], (on) => savePreferences({ dashboard: { [key]: on } }));
  const several = data.sites.length > 1;
  app.replaceChildren(...shell(
    backLink("#/", T("Zum Dashboard")),
    h("h1", {}, T("Dashboard anpassen")),
    h("p", { class: "muted" }, T("Hier legst du fest, was die Startseite zeigt. Ausgeblendetes bleibt in der Suche, in der Auswertung und in allen Listen. Die Auswahl ist Teil jeder Sicherung.")),
    h("p", { class: "muted small" }, T("Das Titelbild eines Raums änderst du über den Stift auf seiner Kachel oder hier unter Räume.")),
    h("section", { class: "card stack" },
      h("h2", {}, T("Bereiche")),
      section("progress", T("Fortschritt"), T("Wie weit die Erfassung ist und was als Nächstes kommt")),
      section("minimap", T("Standorte-Karte"), T("Die Räume als Netz")),
      section("rooms", T("Räume und Bereiche"), T("Die Kacheln zum Öffnen der Räume")),
      section("low", T("Nachkaufen"), T("Der Knopf für alles, was zur Neige geht")),
      section("watch", T("Im Blick"), T("Verliehenes, fällige Wartungen und auslaufende Garantien")),
      section("checkin", T("Kurz nachgefragt"), T("Fragt ab und zu, in unregelmäßigen Abständen von einigen Tagen, ob etwas noch da ist, das du lange nicht bestätigt hast.")),
      dash.checkin ? h("label", { class: "field" }, T("Nachfragen, wenn etwas so lange nicht bestätigt wurde"),
        (() => {
          const select = h("select", { onchange: (event) => savePreferences({ checkin_days: Number(event.target.value) }) },
            CHECKIN_CHOICES.map(([days, label]) => h("option", { value: String(days) }, label)));
          select.value = String(prefs().checkin_days || 90);
          return select;
        })()) : null),
    h("section", { class: "card stack" },
      h("h2", {}, T("Räume")),
      data.rooms.length ? data.sites.map((site) => [
        several ? h("p", { class: "small" }, h("strong", {}, site.name)) : null,
        roomsIn(site).map((room) => h("div", { class: "room-setting" },
          toggle(room.name, `${plural(data.places.filter((place) => mapOf(place).room_id === room.id).length, T("Platz"), T("Plätze"))}`, !hidden.has(room.id), (on) => {
            const next = new Set(dashboardPrefs().hidden_rooms);
            if (on) next.delete(room.id);
            else next.add(room.id);
            savePreferences({ dashboard: { hidden_rooms: [...next] } });
          }),
          h("a", { class: "button cover-link", href: `#/titelbild/${room.id}`, "aria-label": T("Titelbild von {0} ändern", [room.name]) }, icon("edit"), T("Titelbild")))),
      ]) : h("p", { class: "muted small" }, T("Noch keine Räume.")))));
}

// Übersichtskarte: ein Punkt je Raum, verbunden zu einem Netz, das die Suche als Ganzes durchsucht.

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs, ...children) {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value !== undefined && value !== null) element.setAttribute(key, value);
  }
  element.append(...children.filter(Boolean));
  return element;
}

function roomFigures(room) {
  const maps = mapsIn(room);
  const places = data.places.filter((place) => maps.includes(mapOf(place)));
  return {
    items: data.items.filter((item) => places.includes(placeOf(item))).length,
    places: places.length,
    surveyed: places.filter((place) => place.surveyed).length,
  };
}

function shorten(text, length) {
  return text.length > length ? `${text.slice(0, length - 1)}…` : text;
}

// Kein Punkt verdeckt einen anderen: Zu nahe Punkte weichen sanft aus, festgehaltene bleiben stehen.
function separateNodes(nodes, clampNode, gap, held = []) {
  for (let round = 0; round < 40; round += 1) {
    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = b.x - a.x || 0.5;
        const dy = b.y - a.y || 0.5;
        const distance = Math.hypot(dx, dy);
        const wanted = a.r + b.r + gap;
        if (distance >= wanted) continue;
        const push = (wanted - distance) / distance;
        const aHeld = held.includes(a);
        const bHeld = held.includes(b);
        if (aHeld && bHeld) continue;
        const aShare = aHeld ? 0 : bHeld ? 1 : 0.5;
        const bShare = bHeld ? 0 : aHeld ? 1 : 0.5;
        a.x -= dx * push * aShare;
        a.y -= dy * push * aShare;
        b.x += dx * push * bShare;
        b.y += dy * push * bShare;
        clampNode(a);
        clampNode(b);
      }
    }
  }
}

function buildMeshNodes(width, height) {
  const several = data.sites.length > 1;
  const compact = width < 480;
  const rooms = dashboardRooms();
  const figures = new Map(rooms.map((room) => [room.id, roomFigures(room)]));
  const most = Math.max(1, ...[...figures.values()].map((figure) => figure.items));
  const smallest = compact ? 15 : 18;
  const largest = compact ? 30 : 38;
  const nodes = rooms.map((room) => {
    const figure = figures.get(room.id);
    return {
      id: room.id, kind: "room", record: room, site: room.site_id, name: room.name, figure,
      r: smallest + Math.sqrt(figure.items / most) * (largest - smallest),
    };
  });
  if (several) {
    data.sites.forEach((site) => {
      nodes.push({ id: site.id, kind: "site", record: site, site: site.id, name: site.name, r: 8 });
    });
  }
  const clampNode = (node) => {
    const side = Math.min(width / 2, node.kind === "site" ? 44 : Math.max(node.r + 6, compact ? 42 : 56));
    node.x = Math.min(width - side, Math.max(side, node.x));
    node.y = Math.min(height - node.r - 24, Math.max(node.r + 8, node.y));
  };
  const free = [];
  nodes.forEach((node, index) => {
    if (node.record.map_x !== null && node.record.map_x !== undefined) {
      node.x = node.record.map_x * width;
      node.y = node.record.map_y * height;
    } else {
      // Neue Punkte starten rund um die Mitte ihres Standorts. Das Ergebnis ist bei jedem Laden gleich.
      const siteIndex = data.sites.findIndex((site) => site.id === node.site);
      const centerX = ((siteIndex + 0.5) / data.sites.length) * width;
      const siblings = nodes.filter((other) => other.kind === "room" && other.site === node.site);
      const angle = (siblings.indexOf(node) / Math.max(1, siblings.length)) * 2 * Math.PI - Math.PI / 2 + siteIndex;
      const reachX = node.kind === "site" || siblings.length < 2 ? 0 : (width / data.sites.length) * 0.34;
      const reachY = node.kind === "site" || siblings.length < 2 ? 0 : height * 0.3;
      node.x = centerX + Math.cos(angle) * reachX;
      node.y = height * 0.47 + Math.sin(angle) * reachY;
      free.push(node);
    }
    clampNode(node);
  });
  for (let round = 0; round < 90; round += 1) {
    for (const node of free) {
      for (const other of nodes) {
        if (other === node) continue;
        const dx = node.x - other.x || 0.5;
        const dy = node.y - other.y || 0.5;
        const distance = Math.hypot(dx, dy);
        const wanted = node.r + other.r + (compact ? 46 : 62);
        if (distance < wanted) {
          const push = ((wanted - distance) / distance) * 0.5;
          node.x += dx * push;
          node.y += dy * push;
        }
      }
      clampNode(node);
    }
  }
  const gap = compact ? 30 : 34;
  separateNodes(nodes, clampNode, gap);
  return { nodes, clampNode, gap };
}

// Bis fünf Punkte sind alle verbunden. Darüber bleibt das Netz lesbar: jeder hängt am Netz und an seinen zwei Nachbarn.
function buildMeshLinks(nodes) {
  const links = new Map();
  const link = (a, b) => {
    const key = [a.id, b.id].sort().join("|");
    if (!links.has(key)) links.set(key, { a, b });
  };
  const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const hubs = nodes.filter((node) => node.kind === "site");
  hubs.forEach((hub, index) => hubs.slice(index + 1).forEach((other) => link(hub, other)));
  for (const site of data.sites) {
    const rooms = nodes.filter((node) => node.kind === "room" && node.site === site.id);
    const hub = hubs.find((node) => node.id === site.id);
    if (hub) rooms.forEach((room) => link(hub, room));
    if (rooms.length <= 5) {
      rooms.forEach((room, index) => rooms.slice(index + 1).forEach((other) => link(room, other)));
      continue;
    }
    const joined = [rooms[0]];
    const waiting = rooms.slice(1);
    while (waiting.length) {
      let best = null;
      for (const from of joined) {
        for (const to of waiting) {
          if (!best || distance(from, to) < distance(best.from, best.to)) best = { from, to };
        }
      }
      link(best.from, best.to);
      joined.push(best.to);
      waiting.splice(waiting.indexOf(best.to), 1);
    }
    for (const room of rooms) {
      [...rooms].filter((other) => other !== room)
        .sort((x, y) => distance(room, x) - distance(room, y))
        .slice(0, 2)
        .forEach((other) => link(room, other));
    }
  }
  return [...links.values()];
}

function meshMap() {
  const stage = h("div", { class: `mesh-stage${dashboardRooms().length < 2 ? " small" : ""}` });
  const caption = h("span", { class: "muted small" });
  const defaultCaption = dashboardRooms().length > 1
    ? T("Punktgröße: Einträge. Ring: bestätigte Plätze. Ziehen zum Verschieben.")
    : T("Mit weiteren Räumen entsteht hier dein Netz.");
  caption.textContent = defaultCaption;
  const card = h("section", { class: "minimap", "aria-label": T("Übersichtskarte") },
    h("div", { class: "section-head" }, h("h2", {}, T("Deine Standorte")), caption),
    stage);
  let hits = null;
  let nodes = [];
  let links = [];
  let linkLayer = null;
  let drawnWidth = 0;

  const drawLinks = () => {
    linkLayer.replaceChildren(...links.map((entry) => {
      entry.line = svgEl("line", { class: "mesh-link" });
      return entry.line;
    }));
    placeLinks();
    applyHits();
  };
  const placeLinks = () => {
    for (const { a, b, line } of links) {
      line.setAttribute("x1", a.x);
      line.setAttribute("y1", a.y);
      line.setAttribute("x2", b.x);
      line.setAttribute("y2", b.y);
    }
  };
  const placeNode = (node) => node.element.setAttribute("transform", `translate(${node.x} ${node.y})`);
  const touching = (node, on) => {
    for (const entry of links) {
      if (entry.a === node || entry.b === node) entry.line.classList.toggle("active", on);
    }
  };
  function applyHits() {
    const searching = hits !== null;
    card.classList.toggle("searching", searching);
    const lit = (node) => node.kind === "room" && searching && hits.has(node.id);
    for (const node of nodes) {
      node.element.classList.toggle("hit", lit(node));
      node.element.classList.toggle("dim", searching && !lit(node));
    }
    for (const { a, b, line } of links) {
      const both = (lit(a) || a.kind === "site") && (lit(b) || b.kind === "site") && (lit(a) || lit(b));
      line.classList.toggle("lit", searching && both);
      line.classList.toggle("dim", searching && !both);
    }
  }

  const save = (moved) => {
    if (offlineSince !== null) return;
    const width = stage.clientWidth;
    const height = stage.clientHeight;
    for (const node of moved) {
      const x = Math.min(1, Math.max(0, node.x / width));
      const y = Math.min(1, Math.max(0, node.y / height));
      if (node.record.map_x === x && node.record.map_y === y) continue;
      node.record.map_x = x;
      node.record.map_y = y;
      const path = node.kind === "site" ? "sites" : "rooms";
      api("PATCH", `api/${path}/${node.id}`, { map_x: x, map_y: y }).catch((error) => {
        if (error.message !== "PIN erforderlich") toast(error.message);
      });
    }
  };

  const draw = () => {
    const width = stage.clientWidth;
    if (!width || width === drawnWidth) return;
    drawnWidth = width;
    const height = stage.clientHeight;
    const built = buildMeshNodes(width, height);
    const { clampNode, gap } = built;
    nodes = built.nodes;
    links = buildMeshLinks(nodes);
    linkLayer = svgEl("g", {});
    const nodeLayer = svgEl("g", {});
    for (const node of nodes) {
      const isRoom = node.kind === "room";
      const figure = node.figure;
      const share = isRoom && figure.places ? figure.surveyed / figure.places : 0;
      const label = svgEl("text", { class: "mesh-label", y: isRoom ? node.r + 18 : -14, "text-anchor": "middle" });
      label.textContent = shorten(node.name, width < 480 ? 13 : 18);
      const shape = isRoom
        ? [
          svgEl("circle", { class: `mesh-core${figure.items ? "" : " empty"}`, r: node.r }),
          svgEl("circle", { class: "mesh-track", r: node.r + 4 }),
          share ? svgEl("circle", {
            class: "mesh-ring",
            r: node.r + 4,
            pathLength: 100,
            "stroke-dasharray": `${share * 100} 100`,
            transform: "rotate(-90)",
          }) : null,
          (() => {
            const count = svgEl("text", { class: "mesh-count", "text-anchor": "middle", "dominant-baseline": "central" });
            count.textContent = String(figure.items);
            return count;
          })(),
        ]
        : [svgEl("circle", { class: "mesh-hub", r: node.r })];
      node.element = svgEl("a", {
        class: `mesh-node ${node.kind}`,
        href: isRoom ? roomHref(node.record) : "#/",
        "aria-label": isRoom
          ? T("{0}: {1}, {2} von {3} bestätigt", [node.name, plural(figure.items, T("Eintrag"), T("Einträge")), figure.surveyed, plural(figure.places, T("Platz"), T("Plätzen"))])
          : T("{0}, Standort", [node.name]),
      }, svgEl("circle", { class: "mesh-hit", r: Math.max(node.r + 8, 24) }), ...shape, label);
      placeNode(node);

      // Am Standortpunkt hängen seine Räume und ziehen mit.
      const group = () => (isRoom ? [node] : nodes.filter((other) => other.site === node.site));
      let start = null;
      let moved = false;
      node.element.addEventListener("pointerdown", (event) => {
        if (event.button) return;
        start = { x: event.clientX, y: event.clientY, origin: group().map((member) => ({ member, x: member.x, y: member.y })) };
        moved = false;
        node.element.setPointerCapture(event.pointerId);
      });
      node.element.addEventListener("pointermove", (event) => {
        if (!start) return;
        const dx = event.clientX - start.x;
        const dy = event.clientY - start.y;
        if (!moved && Math.hypot(dx, dy) < 6) return;
        if (!moved) {
          moved = true;
          node.element.classList.add("dragging");
          touching(node, true);
        }
        for (const { member, x, y } of start.origin) {
          member.x = x + dx;
          member.y = y + dy;
          clampNode(member);
          placeNode(member);
        }
        placeLinks();
      });
      const finish = () => {
        if (!start) return;
        start = null;
        node.element.classList.remove("dragging");
        touching(node, false);
        if (moved) {
          separateNodes(nodes, clampNode, gap, group());
          nodes.forEach(placeNode);
          save(nodes); // Beim ersten Mal halten so auch die übrigen Punkte ihre Lage.
          links = buildMeshLinks(nodes);
          drawLinks();
        }
      };
      node.element.addEventListener("pointerup", finish);
      node.element.addEventListener("pointercancel", finish);
      node.element.addEventListener("click", (event) => {
        if (moved || !isRoom) event.preventDefault();
        moved = false;
      });
      node.element.addEventListener("pointerenter", () => touching(node, true));
      node.element.addEventListener("pointerleave", () => { if (!start) touching(node, false); });
      // Auch ohne Maus verschiebbar: Pfeiltasten bei ausgewähltem Punkt.
      node.element.addEventListener("keydown", (event) => {
        const step = { ArrowLeft: [-12, 0], ArrowRight: [12, 0], ArrowUp: [0, -12], ArrowDown: [0, 12] }[event.key];
        if (!step) return;
        event.preventDefault();
        for (const member of group()) {
          member.x += step[0];
          member.y += step[1];
          clampNode(member);
          placeNode(member);
        }
        placeLinks();
        save(nodes);
      });
      nodeLayer.append(node.element);
    }
    const dots = svgEl("pattern", { id: "mesh-dots", width: 22, height: 22, patternUnits: "userSpaceOnUse" },
      svgEl("circle", { class: "mesh-dot", cx: 1.5, cy: 1.5, r: 1 }));
    const svg = svgEl("svg", { width, height, role: "group", "aria-label": T("Räume als verschiebbare Punkte") },
      svgEl("defs", {}, dots),
      svgEl("rect", { width, height, fill: "url(#mesh-dots)" }),
      linkLayer,
      nodeLayer);
    stage.replaceChildren(svg);
    drawLinks();
  };

  const observer = new ResizeObserver(() => {
    if (!card.isConnected) {
      observer.disconnect();
      return;
    }
    draw();
  });
  observer.observe(stage);

  return {
    element: card,
    // Zeigt, in welchen Räumen die aktuelle Suche etwas findet.
    highlight(roomIds) {
      hits = roomIds;
      caption.textContent = roomIds === null
        ? defaultCaption
        : roomIds.size === 1 ? T("Treffer in einem Raum") : T("Treffer in {0} Räumen", [roomIds.size]);
      if (linkLayer) applyHits();
    },
  };
}

function roomsWithHits(query, low) {
  const rooms = new Set();
  const addPlace = (place) => rooms.add(mapOf(place).room_id);
  for (const group of searchItems(query, low)) group.items.forEach((item) => addPlace(placeOf(item)));
  if (!low) {
    searchPlaces(query).forEach(addPlace);
    searchRooms(query).forEach((room) => rooms.add(room.id));
  }
  return rooms;
}

function roomTile(room) {
  const maps = mapsIn(room);
  const items = data.items.filter((item) => maps.includes(mapOf(placeOf(item))));
  return h("div", { class: "tile-wrap" },
    h("a", { class: "tile", href: roomHref(room) },
      roomCover(room),
      h("div", { class: "tile-text" },
        h("strong", {}, room.name),
        h("span", { class: "muted small" }, maps.length
          ? `${plural(maps.length, T("Schrank"), T("Schränke"))} · ${plural(items.length, T("Eintrag"), T("Einträge"))}`
          : T("noch leer")))),
    h("a", { class: "tile-edit", href: `#/titelbild/${room.id}`, title: T("Titelbild ändern"), "aria-label": T("Titelbild von {0} ändern", [room.name]) }, icon("edit")));
}

// Titelbild einer Raumkachel: gewähltes Symbol, gewählter Ausschnitt oder automatisch das erste Raumfoto.
const COVER_ICONS = [
  ["werkzeug", T("Werkzeug")],
  ["werkzeugkasten", T("Werkzeugkasten")],
  ["auto", T("Auto")],
  ["fahrrad", T("Fahrrad")],
  ["garten", T("Garten")],
  ["haus", T("Haus")],
  ["keller", T("Keller")],
  ["dachboden", T("Dachboden")],
  ["kiste", T("Kiste")],
  ["regal", T("Regal")],
];
const COVER_ZOOM_MAX = 4;

function automaticCover(room) {
  return room.plan_photo || (mapsIn(room).find((map) => map.photo) || {}).photo || null;
}

// Der Punkt (x, y) des Fotos steht in der Mitte der Kachel, soweit das Foto bis zum Rand reicht.
// Die Lage hängt von der Kachelgröße ab und wird deshalb bei jeder Größenänderung neu berechnet.
// Ein noch nicht hochgeladenes Foto kommt als Canvas, denn die Sicherheitsrichtlinie erlaubt nur Bilder vom Server.
function coverImage(picture, x = 0.5, y = 0.5, zoom = 1) {
  const element = typeof picture === "string" ? h("img", { src: picture, alt: "" }) : copyCanvas(picture);
  const frame = h("div", { class: "cover" }, element);
  const place = () => {
    const width = frame.clientWidth;
    const height = frame.clientHeight;
    const [naturalWidth, naturalHeight] = element.tagName === "IMG" ? [element.naturalWidth, element.naturalHeight] : [element.width, element.height];
    if (!width || !height || !naturalWidth || !naturalHeight) return;
    const scale = Math.max(width / naturalWidth, height / naturalHeight) * zoom;
    const shownWidth = naturalWidth * scale;
    const shownHeight = naturalHeight * scale;
    const offset = (wanted, lowest) => Math.min(0, Math.max(lowest, wanted));
    Object.assign(element.style, {
      width: `${shownWidth}px`,
      height: `${shownHeight}px`,
      left: `${offset(width / 2 - x * shownWidth, width - shownWidth)}px`,
      top: `${offset(height / 2 - y * shownHeight, height - shownHeight)}px`,
    });
  };
  if (element.tagName === "IMG") element.addEventListener("load", place);
  const observer = new ResizeObserver(() => {
    if (frame.isConnected) place();
    else observer.disconnect();
  });
  observer.observe(frame);
  return frame;
}

function copyCanvas(source) {
  const canvas = h("canvas", { class: "look", width: String(source.width), height: String(source.height) });
  canvas.getContext("2d").drawImage(source, 0, 0);
  return canvas;
}

async function photoCanvas(file) {
  const bitmap = await createImageBitmap(await readableImage(file));
  const scale = Math.min(1, MAX_PHOTO_EDGE / Math.max(bitmap.width, bitmap.height));
  const canvas = h("canvas", { width: String(Math.round(bitmap.width * scale)), height: String(Math.round(bitmap.height * scale)) });
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return canvas;
}

function roomCover(room) {
  if (room.cover_icon && ICONS[room.cover_icon]) return h("div", { class: "tile-icon cover-icon" }, icon(room.cover_icon));
  if (room.cover_photo) return coverImage(`fotos/${room.cover_photo}`, room.cover_x ?? 0.5, room.cover_y ?? 0.5, room.cover_zoom || 1);
  const picture = automaticCover(room);
  return picture ? coverImage(`fotos/${picture}`) : h("div", { class: "tile-icon" }, icon("plan"));
}

// Alle Fotos, die zu einem Raum gehören: Plan, Schränke, Inhalte und das bisherige Titelbild.
function roomPhotos(room) {
  const maps = mapsIn(room);
  const ids = [room.cover_photo, room.plan_photo, ...maps.map((map) => map.photo),
    ...data.places.filter((place) => maps.includes(mapOf(place))).flatMap((place) => place.photos)];
  return [...new Set(ids.filter(Boolean))];
}

function viewCover(roomId) {
  const room = data.rooms.find((candidate) => candidate.id === roomId);
  if (!room) return viewMissing(T("Diesen Raum gibt es nicht."));
  const draft = {
    photo: room.cover_photo, x: room.cover_x ?? 0.5, y: room.cover_y ?? 0.5, zoom: room.cover_zoom || 1,
    icon: room.cover_icon, file: null, canvas: null,
  };
  const photos = roomPhotos(room);
  const previewSlot = h("div", { class: "cover-preview" });
  const editor = h("div", { class: "stack" });
  const hasPhoto = () => Boolean(draft.photo || draft.canvas);
  const picture = () => draft.canvas || `fotos/${draft.photo}`;
  const choose = (change) => {
    Object.assign(draft, { photo: null, icon: null, file: null, canvas: null, x: 0.5, y: 0.5, zoom: 1 }, change);
    draw();
  };

  const updatePreview = () => {
    const cover = draft.icon
      ? h("div", { class: "tile-icon cover-icon" }, icon(draft.icon))
      : hasPhoto()
        ? coverImage(picture(), draft.x, draft.y, draft.zoom)
        : roomCover({ ...room, cover_photo: null, cover_icon: null });
    previewSlot.replaceChildren(h("div", { class: "tile" }, cover,
      h("div", { class: "tile-text" }, h("strong", {}, room.name),
        h("span", { class: "muted small" }, draft.icon ? T("Symbol") : hasPhoto() ? T("Eigener Ausschnitt") : T("Automatisch")))));
  };

  // Antippen oder Ziehen legt fest, welcher Punkt des Fotos in der Mitte der Kachel steht.
  const cropper = () => {
    const marker = h("span", { class: "cover-marker" });
    const place = () => Object.assign(marker.style, { left: `${draft.x * 100}%`, top: `${draft.y * 100}%` });
    const image = draft.canvas ? copyCanvas(draft.canvas) : h("img", { src: picture(), alt: "", draggable: "false" });
    let pressed = false;
    const pick = (event) => {
      const box = image.getBoundingClientRect();
      if (!box.width || !box.height) return;
      draft.x = Math.round(Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)) * 1000) / 1000;
      draft.y = Math.round(Math.min(1, Math.max(0, (event.clientY - box.top) / box.height)) * 1000) / 1000;
      place();
      updatePreview();
    };
    const frame = h("div", {
      class: "cover-source",
      onpointerdown: (event) => { pressed = true; frame.setPointerCapture(event.pointerId); pick(event); },
      onpointermove: (event) => { if (pressed) pick(event); },
      onpointerup: () => { pressed = false; },
      onpointercancel: () => { pressed = false; },
    }, image, marker);
    place();
    const zoom = h("input", {
      type: "range", min: "1", max: String(COVER_ZOOM_MAX), step: "0.1", value: String(draft.zoom),
      "aria-label": T("Vergrößerung"),
      oninput: (event) => { draft.zoom = Number(event.target.value); updatePreview(); },
    });
    return h("section", { class: "card stack" },
      h("h2", {}, T("Ausschnitt")),
      h("p", { class: "muted small" }, T("Tippe auf die Stelle, die in der Mitte stehen soll, und vergrößere nach Bedarf.")),
      frame,
      h("label", { class: "field" }, T("Vergrößerung"), zoom));
  };

  const photoChoice = () => h("section", { class: "card stack" },
    h("h2", {}, T("Foto auswählen")),
    photos.length ? h("div", { class: "cover-choices" }, photos.map((id) => h("button", {
      type: "button",
      class: "cover-choice",
      "aria-pressed": String(draft.photo === id),
      "aria-label": T("Dieses Foto wählen"),
      onclick: () => choose({ photo: id }),
    }, h("img", { src: `fotos/${id}`, alt: "" })))) : h("p", { class: "muted small" }, T("Dieser Raum hat noch keine Fotos.")),
    h("div", { class: "row" }, photoButton(T("Neues Foto hochladen"), "", async (file) => {
      try {
        choose({ file, canvas: await photoCanvas(file) });
      } catch (error) {
        toast(error.message || T("Dieses Bild konnte nicht gelesen werden"));
      }
    }), draft.canvas ? h("span", { class: "muted small" }, T("Wird beim Speichern hinzugefügt.")) : null));

  const iconChoice = () => h("section", { class: "card stack" },
    h("h2", {}, T("Oder ein Symbol")),
    h("div", { class: "cover-icons" }, COVER_ICONS.map(([name, label]) => h("button", {
      type: "button",
      class: "cover-icon-choice",
      "aria-pressed": String(draft.icon === name),
      onclick: () => choose({ icon: name }),
    }, icon(name), h("span", { class: "small" }, label)))));

  const save = () => act(async () => {
    let body = { cover_photo: null, cover_icon: null };
    if (draft.icon) body = { cover_icon: draft.icon };
    else if (hasPhoto()) {
      const photo = draft.file ? (await uploadPhoto(draft.file)).id : draft.photo;
      body = { cover_photo: photo, cover_x: draft.x, cover_y: draft.y, cover_zoom: draft.zoom };
    }
    await api("PATCH", `api/rooms/${room.id}`, body);
  }, () => {
    toast(T("Titelbild gespeichert"));
    location.hash = "#/";
  });

  function draw() {
    updatePreview();
    editor.replaceChildren(...[hasPhoto() ? cropper() : null, photoChoice(), iconChoice()].filter(Boolean));
  }

  draw();
  app.replaceChildren(...shell(
    backLink("#/", T("Zum Dashboard")),
    h("h1", {}, T("Titelbild: {0}", [room.name])),
    h("p", { class: "muted" }, T("Wähle einen Ausschnitt aus einem Foto des Raums, lade ein neues hoch oder nimm ein Symbol.")),
    h("div", { class: "cover-layout" },
      h("div", { class: "cover-side" }, previewSlot,
        h("div", { class: "row" },
          h("button", { type: "button", class: "primary", onclick: save }, icon("check"), T("Speichern")),
          h("button", { type: "button", onclick: () => choose({}) }, T("Automatisch")),
          h("a", { class: "button", href: "#/" }, T("Abbrechen")))),
      editor)));
}

function mapTile(map) {
  const places = placesOf(map);
  return h("a", { class: "tile", href: `#/karte/${map.id}` },
    map.photo ? h("img", { src: `fotos/${map.photo}`, alt: "" }) : h("div", { class: "tile-icon" }, icon("cabinet")),
    h("div", { class: "tile-text" },
      h("strong", {}, map.name),
      h("span", { class: "muted small" }, plural(places.length, T("Platz"), T("Plätze")))));
}

function sitesSection() {
  const newName = h("input", { type: "text", placeholder: T("Zum Beispiel: Ferienhaus"), "aria-label": T("Neues Haus oder Grundstück") });
  return h("details", {
    class: "more",
    open: sitesOpen,
    ontoggle: (event) => { sitesOpen = event.target.open; },
  },
  h("summary", {}, T("Häuser und Grundstücke")),
  h("div", { class: "stack" },
    data.sites.map((site) => h("div", { class: "add-row" },
      h("input", {
        type: "text",
        value: site.name,
        "aria-label": T("Name von {0}", [site.name]),
        onchange: (event) => act(() => api("PATCH", `api/sites/${site.id}`, { name: event.target.value })),
      }),
      data.sites.length > 1 ? h("button", {
        type: "button",
        class: "compact danger",
        onclick: () => {
          const count = roomsIn(site).length;
          if (confirm(T("„{0}“ mit {1} und allem Inhalt löschen? Es bleibt 30 Tage im Papierkorb.", [site.name, plural(count, T("Raum"), T("Räumen"))]))) {
            deleteWithUndo(`api/sites/${site.id}`, T("„{0}“ gelöscht", [site.name]));
          }
        },
      }, T("Löschen")) : null)),
    h("form", {
      class: "add-row",
      onsubmit: (event) => {
        event.preventDefault();
        if (newName.value.trim()) act(() => api("POST", "api/sites", { name: newName.value }));
      },
    }, newName, h("button", { type: "submit" }, T("Hinzufügen")))));
}

function welcome() {
  return h("section", { class: "welcome" },
    brandHero(),
    h("h1", {}, T("Wo fangen wir an?")),
    h("p", { class: "lead" }, T("Ein Raum nach dem anderen. Werkstatt, Garage, Carport oder Gartenhaus: Du entscheidest, was dazugehört.")),
    h("ol", { class: "steps" },
      h("li", {}, h("strong", {}, T("Raum anlegen")), h("span", {}, T("auf Wunsch mit Grundriss"))),
      h("li", {}, h("strong", {}, T("Schrank fotografieren")), h("span", {}, T("und jede Schublade antippen"))),
      h("li", {}, h("strong", {}, T("Inhalt fotografieren")), h("span", {}, T("und auf Wunsch erkennen lassen"))),
      h("li", {}, h("strong", {}, T("Etiketten drucken")), h("span", {}, T("aufkleben, fertig")))),
    h("a", { class: "button primary large", href: `#/neuer-raum/${data.sites[0].id}` }, icon("plus"), T("Ersten Raum anlegen")),
    h("section", { class: "card stack welcome-restore" },
      h("h2", {}, T("Umzug oder neuer Server?")),
      h("p", { class: "muted small" }, T("Spiel eine Sicherung ein, dann ist findling sofort auf dem alten Stand, mit Inventar und Fotos.")),
      h("div", { class: "row" },
        backupUploadButton(T("Sicherung wählen")),
        h("a", { class: "button", href: "#/sicherungen" }, T("Vom Speicherort")))),
    makerLine());
}

function scheduleSearchLog() {
  clearTimeout(searchLogTimer);
  searchLogTimer = setTimeout(() => {
    const query = searchQuery.trim();
    if (query.length < 2) return;
    const hits = searchItems(query, false).length + searchPlaces(query).length;
    api("POST", "api/events", { q: query, hits }).catch(() => {});
  }, 1500);
}

function renderResults(container) {
  const query = searchQuery.trim();
  if (!query && !onlyLow) {
    container.replaceChildren();
    return;
  }
  const groups = searchItems(query, onlyLow);
  const places = onlyLow ? [] : searchPlaces(query);
  const rooms = onlyLow ? [] : searchRooms(query);
  if (!groups.length && !places.length && !rooms.length) {
    container.replaceChildren(noResults(query));
    return;
  }
  container.replaceChildren(
    ...groups.map(resultGroup),
    ...places.map((place) => h("a", { class: "card result-link", href: `#/p/${place.code}` },
      thumb(place),
      h("div", { class: "grow" },
        h("strong", {}, placeName(place)),
        h("div", { class: "muted small" }, `${placePath(place)} · ${place.code}`)),
      icon("next"))),
    ...rooms.map((room) => h("a", { class: "card result-link", href: roomHref(room) },
      h("span", { class: "number" }, icon("plan")),
      h("div", { class: "grow" },
        h("strong", {}, room.name),
        h("div", { class: "muted small" }, plural(mapsIn(room).length, T("Schrank"), T("Schränke")))),
      icon("next"))));
}

function noResults(query) {
  if (onlyLow) return h("p", { class: "muted" }, T("Dazu ist nichts als wenig oder leer markiert."));
  const cover = coverage();
  if (cover.total && cover.done === cover.total) {
    return h("div", { class: "card empty" }, h("h2", {}, T("„{0}“ hast du nicht", [query])),
      h("p", { class: "muted" }, T("Alle Plätze sind vollständig erfasst.")));
  }
  return h("div", { class: "card empty" }, h("h2", {}, T("„{0}“ ist nicht im Inventar", [query])),
    h("p", { class: "muted" },
      T("Vielleicht hast du es trotzdem, denn erst {0} von {1} Plätzen sind vollständig erfasst.", [cover.done, cover.total])));
}

function resultGroup(group) {
  return h("section", { class: "card result" },
    h("h2", {}, group.name),
    group.items.map((item) => {
      const place = placeOf(item);
      return h("div", { class: "result-row" },
        h("a", { class: "result-link", href: `#/p/${place.code}` },
          h("div", { class: "thumbs" }, planThumb(mapOf(place)), thumb(place)),
          h("div", { class: "grow" },
            h("strong", { class: "where" }, placePath(place)),
            h("div", { class: "muted small" }, [place.code, quantityOf(item) > 1 ? T("{0} Stück", [quantityOf(item)]) : "", item.note].filter(Boolean).join(" · ")),
            (() => {
              const hits = detailHits(item, searchQuery);
              return hits.length ? h("div", { class: "small detail-hit" }, T("Darin: {0}", [hits.slice(0, 6).join(", ")])) : null;
            })(),
            h("div", { class: "row tight" }, fillChip(item.fill, item),
              item.missing ? h("span", { class: "flag-missing small" }, T("zuletzt nicht da")) : null),
            itemFlags(item)),
          icon("next")),
        h("div", { class: "row tight" },
          detailLines(item).length || (item.photos || []).length
            ? h("a", { class: "linklike small detail-link", href: `#/detail/${item.id}` }, icon("lupe"), T("Inhalt ansehen"))
            : null,
          hasPassport(item) ? h("a", { class: "linklike small detail-link", href: `#/steckbrief/${item.id}` }, icon("doc"), T("Steckbrief")) : null),
        foundButtons(item));
    }));
}

function foundButtons(item) {
  return h("div", { class: "row tight found-buttons" },
    h("button", {
      type: "button",
      class: "compact",
      onclick: () => act(() => api("POST", `api/items/${item.id}/found`), () => { toast(T("Gemerkt: Es liegt noch dort.")); render(); }),
    }, icon("check"), T("Gefunden")),
    h("button", {
      type: "button",
      class: "compact quiet",
      onclick: () => act(() => api("POST", `api/items/${item.id}/missing`), () => { toast(T("Gemerkt: Dort lag es nicht.")); render(); }),
    }, T("Nicht da")));
}

function photoDropzone(title, onFile, small) {
  const zone = h("label", {
    class: `dropzone${small ? " small" : ""}`,
    ondragover: (event) => { event.preventDefault(); zone.classList.add("over"); },
    ondragleave: () => zone.classList.remove("over"),
    ondrop: (event) => {
      event.preventDefault();
      zone.classList.remove("over");
      const file = event.dataTransfer.files[0];
      if (file) onFile(file);
    },
  },
  icon("camera"),
  h("strong", {}, title),
  h("span", { class: "muted" }, T("Hier antippen oder Bild hineinziehen")),
  photoInput(onFile));
  return zone;
}

// Ansicht: Neuer Raum

function viewNewRoom(siteId) {
  const site = data.sites.find((candidate) => candidate.id === siteId);
  if (!site) return viewMissing(T("Dieses Haus oder Grundstück gibt es nicht."));
  const used = new Set(roomsIn(site).map((room) => room.name));
  const create = (name) => {
    let created;
    act(async () => {
      created = await api("POST", "api/rooms", { site_id: site.id, name });
    }, () => { location.hash = `#/neu/${created.id}`; });
  };
  const nameInput = h("input", { type: "text", placeholder: T("Anderer Name"), "aria-label": T("Name des Raums") });
  app.replaceChildren(...shell(
    backLink("#/", T("Zurück")),
    h("h1", {}, T("Neuer Raum oder Bereich")),
    data.sites.length > 1 ? h("p", { class: "muted" }, site.name) : null,
    h("div", { class: "chips room-ideas" }, ROOM_IDEAS.filter((name) => !used.has(name)).map((name) =>
      h("button", { type: "button", class: "chip", onclick: () => create(name) }, name))),
    h("form", {
      class: "add-row",
      onsubmit: (event) => {
        event.preventDefault();
        if (nameInput.value.trim()) create(nameInput.value);
      },
    }, nameInput, h("button", { class: "primary wide", type: "submit" }, T("Anlegen")))));
}

// Ansicht: Neuer Schrank

function viewNewMap(roomId) {
  const room = data.rooms.find((candidate) => candidate.id === roomId);
  if (!room) return viewMissing(T("Diesen Raum gibt es nicht."));
  const body = h("div", {});
  const choose = (file) => {
    body.replaceChildren(h("div", { class: "dropzone" }, h("strong", {}, T("Foto wird geladen ..."))));
    let created;
    act(async () => {
      const photo = await uploadPhoto(file);
      // Der Name ist nur ein Vorschlag und lässt sich auf der nächsten Seite direkt ändern.
      created = await api("POST", "api/maps", { room_id: room.id, name: T("Schrank {0}", [mapsIn(room).length + 1]), photo: photo.id });
    }, () => { location.hash = `#/karte/${created.id}`; }).then(() => {
      if (!created) body.replaceChildren(photoDropzone(T("Foto vom ganzen Schrank oder Bereich"), choose));
    });
  };
  body.replaceChildren(photoDropzone(T("Foto vom ganzen Schrank oder Bereich"), choose));
  app.replaceChildren(...shell(
    backLink(roomHref(room), room.name),
    h("h1", {}, T("Neuer Schrank oder Regal")),
    h("p", { class: "muted" }, T("In {0}. Das kann auch ein ganzer Bereich sein, etwa der Holzstapel im Schuppen.", [room.name])),
    body));
}

// Ansicht: Schrank mit seinen Plätzen

function viewMap(mapId) {
  const map = data.maps.find((candidate) => candidate.id === mapId);
  if (!map) return viewMissing(T("Diesen Schrank gibt es nicht."));
  const places = placesOf(map);
  const room = roomOf(map);
  const nextPhoto = places.find((place) => !place.surveyed && !place.photos.length);
  if (offlineSince !== null || editFrames === map.id) {
    pageCamera = null;
  } else if (nextPhoto) {
    pageCamera = {
      // Mit API-Schlüssel kostet die Erkennung, deshalb steht es auf dem Knopf.
      text: automaticRecognition() ? T("{0}: Foto + erkennen", [placeName(nextPhoto)]) : `${placeName(nextPhoto)} fotografieren`,
      onFile: async (file) => {
        toast(T("Foto wird geladen ..."));
        try {
          const created = await uploadPhoto(file, nextPhoto.id);
          recognizeOnArrival = created.id;
          await reload();
        } catch (error) {
          if (error.message !== "PIN erforderlich") toast(error.message);
          return;
        }
        document.getElementById("toast").hidden = true;
        location.hash = `#/p/${nextPhoto.code}`;
      },
    };
  } else if (!places.length && !map.photo) {
    pageCamera = {
      text: T("Schrank fotografieren"),
      onFile: (file) => {
        toast(T("Foto wird geladen ..."));
        act(async () => {
          const photo = await uploadPhoto(file);
          await api("PATCH", `api/maps/${map.id}`, { photo: photo.id });
        }, () => {
          editFrames = map.id;
          document.getElementById("toast").hidden = true;
          render();
        });
      },
    };
  }

  const stage = h("div", { class: "stage editor" },
    map.photo ? h("img", { src: `fotos/${map.photo}`, alt: T("Foto: {0}", [map.name]), draggable: "false" }) : null,
    places.map((place) => (editFrames === map.id ? null : placeBox(place))));
  if (editFrames === map.id) {
    stage.classList.add("adjusting");
    places.forEach((place) => stage.append(frameEditor(place, stage)));
  }
  const draftBox = h("div", { class: "box draft", hidden: true });
  stage.append(draftBox);

  let draft = null;
  let drag = null;

  const position = (event) => {
    const rect = stage.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
    };
  };
  const drawDraft = () => {
    draftBox.hidden = !draft;
    if (!draft) return;
    Object.assign(draftBox.style, {
      left: `${draft.x * 100}%`, top: `${draft.y * 100}%`, width: `${draft.w * 100}%`, height: `${draft.h * 100}%`,
    });
  };
  // Jeder Tipp ist sofort ein Platz. Ein Name ist freiwillig, ein Fehltipp lässt sich zurücknehmen.
  const savePlace = (box) => {
    const y = window.scrollY;
    let created;
    act(async () => {
      created = await api("POST", "api/places", { map_id: map.id, label: "", ...box });
    }, () => {
      render();
      window.scrollTo(0, y);
      toast(`${placeName(created)} gespeichert`, {
        text: T("Rückgängig"),
        run: () => act(async () => {
          const removed = await api("DELETE", `api/places/${created.id}`);
          await api("DELETE", `api/trash/${removed.trash_id}`);
        }),
      });
    });
  };

  stage.addEventListener("pointerdown", (event) => {
    if (editFrames === map.id) return;
    if (event.button || event.target.closest(".box")) return; // Ein vorhandener Platz öffnet sich über seinen Link.
    drag = { start: position(event), moved: false, mouse: event.pointerType === "mouse" };
    stage.setPointerCapture(event.pointerId);
    if (drag.mouse) event.preventDefault();
  });
  stage.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const now = position(event);
    const w = Math.abs(now.x - drag.start.x);
    const hgt = Math.abs(now.y - drag.start.y);
    if (w < 0.015 && hgt < 0.015 && !drag.moved) return;
    drag.moved = true;
    draft = { x: Math.min(drag.start.x, now.x), y: Math.min(drag.start.y, now.y), w, h: hgt };
    drawDraft();
  });
  stage.addEventListener("pointerup", (event) => {
    if (!drag) return;
    const { moved } = drag;
    const end = position(event);
    drag = null;
    let box = draft;
    if (!moved) {
      const w = 0.16;
      const hgt = 0.12;
      box = {
        x: Math.max(0, Math.min(1 - w, end.x - w / 2)),
        y: Math.max(0, Math.min(1 - hgt, end.y - hgt / 2)),
        w,
        h: hgt,
      };
    } else {
      box = { ...box, w: Math.max(box.w, 0.03), h: Math.max(box.h, 0.03) };
    }
    draft = null;
    drawDraft();
    savePlace(box);
  });
  stage.addEventListener("pointercancel", () => { drag = null; draft = null; drawDraft(); });

  app.replaceChildren(...shell(
    backLink(roomHref(room), room.name),
    h("div", { class: "title-row" },
      h("div", { class: "grow" }, h("input", {
        type: "text",
        class: "title-input",
        value: map.name,
        "aria-label": T("Name des Schranks"),
        onchange: (event) => act(() => api("PATCH", `api/maps/${map.id}`, { name: event.target.value })),
      })),
      places.length ? h("a", { class: "button", href: `#/etiketten/${map.id}` }, icon("printer"), T("Etiketten")) : null),
    !map.photo && places.length && offlineSince === null ? h("div", { class: "notice stack" },
      h("p", {}, T("Dieser Schrank hat noch kein Foto, etwa nach einem Massenimport. Mit einem Foto erscheinen die Plätze als Rahmen, die du verschieben und anpassen kannst.")),
      photoButton(T("Schrankfoto hinzufügen"), "primary", setMapPhoto(map))) : null,
    !map.photo && places.length ? null : h("p", { class: "lead hint" }, editFrames === map.id
      ? T("Zieh einen Rahmen, um ihn zu verschieben. Der runde Griff ändert die Größe.")
      : places.length
        ? T("Tippe auf jede weitere Schublade. Jeder Tipp ist sofort ein Platz, Namen sind freiwillig.")
        : T("Tippe auf jede Schublade oder zieh einen Rahmen darum. Jeder Tipp ist sofort ein Platz.")),
    !places.length && map.photo ? h("button", {
      type: "button",
      class: "whole-photo",
      onclick: () => {
        let created;
        act(async () => {
          created = await api("POST", "api/places", {
            map_id: map.id, label: map.name, x: 0, y: 0, w: 1, h: 1, use_map_photo: true,
          });
        }, () => { location.hash = `#/p/${created.code}`; });
      },
    }, T("Das ganze Foto ist ein Platz")) : null,
    stage,
    places.length && editFrames !== map.id ? nextInMap(map, places) : null,
    places.length ? h("div", { class: "row tight map-actions" },
      editFrames === map.id ? null : h("a", { class: "button compact", href: `#/serie/${map.id}` }, icon("camera"), T("Alle nacheinander fotografieren")),
      h("button", {
        type: "button",
        class: `compact${editFrames === map.id ? " primary" : ""}`,
        onclick: () => { editFrames = editFrames === map.id ? null : map.id; render(); },
      }, editFrames === map.id ? T("Fertig") : T("Rahmen anpassen"))) : null,
    places.length ? h("ul", { class: "place-list" }, places.map((place) => {
      const count = itemsOf(place).length;
      return h("li", {}, h("a", { href: `#/p/${place.code}` },
        h("span", { class: `number${place.surveyed ? " done" : ""}` },
          place.surveyed ? icon("check") : String(placeNumber(place))),
        h("span", { class: "grow" },
          h("strong", {}, placeName(place)),
          h("span", { class: "muted small block" }, count ? plural(count, T("Eintrag"), T("Einträge")) : T("noch leer"))),
        icon("next")));
    })) : null,
    h("a", {
      class: "card result-link standort",
      href: roomHref(room),
      onclick: () => { planSelection = map.id; },
    },
    planThumb(map) || h("span", { class: "number" }, icon("plan")),
    h("span", { class: "grow" },
      h("strong", {}, map.plan_x !== null ? T("Standort im Raumplan") : T("Standort festlegen")),
      h("span", { class: "muted small block" }, room.name)),
    icon("next")),
    h("details", { class: "more" },
      h("summary", {}, T("Mehr")),
      mapManage(map, room),
      h("button", {
        type: "button",
        class: "danger",
        onclick: () => {
          if (confirm(T("„{0}“ mit {1} und allen Einträgen löschen? Es bleibt 30 Tage im Papierkorb.", [map.name, plural(places.length, T("Platz"), T("Plätzen"))]))) {
            deleteWithUndo(`api/maps/${map.id}`, T("„{0}“ gelöscht", [map.name]), () => { location.hash = roomHref(room); });
          }
        },
      }, T("Schrank löschen")))));
}

function frameEditor(place, stage) {
  const handle = h("span", { class: "handle" });
  const frame = h("div", {
    class: "box adjustable",
    style: {
      left: `${place.x * 100}%`, top: `${place.y * 100}%`, width: `${place.w * 100}%`, height: `${place.h * 100}%`,
    },
  }, h("span", {}, String(placeNumber(place))), handle);
  const box = { x: place.x, y: place.y, w: place.w, h: place.h };
  let drag = null;
  const show = () => Object.assign(frame.style, {
    left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.w * 100}%`, height: `${box.h * 100}%`,
  });
  frame.addEventListener("pointerdown", (event) => {
    if (event.button) return;
    drag = { resize: event.target === handle, x: event.clientX, y: event.clientY, origin: { ...box } };
    frame.setPointerCapture(event.pointerId);
    event.preventDefault();
    event.stopPropagation();
  });
  frame.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const rect = stage.getBoundingClientRect();
    const dx = (event.clientX - drag.x) / rect.width;
    const dy = (event.clientY - drag.y) / rect.height;
    if (drag.resize) {
      box.w = Math.min(1 - box.x, Math.max(0.03, drag.origin.w + dx));
      box.h = Math.min(1 - box.y, Math.max(0.03, drag.origin.h + dy));
    } else {
      box.x = Math.min(1 - box.w, Math.max(0, drag.origin.x + dx));
      box.y = Math.min(1 - box.h, Math.max(0, drag.origin.y + dy));
    }
    show();
  });
  const finish = () => {
    if (!drag) return;
    drag = null;
    Object.assign(place, box);
    api("PATCH", `api/places/${place.id}`, box).catch((error) => {
      if (error.message !== "PIN erforderlich") toast(error.message);
    });
  };
  frame.addEventListener("pointerup", finish);
  frame.addEventListener("pointercancel", finish);
  return frame;
}

// Neues Foto für einen Schrank. Danach lassen sich die Rahmen der Plätze darauf anpassen.
function setMapPhoto(map) {
  return (file) => {
    toast(T("Foto wird geladen ..."));
    act(async () => {
      const photo = await uploadPhoto(file);
      await api("PATCH", `api/maps/${map.id}`, { photo: photo.id });
    }, () => {
      editFrames = map.id;
      document.getElementById("toast").hidden = true;
      render();
    });
  };
}

function mapManage(map, room) {
  const otherRooms = data.rooms.filter((candidate) => candidate.id !== room.id);
  const target = otherRooms.length ? h("select", { "aria-label": T("Neuer Raum") }, otherRooms.map((candidate) => {
    const site = data.sites.length > 1 ? `${data.sites.find((entry) => entry.id === candidate.site_id).name} › ` : "";
    return h("option", { value: candidate.id }, `${site}${candidate.name}`);
  })) : null;
  return h("div", { class: "stack manage" },
    photoButton(T("Anderes Foto"), "", setMapPhoto(map)),
    target ? h("div", { class: "add-row" }, target, h("button", {
      type: "button",
      onclick: () => act(() => api("PATCH", `api/maps/${map.id}`, { room_id: target.value }), () => {
        toast(T("Schrank verschoben. Die Adressen und Etiketten bleiben gültig."));
        render();
      }),
    }, T("In diesen Raum"))) : null);
}

function nextInMap(map, places) {
  const open = places.filter((place) => !place.surveyed);
  if (!open.length) return h("p", { class: "notice" }, T("Alle Plätze hier sind bestätigt."));
  return h("a", { class: "button primary next-step", href: `#/p/${open[0].code}` },
    icon("camera"), T("Inhalt erfassen ({0} offen)", [open.length]));
}

// Ansicht: Raum mit Plan und Schränken

function viewRoom(roomId) {
  const room = data.rooms.find((candidate) => candidate.id === roomId);
  if (!room) return viewMissing(T("Diesen Raum gibt es nicht."));
  const maps = mapsIn(room);
  const site = data.sites.find((candidate) => candidate.id === room.site_id);
  const savePlan = (file) => {
    toast(T("Bild wird geladen ..."));
    return act(async () => {
      const photo = await uploadPhoto(file);
      await api("PATCH", `api/rooms/${room.id}`, { plan_photo: photo.id });
    }, loaded);
  };
  const nameInput = h("input", {
    type: "text",
    value: room.name,
    "aria-label": T("Name des Raums"),
    onchange: (event) => act(() => api("PATCH", `api/rooms/${room.id}`, { name: event.target.value })),
  });
  const cabinets = maps.length
    ? h("div", { class: "tiles" },
      maps.map(mapTile),
      h("a", { class: "tile tile-add", href: `#/neu/${room.id}` }, icon("plus"), T("Schrank oder Regal")))
    : h("a", { class: "button primary large", href: `#/neu/${room.id}` }, icon("camera"), T("Ersten Schrank anlegen"));

  app.replaceChildren(...shell(
    backLink("#/", T("Zurück")),
    h("h1", {}, room.name),
    data.sites.length > 1 ? h("p", { class: "muted" }, site.name) : null,
    room.plan_photo ? planEditor(room, maps) : null,
    h("div", { class: "section-head room-head" }, h("h2", {}, T("Schränke und Regale"))),
    cabinets,
    room.plan_photo ? null : h("div", { class: "plan-offer" },
      photoDropzone(T("Grundriss oder Raumfoto hinzufügen"), savePlan, true),
      h("p", { class: "muted small" }, T("Freiwillig. Damit zeigt dir die App später, wo im Raum ein Schrank steht."))),
    h("details", { class: "more" },
      h("summary", {}, T("Mehr")),
      h("div", { class: "stack" },
        h("label", { class: "field" }, T("Name"), nameInput),
        data.sites.length > 1 ? (() => {
          const target = h("select", { "aria-label": T("Haus oder Grundstück") }, data.sites.map((entry) => h("option", { value: entry.id }, entry.name)));
          target.value = room.site_id;
          return h("div", { class: "add-row" }, target, h("button", {
            type: "button",
            onclick: () => act(() => api("PATCH", `api/rooms/${room.id}`, { site_id: target.value, map_x: 0.5, map_y: 0.5 }), () => { toast(T("Raum verschoben")); render(); }),
          }, T("Hierhin")));
        })() : null,
        room.plan_photo ? h("div", { class: "row" },
          photoButton(T("Anderes Bild"), "", savePlan),
          h("button", {
            type: "button",
            class: "danger",
            onclick: () => {
              if (confirm(T("Raumplan mit allen Standorten löschen? Schränke und Inhalte bleiben erhalten."))) {
                act(() => api("PATCH", `api/rooms/${room.id}`, { plan_photo: null }));
              }
            },
          }, T("Raumplan löschen"))) : null,
        h("button", {
          type: "button",
          class: "danger",
          onclick: () => {
            if (confirm(T("„{0}“ mit {1} und allem Inhalt löschen? Es bleibt 30 Tage im Papierkorb.", [room.name, plural(maps.length, T("Schrank"), T("Schränken"))]))) {
              deleteWithUndo(`api/rooms/${room.id}`, T("„{0}“ gelöscht", [room.name]), () => { location.hash = "#/"; });
            }
          },
        }, T("Raum löschen"))))));
}

function planEditor(room, maps) {
  const unplaced = maps.filter((map) => map.plan_x === null);
  if (!maps.some((map) => map.id === planSelection)) planSelection = unplaced.length ? unplaced[0].id : null;
  const selected = maps.find((map) => map.id === planSelection);

  const stage = h("div", { class: `stage editor plan-stage${selected ? " placing" : ""}` },
    h("img", { src: `fotos/${room.plan_photo}`, alt: T("Raumplan {0}", [room.name]), draggable: "false" }));

  const position = (event) => {
    const rect = stage.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
    };
  };
  const savePosition = (map, point) => act(
    () => api("PATCH", `api/maps/${map.id}`, { plan_x: point.x, plan_y: point.y }),
    () => {
      if (planSelection === map.id) {
        const next = data.maps.find((candidate) => candidate.room_id === room.id && candidate.plan_x === null);
        planSelection = next ? next.id : null;
      }
      render();
    },
  );

  for (const map of maps.filter((candidate) => candidate.plan_x !== null)) {
    const pin = h("a", {
      class: `pin${map.id === planSelection ? " current" : ""}`,
      href: `#/karte/${map.id}`,
      draggable: "false",
      title: map.name,
      style: { left: `${map.plan_x * 100}%`, top: `${map.plan_y * 100}%` },
    }, map.name);
    let dragging = false;
    let moved = false;
    pin.addEventListener("pointerdown", (event) => {
      if (event.button) return;
      dragging = true;
      moved = false;
      pin.setPointerCapture(event.pointerId);
      event.stopPropagation();
    });
    pin.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      const point = position(event);
      const rect = stage.getBoundingClientRect();
      const shift = Math.hypot((point.x - map.plan_x) * rect.width, (point.y - map.plan_y) * rect.height);
      if (!moved && shift < 6) return;
      moved = true;
      pin.style.left = `${point.x * 100}%`;
      pin.style.top = `${point.y * 100}%`;
    });
    pin.addEventListener("pointerup", (event) => {
      if (!dragging) return;
      dragging = false;
      if (moved) savePosition(map, position(event));
    });
    pin.addEventListener("pointercancel", () => { dragging = false; render(); });
    // Nach dem Verschieben soll sich der Schrank nicht auch noch öffnen.
    pin.addEventListener("click", (event) => {
      event.stopPropagation();
      if (moved) event.preventDefault();
    });
    stage.append(pin);
  }
  stage.addEventListener("click", (event) => {
    if (selected) savePosition(selected, position(event));
  });

  let hint = T("Leg unten einen Schrank an, dann kannst du ihn hier einzeichnen.");
  if (selected) hint = T("Tippe im Plan auf den Standort von „{0}“.", [selected.name]);
  else if (maps.length) hint = T("Zieh eine Markierung, um sie zu verschieben. Tippst du darauf, öffnet sich der Schrank.");

  return [
    h("p", { class: "lead hint" }, hint),
    maps.length ? h("div", { class: "chips plan-chips" }, maps.map((map) => h("button", {
      type: "button",
      class: "chip",
      "aria-pressed": String(map.id === planSelection),
      onclick: () => { planSelection = map.id === planSelection ? null : map.id; render(); },
    }, map.plan_x !== null ? icon("check") : null, map.name))) : null,
    selected && selected.plan_x !== null ? h("button", {
      type: "button",
      class: "linklike small",
      onclick: () => act(
        () => api("PATCH", `api/maps/${selected.id}`, { plan_x: null, plan_y: null }),
        () => { planSelection = null; render(); },
      ),
    }, T("„{0}“ vom Plan nehmen", [selected.name])) : null,
    stage,
  ];
}

// Ansicht: Platz

function viewPlace(code) {
  const place = data.places.find((candidate) => candidate.code === code);
  if (!place) return viewMissing(T("Den Platz {0} gibt es nicht.", [code]));
  const map = mapOf(place);
  const items = itemsOf(place);

  if (!place.surveyed) ensureRound();
  const auto = automaticRecognition();
  // Kommt das Foto vom Kamera-Button im Schrank, geht es hier gleich mit dem Erkennen weiter.
  if (recognizeOnArrival && place.photos.includes(recognizeOnArrival)) {
    const photoId = recognizeOnArrival;
    recognizeOnArrival = null;
    autoOpened.add(place.id);
    if (auto && data.recognized_photos[photoId] === undefined) {
      recognizingPhoto = photoId;
      setTimeout(() => recognize(photoId, place, false), 0);
    } else if (!auto) {
      chatPhoto = photoId;
    }
  }
  // Nach einer Fotoserie geht es von selbst weiter: Ein gespeichertes Ergebnis kostet nichts mehr.
  if (!place.surveyed && !items.length && !autoOpened.has(place.id) && offlineSince === null && !suggestions) {
    const known = place.photos.find((id) => data.recognized_photos[id] !== undefined && data.recognized_photos[id] === hintOf(id));
    if (known) {
      autoOpened.add(place.id);
      setTimeout(() => recognize(known, place, false), 0);
    } else if (!auto && place.photos.length && !chatPhoto) {
      autoOpened.add(place.id);
      chatPhoto = place.photos[0];
    }
  }
  // Ein Tipp, zwei Schritte: Das Foto kommt hoch und wird erkannt, weil der Knopf genau das sagt.
  const addPhoto = async (file, recognizeNow) => {
    toast(T("Foto wird geladen ..."));
    let created;
    try {
      created = await uploadPhoto(file, place.id);
      const hint = (pendingHints[place.id] || "").trim();
      if (hint) photoHints[created.id] = hint;
      delete pendingHints[place.id];
      if (!auto) chatPhoto = created.id;
      if (recognizeNow && auto) recognizingPhoto = created.id;
      await reload();
    } catch (error) {
      if (error.message !== "PIN erforderlich") toast(error.message);
      return;
    }
    document.getElementById("toast").hidden = true;
    render();
    revealPanel();
    if (recognizeNow && auto) await recognize(created.id, place, false);
  };
  pageCamera = offlineSince === null ? {
    text: auto ? T("Foto + erkennen") : T("Inhalt fotografieren"),
    onFile: (file) => addPhoto(file, true),
  } : null;
  const nameInput = h("input", { type: "text", class: "item-name-input", placeholder: T("Fehlt etwas? Hier ergänzen"), "aria-label": T("Name des Eintrags") });
  const addItem = (event) => {
    event.preventDefault();
    if (!nameInput.value.trim()) return;
    act(() => api("POST", "api/items", { place_id: place.id, name: nameInput.value }), () => {
      render();
      document.querySelector(".item-name-input")?.focus();
    });
  };
  const bulk = h("textarea", { placeholder: T("Ein Eintrag je Zeile"), "aria-label": T("Mehrere Einträge") });
  const addBulk = () => {
    const names = bulk.value.split("\n").map((line) => line.trim()).filter(Boolean);
    if (!names.length) return;
    act(async () => {
      for (const name of names) await api("POST", "api/items", { place_id: place.id, name });
    });
  };
  const titleInput = h("input", {
    type: "text",
    class: "title-input",
    value: place.label,
    placeholder: placeName(place),
    "aria-label": T("Name des Platzes"),
    onchange: (event) => act(() => api("PATCH", `api/places/${place.id}`, { label: event.target.value })),
  });

  app.replaceChildren(...shell(
    backLink(`#/karte/${map.id}`, map.name),
    roundBar(place),
    placeSteps(place, items),
    h("div", { class: "place-head" },
      h("div", { class: "grow" }, titleInput, h("p", { class: "muted small" }, place.code)),
      h("a", { href: `#/karte/${map.id}`, "aria-label": T("Lage in {0}", [map.name]) }, thumb(place))),
    h("section", { class: "card stack" },
      h("div", { class: "section-head" },
        h("h2", {}, T("Inhalt per Foto erfassen")),
        place.photos.length ? photoButton(T("Weiteres Foto"), "", (file) => addPhoto(file, false)) : null),
      place.photos.length ? h("div", { class: "photos" }, place.photos.map((photoId) =>
        h("div", { class: "photo" },
          h("a", { href: `fotos/${photoId}`, target: "_blank", rel: "noopener" },
            h("img", { src: `fotos/${photoId}`, alt: T("Inhalt des Platzes") })),
          recognizeButton(photoId, place),
          h("button", {
            type: "button",
            class: "linklike small",
            onclick: () => deleteWithUndo(`api/photos/${photoId}`, T("Foto gelöscht")),
          }, T("Foto löschen"))))) : firstPhoto(place, addPhoto),
      recognitionHint(place),
      place.photos.includes(chatPhoto) ? chatPanel(place) : null,
      suggestions && suggestions.placeId === place.id ? suggestionPanel(place, items) : null),
    suggestions && suggestions.placeId === place.id && !items.length ? null : h("section", { class: "card" },
      h("div", { class: "section-head" },
        h("h2", {}, T("Das liegt hier")),
        h("a", { class: "linklike small", href: `#/bearbeiten/${roomOf(map).id}` }, T("Schnellbearbeitung")),
        items.length > 1 ? h("button", {
          type: "button",
          class: "linklike small select-toggle",
          onclick: () => {
            selecting = selecting === place.id ? null : place.id;
            selectedItems.clear();
            render();
          },
        }, selecting === place.id ? T("Abbrechen") : T("Auswählen")) : null),
      selecting === place.id ? selectionList(place, items) : items.length ? h("div", { class: "items" }, items.map(itemRow)) :
        h("p", { class: "muted empty-note" }, T("Noch nichts eingetragen.")),
      suggestions && suggestions.placeId === place.id ? null : h("form", { class: "add-row item-add", onsubmit: addItem },
        nameInput,
        h("button", { class: "primary", type: "submit", "aria-label": T("Hinzufügen") }, icon("plus")))),
    suggestions && suggestions.placeId === place.id ? null : confirmCard(place, items),
    h("details", { class: "more" },
      h("summary", {}, T("Mehr")),
      h("div", { class: "stack" },
        h("label", { class: "field" }, T("Liste einfügen"), bulk),
        h("button", { type: "button", onclick: addBulk }, T("Alle hinzufügen")),
        h("button", {
          type: "button",
          class: "danger",
          onclick: () => {
            if (confirm(T("{0} mit allen Einträgen löschen? Es bleibt 30 Tage im Papierkorb, die Nummer wird wieder frei.", [placeName(place)]))) {
              deleteWithUndo(`api/places/${place.id}`, T("{0} gelöscht", [placeName(place)]), () => { location.hash = `#/karte/${map.id}`; });
            }
          },
        }, T("Platz löschen"))))));
}

function selectionList(place, items) {
  const others = data.places.filter((candidate) => candidate.id !== place.id);
  const status = h("span", { class: "small muted" });
  const target = others.length ? h("select", { "aria-label": T("Neuer Platz") }, others.map((candidate) =>
    h("option", { value: candidate.id }, `${placePath(candidate)} (${candidate.code})`))) : null;
  const fill = h("select", { "aria-label": T("Füllstand oder Zustand") }, FILL_LEVELS.map((level) => h("option", { value: level }, bothLabels(level))));
  const update = () => { status.textContent = T("{0} ausgewählt", [selectedItems.size]); };
  const ids = () => [...selectedItems];
  const done = (message) => {
    selecting = null;
    selectedItems.clear();
    toast(message);
    render();
  };
  update();
  const need = () => {
    if (!selectedItems.size) toast(T("Wähle zuerst Einträge aus"));
    return selectedItems.size > 0;
  };
  return h("div", { class: "stack" },
    h("div", { class: "selection" }, items.map((item) => h("label", { class: "item-select" },
      h("input", {
        type: "checkbox",
        checked: selectedItems.has(item.id),
        onchange: (event) => {
          if (event.target.checked) selectedItems.add(item.id);
          else selectedItems.delete(item.id);
          update();
        },
      }),
      h("span", {}, item.name)))),
    status,
    target ? h("div", { class: "add-row" }, target, h("button", {
      type: "button",
      onclick: () => {
        if (need()) act(() => api("POST", "api/items/move", { item_ids: ids(), place_id: target.value }), () => done(T("Verlegt")));
      },
    }, T("Verlegen"))) : null,
    h("div", { class: "add-row" }, fill, h("button", {
      type: "button",
      onclick: () => {
        if (need()) {
          act(async () => {
            for (const id of ids()) await api("PATCH", `api/items/${id}`, { fill: fill.value });
          }, () => done(T("Füllstand gesetzt")));
        }
      },
    }, T("Setzen"))),
    h("button", {
      type: "button",
      class: "danger",
      onclick: () => {
        if (!need()) return;
        const trash = [];
        act(async () => {
          for (const id of ids()) trash.push((await api("DELETE", `api/items/${id}`)).trash_id);
        }, () => {
          selecting = null;
          selectedItems.clear();
          render();
          toast(T("{0} gelöscht", [plural(trash.length, T("Eintrag"), T("Einträge"))]), {
            text: T("Rückgängig"),
            run: () => act(async () => {
              for (const id of trash) await api("POST", `api/trash/${id}/restore`, {});
            }),
          });
        });
      },
    }, T("Löschen")));
}

// Ansicht: Fotoserie. Erst alle Plätze fotografieren, später in Ruhe prüfen.

function viewSeries(mapId) {
  const map = data.maps.find((candidate) => candidate.id === mapId);
  if (!map) return viewMissing(T("Diesen Schrank gibt es nicht."));
  ensureRound();
  const places = placesOf(map);
  const open = places.filter((place) => !place.surveyed && !place.photos.length && !skippedInSeries.has(place.id));
  if (!open.length) return seriesEnd(map, places);
  const place = open[0];
  const number = places.filter((candidate) => candidate.surveyed || candidate.photos.length || skippedInSeries.has(candidate.id)).length + 1;
  const take = async (files) => {
    const targets = [...open];
    const count = Math.min(files.length, targets.length);
    try {
      for (let index = 0; index < count; index += 1) {
        toast(T("Foto {0} von {1} wird geladen ...", [index + 1, count]));
        await uploadPhoto(files[index], targets[index].id);
      }
      await reload();
    } catch (error) {
      if (error.message !== "PIN erforderlich") toast(error.message);
      return;
    }
    if (files.length > targets.length) toast(T("{0} Fotos waren zu viel und wurden nicht verwendet", [files.length - targets.length]));
    else document.getElementById("toast").hidden = true;
    render();
  };
  pageCamera = { text: `${placeName(place)} fotografieren`, onFile: (file) => take([file]) };
  const body = h("div", { class: "stack" },
    h("div", { class: "series-place" }, thumb(place), h("div", {},
      h("strong", {}, placeName(place)),
      h("div", { class: "muted small" }, place.code))),
    h("label", { class: "dropzone" }, icon("camera"),
      h("strong", {}, T("Foto von diesem Platz")),
      h("span", { class: "muted" }, T("Mehrere gewählte Fotos gehen der Reihe nach an die nächsten Plätze")),
      photoInput(take, true)),
    h("button", {
      type: "button",
      class: "quiet",
      onclick: () => { skippedInSeries.add(place.id); render(); },
    }, T("Diesen Platz überspringen")));
  app.replaceChildren(...shell(
    backLink(`#/karte/${map.id}`, map.name),
    h("h1", {}, T("Platz {0} von {1}", [number, places.length])),
    h("div", { class: "meter" }, h("div", { style: { width: `${((number - 1) / places.length) * 100}%` } })),
    body));
}

function seriesEnd(map, places) {
  skippedInSeries.clear();
  const auto = automaticRecognition();
  const pending = places.filter((place) => !place.surveyed && place.photos.length && !itemsOf(place).length);
  const unknown = pending.filter((place) => !place.photos.some((id) => data.recognized_photos[id] !== undefined));
  const start = pending[0] || places.find((place) => !place.surveyed);
  const status = h("p", { class: "muted small" }, auto && unknown.length ? T("Jedes Foto kostet ungefähr ein paar Cent. Es läuft erst nach deinem Tipp.") : "");
  app.replaceChildren(...shell(
    backLink(`#/karte/${map.id}`, map.name),
    h("section", { class: "round-end" },
      icon("check"),
      h("h1", {}, start ? T("Fotos sind drin") : T("Hier ist alles erfasst")),
      pending.length ? h("p", { class: "lead" }, T("{0} aufs Prüfen. Das geht auch später.", [plural(pending.length, T("Platz wartet"), T("Plätze warten"))])) : null,
      auto && unknown.length ? h("button", {
        type: "button",
        class: "primary large",
        onclick: async (event) => {
          event.target.disabled = true;
          try {
            for (let index = 0; index < unknown.length; index += 1) {
              status.textContent = T("Foto {0} von {1} wird erkannt ...", [index + 1, unknown.length]);
              const photoId = unknown[index].photos[0];
              await api("POST", `api/photos/${photoId}/recognize`, { instruction: hintOf(photoId) });
            }
            await reload();
            location.hash = `#/p/${pending[0].code}`;
          } catch (error) {
            if (error.message !== "PIN erforderlich") toast(error.message);
            await reload().catch(() => {});
            render();
          }
        },
      }, icon("spark"), T("{0} jetzt erkennen", [plural(unknown.length, T("Foto"), T("Fotos"))])) : null,
      status,
      start ? h("a", { class: `button${auto && unknown.length ? "" : " primary"}`, href: `#/p/${start.code}` }, T("Jetzt prüfen")) : null,
      h("a", { class: "button", href: "#/" }, T("Später")))));
}

const PLACE_STEPS = [T("Foto"), T("Erkennen"), T("Prüfen"), T("Ergänzen"), T("Bestätigen")];

function placeSteps(place, items) {
  let current = 3;
  if (place.surveyed) current = PLACE_STEPS.length;
  else if (suggestions && suggestions.placeId === place.id) current = 2;
  else if (!items.length && !place.photos.length) current = 0;
  else if (!items.length && !place.photos.some((id) => data.recognized_photos[id] !== undefined)) current = 1;
  return h("ol", { class: "flow", "aria-label": T("Fortschritt") }, PLACE_STEPS.map((step, index) => h("li", {
    class: index < current ? "done" : index === current ? "current" : undefined,
    "aria-current": index === current ? "step" : undefined,
  }, step)));
}

// Bestätigen ist der letzte Schritt und führt gleich zum nächsten offenen Platz.
function confirmPlace(place) {
  act(() => api("PATCH", `api/places/${place.id}`, { surveyed: true }), () => {
    notePace();
    const next = nextOpenPlace(place);
    const map = mapOf(place);
    const room = roomOf(map);
    const roomPlaces = data.places.filter((candidate) => mapOf(candidate).room_id === room.id);
    const cover = coverage();
    const left = cover.total - cover.done;
    const status = T("Überblick {0} %{1}", [cover.percent, left ? T(", noch {0}", [plural(left, T("Platz"), T("Plätze"))]) : ""]);
    if (roomPlaces.length > 1 && roomPlaces.every((candidate) => candidate.surveyed)) cheer(`${room.name} komplett`, status, true);
    else cheer(`${placeName(place)} erledigt`, status);
    let target = `#/karte/${place.map_id}`;
    if (next) target = `#/p/${next.code}`;
    else if (round) target = "#/runde";
    if (location.hash === target) render();
    else location.hash = target;
  });
}

function confirmCard(place, items) {
  if (place.surveyed) {
    const next = nextOpenPlace(place);
    return h("section", { class: "card stack confirm done" },
      h("div", { class: "row tight" }, icon("check"),
        h("strong", {}, place.surveyed_at ? T("Bestätigt am {0}", [formatDate(place.surveyed_at)]) : T("Bestätigt"))),
      h("div", { class: "row" },
        next ? h("a", { class: "button primary", href: `#/p/${next.code}` }, T("Nächster offener Platz")) : null,
        h("button", { type: "button", onclick: () => act(() => api("PATCH", `api/places/${place.id}`, { surveyed: true }), () => { toast(T("Neu bestätigt")); render(); }) }, T("Erneut bestätigen")),
        h("button", { type: "button", class: "linklike small", onclick: () => act(() => api("PATCH", `api/places/${place.id}`, { surveyed: false })) }, T("Zurücknehmen"))));
  }
  return h("section", { class: "card stack confirm" },
    h("strong", {}, items.length ? T("Ist hier alles erfasst?") : T("Liegt hier nichts?")),
    h("p", { class: "muted small" }, T("Erst nach der Bestätigung kann die App sicher sagen, wenn etwas nicht vorhanden ist.")),
    h("button", { type: "button", class: "primary", onclick: () => confirmPlace(place) }, nextOpenPlace(place) ? T("Bestätigen und weiter") : T("Bestätigen")));
}

function firstPhoto(place, addPhoto) {
  const auto = automaticRecognition();
  return h("div", { class: "stack tight-stack" },
    hintField(T("Nur bestimmte Dinge erfassen?"), pendingHints[place.id] || "", (value) => { pendingHints[place.id] = value; }),
    photoDropzone(auto ? T("Foto machen und erkennen") : T("Foto vom Inhalt"), (file) => addPhoto(file, true), true),
    auto ? h("label", { class: "button compact file-button" }, T("Nur Foto speichern"), photoInput((file) => addPhoto(file, false))) : null);
}

function hintField(title, value, onInput) {
  return h("details", { class: "hint-field", open: Boolean(value) },
    h("summary", { class: "small" }, title),
    h("input", {
      type: "text",
      maxlength: 300,
      value,
      "aria-label": T("Hinweis zum Foto"),
      placeholder: T("z. B. nur M8-Muttern zählen"),
      oninput: (event) => onInput(event.target.value),
    }));
}

function revealPanel() {
  requestAnimationFrame(() => {
    document.querySelector(".suggestions, .chat-panel")?.scrollIntoView({ block: "start", behavior: "smooth" });
  });
}

function roundBar(place) {
  if (!round || place.surveyed) return null;
  const { places, items } = roundFigures();
  return h("div", { class: "round-bar small" },
    h("span", { class: "grow" }, places ? T("Diese Runde: {0}, {1}", [plural(places, T("Platz"), T("Plätze")), plural(items, T("Eintrag"), T("Einträge"))]) : T("Los geht's")),
    h("button", {
      type: "button",
      class: "linklike small",
      onclick: () => {
        round.skipped.push(place.id);
        saveRound();
        const next = nextOpenPlace(place);
        if (next) location.hash = `#/p/${next.code}`;
        else toast(T("Das ist der letzte offene Platz"));
      },
    }, T("Später")),
    places ? h("a", { class: "small", href: "#/runde" }, T("Fertig für heute")) : null);
}

// Ansicht: Ende einer Runde

function viewRound() {
  if (!round) {
    location.hash = "#/";
    return;
  }
  const figures = roundFigures();
  const cover = coverage();
  const next = nextOpenPlace();
  const close = () => {
    round = null;
    saveRound();
  };
  app.replaceChildren(...shell(
    h("section", { class: "round-end" },
      h("div", { class: "round-pixels" }, logoPixels(cover.percent, true)),
      h("h1", {}, figures.places ? T("Gut gemacht") : T("Bis zum nächsten Mal")),
      h("p", { class: "lead" }, cover.percent > round.percent
        ? T("Dein Überblick ist von {0} auf {1} % gewachsen.", [round.percent, cover.percent])
        : T("Dein Überblick liegt bei {0} %.", [cover.percent])),
      h("div", { class: "stats" },
        statTile(figures.places, figures.places === 1 ? T("Platz erledigt") : T("Plätze erledigt")),
        statTile(figures.items, figures.items === 1 ? T("Eintrag neu") : T("Einträge neu")),
        statTile(figures.minutes, figures.minutes === 1 ? T("Minute") : T("Minuten"))),
      round.earned.length ? h("ul", { class: "milestones" }, round.earned.map((title) =>
        h("li", {}, icon("check"), title))) : null,
      h("div", { class: "row" },
        next ? h("a", { class: "button primary", href: `#/p/${next.code}` }, T("Noch ein Platz")) : null,
        h("a", { class: next ? "button" : "button primary", href: "#/", onclick: close }, T("Zur Startseite"))))));
}

function hintOf(photoId) {
  return (photoHints[photoId] ?? data.recognized_photos[photoId] ?? "").trim();
}

function automaticRecognition() {
  return data.recognition.installed && data.recognition.configured;
}

// Jede automatische Erkennung kostet Geld. Sie startet deshalb nur hier, durch einen Tipp auf diesen Knopf.
async function recognize(photoId, place, force) {
  recognizingPhoto = photoId;
  render();
  try {
    const result = await api("POST", `api/photos/${photoId}/recognize`, { instruction: hintOf(photoId), ...(force ? { force: true } : {}) });
    suggestions = {
      placeId: place.id,
      items: result.items,
      notRecognized: result.not_recognized,
      fromCache: result.from_cache,
    };
    await reload();
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
  }
  recognizingPhoto = null;
  render();
  revealPanel();
}

function recognizeButton(photoId, place) {
  const auto = automaticRecognition();
  const saved = data.recognized_photos[photoId]; // Der Hinweis der letzten Erkennung, falls es eine gab.
  const busy = recognizingPhoto === photoId;
  const main = h("button", { type: "button", disabled: Boolean(recognizingPhoto), onclick: () => recognize(photoId, place, false) });
  const again = h("button", {
    type: "button",
    class: "linklike small",
    disabled: Boolean(recognizingPhoto),
    onclick: () => {
      if (confirm(T("Dieses Foto noch einmal an Claude schicken? Das kostet erneut Guthaben."))) recognize(photoId, place, true);
    },
  }, T("Noch einmal erkennen"));
  const chat = h("button", {
    type: "button",
    disabled: Boolean(recognizingPhoto),
    "aria-expanded": String(chatPhoto === photoId),
    onclick: () => {
      chatPhoto = chatPhoto === photoId ? null : photoId;
      render();
      revealPanel();
    },
  }, T("Kostenlos per Chat"));
  // Der Knopf sagt immer, ob ein Tipp Geld kostet: Ein geänderter Hinweis braucht einen neuen Abruf.
  const refresh = () => {
    const same = saved !== undefined && hintOf(photoId) === saved;
    main.className = `compact${same ? "" : " primary"}`;
    let text = T("Inhalt erkennen");
    if (busy) text = T("Einen Moment ...");
    else if (same) text = T("Ergebnis ansehen");
    else if (saved !== undefined) text = T("Neu erkennen");
    main.replaceChildren(icon("spark"), text);
    main.hidden = !auto && !same;
    again.hidden = !auto || !same;
    chat.className = `compact${main.hidden ? " primary" : ""}`;
    if (chatPhoto === photoId && chatPromptBox) chatPromptBox.value = chatPrompt(hintOf(photoId));
  };
  refresh();
  return h("div", { class: "stack tight-stack" },
    hintField(T("Nur bestimmte Dinge erfassen?"), hintOf(photoId), (value) => { photoHints[photoId] = value; refresh(); }),
    main,
    chat,
    again);
}

function recognitionHint(place) {
  if (offlineSince !== null) return null;
  const auto = automaticRecognition();
  if (!place.photos.length) {
    return h("p", { class: "muted small" }, auto
      ? T("Der Knopf schickt das Foto an Claude und kostet ungefähr ein paar Cent. Sonst verlässt nichts {0}.", [hostWord()])
      : T("Danach hilft dir dein eigener Claude- oder ChatGPT-Chat beim Erkennen. Vor deinem Tipp verlässt das Foto {0} nicht.", [hostWord()]));
  }
  if (!auto) {
    return h("p", { class: "muted small" }, T("Automatisch geht es mit einem API-Schlüssel: "), h("a", { href: "#/daten" }, T("Hier einrichten")), ".");
  }
  return h("p", { class: "muted small" }, T("„Inhalt erkennen“ kostet ungefähr ein paar Cent und läuft nur auf deinen Tipp. Mengen sind Schätzungen."));
}

function chatPrompt(hint) {
  return data.recognition.chat_prompt.replace("{{HINWEIS}}", () => (hint ? T("\n\nHinweis: {0}", [hint]) : ""));
}

// Kopiert in die Zwischenablage des Geräts. Zuerst der klassische Weg, solange der Tipp noch „frisch“ ist:
// Er klappt auch über HTTP im Heimnetz, im Rahmen von Home Assistant und auf dem iPhone.
// Danach die moderne Zwischenablage, die nur mit HTTPS und Freigabe zur Verfügung steht.
function copyLegacy(text) {
  const box = document.createElement("textarea");
  box.value = text;
  box.setAttribute("readonly", "");
  // 16 px, damit das iPhone nicht hineinzoomt. Sichtbar genug für die Auswahl, aber außerhalb des Bildes.
  Object.assign(box.style, { position: "absolute", left: "-9999px", top: `${window.scrollY}px`, fontSize: "16px", border: "0", padding: "0", margin: "0" });
  document.body.append(box);
  const active = document.activeElement;
  box.select();
  box.setSelectionRange(0, text.length);
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    copied = false;
  }
  box.remove();
  window.getSelection()?.removeAllRanges();
  if (active && active.focus) active.focus({ preventScroll: true });
  return copied;
}

async function copyText(text) {
  if (copyLegacy(text)) return true;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Dann bleibt nur das Kopieren von Hand.
  }
  return false;
}

// Ein Knopf, der Text kopiert und kurz „Kopiert“ zeigt. Klappt es nicht, öffnet onFail den Text zum Markieren.
function copyButton(label, getText, { className = "", onFail } = {}) {
  const button = h("button", { type: "button", class: `copy-button ${className}`.trim() }, icon("copy"), h("span", {}, label));
  button.addEventListener("click", async () => {
    const copied = await copyText(getText());
    const caption = button.querySelector("span");
    if (copied) {
      button.classList.add("copied");
      caption.textContent = T("Kopiert");
      toast(T("In der Zwischenablage. Im Chat einfach einfügen."));
      setTimeout(() => {
        button.classList.remove("copied");
        caption.textContent = label;
      }, 2500);
    } else {
      toast(T("Kopieren hat hier nicht geklappt. Bitte den markierten Text selbst kopieren."));
      if (onFail) onFail();
    }
  });
  return button;
}

function chatPanel(place) {
  const photoId = chatPhoto;
  return h("div", { class: "chat-panel stack" },
    h("h2", {}, T("Kostenlos über deinen Chat")),
    handoverSteps({
      getPrompt: () => chatPrompt(hintOf(photoId)),
      keepBox: true,
      draftKey: photoId,
      retryPrompt: data.recognition.chat_retry,
      middleTitle: T("Im Chat Foto anhängen, Auftrag einfügen und senden"),
      extraLink: h("a", { class: "button compact", href: `fotos/${photoId}`, download: `foto-${place.code}.jpg` }, T("Foto speichern")),
      submit: async (answer) => {
        const result = await api("POST", `api/photos/${photoId}/chat-answer`, { instruction: hintOf(photoId), answer });
        suggestions = { placeId: place.id, items: result.items, notRecognized: result.not_recognized, fromCache: false };
        delete chatAnswers[photoId];
        chatPhoto = null;
      },
    }),
    h("p", { class: "muted small" },
      T("Das Foto bringst du selbst in den Chat, die App sendet nichts. Es gelten die Regeln und Limits deines Kontos.")));
}

const CHAT_KEY = "werkstatt-chat";
const CHATS = [
  { key: "chatgpt", name: "ChatGPT", href: "https://chatgpt.com/" },
  { key: "claude", name: "Claude", href: "https://claude.ai/new" },
];

function favoriteChat() {
  return prefs().chat || CHATS[0].key;
}

function handoverSteps({ getPrompt, keepBox, draftKey, retryPrompt, middleTitle, extraLink, submit }) {
  const problem = h("div", { class: "notice stack tight-stack", role: "alert", hidden: true });
  const details = h("details", {}, h("summary", { class: "small" }, T("Auftrag ansehen")));
  const box = h("textarea", { readonly: true, "aria-label": T("Auftrag für den Chat") });
  box.value = getPrompt();
  details.append(box);
  if (keepBox) chatPromptBox = box;
  const evaluate = async () => {
    if (!answer.value.trim()) {
      toast(T("Füge zuerst die Antwort aus dem Chat ein"));
      return;
    }
    problem.hidden = true;
    try {
      await submit(answer.value);
      await reload();
      render();
      revealPanel();
    } catch (error) {
      if (error.message === "PIN erforderlich") return;
      problem.hidden = false;
      problem.replaceChildren(
        h("div", {}, T(error.message)),
        h("div", { class: "small" }, T("Deine Antwort bleibt hier stehen. Bitte den Chat, sie noch einmal im richtigen Format zu schreiben, und füge die neue Antwort ein.")),
        copyButton(T("Bitte an den Chat kopieren"), () => retryPrompt, { className: "compact" }),
      );
    }
  };
  const answer = h("textarea", {
    placeholder: T("Antwort aus dem Chat hier einfügen. Die App wertet sie gleich aus."),
    "aria-label": T("Antwort aus dem Chat"),
    value: chatAnswers[draftKey] || "",
    oninput: (event) => { chatAnswers[draftKey] = event.target.value; },
    onpaste: () => {
      setTimeout(() => {
        chatAnswers[draftKey] = answer.value;
        evaluate();
      }, 0);
    },
  });
  const favorite = favoriteChat();
  const openChat = (chat) => h("a", {
    class: "button compact",
    href: chat.href,
    target: "_blank",
    rel: "noopener noreferrer",
    onclick: async () => {
      // Zur Sicherheit noch einmal kopieren, falls der Knopf davor übersprungen wurde.
      const copied = copyText(getPrompt());
      if (chat.key !== prefs().chat) savePreferences({ chat: chat.key }, true);
      await copied;
    },
  }, T("{0} öffnen", [chat.name]));
  const showBox = () => {
    details.open = true;
    box.focus();
    box.select();
    box.setSelectionRange(0, box.value.length);
  };
  return h("ol", { class: "steps" },
    h("li", {},
      h("strong", {}, T("Auftrag kopieren und Chat öffnen")),
      copyButton(T("Auftrag kopieren"), getPrompt, { className: "primary", onFail: showBox }),
      h("div", { class: "row tight" },
        [...CHATS].sort((a, b) => Number(b.key === favorite) - Number(a.key === favorite)).map(openChat),
        extraLink),
      details),
    h("li", {}, h("strong", {}, middleTitle)),
    h("li", {},
      h("strong", {}, T("Antwort kopieren und hier einfügen")),
      answer,
      problem,
      h("div", { class: "row tight" },
        h("button", { type: "button", class: "compact", onclick: evaluate }, T("Auswerten")))));
}

function suggestionPanel(place, items) {
  const existing = new Set(items.map((item) => normalize(item.name)));
  const rows = [];
  const list = h("div", { class: "suggestion-list" });
  const acceptButton = h("button", { type: "button", class: "primary large", onclick: () => accept(true) });
  const countChecked = () => {
    const count = rows.filter((row) => row.use.checked && row.name.value.trim()).length;
    acceptButton.textContent = count ? T("{0} übernehmen und weiter", [plural(count, T("Eintrag"), T("Einträge"))]) : T("Ohne Einträge weiter");
  };
  const addRow = (suggestion, fromHand) => {
    const key = normalize(suggestion.name);
    const duplicate = existing.has(key);
    const elsewhere = [...new Set(data.items
      .filter((item) => item.place_id !== place.id && normalize(item.name) === key)
      .map((item) => placeOf(item).code))];
    const fill = h("select", { "aria-label": T("Füllstand von {0}", [suggestion.name]) },
      FILL_LEVELS.map((level) => h("option", { value: level }, fillLabel(level))));
    fill.value = FILL_LEVELS.includes(suggestion.fill) ? suggestion.fill : "ok";
    // Eine reine Stückzahl wie „3“ oder „3 Stück“ wird zur Anzahl, Schätzungen wie „ca. 40 Stück“ bleiben Notiz.
    const counted = /^\s*(\d{1,4})\s*(stück|stk\.?|x|×|pieces?|pcs\.?)?\s*$/i.exec(suggestion.amount || "");
    const quantity = counted && Number(counted[1]) >= 1 ? Number(counted[1]) : 1;
    const noteText = [counted ? "" : suggestion.amount, suggestion.details].filter(Boolean).join(" · ").slice(0, 200);
    const row = {
      suggestion,
      quantity,
      use: h("input", {
        type: "checkbox",
        "aria-label": T("{0} übernehmen", [suggestion.name]),
        checked: !duplicate && suggestion.certainty !== "unsicher",
        onchange: countChecked,
      }),
      name: h("input", { type: "text", value: suggestion.name, "aria-label": T("Name"), oninput: countChecked }),
      note: h("input", {
        type: "text",
        value: noteText,
        placeholder: T("Menge, Farbton, Maß, Norm"),
        "aria-label": T("Notiz"),
      }),
      fill,
    };
    rows.push(row);
    const flags = [
      fromHand ? null : (suggestion.certainty === "sicher" ? null : T(suggestion.certainty)),
      duplicate ? T("hier schon eingetragen") : null,
      elsewhere.length ? T("auch an {0}", [elsewhere.join(", ")]) : null,
    ].filter(Boolean);
    list.append(h("div", { class: "suggestion" },
      row.use,
      h("div", { class: "suggestion-main" },
        quantity > 1 ? h("div", { class: "row tight" }, h("span", { class: "qty" }, `${quantity}×`), row.name) : row.name,
        flags.length ? h("div", { class: "muted small" }, flags.join(" · ")) : null,
        h("details", { class: "suggestion-more" },
          h("summary", { class: "small muted" }, noteText || T("Notiz und Füllstand")),
          h("div", { class: "stack tight-stack" }, row.note, fill)))));
  };
  suggestions.items.forEach((suggestion) => addRow(suggestion, false));
  countChecked();
  const extra = h("input", { type: "text", placeholder: T("Fehlt etwas? Hier ergänzen"), "aria-label": T("Weiteren Eintrag ergänzen") });
  function accept(thenConfirm) {
    act(async () => {
      for (const row of rows.filter((candidate) => candidate.use.checked && candidate.name.value.trim())) {
        await api("POST", "api/items", {
          place_id: place.id,
          name: row.name.value,
          note: row.note.value,
          synonyms: (row.suggestion.also_known_as || []).join(", ").slice(0, 200),
          fill: row.fill.value,
          quantity: row.quantity,
        });
      }
      suggestions = null;
    }, () => {
      if (thenConfirm) confirmPlace(place);
      else render();
    });
  }
  return h("div", { class: "suggestions stack" },
    h("h2", {}, suggestions.items.length ? T("Stimmt das?") : T("Nichts erkannt")),
    list,
    h("form", {
      class: "add-row",
      onsubmit: (event) => {
        event.preventDefault();
        if (!extra.value.trim()) return;
        addRow({ name: extra.value.trim(), details: "", amount: "", fill: "ok", certainty: "sicher" }, true);
        countChecked();
        extra.value = "";
        extra.focus();
      },
    }, extra, h("button", { class: "primary", type: "submit", "aria-label": T("Ergänzen") }, icon("plus"))),
    suggestions.notRecognized ? h("p", { class: "small" }, T("Nicht erkannt: {0}", [suggestions.notRecognized])) : null,
    suggestions.fromCache ? h("p", { class: "muted small" }, T("Gespeichertes Ergebnis, ohne neue Kosten.")) : null,
    acceptButton,
    h("div", { class: "row tight" },
      h("button", { type: "button", class: "compact", onclick: () => accept(false) }, T("Nur übernehmen, noch nicht bestätigen")),
      h("button", { type: "button", class: "compact quiet", onclick: () => { suggestions = null; render(); } }, T("Verwerfen"))));
}

// Anzahl: Manches hat man doppelt oder mehrfach. Ein Eintrag steht dann für mehrere gleiche Stücke.
const QUANTITY_MAX = 9999;

function quantityOf(item) {
  return item?.quantity > 1 ? item.quantity : 1;
}

function quantityBadge(item) {
  return quantityOf(item) > 1 ? h("span", { class: "qty" }, `${quantityOf(item)}×`) : null;
}

function quantityField(item) {
  const count = quantityOf(item);
  const save = (value) => act(() => api("PATCH", `api/items/${item.id}`, { quantity: Math.min(QUANTITY_MAX, Math.max(1, value)) }));
  const input = h("input", {
    type: "number",
    min: "1",
    max: String(QUANTITY_MAX),
    inputmode: "numeric",
    value: String(count),
    "aria-label": T("Anzahl von {0}", [item.name]),
    onchange: (event) => {
      const value = Number.parseInt(event.target.value, 10);
      if (Number.isInteger(value) && value >= 1 && value !== count) save(value);
      else event.target.value = String(count);
    },
  });
  return h("div", { class: "field quantity-field" }, T("Anzahl"),
    h("div", { class: "stepper" },
      h("button", { type: "button", "aria-label": T("Eins weniger"), disabled: count <= 1, onclick: () => save(count - 1) }, "−"),
      input,
      h("button", { type: "button", "aria-label": T("Eins mehr"), disabled: count >= QUANTITY_MAX, onclick: () => save(count + 1) }, "+")));
}

// Füllstand für Material, Zustand für Geräte. Dieselben vier Stufen, umschaltbar je Eintrag.
function levelField(item) {
  const device = isDevice(item);
  return h("div", { class: "field level-field" },
    h("div", { class: "row spread level-head" },
      h("span", {}, device ? T("Zustand") : T("Füllstand")),
      h("div", { class: "segments scale-switch", role: "group", "aria-label": T("Skala für {0}", [item.name]) },
        [["fill", T("Füllstand")], ["state", T("Gerätezustand")]].map(([scale, label]) => h("button", {
          type: "button",
          "aria-pressed": String((device ? "state" : "fill") === scale),
          onclick: () => act(() => api("PATCH", `api/items/${item.id}`, { scale })),
        }, label)))),
    h("div", { class: `segments${device ? " state-levels" : ""}`, role: "group", "aria-label": device ? T("Zustand von {0}", [item.name]) : T("Füllstand von {0}", [item.name]) },
      FILL_LEVELS.map((level) => h("button", {
        type: "button",
        "aria-pressed": String(item.fill === level),
        onclick: () => act(() => api("PATCH", `api/items/${item.id}`, { fill: level })),
      }, fillLabel(level, item)))));
}

function itemRow(item) {
  const name = h("input", { type: "text", value: item.name });
  const synonyms = h("input", { type: "text", value: item.synonyms, placeholder: T("Andere Wörter dafür") });
  const note = h("input", { type: "text", value: item.note, placeholder: T("Farbton, Maß, Norm") });
  const target = h("select", {}, data.places.map((place) => h("option", { value: place.id }, `${placePath(place)} (${place.code})`)));
  target.value = item.place_id;
  return h("details", {
    class: "item",
    open: openItem === item.id,
    ontoggle: (event) => {
      if (event.target.open) openItem = item.id;
      else if (openItem === item.id) openItem = null;
    },
  },
  h("summary", {},
    h("span", { class: "grow" },
      quantityBadge(item),
      h("span", { class: "item-title" }, item.name),
      item.note ? h("span", { class: "muted small block" }, item.note) : null,
      detailLines(item).length || (item.photos || []).length
        ? h("span", { class: "detail-badge small block" }, icon("lupe"), detailSummary(item)) : null,
      item.missing ? h("span", { class: "flag-missing small block" }, T("zuletzt nicht da")) : null,
      itemFlags(item)),
    fillChip(item.fill, item),
    icon("next")),
  h("div", { class: "item-body stack" },
    h("div", { class: "row tight item-links" },
      h("a", { class: "button compact passport-open", href: `#/steckbrief/${item.id}` }, icon("doc"),
        hasPassport(item) ? T("Steckbrief: {0}", [passportSummary(item)]) : T("Steckbrief")),
      h("a", { class: "button compact detail-open", href: `#/detail/${item.id}` }, icon("lupe"),
        detailLines(item).length || (item.photos || []).length ? T("Detailmodus: {0}", [detailSummary(item)]) : T("Detailmodus: Foto und Inhalt"))),
    awayEditor(item),
    h("div", { class: "row level-row" }, quantityField(item), levelField(item)),
    h("form", {
      class: "stack",
      onsubmit: (event) => {
        event.preventDefault();
        act(() => api("PATCH", `api/items/${item.id}`, {
          name: name.value, synonyms: synonyms.value, note: note.value, place_id: target.value,
        }));
      },
    },
    h("label", { class: "field" }, T("Name"), name),
    h("label", { class: "field" }, T("Notiz"), note),
    h("label", { class: "field" }, T("Auch genannt"), synonyms),
    h("label", { class: "field" }, T("Liegt an"), target),
    h("div", { class: "row spread" },
      h("button", { type: "submit", class: "primary compact" }, T("Speichern")),
      h("button", {
        type: "button",
        class: "compact danger",
        onclick: () => deleteWithUndo(`api/items/${item.id}`, T("„{0}“ gelöscht", [item.name])),
      }, T("Löschen")))),
    h("div", { class: "row spread" },
      foundButtons(item),
      h("span", { class: "muted small" }, T("Bestätigt: {0}", [formatDate(item.last_seen)])))));
}

function detailSummary(item) {
  const parts = [];
  if (detailLines(item).length) parts.push(plural(detailLines(item).length, T("Teil"), T("Teile")));
  const count = (item.photos || []).length;
  if (count) parts.push(count === 1 ? T("1 Detailfoto") : T("{0} Detailfotos", [count]));
  return parts.join(" · ");
}

// Ansicht: Detailmodus. Ein Eintrag wie eine Bitbox oder ein Satz Innensechskantschlüssel bekommt
// eigene Fotos und eine Liste seiner Teile. Die Liste ist durchsuchbar.

// Der Auftrag an die Erkennung: jedes Teil einzeln, mit Größe im Namen. Höchstens 300 Zeichen.
function detailInstruction(item, photoId) {
  const hint = (photoHints[photoId] ?? "").trim();
  const base = T("Detailfoto vom Inhalt von „{0}“. Jedes Teil einzeln mit Größe oder Typ im Namen, etwa „Bit T20“ oder „Innensechskant 4 mm“. Behälter und Halter weglassen.", [item.name.slice(0, 60)]);
  return (hint ? `${base} ${hint}` : base).slice(0, 300);
}

function detailLine(suggestion) {
  const name = (suggestion.name || "").trim();
  const extra = (suggestion.details || "").trim();
  const line = extra && !normalize(name).includes(normalize(extra)) ? `${name} (${extra})` : name;
  return line.slice(0, 80);
}

async function recognizeDetail(item, photoId, force) {
  recognizingPhoto = photoId;
  render();
  try {
    const result = await api("POST", `api/photos/${photoId}/recognize`, { instruction: detailInstruction(item, photoId), ...(force ? { force: true } : {}) });
    detailSuggestions = { itemId: item.id, lines: result.items.map(detailLine).filter(Boolean), notRecognized: result.not_recognized };
    await reload();
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
  }
  recognizingPhoto = null;
  render();
  revealPanel();
}

function detailRecognizeButtons(item, photoId) {
  const auto = automaticRecognition();
  const saved = data.recognized_photos[photoId];
  const main = h("button", { type: "button", disabled: Boolean(recognizingPhoto), onclick: () => recognizeDetail(item, photoId, false) });
  const again = h("button", {
    type: "button",
    class: "linklike small",
    disabled: Boolean(recognizingPhoto),
    onclick: () => {
      if (confirm(T("Dieses Foto noch einmal an Claude schicken? Das kostet erneut Guthaben."))) recognizeDetail(item, photoId, true);
    },
  }, T("Noch einmal erkennen"));
  const chat = h("button", {
    type: "button",
    disabled: Boolean(recognizingPhoto),
    "aria-expanded": String(chatPhoto === photoId),
    onclick: () => {
      chatPhoto = chatPhoto === photoId ? null : photoId;
      render();
      revealPanel();
    },
  }, T("Kostenlos per Chat"));
  // Wie bei den Platzfotos sagt der Knopf, ob ein Tipp Geld kostet.
  const refresh = () => {
    const same = saved !== undefined && detailInstruction(item, photoId) === saved;
    main.className = `compact${same ? "" : " primary"}`;
    let text = T("Teile erkennen");
    if (recognizingPhoto === photoId) text = T("Einen Moment ...");
    else if (same) text = T("Ergebnis ansehen");
    else if (saved !== undefined) text = T("Neu erkennen");
    main.replaceChildren(icon("spark"), text);
    main.hidden = !auto && !same;
    again.hidden = !auto || !same;
    chat.className = `compact${main.hidden ? " primary" : ""}`;
  };
  refresh();
  return h("div", { class: "stack tight-stack" },
    hintField(T("Nur bestimmte Teile erfassen?"), photoHints[photoId] || "", (value) => { photoHints[photoId] = value; refresh(); }),
    main,
    offlineSince === null ? chat : null,
    again);
}

function detailSuggestionPanel(item) {
  const present = new Set(detailLines(item).map(normalize));
  const rows = detailSuggestions.lines.map((line) => ({
    line,
    use: h("input", { type: "checkbox", checked: !present.has(normalize(line)), "aria-label": T("{0} übernehmen", [line]) }),
    text: h("input", { type: "text", value: line, maxlength: 80, "aria-label": T("Teil") }),
  }));
  const take = () => {
    const chosen = rows.filter((row) => row.use.checked && row.text.value.trim()).map((row) => row.text.value.trim());
    act(() => api("PATCH", `api/items/${item.id}`, { details: [...detailLines(item), ...chosen] }), () => {
      detailSuggestions = null;
      toast(T("{0} übernommen", [plural(chosen.length, T("Teil"), T("Teile"))]));
      render();
    });
  };
  return h("div", { class: "suggestions stack" },
    h("h2", {}, T("Erkannte Teile")),
    rows.length ? h("div", { class: "suggestion-list" }, rows.map((row) => h("div", { class: "suggestion" },
      row.use,
      h("div", { class: "suggestion-main" }, row.text,
        present.has(normalize(row.line)) ? h("div", { class: "muted small" }, T("schon in der Liste")) : null))))
      : h("p", { class: "muted" }, T("Auf dem Foto wurden keine einzelnen Teile erkannt.")),
    detailSuggestions.notRecognized ? h("p", { class: "muted small" }, detailSuggestions.notRecognized) : null,
    h("div", { class: "row" },
      rows.length ? h("button", { type: "button", class: "primary", onclick: take }, icon("check"), T("Übernehmen")) : null,
      h("button", { type: "button", onclick: () => { detailSuggestions = null; render(); } }, T("Verwerfen"))));
}

function detailChatPanel(item, photoId) {
  return h("div", { class: "chat-panel stack" },
    h("h2", {}, T("Kostenlos über deinen Chat")),
    handoverSteps({
      getPrompt: () => chatPrompt(detailInstruction(item, photoId)),
      keepBox: false,
      draftKey: photoId,
      retryPrompt: data.recognition.chat_retry,
      middleTitle: T("Im Chat Foto anhängen, Auftrag einfügen und senden"),
      extraLink: h("a", { class: "button compact", href: `fotos/${photoId}`, download: "detailfoto.jpg" }, T("Foto speichern")),
      submit: async (answer) => {
        const result = await api("POST", `api/photos/${photoId}/chat-answer`, { instruction: detailInstruction(item, photoId), answer });
        detailSuggestions = { itemId: item.id, lines: result.items.map(detailLine).filter(Boolean), notRecognized: result.not_recognized };
        delete chatAnswers[photoId];
        chatPhoto = null;
      },
    }),
    h("p", { class: "muted small" },
      T("Das Foto bringst du selbst in den Chat, die App sendet nichts. Es gelten die Regeln und Limits deines Kontos.")));
}

function viewDetail(itemId) {
  const item = data.items.find((candidate) => candidate.id === itemId);
  if (!item) return viewMissing(T("Diesen Eintrag gibt es nicht."));
  const place = placeOf(item);
  const lines = detailLines(item);
  const photos = item.photos || [];
  if (detailSuggestions && detailSuggestions.itemId !== item.id) detailSuggestions = null;
  const saveLines = (next, message) => act(() => api("PATCH", `api/items/${item.id}`, { details: next }), () => {
    if (message) toast(message);
    render();
  });
  const addPhoto = async (file) => {
    toast(T("Foto wird geladen ..."));
    try {
      const created = await uploadPhoto(file, null, item.id);
      if (!automaticRecognition()) chatPhoto = created.id;
      await reload();
    } catch (error) {
      if (error.message !== "PIN erforderlich") toast(error.message);
      return;
    }
    document.getElementById("toast").hidden = true;
    render();
    revealPanel();
  };
  pageCamera = offlineSince === null ? { text: T("Detailfoto"), onFile: addPhoto } : null;

  const newLine = h("input", { type: "text", maxlength: 80, placeholder: T("z. B. Bit T20 oder Innensechskant 4 mm"), "aria-label": T("Teil ergänzen") });
  const bulk = h("textarea", { placeholder: T("Ein Teil je Zeile"), "aria-label": T("Mehrere Teile") });
  const lineRow = (line, index) => h("div", { class: "detail-line" },
    h("input", {
      type: "text",
      value: line,
      maxlength: 80,
      "aria-label": T("Teil"),
      onchange: (event) => {
        const next = [...lines];
        next[index] = event.target.value;
        saveLines(next);
      },
    }),
    h("button", {
      type: "button",
      class: "compact quiet",
      "aria-label": T("{0} entfernen", [line]),
      onclick: () => saveLines(lines.filter((_, position) => position !== index), T("„{0}“ entfernt", [line])),
    }, icon("trash")));

  app.replaceChildren(...shell(
    backLink(`#/p/${place.code}`, placeName(place)),
    h("h1", {}, item.name),
    h("p", { class: "muted" }, `${placePath(place)} · ${place.code}`),
    h("p", { class: "muted small" }, T("Detailmodus: Fotografiere den Inhalt, etwa die Bits einer Bitbox oder die Größen eines Schlüsselsatzes, und halte die Teile als Liste fest. Die Suche findet jedes Teil.")),
    h("section", { class: "card stack" },
      h("div", { class: "section-head" },
        h("h2", {}, T("Detailfotos")),
        photos.length ? photoButton(T("Weiteres Detailfoto"), "", addPhoto) : null),
      photos.length ? h("div", { class: "photos" }, photos.map((photoId) => h("div", { class: "photo" },
        h("a", { href: `fotos/${photoId}`, target: "_blank", rel: "noopener" }, h("img", { src: `fotos/${photoId}`, alt: T("Detailfoto von {0}", [item.name]) })),
        offlineSince === null ? detailRecognizeButtons(item, photoId) : null,
        h("button", {
          type: "button",
          class: "linklike small",
          onclick: () => deleteWithUndo(`api/photos/${photoId}`, T("Foto gelöscht")),
        }, T("Foto löschen")))))
        : photoDropzone(T("Detailfoto aufnehmen"), addPhoto),
      offlineSince === null ? h("p", { class: "muted small" }, automaticRecognition()
        ? T("„Teile erkennen“ kostet ungefähr ein paar Cent und läuft nur auf deinen Tipp.")
        : T("Danach hilft dir dein eigener Claude- oder ChatGPT-Chat beim Erkennen. Vor deinem Tipp verlässt das Foto {0} nicht.", [hostWord()])) : null,
      photos.includes(chatPhoto) ? detailChatPanel(item, chatPhoto) : null,
      detailSuggestions ? detailSuggestionPanel(item) : null),
    h("section", { class: "card stack" },
      h("div", { class: "section-head" }, h("h2", {}, T("Inhalt")),
        lines.length ? h("span", { class: "muted small" }, plural(lines.length, T("Teil"), T("Teile"))) : null),
      lines.length ? h("div", { class: "detail-lines" }, lines.map(lineRow)) : h("p", { class: "muted empty-note" }, T("Noch keine Teile eingetragen.")),
      h("form", {
        class: "add-row",
        onsubmit: (event) => {
          event.preventDefault();
          if (newLine.value.trim()) saveLines([...lines, newLine.value]);
        },
      }, newLine, h("button", { class: "primary", type: "submit", "aria-label": T("Hinzufügen") }, icon("plus"))),
      h("details", { class: "more" },
        h("summary", {}, T("Liste einfügen")),
        h("div", { class: "stack" }, bulk,
          h("button", {
            type: "button",
            onclick: () => {
              const added = bulk.value.split("\n").map((line) => line.trim()).filter(Boolean);
              if (added.length) saveLines([...lines, ...added]);
            },
          }, T("Alle hinzufügen")))))));
}

// Steckbrief: alles, was man später zu einem Gerät, Werkzeug oder Material wissen möchte. Erfasst wird
// weiter nur mit Namen und Foto. Angaben, Dokumente, Verleih und Wartung kommen dazu, wann man mag.

const DOCUMENT_KINDS = [["anleitung", T("Anleitung")], ["rechnung", T("Rechnung")], ["garantie", T("Garantie")], ["wartung", T("Wartungsplan")], ["sonstiges", T("Sonstiges")]];
const SERVICE_CHOICES = [[1, T("jeden Monat")], [3, T("alle 3 Monate")], [6, T("alle 6 Monate")], [12, T("jedes Jahr")], [24, T("alle 2 Jahre")], [36, T("alle 3 Jahre")]];
const PASSPORT_FACTS = [
  ["maker", T("Hersteller"), "text", 60, T("z. B. Bosch")],
  ["model", T("Modell"), "text", 80, T("z. B. GSR 18V-55")],
  ["serial", T("Seriennummer"), "text", 60, ""],
  ["bought", T("Kaufdatum"), "date"],
  ["price", T("Kaufpreis"), "text", 30, T("z. B. 129 €")],
  ["shop", T("Gekauft bei"), "text", 60, ""],
  ["warranty", T("Garantie bis"), "date"],
  ["link", T("Webseite"), "url", 300, "https://"],
];
const MAX_DOCUMENT_BYTES = 30 * 1024 * 1024;
const MAX_DOCUMENT_EDGE = 3000;
const SERVICE_SOON_DAYS = 30;
const WARRANTY_SOON_DAYS = 60;
let passportEdit = null; // { itemId, section }: welcher Teil des Steckbriefs gerade offen ist.
let borrowerListId = 0;

// Überschriften aus Wörtern, die im Englischen sonst klein stehen, etwa „documents“.
function cap(text) {
  return text.charAt(0).toLocaleUpperCase(LOCALE) + text.slice(1);
}

function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function formatDay(iso) {
  return iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(LOCALE) : "";
}

function daysUntil(iso) {
  return Math.round((new Date(`${iso}T00:00:00`) - new Date(`${todayIso()}T00:00:00`)) / 86400000);
}

function passportOf(item) {
  return item.passport || {};
}

function deviceLine(item) {
  const passport = passportOf(item);
  return [passport.maker, passport.model].filter(Boolean).join(" ");
}

function hasPassport(item) {
  return Object.keys(passportOf(item)).length > 0 || (item.documents || []).length > 0;
}

function passportSummary(item) {
  const count = (item.documents || []).length;
  return [deviceLine(item), count ? plural(count, T("Dokument"), T("Dokumente")) : ""].filter(Boolean).join(" · ") || T("Angaben");
}

function passportLink(item) {
  if (data.server.label_url) return data.server.label_url.replace("/p/{code}", `/s/${item.id}`);
  return `${baseUrl()}/#/s/${item.id}`;
}

function isLent(text) {
  return text === T("Verliehen") || text === "Verliehen";
}

function awayText(item) {
  if (!item.away) return "";
  if (!item.away_to) return item.away;
  return isLent(item.away) ? T("Verliehen an {0}", [item.away_to]) : T("{0}, bei {1}", [item.away, item.away_to]);
}

function lendingLate(item) {
  return Boolean(item.away && item.away_due && daysUntil(item.away_due) < 0);
}

function lendDueText(item) {
  return lendingLate(item) ? T("Rückgabe überfällig seit {0}", [formatDay(item.away_due)]) : T("zurück bis {0}", [formatDay(item.away_due)]);
}

function serviceState(item) {
  if (!item.next_service) return null;
  const days = daysUntil(item.next_service);
  return days < 0 ? "overdue" : days <= SERVICE_SOON_DAYS ? "soon" : "ok";
}

function serviceText(item) {
  const state = serviceState(item);
  if (state === "overdue") return T("Wartung überfällig seit {0}", [formatDay(item.next_service)]);
  if (state === "soon") return T("Wartung fällig am {0}", [formatDay(item.next_service)]);
  return state ? T("Nächste Wartung am {0}", [formatDay(item.next_service)]) : "";
}

function warrantyState(item) {
  const end = passportOf(item).warranty;
  if (!end) return null;
  const days = daysUntil(end);
  return days < 0 ? "over" : days <= WARRANTY_SOON_DAYS ? "soon" : "ok";
}

function warrantyText(item) {
  const state = warrantyState(item);
  const end = formatDay(passportOf(item).warranty);
  if (state === "over") return T("Garantie endete am {0}", [end]);
  if (state === "soon") return T("Garantie endet am {0}", [end]);
  return state ? T("Garantie bis {0}", [end]) : "";
}

// Kurze Hinweise für Listen: nur, was gerade Aufmerksamkeit braucht.
function itemFlags(item) {
  const flags = [];
  if (item.away) {
    flags.push(h("span", { class: `flag-away small block${lendingLate(item) ? " flag-late" : ""}` },
      T("Gerade: {0}", [awayText(item)]), item.away_due ? ` · ${lendDueText(item)}` : ""));
  }
  const service = serviceState(item);
  if (service === "overdue" || service === "soon") {
    flags.push(h("span", { class: `flag-service small block${service === "overdue" ? " flag-late" : ""}` }, serviceText(item)));
  }
  return flags;
}

function knownBorrowers() {
  const names = new Map();
  for (const item of data.items) {
    for (const entry of item.log || []) if (entry.kind === "weg" && entry.who) names.set(normalize(entry.who), entry.who);
    if (item.away_to) names.set(normalize(item.away_to), item.away_to);
  }
  return [...names.values()].sort((a, b) => a.localeCompare(b, LOCALE)).slice(0, 50);
}

// Verleihen oder woanders: mit Name und Rückgabedatum, beides freiwillig. Steht am Eintrag und im Steckbrief.
function awayEditor(item) {
  const save = (body, message) => act(() => api("PATCH", `api/items/${item.id}`, body), () => {
    if (message) toast(message);
    render();
  });
  if (item.away) {
    const accessories = passportOf(item).accessories;
    return h("div", { class: "field" }, T("Gerade woanders"),
      h("div", { class: "row tight away-row" },
        h("span", { class: `flag-away grow${lendingLate(item) ? " flag-late" : ""}` },
          `${awayText(item)}${item.away_since ? T(", seit {0}", [formatDate(item.away_since)]) : ""}`,
          item.away_due ? h("span", { class: "block small" }, lendDueText(item)) : null),
        h("button", { type: "button", class: "compact primary", onclick: () => save({ away: "" }, T("Wieder da")) }, T("Ist zurück"))),
      accessories && isLent(item.away) ? h("p", { class: "muted small" }, T("Beim Zurücknehmen prüfen: {0}", [accessories.split(/\n+/).join(", ")])) : null);
  }
  const listId = `borrowers-${++borrowerListId}`;
  const who = h("input", { type: "text", maxlength: 60, list: listId, placeholder: T("Name"), autocomplete: "off" });
  const due = h("input", { type: "date", min: todayIso() });
  const custom = h("input", { type: "text", maxlength: 80, placeholder: T("Oder selbst eintragen, z. B. im Vereinsheim"), "aria-label": T("Wo es gerade ist") });
  return h("details", { class: "away-pick" },
    h("summary", { class: "small muted" }, T("Verleihen oder woanders?")),
    h("div", { class: "stack tight-stack" },
      h("form", {
        class: "lend-form",
        onsubmit: (event) => {
          event.preventDefault();
          save({ away: T("Verliehen"), away_to: who.value, away_due: due.value }, T("Verleih gemerkt"));
        },
      },
      h("label", { class: "field" }, T("An wen?"), who),
      h("label", { class: "field" }, T("Zurück bis (freiwillig)"), due),
      h("button", { type: "submit", class: "primary" }, T("Verleihen")),
      h("datalist", { id: listId }, knownBorrowers().map((name) => h("option", { value: name })))),
      h("div", { class: "chips" }, [T("Im Auto"), T("In Reparatur"), T("Auf der Baustelle")].map((text) =>
        h("button", { type: "button", class: "chip", onclick: () => save({ away: text }) }, text))),
      h("form", {
        class: "add-row",
        onsubmit: (event) => {
          event.preventDefault();
          if (custom.value.trim()) save({ away: custom.value });
        },
      }, custom, h("button", { type: "submit" }, T("Merken")))));
}

// Dokumente: PDFs gehen unverändert hoch. Fotos werden verkleinert, dabei fallen Metadaten wie der Aufnahmeort weg.
async function uploadDocument(file, itemId, kind, title) {
  const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
  let body = file;
  if (!isPdf) {
    const bitmap = await createImageBitmap(await readableImage(file));
    const scale = Math.min(1, MAX_DOCUMENT_EDGE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    body = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
  }
  if (body.size > MAX_DOCUMENT_BYTES) throw new Error(T("Die Datei ist größer als 30 MB."));
  const base = file.name.replace(/\.[a-z0-9]{2,5}$/i, "");
  const generic = /^(img|image|photo|foto|dsc|pxl|scan)?[\s_-]*\d*$/i.test(base);
  const name = title || (generic ? "" : file.name);
  const headers = name ? { "X-Datei-Name": encodeURIComponent(name.slice(0, 200)) } : {};
  return api("POST", `api/items/${itemId}/documents?kind=${encodeURIComponent(kind)}`, undefined, body, headers);
}

function documentKindLabel(kind) {
  return (DOCUMENT_KINDS.find(([key]) => key === kind) || DOCUMENT_KINDS[4])[1];
}

function kindSelect(value) {
  const select = h("select", { "aria-label": T("Art") }, DOCUMENT_KINDS.map(([key, label]) => h("option", { value: key }, label)));
  select.value = value;
  return select;
}

function sectionHead(title, editButton) {
  return h("div", { class: "section-head" }, h("h2", {}, title), editButton);
}

function editButton(onclick) {
  return offlineSince === null ? h("button", { type: "button", class: "compact quiet", onclick }, icon("edit"), T("Bearbeiten")) : null;
}

function formButtons(cancel) {
  return h("div", { class: "row tight" },
    h("button", { type: "submit", class: "primary compact" }, T("Speichern")),
    h("button", { type: "button", class: "compact quiet", onclick: cancel }, T("Abbrechen")));
}

function savePassport(item, change, message = T("Gespeichert")) {
  act(() => api("PATCH", `api/items/${item.id}`, { passport: change }), () => {
    passportEdit = null;
    toast(message);
    render();
  });
}

function factValue(key, value) {
  if (key === "bought" || key === "warranty") return formatDay(value);
  return value;
}

function factsCard(item, editing, edit) {
  const passport = passportOf(item);
  if (editing) {
    const inputs = {};
    return h("section", { class: "card stack" },
      sectionHead(T("Angaben")),
      h("form", {
        class: "stack passport-form",
        onsubmit: (event) => {
          event.preventDefault();
          savePassport(item, Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value.trim()])));
        },
      },
      h("div", { class: "form-grid" }, PASSPORT_FACTS.map(([key, label, type, max, hint]) => {
        inputs[key] = h("input", { type, value: passport[key] || "", maxlength: max, placeholder: hint || undefined, autocomplete: "off" });
        return h("label", { class: "field" }, label, inputs[key]);
      })),
      formButtons(() => edit(null))));
  }
  const rows = PASSPORT_FACTS.filter(([key]) => passport[key]).map(([key, label]) => [label, key === "link"
    ? h("a", { href: passport.link, target: "_blank", rel: "noopener noreferrer" }, (() => { try { return new URL(passport.link).host; } catch { return passport.link; } })())
    : key === "warranty" ? h("span", { class: warrantyState(item) === "soon" ? "flag-away" : "" }, factValue(key, passport[key])) : factValue(key, passport[key])]);
  return h("section", { class: "card stack" },
    sectionHead(T("Angaben"), editButton(() => edit("facts"))),
    h("dl", { class: "facts" }, rows.map(([label, value]) => [h("dt", {}, label), h("dd", {}, value)])));
}

function documentsCard(item, edit) {
  const documents = item.documents || [];
  const online = offlineSince === null;
  const kind = kindSelect("anleitung");
  const add = async (file) => {
    toast(T("Datei wird geladen ..."));
    try {
      await uploadDocument(file, item.id, kind.value);
      await reload();
    } catch (error) {
      if (error.message !== "PIN erforderlich") toast(error.message);
      return;
    }
    passportEdit = null;
    toast(T("Dokument abgelegt"));
    render();
  };
  const fileInput = h("input", {
    type: "file",
    accept: "application/pdf,image/*",
    onchange: (event) => {
      const file = event.target.files[0];
      event.target.value = "";
      if (file) add(file);
    },
  });
  const documentRow = (doc) => {
    const title = h("input", { type: "text", value: doc.title, maxlength: 120, "aria-label": T("Titel") });
    const kindChoice = kindSelect(doc.kind);
    return h("div", { class: "doc-row" },
      h("a", { class: "doc-link", href: `api/documents/${doc.id}`, target: "_blank", rel: "noopener" },
        icon("doc"),
        h("span", { class: "grow" },
          h("strong", {}, doc.title),
          h("span", { class: "muted small block" }, `${documentKindLabel(doc.kind)} · ${doc.ext === ".pdf" ? "PDF" : T("Bild")} · ${backupSize(doc.size)} · ${formatDate(doc.created)}`))),
      online ? h("details", { class: "doc-edit" },
        h("summary", { class: "small muted" }, T("Ändern")),
        h("form", {
          class: "stack tight-stack",
          onsubmit: (event) => {
            event.preventDefault();
            act(() => api("PATCH", `api/documents/${doc.id}`, { title: title.value, kind: kindChoice.value }), () => { toast(T("Gespeichert")); render(); });
          },
        },
        h("label", { class: "field" }, T("Titel"), title),
        h("label", { class: "field" }, T("Art"), kindChoice),
        h("div", { class: "row spread" },
          h("button", { type: "submit", class: "compact primary" }, T("Speichern")),
          h("button", { type: "button", class: "compact danger", onclick: () => deleteWithUndo(`api/documents/${doc.id}`, T("„{0}“ gelöscht", [doc.title])) }, T("Löschen"))))) : null);
  };
  return h("section", { class: "card stack" },
    sectionHead(cap(T("Dokumente")), documents.length ? h("span", { class: "muted small" }, String(documents.length)) : null),
    documents.length ? h("div", { class: "doc-list" }, documents.map(documentRow)) : null,
    online ? h("div", { class: "doc-add" },
      h("label", { class: "field" }, T("Art"), kind),
      h("label", { class: "button primary file-button" }, icon("plus"), T("Datei hinzufügen"), fileInput)) : null,
    online ? h("p", { class: "muted small" }, T("Anleitung, Rechnung oder Garantie als PDF oder Foto, bis 30 MB. Die Datei liegt nur in findling und ist Teil jeder Sicherung.")) : null,
    !documents.length && online ? h("button", { type: "button", class: "compact quiet", onclick: () => edit(null) }, T("Abbrechen")) : null);
}

function operationCard(item, editing, edit) {
  const passport = passportOf(item);
  if (editing) {
    const accessories = h("textarea", { maxlength: 500, placeholder: T("z. B. 2 Akkus, Ladegerät, Koffer, Bitsatz") });
    accessories.value = passport.accessories || "";
    const usage = h("textarea", { class: "tall", maxlength: 3000, placeholder: T("Wie man es benutzt, worauf man achten muss, Sicherheitshinweise") });
    usage.value = passport.usage || "";
    return h("section", { class: "card stack" },
      sectionHead(T("Bedienung")),
      h("form", {
        class: "stack",
        onsubmit: (event) => {
          event.preventDefault();
          savePassport(item, { accessories: accessories.value, usage: usage.value });
        },
      },
      h("label", { class: "field" }, T("Gehört dazu"), accessories),
      h("label", { class: "field" }, T("Bedienung und Hinweise"), usage),
      formButtons(() => edit(null))));
  }
  const parts = (passport.accessories || "").split(/\n|,\s*/).map((part) => part.trim()).filter(Boolean);
  return h("section", { class: "card stack" },
    sectionHead(T("Bedienung"), editButton(() => edit("usage"))),
    parts.length ? h("div", {}, h("strong", { class: "small" }, T("Gehört dazu")), h("ul", { class: "parts" }, parts.map((part) => h("li", {}, part)))) : null,
    passport.usage ? h("p", { class: "prewrap" }, passport.usage) : null);
}

function serviceDoneForm(item) {
  const note = h("input", { type: "text", maxlength: 200, placeholder: T("Was wurde gemacht? (freiwillig)") });
  const day = h("input", { type: "date", value: todayIso(), max: todayIso() });
  return h("form", {
    class: "stack tight-stack service-done",
    onsubmit: (event) => {
      event.preventDefault();
      act(() => api("POST", `api/items/${item.id}/service`, { note: note.value, date: day.value }), () => {
        passportEdit = null;
        toast(T("Wartung eingetragen"));
        render();
      });
    },
  },
  h("label", { class: "field" }, T("Wartung erledigt am"), day),
  h("label", { class: "field" }, T("Notiz"), note),
  formButtons(() => { passportEdit = null; render(); }));
}

function serviceCard(item, editing, edit) {
  const passport = passportOf(item);
  if (editing) {
    const every = h("select", {}, h("option", { value: "" }, T("Kein fester Takt")), SERVICE_CHOICES.map(([months, label]) => h("option", { value: String(months) }, label)));
    every.value = passport.service_months ? String(passport.service_months) : "";
    if (passport.service_months && every.value !== String(passport.service_months)) {
      every.append(h("option", { value: String(passport.service_months) }, T("alle {0} Monate", [passport.service_months])));
      every.value = String(passport.service_months);
    }
    const last = h("input", { type: "date", value: passport.service_last || "", max: todayIso() });
    const care = h("textarea", { class: "tall", maxlength: 3000, placeholder: T("z. B. Kette ölen, Filter wechseln, Messer schärfen") });
    care.value = passport.care || "";
    return h("section", { class: "card stack" },
      sectionHead(T("Wartung")),
      h("form", {
        class: "stack",
        onsubmit: (event) => {
          event.preventDefault();
          savePassport(item, { service_months: every.value ? Number(every.value) : "", service_last: last.value, care: care.value });
        },
      },
      h("label", { class: "field" }, T("Wartung"), every),
      h("label", { class: "field" }, T("Zuletzt gewartet"), last),
      h("label", { class: "field" }, T("Wartungshinweise"), care),
      formButtons(() => edit(null))));
  }
  const state = serviceState(item);
  return h("section", { class: "card stack" },
    sectionHead(T("Wartung"), editButton(() => edit("service"))),
    h("dl", { class: "facts" },
      h("dt", {}, T("Takt")), h("dd", {}, passport.service_months
        ? (SERVICE_CHOICES.find(([months]) => months === passport.service_months) || [0, T("alle {0} Monate", [passport.service_months])])[1]
        : T("Kein fester Takt")),
      h("dt", {}, T("Zuletzt")), h("dd", {}, passport.service_last ? formatDay(passport.service_last) : T("noch nicht eingetragen")),
      item.next_service ? [h("dt", {}, T("Nächste")), h("dd", { class: state === "overdue" ? "flag-service flag-late" : state === "soon" ? "flag-service" : "" }, formatDay(item.next_service))] : null),
    passport.care ? h("p", { class: "prewrap" }, passport.care) : null,
    passportEdit?.section === "done" ? serviceDoneForm(item)
      : offlineSince === null ? h("button", { type: "button", class: state === "ok" ? "" : "primary", onclick: () => edit("done") }, icon("check"), T("Wartung erledigt")) : null);
}

function logText(entry) {
  if (entry.kind === "weg") return entry.who ? (isLent(entry.text) ? T("Verliehen an {0}", [entry.who]) : T("{0}, bei {1}", [entry.text, entry.who])) : entry.text;
  if (entry.kind === "zurueck") return entry.who ? T("Zurück von {0}", [entry.who]) : T("Wieder da ({0})", [entry.text]);
  if (entry.kind === "wartung") return entry.text ? T("Gewartet: {0}", [entry.text]) : T("Gewartet");
  return entry.text;
}

function logDate(entry) {
  return entry.kind === "wartung" && entry.day ? formatDay(entry.day) : formatDate(entry.at);
}

function historyCard(item) {
  const log = item.log || [];
  const online = offlineSince === null;
  const note = h("input", { type: "text", maxlength: 200, placeholder: T("z. B. Bohrfutter klemmt, neuer Akku"), "aria-label": T("Notiz für den Verlauf") });
  return h("section", { class: "card stack" },
    sectionHead(T("Verlauf")),
    log.length ? h("ul", { class: "log-list" }, log.slice(0, 30).map((entry) => h("li", {},
      h("span", { class: "log-date muted small" }, logDate(entry)),
      h("span", { class: "grow" }, logText(entry)),
      online ? h("button", {
        type: "button",
        class: "compact quiet",
        "aria-label": T("Zeile löschen"),
        onclick: () => {
          if (confirm(T("Diese Zeile aus dem Verlauf löschen?"))) act(() => api("DELETE", `api/log/${entry.id}`));
        },
      }, icon("trash")) : null)))
      : h("p", { class: "muted small" }, T("Verleih, Rückgabe und Wartung landen hier von selbst.")),
    online ? h("form", {
      class: "add-row",
      onsubmit: (event) => {
        event.preventDefault();
        if (note.value.trim()) act(() => api("POST", `api/items/${item.id}/log`, { text: note.value }));
      },
    }, note, h("button", { type: "submit", "aria-label": T("Notiz hinzufügen") }, icon("plus"))) : null);
}

function statusCard(item) {
  const place = placeOf(item);
  const warranty = warrantyState(item);
  return h("section", { class: "card stack" },
    sectionHead(T("Status")),
    item.away ? null : h("p", { class: "small" }, T("Liegt an {0}", [placeName(place)]),
      h("span", { class: "muted block" }, T("Bestätigt: {0}", [formatDate(item.last_seen)]))),
    offlineSince === null ? awayEditor(item) : item.away ? h("p", { class: "flag-away" }, awayText(item)) : null,
    offlineSince === null ? h("div", { class: "row level-row" }, quantityField(item), levelField(item)) : h("p", { class: "small" }, `${isDevice(item) ? T("Zustand") : T("Füllstand")}: ${fillLabel(item.fill, item)}`),
    serviceState(item) && serviceState(item) !== "ok" ? h("p", { class: `small flag-service${serviceState(item) === "overdue" ? " flag-late" : ""}` }, serviceText(item)) : null,
    warranty === "soon" || warranty === "over" ? h("p", { class: `small ${warranty === "soon" ? "flag-away" : "muted"}` }, warrantyText(item)) : null);
}

// Ansicht: Steckbrief eines Eintrags. Leere Teile bleiben verborgen, damit nichts nach Pflicht aussieht.
function viewPassport(itemId) {
  const item = data.items.find((candidate) => candidate.id === itemId);
  if (!item) return viewMissing(T("Diesen Eintrag gibt es nicht."));
  if (passportEdit && passportEdit.itemId !== item.id) passportEdit = null;
  const place = placeOf(item);
  const passport = passportOf(item);
  const open = (section) => passportEdit?.section === section;
  const edit = (section) => {
    passportEdit = section ? { itemId: item.id, section } : null;
    render();
  };
  const has = {
    facts: PASSPORT_FACTS.some(([key]) => passport[key]),
    documents: (item.documents || []).length > 0,
    usage: Boolean(passport.usage || passport.accessories),
    service: Boolean(passport.service_months || passport.service_last || passport.care),
  };
  const contents = detailLines(item).length || (item.photos || []).length;
  const missing = [["facts", T("Angaben")], ["documents", cap(T("Dokument"))], ["usage", T("Bedienung")], ["service", T("Wartung")]]
    .filter(([key]) => !has[key] && !open(key));
  app.replaceChildren(...shell(
    backLink(`#/p/${place.code}`, placeName(place)),
    h("p", { class: "eyebrow" }, icon("doc"), T("Steckbrief")),
    (item.photos || []).length ? h("a", { class: "passport-photo", href: `fotos/${item.photos[0]}`, target: "_blank", rel: "noopener" },
      h("img", { src: `fotos/${item.photos[0]}`, alt: T("Foto von {0}", [item.name]) })) : null,
    h("h1", {}, item.name),
    deviceLine(item) ? h("p", { class: "lead" }, deviceLine(item)) : null,
    h("p", { class: "muted small" }, quantityOf(item) > 1 ? `${T("{0} Stück", [quantityOf(item)])} · ` : "", `${placePath(place)} · ${place.code}`, item.note ? ` · ${item.note}` : ""),
    statusCard(item),
    offlineSince === null && missing.length ? h("section", { class: "card stack passport-add" },
      sectionHead(T("Ergänzen")),
      h("p", { class: "muted small" }, T("Alles freiwillig und jederzeit später. Was leer bleibt, wird nicht angezeigt.")),
      h("div", { class: "chips" }, missing.map(([key, label]) => h("button", { type: "button", class: "chip", onclick: () => edit(key) }, icon("plus"), label)))) : null,
    has.facts || open("facts") ? factsCard(item, open("facts"), edit) : null,
    has.documents || open("documents") ? documentsCard(item, edit) : null,
    has.usage || open("usage") ? operationCard(item, open("usage"), edit) : null,
    has.service || open("service") || open("done") ? serviceCard(item, open("service"), edit) : null,
    contents ? h("section", { class: "card stack" },
      sectionHead(T("Inhalt")),
      h("a", { class: "button compact detail-open", href: `#/detail/${item.id}` }, icon("lupe"), T("Detailmodus: {0}", [detailSummary(item)]))) : null,
    historyCard(item),
    h("div", { class: "row passport-actions" },
      h("button", { type: "button", onclick: () => downloadPassportPdf(item) }, icon("printer"), T("Steckbrief als PDF")),
      contents ? null : h("a", { class: "button quiet", href: `#/detail/${item.id}` }, icon("lupe"), T("Detailmodus")))));
  if (passportEdit) document.querySelector(".passport-form input, form.stack textarea, .doc-add select, .service-done input")?.scrollIntoView({ block: "center" });
}

// Ansicht: Im Blick. Was verliehen ist, was gewartet werden will und wo die Garantie bald endet.
function watchLists() {
  const byName = (a, b) => a.name.localeCompare(b.name, LOCALE);
  const away = data.items.filter((item) => item.away).sort((a, b) =>
    Number(lendingLate(b)) - Number(lendingLate(a)) || (a.away_due || "9999").localeCompare(b.away_due || "9999") || (a.away_since || 0) - (b.away_since || 0));
  const service = data.items.filter((item) => ["overdue", "soon"].includes(serviceState(item))).sort((a, b) => a.next_service.localeCompare(b.next_service));
  const warranty = data.items.filter((item) => warrantyState(item) === "soon").sort((a, b) => passportOf(a).warranty.localeCompare(passportOf(b).warranty));
  const passports = data.items.filter(hasPassport).sort(byName);
  const check = data.items.filter(needsCheck).sort((a, b) => FILL_LEVELS.indexOf(b.fill) - FILL_LEVELS.indexOf(a.fill) || byName(a, b));
  return { away, service, warranty, passports, check };
}

function watchRow(item, detail, action) {
  return h("div", { class: "watch-row" },
    h("a", { class: "grow watch-link", href: `#/steckbrief/${item.id}` },
      h("strong", {}, item.name),
      detail ? h("span", { class: "small block" }, detail) : null,
      h("span", { class: "muted small block" }, placePath(placeOf(item)))),
    action);
}

function viewWatch() {
  const lists = watchLists();
  const online = offlineSince === null;
  const late = lists.away.filter(lendingLate).length;
  const returned = (item) => online ? h("button", {
    type: "button",
    class: "compact",
    onclick: () => act(() => api("PATCH", `api/items/${item.id}`, { away: "" }), () => { toast(T("„{0}“ ist wieder da", [item.name])); render(); }),
  }, T("Ist zurück")) : null;
  const serviced = (item) => online ? h("button", {
    type: "button",
    class: "compact",
    onclick: () => act(() => api("POST", `api/items/${item.id}/service`, { date: todayIso() }), () => { toast(T("Wartung eingetragen")); render(); }),
  }, T("Erledigt")) : null;
  const fine = (item) => online ? h("button", {
    type: "button",
    class: "compact",
    onclick: () => act(() => api("PATCH", `api/items/${item.id}`, { fill: "ok" }), () => { toast(T("„{0}“ ist wieder in Ordnung", [item.name])); render(); }),
  }, T("In Ordnung")) : null;
  const empty = !lists.away.length && !lists.service.length && !lists.warranty.length && !lists.passports.length && !lists.check.length;
  app.replaceChildren(...shell(
    backLink("#/", T("Zum Dashboard")),
    h("h1", {}, T("Im Blick")),
    h("p", { class: "muted" }, T("Was verliehen oder unterwegs ist, welche Geräte geprüft werden sollten, welche Wartung ansteht und wo die Garantie bald endet. Alles Weitere steht im Steckbrief des jeweiligen Eintrags.")),
    h("div", { class: "watch-figures" },
      h("div", {}, h("strong", {}, String(lists.away.length)), h("span", { class: "muted small" }, T("unterwegs"))),
      h("div", { class: late ? "late" : "" }, h("strong", {}, String(late)), h("span", { class: "muted small" }, T("Rückgabe überfällig"))),
      h("div", {}, h("strong", {}, String(lists.service.length)), h("span", { class: "muted small" }, T("Wartung fällig"))),
      h("div", {}, h("strong", {}, String(lists.passports.length)), h("span", { class: "muted small" }, T("Steckbriefe")))),
    empty ? h("p", { class: "notice" }, T("Noch ist nichts im Blick. Öffne einen Eintrag und tippe auf „Steckbrief“, um zu verleihen, eine Wartung zu planen oder eine Anleitung abzulegen. Das geht jederzeit später.")) : null,
    lists.away.length ? h("section", { class: "card stack" },
      sectionHead(T("Verliehen und unterwegs")),
      lists.away.map((item) => watchRow(item,
        h("span", { class: lendingLate(item) ? "flag-away flag-late" : "flag-away" },
          awayText(item), item.away_since ? T(", seit {0}", [formatDate(item.away_since)]) : "", item.away_due ? ` · ${lendDueText(item)}` : ""),
        returned(item)))) : null,
    lists.service.length ? h("section", { class: "card stack" },
      sectionHead(cap(T("Wartung fällig"))),
      lists.service.map((item) => watchRow(item,
        h("span", { class: serviceState(item) === "overdue" ? "flag-service flag-late" : "flag-service" }, serviceText(item)),
        serviced(item)))) : null,
    lists.check.length ? h("section", { class: "card stack" },
      sectionHead(T("Geräte prüfen oder reparieren")),
      lists.check.map((item) => watchRow(item,
        h("span", { class: item.fill === "leer" ? "flag-service flag-late" : "flag-service" }, T("Zustand: {0}", [fillLabel(item.fill, item)])),
        fine(item)))) : null,
    lists.warranty.length ? h("section", { class: "card stack" },
      sectionHead(cap(T("Garantie endet bald"))),
      lists.warranty.map((item) => watchRow(item, h("span", { class: "flag-away" }, warrantyText(item)), null))) : null,
    lists.passports.length ? h("section", { class: "card stack" },
      sectionHead(T("Alle Steckbriefe"), h("span", { class: "muted small" }, String(lists.passports.length))),
      lists.passports.map((item) => watchRow(item, passportSummary(item), null))) : null));
}

function watchCard() {
  const lists = watchLists();
  const late = lists.away.filter(lendingLate).length;
  const parts = [];
  if (lists.away.length) parts.push(plural(lists.away.length, T("Ding unterwegs"), T("Dinge unterwegs")));
  if (late) parts.push(T("{0} Rückgabe überfällig", [late]));
  if (lists.service.length) parts.push(plural(lists.service.length, T("Wartung fällig"), T("Wartungen fällig")));
  if (lists.check.length) parts.push(plural(lists.check.length, T("Gerät zu prüfen"), T("Geräte zu prüfen")));
  if (lists.warranty.length) parts.push(plural(lists.warranty.length, T("Garantie endet bald"), T("Garantien enden bald")));
  if (!parts.length) return null;
  const urgent = late || lists.service.some((item) => serviceState(item) === "overdue") || lists.check.some((item) => item.fill === "leer");
  return h("a", { class: `watch-card${urgent ? " late" : ""}`, href: "#/blick" },
    icon("blick"),
    h("span", { class: "grow" }, h("strong", {}, T("Im Blick")), h("span", { class: "small block" }, parts.join(" · "))),
    icon("next"));
}

// Steckbrief als PDF: zum Ausdrucken, Mitgeben beim Verleihen oder Ablegen beim Gerät.
function buildPassportPdf(item) {
  const today = new Date().toLocaleDateString(LOCALE);
  const passport = passportOf(item);
  const place = placeOf(item);
  const usable = PDF_W - 2 * PDF_MARGIN;
  const labelW = 120;
  const pages = [];
  let page = pdfPage();
  let y = PDF_MARGIN;
  const newPage = () => {
    pages.push(page);
    page = pdfPage();
    y = PDF_MARGIN + 6;
  };
  const need = (space) => { if (y + space > PDF_H - PDF_MARGIN - 20) newPage(); };
  const qrSize = 84;
  const titleW = usable - qrSize - 16;
  page.qr(PDF_W - PDF_MARGIN - qrSize, PDF_MARGIN, qrSize, passportLink(item));
  page.text(PDF_MARGIN, y + 10, 9, T("Steckbrief"), { bold: true, gray: 0.45 });
  y += 14;
  for (const line of pdfWrap(item.name, 22, true, titleW).slice(0, 2)) {
    page.text(PDF_MARGIN, y + 22, 22, line, { bold: true });
    y += 26;
  }
  if (deviceLine(item)) {
    page.text(PDF_MARGIN, y + 12, 12, pdfFit(deviceLine(item), 12, false, titleW), { gray: 0.2 });
    y += 18;
  }
  pdfWrap(`${placePath(place)} · ${place.code}`, 9, false, titleW).slice(0, 2).forEach((line) => {
    page.text(PDF_MARGIN, y + 10, 9, line, { gray: 0.45 });
    y += 12;
  });
  y = Math.max(y, PDF_MARGIN + qrSize) + 14;
  const heading = (text) => {
    need(44);
    y += 6;
    page.text(PDF_MARGIN, y + 12, 12, text, { bold: true });
    page.box(PDF_MARGIN, y + 17, usable, 0.6, 0.8);
    y += 26;
  };
  const pair = (label, value) => {
    const lines = pdfWrap(value, 9, false, usable - labelW);
    need(lines.length * 12 + 3);
    page.text(PDF_MARGIN, y + 9, 9, pdfFit(label, 9, false, labelW - 8), { gray: 0.45 });
    lines.forEach((line, index) => page.text(PDF_MARGIN + labelW, y + 9 + index * 12, 9, line));
    y += Math.max(1, lines.length) * 12 + 3;
  };
  const paragraph = (text) => {
    for (const raw of text.split("\n")) {
      for (const line of raw.trim() ? pdfWrap(raw, 9, false, usable) : [""]) {
        need(12);
        page.text(PDF_MARGIN, y + 9, 9, line);
        y += 12;
      }
    }
    y += 4;
  };
  if (item.away) {
    heading(T("Status"));
    pair(T("Gerade"), awayText(item));
    if (item.away_since) pair(T("Seit"), formatDate(item.away_since));
    if (item.away_due) pair(T("Zurück bis"), formatDay(item.away_due));
  }
  const facts = PASSPORT_FACTS.filter(([key]) => passport[key]);
  if (facts.length || item.note || quantityOf(item) > 1) {
    heading(T("Angaben"));
    if (item.note) pair(T("Notiz"), item.note);
    if (quantityOf(item) > 1) pair(T("Anzahl"), T("{0} Stück", [quantityOf(item)]));
    facts.forEach(([key, label]) => pair(label, factValue(key, passport[key])));
  }
  const parts = (passport.accessories || "").split(/\n|,\s*/).map((part) => part.trim()).filter(Boolean);
  if (parts.length) {
    heading(T("Gehört dazu"));
    for (const part of parts) {
      need(15);
      page.frame(PDF_MARGIN, y + 1, 9, 9, 0.3);
      page.text(PDF_MARGIN + 16, y + 9, 9, pdfFit(part, 9, false, usable - 16));
      y += 15;
    }
    page.text(PDF_MARGIN, y + 8, 7, T("Beim Verleihen und Zurückgeben abhaken."), { gray: 0.5 });
    y += 14;
  }
  if (passport.usage) {
    heading(T("Bedienung"));
    paragraph(passport.usage);
  }
  if (passport.service_months || passport.service_last || passport.care) {
    heading(T("Wartung"));
    if (passport.service_months) pair(T("Takt"), (SERVICE_CHOICES.find(([months]) => months === passport.service_months) || [0, T("alle {0} Monate", [passport.service_months])])[1]);
    if (passport.service_last) pair(T("Zuletzt"), formatDay(passport.service_last));
    if (item.next_service) pair(T("Nächste"), formatDay(item.next_service));
    if (passport.care) paragraph(passport.care);
  }
  if ((item.documents || []).length) {
    heading(cap(T("Dokumente")));
    item.documents.forEach((doc) => pair(documentKindLabel(doc.kind), doc.title));
    page.text(PDF_MARGIN, y + 8, 7, T("Die Dateien liegen in findling, erreichbar über den QR-Code."), { gray: 0.5 });
    y += 14;
  }
  if (detailLines(item).length) {
    heading(T("Inhalt"));
    paragraph(detailLines(item).join(", "));
  }
  if ((item.log || []).length) {
    heading(T("Verlauf"));
    item.log.slice(0, 12).forEach((entry) => pair(logDate(entry), logText(entry)));
  }
  pages.push(page);
  pages.forEach((entry, index) => {
    entry.text(PDF_MARGIN, PDF_H - 18, 7, T("findling · Stand {0}", [today]), { gray: 0.5 });
    if (pages.length > 1) entry.textRight(PDF_W - PDF_MARGIN, PDF_H - 18, 7, T("Seite {0} von {1}", [index + 1, pages.length]), { gray: 0.5 });
  });
  return pdfDocument(pages);
}

function downloadPassportPdf(item) {
  let bytes;
  try {
    bytes = buildPassportPdf(item);
  } catch (error) {
    toast(T("Die PDF ließ sich nicht erstellen: {0}", [T(error.message)]));
    return;
  }
  const slug = normalize(item.name).replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "eintrag";
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
  const link = h("a", { href: url, download: `findling-steckbrief-${slug}.pdf`, hidden: true });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
  toast(T("Steckbrief erstellt"));
}

// Ansicht: Massenimport. Für Tage, an denen hunderte Dinge auf einmal erfasst werden: eine Tabelle statt der Maske.
// Erst prüft der Server alles und zeigt eine Vorschau, übernommen wird nur ohne Fehler und nach einer Sicherung.
let importFile = null;
let importResult = null;

const IMPORT_COLUMNS_HELP = [
  [T("Raum"), T("Pflicht. Was es noch nicht gibt, wird angelegt.")],
  [T("Schrank oder Regal"), T("Pflicht. Auch Kiste, Wand oder Stapel.")],
  [T("Platz"), T("Zum Beispiel „Schublade 2“ oder „Fach oben“. Leer heißt: der ganze Schrank.")],
  [T("Name"), T("Pflicht. Eine Zeile je Gegenstand.")],
  [T("Anzahl"), T("Wie viele gleiche Stücke dort liegen, etwa 4 Zwingen. Leer heißt 1.")],
  [T("Gerät"), T("„ja“ für Geräte und Werkzeuge. Sie bekommen einen Zustand statt eines Füllstands.")],
  [T("Füllstand oder Zustand"), T("voll, ok, wenig oder leer. Bei Geräten ausgezeichnet, in Ordnung, zu überprüfen oder kaputt. Leer heißt ok.")],
  [T("Notiz"), T("Farbton, Maß, Norm.")],
  [T("Auch genannt"), T("Andere Wörter für die Suche.")],
  [T("Inhalt"), T("Teile, getrennt mit |, etwa „Bit T20 | Bit T25“.")],
  [T("Hersteller, Modell, Seriennummer"), T("Für den Steckbrief.")],
  [T("Kaufdatum, Garantie bis"), T("Datum wie 01.03.2024.")],
  [T("Haus oder Grundstück"), T("Nur nötig, wenn du mehrere Standorte hast.")],
];

function importSummary(result) {
  const parts = [
    result.sites ? plural(result.sites, T("Haus oder Grundstück"), T("Häuser oder Grundstücke")) : "",
    result.rooms ? plural(result.rooms, T("Raum"), T("Räume")) : "",
    result.maps ? plural(result.maps, T("Schrank"), T("Schränke")) : "",
    result.places ? plural(result.places, T("Platz"), T("Plätze")) : "",
    result.items_new ? plural(result.items_new, T("Eintrag"), T("Einträge")) : "",
  ].filter(Boolean);
  // Im Englischen stehen manche Wörter sonst groß, etwa „Rooms“ als Überschrift.
  return LANG === "en" ? parts.map((part) => part.toLocaleLowerCase(LOCALE)) : parts;
}

function importResultCard(result) {
  const created = importSummary(result);
  if (result.applied) {
    return h("section", { class: "card stack" },
      h("h2", {}, T("Übernommen")),
      h("p", {}, created.length ? T("Neu: {0}.", [created.join(", ")]) : T("Nichts Neues angelegt.")),
      result.items_updated ? h("p", {}, T("Aktualisiert: {0}.", [plural(result.items_updated, T("Eintrag"), T("Einträge"))])) : null,
      result.backup ? h("p", { class: "muted small" }, T("Der Stand davor ist gesichert und lässt sich unter Sicherungen zurückholen.")) : null,
      h("div", { class: "row" },
        h("a", { class: "button primary", href: "#/" }, T("Zum Dashboard")),
        h("button", { type: "button", onclick: () => { importFile = null; importResult = null; render(); } }, T("Weitere Datei einlesen"))));
  }
  const errors = result.errors || [];
  return h("section", { class: "card stack" },
    h("h2", {}, errors.length ? T("Bitte zuerst korrigieren") : T("Vorschau")),
    h("p", {}, T("{0} gelesen.", [plural(result.rows, T("Zeile"), T("Zeilen"))])),
    errors.length ? [
      h("p", { class: "small" }, T("Solange eine Zeile nicht passt, wird nichts übernommen. Korrigiere die Tabelle und lies sie noch einmal ein.")),
      h("ul", { class: "import-errors small" }, errors.map((error) => h("li", {}, h("strong", {}, T("Zeile {0}", [error.line])), " ", T(error.message)))),
      errors.length >= 50 ? h("p", { class: "muted small" }, T("Weitere Fehler werden erst nach diesen angezeigt.")) : null,
    ] : [
      h("p", {}, created.length ? T("Neu: {0}.", [created.join(", ")]) : T("Nichts Neues.")),
      result.items_updated ? h("p", {}, T("Aktualisiert: {0}. Gleichnamige Einträge am selben Platz werden überschrieben, nicht verdoppelt.", [plural(result.items_updated, T("Eintrag"), T("Einträge"))])) : null,
    ],
    result.ignored.length ? h("p", { class: "muted small" }, T("Nicht gelesen: {0}", [result.ignored.join(", ")])) : null,
    errors.length ? null : h("p", { class: "muted small" }, T("Vor dem Übernehmen sichert findling den jetzigen Stand.")),
    h("div", { class: "row" },
      errors.length ? null : h("button", {
        type: "button",
        class: "primary",
        onclick: () => runImport(true),
      }, icon("check"), T("Jetzt übernehmen")),
      h("button", { type: "button", class: errors.length ? "primary" : "quiet", onclick: () => { importFile = null; importResult = null; render(); } }, T("Andere Datei"))));
}

async function runImport(apply) {
  toast(apply ? T("Wird übernommen ...") : T("Wird geprüft ..."));
  try {
    const result = await api("POST", `api/import${apply ? "?apply=1" : ""}`, undefined, importFile, { "Content-Type": "text/csv" });
    importResult = result;
    if (result.applied) await reload();
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
    return;
  }
  document.getElementById("toast").hidden = true;
  render();
  document.querySelector(".import-result")?.scrollIntoView({ block: "start" });
}

function viewImport() {
  const online = offlineSince === null;
  const fileInput = h("input", {
    type: "file",
    accept: ".csv,text/csv,text/plain",
    onchange: (event) => {
      const file = event.target.files[0];
      event.target.value = "";
      if (!file) return;
      if (file.size > 5 * 1024 * 1024) {
        toast(T("Die Datei ist zu groß"));
        return;
      }
      importFile = file;
      importResult = null;
      runImport(false);
    },
  });
  app.replaceChildren(...shell(
    backLink("#/daten", T("Einstellungen")),
    h("h1", {}, T("Massenimport")),
    h("p", { class: "lead" }, T("Für Tage, an denen du viel auf einmal erfasst: Trag Räume, Schränke, Plätze und Gegenstände in eine Tabelle ein und lies sie hier in einem Rutsch ein. Fotos und Rahmen ergänzt du später.")),
    h("section", { class: "card stack" },
      h("h2", {}, T("1. Vorlage laden")),
      h("p", { class: "muted small" }, T("Eine Tabelle mit allen Spalten und vier Beispielzeilen. Sie öffnet sich in Excel, Numbers oder LibreOffice. Die Beispiele überschreibst du einfach.")),
      h("a", { class: "button primary", href: "api/import-vorlage.csv" }, icon("download"), T("Vorlage herunterladen")),
      h("p", { class: "muted small" }, T("Auch die Bestandsliste aus den Einstellungen lässt sich ergänzen und wieder einlesen. Dann zählt die Adresse, etwa W-R-03."))),
    h("section", { class: "card stack" },
      h("h2", {}, T("2. Ausfüllen")),
      h("p", { class: "muted small" }, T("Eine Zeile je Gegenstand. Die Reihenfolge der Spalten ist egal, die Überschriften in der ersten Zeile zählen.")),
      h("dl", { class: "facts import-help" }, IMPORT_COLUMNS_HELP.map(([column, text]) => [h("dt", {}, column), h("dd", {}, text)])),
      h("p", { class: "muted small" }, T("Gibt es einen Gegenstand am selben Platz schon, wird er aktualisiert statt doppelt angelegt. So trägst du auch Zustände später per Tabelle nach.")),
      h("p", { class: "muted small" }, T("Speichern als CSV. In Excel: „CSV UTF-8“ oder „CSV (Trennzeichen-getrennt)“."))),
    h("section", { class: "card stack" },
      h("h2", {}, T("3. Einlesen")),
      online ? h("label", { class: "button primary file-button" }, icon("plus"), importFile ? T("Andere Datei wählen") : T("Tabelle wählen"), fileInput)
        : h("p", { class: "notice" }, T("Einlesen geht nur im Heimnetz.")),
      importFile ? h("p", { class: "muted small" }, importFile.name) : h("p", { class: "muted small" }, T("Erst kommt eine Vorschau. Übernommen wird erst nach deiner Bestätigung."))),
    importResult ? h("div", { class: "import-result" }, importResultCard(importResult)) : null,
    importResult?.applied ? null : h("p", { class: "muted small" }, T("Importierte Plätze gelten als erfasst und liegen als Raster auf dem Schrank. Mit einem Schrankfoto passt du die Rahmen später an."))));
}

// Ansicht: Schnellerfassung. Etwas Neues kommt ins Haus, ob Kauf, Geschenk oder Fund:
// Foto machen, Namen tippen, Lagerplatz wählen, fertig. Der Platz bleibt für das nächste Teil stehen.
const INTAKE_ORIGINS = [["kauf", T("Gekauft")], ["geschenk", T("Geschenkt")], ["fund", T("Gefunden")]];
let intake = null;

function freshIntake(placeId, saved = []) {
  return { file: null, preview: null, receipt: null, receiptPreview: null, name: "", quantity: 1, note: "", from: "", origin: "", device: false, placeId: placeId || lastStorePlace, saved };
}

function viewIntake() {
  if (!data.places.length) return viewMissing(T("Lege zuerst einen Schrank mit Plätzen an. Dann kannst du Neues direkt einlagern."));
  intake ||= freshIntake();
  const online = offlineSince === null;
  const setPhoto = async (file) => {
    try {
      intake.preview = await photoCanvas(file);
      intake.file = file;
    } catch (error) {
      toast(error.message);
      return;
    }
    render();
    if (!intake.name) document.querySelector(".intake-name")?.focus();
  };
  pageCamera = online ? { text: intake.file ? T("Anderes Foto") : T("Foto machen"), onFile: setPhoto } : null;
  const name = h("input", { type: "text", class: "intake-name", maxlength: 120, value: intake.name, placeholder: T("z. B. Stichsäge, Holzleim, Gartenschere"), autocomplete: "off", oninput: (event) => { intake.name = event.target.value; } });
  const note = h("input", { type: "text", maxlength: 200, value: intake.note, placeholder: T("Farbton, Maß, Norm"), oninput: (event) => { intake.note = event.target.value; } });
  const count = h("input", { type: "number", class: "intake-qty", min: "1", max: String(QUANTITY_MAX), inputmode: "numeric", value: String(intake.quantity), "aria-label": T("Anzahl"),
    oninput: (event) => { const value = Number.parseInt(event.target.value, 10); if (Number.isInteger(value) && value >= 1) intake.quantity = Math.min(QUANTITY_MAX, value); } });
  const from = h("input", { type: "text", maxlength: 80, value: intake.from, placeholder: T("z. B. Baumarkt, von Oma, Flohmarkt"), oninput: (event) => { intake.from = event.target.value; } });
  const { filter, select } = placePicker(intake.placeId);
  select.addEventListener("change", () => { intake.placeId = select.value; });
  // Kassenbon oder Rechnung gleich mit ablegen: als Foto oder PDF, landet im Steckbrief unter Dokumente.
  const setReceipt = async (file) => {
    if (file.size > MAX_DOCUMENT_BYTES) {
      toast(T("Die Datei ist größer als 30 MB."));
      return;
    }
    const isPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
    try {
      intake.receiptPreview = isPdf ? null : await photoCanvas(file);
    } catch (error) {
      toast(error.message);
      return;
    }
    intake.receipt = file;
    render();
  };
  const receiptInput = h("input", {
    type: "file",
    accept: "application/pdf,image/*",
    onchange: (event) => {
      const file = event.target.files[0];
      event.target.value = "";
      if (file) setReceipt(file);
    },
  });
  const wantsReceipt = ["kauf", "geschenk"].includes(intake.origin) || intake.receipt;
  const receiptField = wantsReceipt ? h("div", { class: "field intake-receipt" }, intake.origin === "geschenk" ? T("Geschenkbeleg (freiwillig)") : T("Kassenbon oder Rechnung (freiwillig)"),
    intake.receipt
      ? h("div", { class: "row tight receipt-chosen" },
        intake.receiptPreview ? copyCanvas(intake.receiptPreview) : icon("doc"),
        h("span", { class: "grow small" }, intake.receiptPreview ? T("Foto vom Beleg") : intake.receipt.name),
        h("button", { type: "button", class: "compact quiet", onclick: () => { intake.receipt = null; intake.receiptPreview = null; render(); } }, T("Entfernen")))
      : h("label", { class: "button file-button" }, icon("camera"), T("Beleg fotografieren oder PDF wählen"), receiptInput),
    h("span", { class: "muted small block" }, T("Landet im Steckbrief unter Dokumente, gut für Garantie und Umtausch."))) : null;
  const save = () => {
    const title = name.value.trim();
    if (!title) {
      toast(T("Wie heißt es?"));
      name.focus();
      return;
    }
    const placeId = select.value;
    if (!placeId) {
      toast(T("Bitte einen Platz wählen"));
      return;
    }
    const place = data.places.find((candidate) => candidate.id === placeId);
    let itemId = null;
    let refilled = false;
    let shown = title;
    let newCount = 1;
    act(async () => {
      const existing = data.items.find((item) => item.place_id === placeId && normalize(item.name) === normalize(title));
      if (existing) {
        // Ein weiteres Gerät oder Werkzeug erhöht die Anzahl. Material wird aufgefüllt, die alte Packung war ja leer.
        const device = intake.device || isDevice(existing);
        const change = device
          ? { quantity: Math.min(QUANTITY_MAX, quantityOf(existing) + intake.quantity), ...(intake.device ? { scale: "state" } : {}) }
          : { fill: "voll", ...(intake.quantity > 1 ? { quantity: Math.min(QUANTITY_MAX, quantityOf(existing) + intake.quantity - 1) } : {}) };
        await api("PATCH", `api/items/${existing.id}`, change);
        itemId = existing.id;
        refilled = device ? "more" : intake.quantity > 1 ? "refilled-more" : "refilled";
        shown = existing.name;
        newCount = change.quantity || quantityOf(existing);
      } else {
        itemId = (await api("POST", "api/items", { place_id: placeId, name: title, note: note.value, fill: "voll", scale: intake.device ? "state" : "fill", quantity: intake.quantity })).id;
      }
      if (intake.file) await uploadPhoto(intake.file, null, itemId);
      if (intake.receipt) await uploadDocument(intake.receipt, itemId, "rechnung", T(intake.origin === "geschenk" ? "Geschenkbeleg {0}" : "Rechnung {0}", [shown]));
      if (intake.origin === "kauf") await api("PATCH", `api/items/${itemId}`, { passport: { bought: todayIso() } });
      const origin = INTAKE_ORIGINS.find(([key]) => key === intake.origin)?.[1];
      const story = [origin, from.value.trim()].filter(Boolean).join(": ");
      if (story) await api("POST", `api/items/${itemId}/log`, { text: story.slice(0, 200) });
    }, () => {
      lastStorePlace = placeId;
      intake = freshIntake(placeId, [{ id: itemId, name: shown, place: placeName(place), receipt: Boolean(intake.receipt) }, ...intake.saved.filter((entry) => entry.id !== itemId)].slice(0, 8));
      toast(refilled === "more" ? T("„{0}“ an {1}: jetzt {2} Stück", [shown, placeName(place), newCount])
        : refilled === "refilled-more" ? T("„{0}“ an {1} aufgefüllt, jetzt {2} Stück", [shown, placeName(place), newCount])
        : refilled ? T("„{0}“ war schon an {1} und ist jetzt wieder voll", [shown, placeName(place)])
          : T("„{0}“ liegt jetzt an {1}", [shown, placeName(place)]));
      render();
      window.scrollTo(0, 0);
    });
  };
  app.replaceChildren(...shell(
    backLink("#/", T("Zum Dashboard")),
    h("h1", {}, T("Neu reingekommen")),
    h("p", { class: "lead" }, T("Kauf, Geschenk oder Fund: Foto machen, Namen tippen, Lagerplatz wählen. Mehr nicht, den Rest ergänzt du jederzeit im Steckbrief.")),
    online ? null : h("p", { class: "notice" }, T("Erfassen geht nur im Heimnetz.")),
    h("section", { class: "card stack intake" },
      intake.preview
        ? h("div", { class: "intake-photo" }, copyCanvas(intake.preview),
          h("button", { type: "button", class: "compact quiet", onclick: () => { intake.file = null; intake.preview = null; render(); } }, T("Foto entfernen")))
        : online ? photoDropzone(T("Foto machen"), setPhoto, true) : null,
      h("div", { class: "intake-what" },
        h("label", { class: "field grow" }, T("Was ist es?"), name),
        h("label", { class: "field" }, T("Anzahl"), count)),
      h("div", { class: "field" }, T("Wohin kommt es?"), h("div", { class: "stack tight-stack intake-place" }, filter, select)),
      h("div", { class: "segments intake-kind", role: "group", "aria-label": T("Art") },
        [[false, T("Material")], [true, T("Gerät")]].map(([device, label]) => h("button", {
          type: "button",
          "aria-pressed": String(intake.device === device),
          onclick: () => { intake.device = device; render(); },
        }, label))),
      h("details", { class: "more intake-more", open: Boolean(intake.origin || intake.note || intake.from || intake.receipt) },
        h("summary", {}, T("Woher und Notiz (freiwillig)")),
        h("div", { class: "stack" },
          h("div", { class: "chips" }, INTAKE_ORIGINS.map(([key, label]) => h("button", {
            type: "button",
            class: "chip",
            "aria-pressed": String(intake.origin === key),
            onclick: () => { intake.origin = intake.origin === key ? "" : key; render(); },
          }, label))),
          h("label", { class: "field" }, T("Woher genau?"), from),
          receiptField,
          h("label", { class: "field" }, T("Notiz"), note))),
      online ? h("button", { type: "button", class: "primary intake-save", onclick: save }, icon("check"), T("Einlagern")) : null),
    intake.saved.length ? h("section", { class: "card stack" },
      sectionHead(T("Gerade erfasst")),
      h("ul", { class: "plain intake-saved" }, intake.saved.map((entry) => h("li", {},
        h("a", { href: `#/steckbrief/${entry.id}` }, entry.name), h("span", { class: "muted small" }, ` · ${entry.place}${entry.receipt ? T(" · mit Beleg") : ""}`))))) : null));
}

// Kurz nachgefragt: In unregelmäßigen Abständen fragt das Logo, ob etwas, das lange nicht bestätigt wurde,
// noch da ist. Eine Frage, dann Ruhe: Nach einer Antwort kommt die nächste erst nach einigen Tagen, nach „Später“ ebenso.
const CHECKIN_PAUSE_DAYS = [4, 12]; // zufällig dazwischen
const CHECKIN_CHOICES = [[30, T("nach 30 Tagen")], [90, T("nach 3 Monaten")], [180, T("nach 6 Monaten")], [365, T("nach einem Jahr")]];
let checkinStep = null; // { itemId, step: "gone" | "moved" }

function checkinPause() {
  const [low, high] = CHECKIN_PAUSE_DAYS;
  const days = low + Math.floor(Math.random() * (high - low + 1));
  const next = new Date(`${todayIso()}T12:00:00`);
  next.setDate(next.getDate() + days);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`;
}

function checkinCandidates() {
  const limit = Date.now() / 1000 - (prefs().checkin_days || 90) * 86400;
  const seen = (item) => item.last_seen || item.created;
  return data.items.filter((item) => !item.away && !item.missing && seen(item) < limit).sort((a, b) => seen(a) - seen(b));
}

// fromHero: Die Blase hängt am großen Logo der Fortschrittskachel, als frage es selbst. Sonst bekommt sie ein eigenes.
function checkinCard(fromHero) {
  if (offlineSince !== null) return null;
  const next = prefs().checkin_next || "";
  if (next && next > todayIso()) return null;
  const item = checkinCandidates()[0];
  if (!item) return null;
  const place = placeOf(item);
  const step = checkinStep?.itemId === item.id ? checkinStep.step : null;
  const go = (next) => { checkinStep = next ? { itemId: item.id, step: next } : null; render(); };
  const done = (message) => {
    checkinStep = null;
    if (message) toast(message);
    savePreferences({ checkin_next: checkinPause() });
  };
  let body;
  if (step === "gone") {
    body = [
      h("p", { class: "small" }, T("Was ist damit passiert?")),
      h("div", { class: "row tight" },
        h("button", { type: "button", class: "compact", onclick: () => deleteWithUndo(`api/items/${item.id}`, T("„{0}“ aussortiert", [item.name]), () => done()) }, T("Aussortiert")),
        h("button", { type: "button", class: "compact", onclick: () => go("moved") }, T("Liegt woanders")),
        h("button", {
          type: "button",
          class: "compact",
          onclick: () => act(() => api("POST", `api/items/${item.id}/missing`), () => done(T("Als vermisst vermerkt. Die Suche weist darauf hin."))),
        }, T("Weiß nicht")),
        h("button", { type: "button", class: "compact quiet", onclick: () => go(null) }, T("Zurück"))),
    ];
  } else if (step === "moved") {
    const { filter, select } = placePicker(item.place_id);
    body = [
      h("p", { class: "small" }, T("Wo liegt es jetzt?")),
      filter,
      select,
      h("div", { class: "row tight" },
        h("button", {
          type: "button",
          class: "compact primary",
          onclick: () => {
            const target = data.places.find((candidate) => candidate.id === select.value);
            if (!target) return;
            act(() => api("POST", "api/items/move", { item_ids: [item.id], place_id: target.id }), () => done(T("„{0}“ liegt jetzt an {1}", [item.name, placeName(target)])));
          },
        }, T("Hierhin verlegen")),
        h("button", { type: "button", class: "compact quiet", onclick: () => go("gone") }, T("Zurück"))),
    ];
  } else {
    body = [h("div", { class: "row tight" },
      h("button", {
        type: "button",
        class: "compact primary",
        onclick: () => act(() => api("POST", `api/items/${item.id}/still-there`), () => done(T("Danke, ist vermerkt."))),
      }, icon("check"), T("Noch da")),
      h("button", { type: "button", class: "compact", onclick: () => go("gone") }, T("Nicht mehr da")))];
  }
  return h("section", { class: `checkin${fromHero ? " from-hero" : ""}`, "aria-label": T("Kurz nachgefragt") },
    fromHero ? null : h("div", { class: "checkin-speaker" }, logoMark(40, 100, "happy")),
    h("div", { class: "bubble stack" },
      h("div", { class: "row checkin-item" },
        (item.photos || []).length ? h("img", { class: "checkin-photo", src: `fotos/${item.photos[0]}`, alt: "" }) : null,
        h("div", { class: "grow" },
          h("strong", {}, T("Ist „{0}“ noch da?", [item.name])),
          h("span", { class: "muted small block" }, `${placePath(place)} · ${place.code}`),
          h("span", { class: "muted small block" }, T("Zuletzt bestätigt: {0}", [formatDate(item.last_seen || item.created)]))),
        h("button", {
          type: "button",
          class: "compact quiet bubble-close",
          "aria-label": T("Später fragen"),
          title: T("Später fragen"),
          onclick: () => { checkinStep = null; savePreferences({ checkin_next: checkinPause() }); },
        }, "✕")),
      body));
}

// Ansicht: Etiketten

function qrSvg(text) {
  const qr = window.qrcode(0, "Q"); // Stufe Q verträgt Schmutz besser als die üblichen Stufen L und M.
  qr.addData(text);
  qr.make();
  const size = qr.getModuleCount();
  let path = "";
  for (let row = 0; row < size; row += 1) {
    for (let col = 0; col < size; col += 1) {
      if (qr.isDark(row, col)) path += `M${col} ${row}h1v1h-1z`;
    }
  }
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `-4 -4 ${size + 8} ${size + 8}`);
  svg.setAttribute("shape-rendering", "crispEdges");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", T("QR-Code für {0}", [text]));
  const background = document.createElementNS(ns, "rect");
  for (const [key, value] of Object.entries({ x: -4, y: -4, width: size + 8, height: size + 8, fill: "#fff" })) {
    background.setAttribute(key, value);
  }
  const modules = document.createElementNS(ns, "path");
  modules.setAttribute("d", path);
  modules.setAttribute("fill", "#000");
  svg.append(background, modules);
  return svg;
}

function baseUrl() {
  return data.settings.base_url || data.server.suggested_base || "";
}

function labelLink(code) {
  if (data.server.label_url) return data.server.label_url.replace("{code}", code);
  return `${baseUrl()}/#/p/${code}`;
}

function viewLabels(mapId) {
  const map = data.maps.find((candidate) => candidate.id === mapId);
  const places = map ? placesOf(map) : data.places;
  const selected = places.filter((place) => !unselectedLabels.has(place.id));
  const base = baseUrl();
  const sizeButton = (key, text) => h("button", {
    type: "button",
    "aria-pressed": String(prefs().label_size === key),
    onclick: () => savePreferences({ label_size: key }),
  }, text);

  app.replaceChildren(...shell(
    h("div", { class: "no-print" },
      backLink(map ? `#/karte/${map.id}` : "#/", map ? map.name : T("Zurück")),
      h("h1", {}, T("Etiketten drucken")),
      /localhost|127\.0\.0\.1/.test(base) ? h("p", { class: "notice" },
        T("Diese QR-Codes funktionieren nur auf diesem Rechner. Starte die App mit start.command, dann klappt es auch am Telefon.")) : null,
      places.length ? h("div", { class: "label-bar" },
        h("div", { class: "segments", role: "group", "aria-label": T("Etikettengröße") },
          sizeButton("size-s", T("Klein")), sizeButton("size-m", T("Mittel")), sizeButton("size-l", T("Groß"))),
        h("button", { type: "button", class: "primary", disabled: !selected.length, onclick: () => window.print() },
          icon("printer"), `${plural(selected.length, T("Etikett"), T("Etiketten"))} drucken`),
        h("button", { type: "button", onclick: () => downloadPrintPdf("all") }, T("Alles als PDF"))) : h("p", { class: "notice" }, T("Noch keine Plätze markiert.")),
      places.length ? h("p", { class: "muted small" }, T("Tippe ein Etikett an, um es auszulassen.")) : null),
    places.length ? h("div", { class: `label-sheet ${prefs().label_size}` }, places.map((place) =>
      h("button", {
        type: "button",
        class: `label${unselectedLabels.has(place.id) ? " off" : ""}`,
        "aria-pressed": String(!unselectedLabels.has(place.id)),
        onclick: () => {
          if (unselectedLabels.has(place.id)) unselectedLabels.delete(place.id);
          else unselectedLabels.add(place.id);
          render();
        },
      },
      qrSvg(labelLink(place.code)),
      h("strong", {}, place.code),
      h("small", {}, placeName(place))))) : null));
}

// Ansicht: Auswertung

async function viewReport() {
  const request = ++reportRequest;
  let report;
  try {
    report = await api("GET", "api/report");
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
    return;
  }
  if (request !== reportRequest || !location.hash.startsWith("#/auswertung")) return;
  const y = window.scrollY;
  const { totals } = report;
  const focus = h("div", { class: "stat-focus" });
  const tiles = [
    ["items", totals.items, totals.items === 1 ? T("Eintrag") : T("Einträge")],
    ["places", `${totals.surveyed} / ${totals.places}`, T("Plätze bestätigt")],
    ["rooms", totals.rooms, totals.rooms === 1 ? T("Raum") : T("Räume")],
    ["low", totals.low, T("zum Nachkaufen")],
  ].map(([key, value, label]) => statTile(value, label, key, focus));
  if (statFocus) showStatFocus(statFocus, focus, tiles);
  app.replaceChildren(...shell(
    backLink("#/", T("Zurück")),
    h("h1", {}, T("Auswertung")),
    totals.places ? h("p", { class: "muted small" }, T("Tipp auf eine Zahl oder ein Diagramm, dann zeigt findling, was dahintersteckt.")) : null,
    totals.places ? h("div", { class: "stats" }, tiles) : h("p", { class: "notice" }, T("Noch gibt es nichts auszuwerten. Leg zuerst einen Raum und Plätze an.")),
    totals.places ? focus : null,
    report.recommendations.length ? h("div", { class: "section-head room-head" }, h("h2", {}, T("Das kannst du jetzt verbessern"))) : null,
    report.recommendations.map(recommendationCard),
    report.dismissed_count ? h("button", {
      type: "button",
      class: "linklike small",
      onclick: () => act(() => api("POST", "api/report/restore", {})),
    }, T("{0} ausgeblendete Hinweise wieder zeigen", [report.dismissed_count])) : null,
    totals.items ? analysisCard(report) : null,
    totals.places ? h("div", { class: "section-head room-head" }, h("h2", {}, T("Zahlen"))) : null,
    totals.places ? [milestonesCard(), roomBars(report), fillBars(report), weekBars(), usageCard(report), aiCard(report)] : null));
  window.scrollTo(0, y);
}

// Stufen statt fester Ziele: Je Bereich wächst die Stufe ohne Obergrenze, jede braucht etwas mehr als die vorige.
// Punkte gibt es fürs Erfassen genauso wie fürs Ordnen, Pflegen und Benutzen. Erste Male bleiben als Abzeichen.
// Jede Stufe hat ihre eigene Farbe. Nach der letzten beginnt die Reihe von vorn, eine Obergrenze gibt es nicht.
const LEVEL_COLORS = ["#26ff00", "#00e5ff", "#4d9dff", "#b47bff", "#ff5fd2", "#ff9f2e", "#ffe14d", "#e6ece8"];

function levelColor(level) {
  return level > 0 ? LEVEL_COLORS[(level - 1) % LEVEL_COLORS.length] : "#a3a9a6";
}

function toned(node, level) {
  node.style.setProperty("--tone", levelColor(level));
  return node;
}

function levelRow(entry) {
  const value = T("{0} von {1} Punkten", [entry.points, entry.next]);
  const share = Math.min(1, (entry.points - entry.floor) / Math.max(1, entry.next - entry.floor));
  const step = `${T("Stufe {0}", [entry.level])} · ${entry.title}`;
  return toned(h("li", { class: "level-entry" },
    h("div", { class: "bar-label" },
      h("span", {}, entry.label, " ", h("span", { class: "level-chip" }, step)),
      h("span", { class: "muted small" }, value)),
    h("div", { class: "meter", role: "img", "aria-label": `${entry.label} · ${step}: ${value}` },
      h("div", { style: { width: `${Math.round(share * 100)}%` } }))), entry.level);
}

function milestonesCard() {
  const { earned, levels = [], total = 0 } = data.achievements;
  const badges = earned.filter((entry) => !entry.level);
  return h("section", { class: "card stack" },
    h("div", { class: "row tight milestone-head" }, logoMark(36, 100, "happy"),
      h("h2", { class: "grow" }, T("Deine Stufen")),
      toned(h("span", { class: "level-total" }, T("findling-Stufe {0}", [total])), total)),
    h("ul", { class: "bars levels" }, levels.map(levelRow)),
    h("p", { class: "muted small" }, T("Punkte gibt es nicht nur fürs Erfassen, sondern genauso fürs Umräumen, Zusammenlegen, Aussortieren, Pflegen, Reparieren, Warten, Wiederfinden und Verleihen. Jede Stufe braucht etwas mehr als die vorige, ein Ende gibt es nicht.")),
    badges.length ? [h("h3", { class: "small" }, T("Abzeichen")), h("ul", { class: "milestones" }, badges.map((entry) =>
      h("li", { title: formatDate(entry.at) }, icon("check"), entry.title)))] : h("p", { class: "muted small" }, T("Das erste Abzeichen kommt mit dem ersten bestätigten Platz.")));
}

let statFocus = null; // Welche Kennzahl gerade aufgeklappt ist.
let roomMetric = "surveyed"; // Erfassung je Raum: bestätigte Plätze oder Einträge.
let fillFocus = null; // Welcher Füllstand gerade aufgeklappt ist.
let weekFocus = null; // Welche Woche gerade ausgewählt ist.
const FILL_COLORS = { voll: "#3fcf2a", ok: "#4f8f45", wenig: "#d9a21f", leer: "#e0574b" };

function statTile(value, label, key, focus) {
  const tile = h("button", {
    type: "button",
    class: "stat",
    "aria-pressed": String(statFocus === key),
    "aria-expanded": String(statFocus === key),
    onclick: () => {
      statFocus = statFocus === key ? null : key;
      showStatFocus(statFocus, focus, [...tile.parentElement.children]);
    },
  }, h("strong", {}, String(value)), h("span", { class: "muted small" }, label));
  tile.dataset.key = key;
  return tile;
}

function itemLink(item) {
  const place = placeOf(item);
  return h("li", {}, h("a", { href: `#/p/${place.code}` },
    h("span", { class: "grow" }, item.name, " ", fillChip(item.fill, item)),
    h("span", { class: "muted small" }, `${placeName(place)} · ${place.code}`)));
}

// Klappt unter den Kennzahlen auf, was hinter einer Zahl steckt.
function showStatFocus(key, focus, tiles) {
  for (const tile of tiles) {
    tile.setAttribute("aria-pressed", String(tile.dataset.key === key));
    tile.setAttribute("aria-expanded", String(tile.dataset.key === key));
  }
  if (!key) {
    focus.replaceChildren();
    return;
  }
  let title;
  let body;
  if (key === "items") {
    const newest = [...data.items].sort((a, b) => b.created - a.created).slice(0, 8);
    title = T("Zuletzt erfasst");
    body = newest.length ? h("ul", { class: "focus-list" }, newest.map(itemLink)) : h("p", { class: "muted small" }, T("Noch keine Einträge."));
  } else if (key === "places") {
    const open = data.places.filter((place) => !place.surveyed);
    title = open.length ? T("{0} noch offen", [plural(open.length, T("Platz"), T("Plätze"))]) : T("Alle Plätze sind bestätigt");
    body = open.length ? h("ul", { class: "focus-list" }, open.slice(0, 12).map((place) => h("li", {},
      h("a", { href: `#/p/${place.code}` }, h("span", { class: "grow" }, placeName(place)), h("span", { class: "muted small" }, placePath(place)))))) : null;
  } else if (key === "rooms") {
    title = T("Räume");
    body = h("ul", { class: "focus-list" }, data.rooms.map((room) => {
      const places = data.places.filter((place) => mapOf(place).room_id === room.id);
      return h("li", {}, h("a", { href: roomHref(room) },
        h("span", { class: "grow" }, room.name),
        h("span", { class: "muted small" }, T("{0} von {1}", [places.filter((place) => place.surveyed).length, plural(places.length, T("Platz"), T("Plätzen"))]))));
    }));
  } else {
    const low = data.items.filter(runsLow);
    title = low.length ? T("Geht zur Neige") : T("Nichts zum Nachkaufen");
    body = low.length ? [h("ul", { class: "focus-list" }, low.map(itemLink)), h("a", { class: "button compact", href: "#/teilen" }, T("Zur Mitbringliste"))] : null;
  }
  focus.replaceChildren(h("section", { class: "card stack focus-card" },
    h("div", { class: "section-head" }, h("h2", {}, title),
      h("button", { type: "button", class: "linklike small", onclick: () => { statFocus = null; showStatFocus(null, focus, tiles); } }, T("Schließen"))),
    body));
}

// Ein Hinweis für das Diagramm unter dem Finger oder Zeiger. Der Wert steht vorne, kräftig.
function chartTip(card) {
  const tip = h("div", { class: "chart-tip", role: "status", hidden: true });
  card.append(tip);
  return {
    show(target, value, label) {
      tip.replaceChildren(h("strong", {}, value), h("span", {}, label));
      tip.hidden = false;
      const box = card.getBoundingClientRect();
      const mark = target.getBoundingClientRect();
      const left = Math.min(Math.max(mark.left - box.left + mark.width / 2, 70), box.width - 70);
      tip.style.left = `${left}px`;
      tip.style.top = `${mark.top - box.top - 8}px`;
    },
    hide() { tip.hidden = true; },
  };
}

function barRow(label, value, share) {
  return h("li", {},
    h("div", { class: "bar-label" }, h("span", {}, label), h("span", { class: "muted small" }, value)),
    h("div", { class: "meter", role: "img", "aria-label": `${label}: ${value}` },
      h("div", { style: { width: `${Math.round(share * 100)}%` } })));
}

function roomBars(report) {
  const card = h("section", { class: "card chart-card" });
  const draw = () => {
    const most = Math.max(1, ...report.rooms.map((room) => room.items));
    const rows = report.rooms.map((room) => {
      const room_ = data.rooms.find((candidate) => candidate.id === room.id);
      const share = roomMetric === "surveyed" ? (room.places ? room.surveyed / room.places : 0) : room.items / most;
      const value = roomMetric === "surveyed"
        ? T("{0} von {1}", [room.surveyed, plural(room.places, T("Platz"), T("Plätzen"))])
        : plural(room.items, T("Eintrag"), T("Einträge"));
      return h("li", {}, h("a", { class: "bar-link", href: room_ ? roomHref(room_) : "#/" },
        h("div", { class: "bar-label" },
          h("span", {}, data.sites.length > 1 ? `${room.name} (${room.site})` : room.name),
          h("span", { class: "muted small" }, value)),
        h("div", { class: "meter", role: "img", "aria-label": `${room.name}: ${value}` },
          h("div", { style: { width: `${Math.round(share * 100)}%` } }))));
    });
    card.replaceChildren(
      h("div", { class: "section-head" }, h("h2", {}, T("Je Raum")),
        h("div", { class: "segments small-segments", role: "group", "aria-label": T("Was die Balken zeigen") },
          [["surveyed", T("Erfasst")], ["items", T("Einträge")]].map(([key, text]) => h("button", {
            type: "button",
            "aria-pressed": String(roomMetric === key),
            onclick: () => { roomMetric = key; draw(); },
          }, text)))),
      h("ul", { class: "bars" }, rows),
      h("p", { class: "muted small" }, roomMetric === "surveyed" ? T("Anteil der bestätigten Plätze. Tipp auf einen Raum, um ihn zu öffnen.") : T("Einträge im Vergleich zum vollsten Raum. Tipp auf einen Raum, um ihn zu öffnen.")));
  };
  draw();
  return card;
}

function fillBars(report) {
  const total = Object.values(report.fill).reduce((sum, count) => sum + count, 0);
  if (!total) return null;
  const card = h("section", { class: "card chart-card" });
  const tip = () => card.querySelector(".chart-tip") ? null : null;
  const draw = () => {
    const levels = FILL_LEVELS.filter((level) => report.fill[level]);
    const tooltip = { current: null };
    const segments = levels.map((level) => {
      const count = report.fill[level] || 0;
      const segment = h("button", {
        type: "button",
        class: "fill-segment",
        "aria-pressed": String(fillFocus === level),
        "aria-label": `${fillLabel(level)}: ${plural(count, T("Eintrag"), T("Einträge"))}`,
        style: { flexGrow: String(count), background: FILL_COLORS[level] },
        onclick: () => { fillFocus = fillFocus === level ? null : level; draw(); },
        onpointerenter: (event) => tooltip.current?.show(event.currentTarget, plural(count, T("Eintrag"), T("Einträge")), `${fillLabel(level)}, ${Math.round((count / total) * 100)} %`),
        onfocus: (event) => tooltip.current?.show(event.currentTarget, plural(count, T("Eintrag"), T("Einträge")), `${fillLabel(level)}, ${Math.round((count / total) * 100)} %`),
        onpointerleave: () => tooltip.current?.hide(),
        onblur: () => tooltip.current?.hide(),
      });
      return segment;
    });
    const legend = h("div", { class: "chart-legend" }, levels.map((level) => h("button", {
      type: "button",
      class: "legend-key",
      "aria-pressed": String(fillFocus === level),
      onclick: () => { fillFocus = fillFocus === level ? null : level; draw(); },
    }, h("i", { style: { background: FILL_COLORS[level] } }), `${fillLabel(level)} `, h("strong", {}, String(report.fill[level] || 0)))));
    const chosen = fillFocus ? data.items.filter((item) => !isDevice(item) && item.fill === fillFocus) : [];
    card.replaceChildren(
      h("h2", {}, T("Füllstand")),
      h("div", { class: "fill-stack", role: "group", "aria-label": T("Füllstand aller Einträge") }, segments),
      legend,
      fillFocus ? h("div", { class: "stack" },
        h("p", { class: "small" }, T("{0} mit Füllstand „{1}“", [plural(chosen.length, T("Eintrag"), T("Einträge")), fillLabel(fillFocus)])),
        h("ul", { class: "focus-list" }, chosen.slice(0, 20).map(itemLink)),
        chosen.length > 20 ? h("p", { class: "muted small" }, T("und {0} weitere", [chosen.length - 20])) : null) : h("p", { class: "muted small" }, T("Tipp auf eine Farbe, um die Einträge zu sehen.")));
    tooltip.current = chartTip(card);
  };
  draw();
  return card;
}

// Wie viel pro Woche erfasst wurde, die letzten acht Wochen.
function isoWeek(date) {
  const day = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const weekday = day.getUTCDay() || 7;
  day.setUTCDate(day.getUTCDate() + 4 - weekday);
  const yearStart = new Date(Date.UTC(day.getUTCFullYear(), 0, 1));
  return Math.ceil(((day - yearStart) / 86400000 + 1) / 7);
}

function weekBars() {
  if (!data.items.length) return null;
  const now = new Date();
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - ((now.getDay() + 6) % 7));
  const weeks = [];
  for (let back = 7; back >= 0; back -= 1) {
    const start = new Date(monday);
    start.setDate(monday.getDate() - back * 7);
    const end = new Date(start);
    end.setDate(start.getDate() + 7);
    const count = data.items.filter((item) => item.created * 1000 >= start && item.created * 1000 < end).length;
    weeks.push({ week: isoWeek(start), start, count, current: back === 0 });
  }
  const most = Math.max(1, ...weeks.map((week) => week.count));
  const card = h("section", { class: "card chart-card" });
  const tooltip = { current: null };
  const draw = () => {
    const chosen = weeks.find((week) => week.week === weekFocus) || null;
    const columns = weeks.map((week) => {
      const label = week.current ? T("diese Woche") : T("KW {0}", [week.week]);
      const value = plural(week.count, T("neuer Eintrag"), T("neue Einträge"));
      return h("button", {
        type: "button",
        class: "week-column",
        "aria-pressed": String(weekFocus === week.week),
        "aria-label": `${label}: ${value}`,
        onclick: () => { weekFocus = weekFocus === week.week ? null : week.week; draw(); },
        onpointerenter: (event) => tooltip.current?.show(event.currentTarget.querySelector(".week-bar") || event.currentTarget, value, label),
        onfocus: (event) => tooltip.current?.show(event.currentTarget.querySelector(".week-bar") || event.currentTarget, value, label),
        onpointerleave: () => tooltip.current?.hide(),
        onblur: () => tooltip.current?.hide(),
      },
      h("span", { class: "week-value" }, week.count && (week.current || weekFocus === week.week || week.count === most) ? String(week.count) : ""),
      h("span", { class: "week-track" }, h("span", { class: "week-bar", style: { height: `${week.count ? Math.max(4, Math.round((week.count / most) * 100)) : 0}%` } })),
      h("span", { class: "week-name" }, week.current ? T("jetzt") : String(week.week)));
    });
    card.replaceChildren(
      h("h2", {}, T("Erfasst pro Woche")),
      h("div", { class: "week-chart", role: "group", "aria-label": T("Neue Einträge der letzten acht Wochen") }, columns),
      h("p", { class: "muted small" }, chosen
        ? `${chosen.current ? T("Diese Woche") : T("KW {0}", [chosen.week])}: ${plural(chosen.count, T("neuer Eintrag"), T("neue Einträge"))}.`
        : T("Insgesamt {0} in acht Wochen. Tipp auf eine Woche.", [plural(weeks.reduce((sum, week) => sum + week.count, 0), T("neuer Eintrag"), T("neue Einträge"))])));
    tooltip.current = chartTip(card);
  };
  draw();
  return card;
}

function usageCard(report) {
  const { search } = report;
  const hits = search.searches ? Math.round(((search.searches - search.misses) / search.searches) * 100) : null;
  return h("section", { class: "card stack" },
    h("h2", {}, T("Nutzung")),
    h("p", {}, search.searches
      ? T("{0}, davon etwa {1} % mit Treffer. {2}-mal gefunden, {3}-mal nicht da.", [plural(search.searches, T("Suche"), T("Suchen")), hits, search.found, search.missing])
      : T("Noch keine Suchen. Die Zahlen kommen mit der Nutzung.")),
    report.top_items.length ? h("ul", { class: "bars" }, report.top_items.map((item) =>
      h("li", {}, h("div", { class: "bar-label" },
        h("a", { href: `#/p/${item.code}` }, item.name),
        h("span", { class: "muted small" }, T("{0}-mal gefunden", [item.finds])))))) : null);
}

function aiCard(report) {
  const { ai } = report;
  return h("section", { class: "card stack" },
    h("h2", {}, T("KI-Nutzung")),
    h("p", {}, T("{0} per API, {1} per Chat, {2} per API.", [plural(ai.recognitions, T("Erkennung"), T("Erkennungen")), ai.chat_answers, plural(ai.analyses, T("Analyse"), T("Analysen"))])),
    h("p", { class: "muted small" }, T("Kosten laut Listenpreis: ungefähr {0} US-Dollar. Verbindlich ist die Abrechnung bei Anthropic.", [ai.cost_usd.toLocaleString(LOCALE, { minimumFractionDigits: 2 })])));
}

function placeSelect(placeIds) {
  const places = placeIds ? data.places.filter((place) => placeIds.includes(place.id)) : data.places;
  return h("select", { "aria-label": T("Platz wählen") }, places.map((place) => h("option", { value: place.id }, `${placePath(place)} (${place.code})`)));
}

function recommendationCard(rec) {
  return h("section", { class: "card stack rec" },
    h("strong", {}, rec.title),
    h("p", { class: "muted small" }, rec.why),
    recommendationAction(rec),
    h("button", {
      type: "button",
      class: "linklike small",
      onclick: () => act(() => api("POST", "api/report/dismiss", { id: rec.id })),
    }, T("Ausblenden")));
}

function moveControl(itemIds, placeIds, buttonText) {
  const select = placeSelect(placeIds);
  return h("div", { class: "stack tight-stack" }, select,
    h("button", {
      type: "button",
      class: "compact primary",
      onclick: () => {
        const place = data.places.find((candidate) => candidate.id === select.value);
        if (confirm(T("Wirklich nach {0} verlegen? Lege die Dinge dort hin, die App ändert nur den Eintrag.", [place.code]))) {
          act(() => api("POST", "api/items/move", { item_ids: itemIds, place_id: select.value }), () => { toast(T("Geändert")); render(); });
        }
      },
    }, buttonText));
}

function recommendationAction(rec) {
  const open = (code, text) => h("a", { class: "button compact primary", href: `#/p/${code}` }, text);
  switch (rec.kind) {
    case "continue":
      return h("div", { class: "stack tight-stack" }, h("div", { class: "small" }, rec.where), open(rec.code, T("Weiter erfassen")));
    case "stale":
      return h("div", { class: "stack tight-stack" }, h("div", { class: "small" }, rec.where), open(rec.code, T("Stichprobe prüfen")));
    case "missing":
      return h("div", { class: "stack tight-stack" }, h("div", { class: "small" }, rec.item.where), open(rec.item.code, T("Platz öffnen")));
    case "duplicate":
      return h("div", { class: "stack tight-stack" },
        h("ul", { class: "small plain" }, rec.items.map((item) => h("li", {}, item.where))),
        moveControl(rec.items.map((item) => item.id), rec.items.map((item) => data.items.find((i) => i.id === item.id).place_id), T("Hier zusammenlegen")));
    case "frequent":
      return h("div", { class: "stack tight-stack" }, h("div", { class: "small" }, rec.item.where), moveControl([rec.item.id], null, T("Dorthin verlegen")));
    case "failed": {
      const select = h("select", { "aria-label": T("Eintrag wählen") }, data.items.map((item) => h("option", { value: item.id }, item.name)));
      if (!data.items.length) return null;
      return h("div", { class: "stack tight-stack" }, select,
        h("button", {
          type: "button",
          class: "compact primary",
          onclick: () => act(() => api("POST", `api/items/${select.value}/word`, { word: rec.word }), () => { toast(T("Suchwort gespeichert")); render(); }),
        }, T("Als Suchwort speichern")));
    }
    case "shopping":
      return h("div", { class: "stack tight-stack" },
        h("ul", { class: "small plain" }, rec.items.map((item) => h("li", {}, `${item.name} (${fillLabel(item.fill)})`))),
        h("button", {
          type: "button",
          class: "compact primary",
          onclick: async () => {
            const copied = await copyText(rec.items.map((item) => `${item.name} (${fillLabel(item.fill)})`).join("\n"));
            toast(copied ? T("Einkaufsliste kopiert") : T("Kopieren hat nicht geklappt"));
          },
        }, T("Einkaufsliste kopieren")));
    case "away":
      return h("ul", { class: "plain small" }, rec.items.map((item) => h("li", { class: "away-row" },
        h("a", { href: `#/p/${item.code}` }, `${item.name}: ${item.away}`),
        h("button", {
          type: "button",
          class: "compact",
          onclick: () => act(() => api("PATCH", `api/items/${item.id}`, { away: "" })),
        }, T("Ist zurück")))));
    case "overfull":
      return h("a", { class: "button compact primary", href: `#/karte/${rec.map_id}` }, T("Schrank öffnen"));
    case "unplaced":
      return h("a", { class: "button compact primary", href: `#/raum/${rec.room_id}` }, T("Raumplan öffnen"));
    default:
      return null;
  }
}

function analysisCard(report) {
  const auto = automaticRecognition();
  const cents = Math.max(1, Math.round(report.analysis_estimate_usd * 100));
  return h("section", { class: "card stack" },
    h("h2", {}, T("Mit KI weiterdenken")),
    h("p", { class: "muted small" },
      T("Die KI sucht im Bestand nach Verbesserungen und schlägt konkrete Änderungen vor. Dafür gehen Namen, Notizen, Plätze und Suchwörter raus, aber keine Fotos. Nichts passiert ohne deinen Tipp, und jede Änderung bestätigst du einzeln.")),
    h("div", { class: "row" },
      auto ? h("button", {
        type: "button",
        class: "primary",
        disabled: analysisBusy,
        onclick: async () => {
          analysisBusy = true;
          render();
          try {
            await api("POST", "api/analysis", {});
          } catch (error) {
            if (error.message !== "PIN erforderlich") toast(error.message);
          }
          analysisBusy = false;
          await reload().catch(() => {});
          render();
        },
      }, icon("spark"), analysisBusy ? T("Einen Moment ...") : T("Per API analysieren (etwa {0} US-Cent)", [cents])) : null,
      h("button", {
        type: "button",
        class: auto ? "" : "primary",
        "aria-expanded": String(analysisChatOpen),
        onclick: () => { analysisChatOpen = !analysisChatOpen; render(); },
      }, T("Kostenlos per Chat"))),
    !auto ? h("p", { class: "muted small" }, T("Per API geht es mit einem Schlüssel: "), h("a", { href: "#/daten" }, T("Hier einrichten")), ".") : null,
    analysisChatOpen ? h("div", { class: "chat-panel" }, handoverSteps({
      getPrompt: () => report.analysis_prompt,
      draftKey: "analysis",
      retryPrompt: report.analysis_retry,
      middleTitle: T("Im Chat den Auftrag einfügen"),
      submit: async (answer) => {
        await api("POST", "api/analysis/chat-answer", { answer });
        delete chatAnswers.analysis;
        analysisChatOpen = false;
      },
    })) : null,
    report.analysis ? analysisResults(report.analysis) : null);
}

function analysisResults(analysis) {
  return h("div", { class: "stack analysis" },
    h("div", { class: "section-head" },
      h("strong", {}, T("Letzte Analyse")),
      h("span", { class: "muted small" }, `${formatDate(analysis.created)}, ${analysis.source === "api" ? T("per API") : T("per Chat")}`)),
    analysis.recommendations.length ? null : h("p", { class: "muted" }, T("Die KI hat nichts vorgeschlagen.")),
    analysis.recommendations.map((rec) => h("div", { class: `rec stack tight-stack${rec.status ? " settled" : ""}` },
      h("strong", {}, rec.title),
      rec.why ? h("p", { class: "muted small" }, rec.why) : null,
      rec.status ? h("span", { class: "small" }, rec.status === "applied" ? T("Übernommen") : T("Verworfen")) : h("div", { class: "row tight" },
        rec.action_text ? h("button", {
          type: "button",
          class: "compact primary",
          onclick: () => {
            if (confirm(`${rec.action_text}?`)) {
              act(() => api("POST", `api/analysis/${rec.index}/apply`, {}), () => { toast(T("Geändert")); render(); });
            }
          },
        }, rec.action_text) : null,
        h("button", {
          type: "button",
          class: "compact quiet",
          onclick: () => act(() => api("POST", `api/analysis/${rec.index}/dismiss`, {})),
        }, rec.action_text ? T("Verwerfen") : T("Erledigt"))))));
}

// Ansicht: Papierkorb

const TRASH_KINDS = { site: T("Standort"), room: T("Raum"), map: T("Schrank"), place: T("Platz"), item: T("Eintrag"), photo: T("Foto"), document: T("Dokument") };

async function viewTrash() {
  const request = ++reportRequest;
  let trash;
  try {
    trash = await api("GET", "api/trash");
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
    return;
  }
  if (request !== reportRequest || !location.hash.startsWith("#/papierkorb")) return;
  app.replaceChildren(...shell(
    backLink("#/", T("Zurück")),
    h("h1", {}, T("Papierkorb")),
    h("p", { class: "muted" }, T("Gelöschtes bleibt {0} Tage hier und wird danach automatisch endgültig gelöscht.", [trash.days])),
    trash.entries.length ? trash.entries.map(trashCard) : h("p", { class: "notice" }, T("Der Papierkorb ist leer.")),
    trash.entries.length ? h("button", {
      type: "button",
      class: "danger trash-empty",
      onclick: () => {
        if (confirm(T("{0} endgültig löschen? Das lässt sich nicht rückgängig machen.", [plural(trash.entries.length, T("Eintrag"), T("Einträge"))]))) {
          act(() => api("DELETE", "api/trash"), () => { toast(T("Papierkorb geleert")); render(); });
        }
      },
    }, T("Papierkorb leeren")) : null));
}

function trashCounts(entry) {
  const { rooms, maps, places, items, photos, documents } = entry.counts;
  const parts = [];
  if (entry.kind === "site" && rooms) parts.push(plural(rooms, T("Raum"), T("Räume")));
  if (["site", "room"].includes(entry.kind) && maps) parts.push(plural(maps, T("Schrank"), T("Schränke")));
  if (["site", "room", "map"].includes(entry.kind) && places) parts.push(plural(places, T("Platz"), T("Plätze")));
  if (entry.kind !== "item" && items) parts.push(plural(items, T("Eintrag"), T("Einträge")));
  if (entry.kind !== "photo" && photos) parts.push(plural(photos, T("Foto"), T("Fotos")));
  if (entry.kind !== "document" && documents) parts.push(plural(documents, T("Dokument"), T("Dokumente")));
  return parts.join(" · ");
}

function trashParentOptions(table) {
  if (table === "sites") return data.sites.map((site) => [site.id, site.name]);
  if (table === "rooms") return data.rooms.map((room) => [room.id, room.name]);
  if (table === "maps") return data.maps.map((map) => [map.id, `${roomOf(map).name} › ${map.name}`]);
  return data.places.map((place) => [place.id, placePath(place)]);
}

function trashCard(entry) {
  const options = entry.parent_missing ? trashParentOptions(entry.parent_table) : [];
  const target = options.length
    ? h("select", { "aria-label": T("Neuer Ort") }, options.map(([id, name]) => h("option", { value: id }, name)))
    : null;
  const blocked = entry.parent_missing && !options.length;
  return h("section", { class: "card stack rec" },
    h("div", { class: "section-head" },
      h("strong", {}, entry.label),
      h("span", { class: "status" }, TRASH_KINDS[entry.kind])),
    entry.detail ? h("p", { class: "muted small" }, T("Aus: {0}", [entry.detail])) : null,
    trashCounts(entry) ? h("p", { class: "small" }, trashCounts(entry)) : null,
    h("p", { class: "muted small" }, T("Gelöscht am {0}, noch {1}", [formatDate(entry.created), plural(entry.days_left, T("Tag"), T("Tage"))])),
    entry.parent_missing ? h("p", { class: "small" }, blocked
      ? T("Den ursprünglichen Ort gibt es nicht mehr, und es gibt noch keinen anderen. Stelle zuerst den Ort wieder her oder leg einen neuen an.")
      : T("Den ursprünglichen Ort gibt es nicht mehr. Wähle, wohin es zurückkommt:")) : null,
    target,
    h("div", { class: "row tight" },
      h("button", {
        type: "button",
        class: "compact primary",
        disabled: blocked,
        onclick: () => {
          let result;
          act(async () => {
            result = await api("POST", `api/trash/${entry.id}/restore`, target ? { parent_id: target.value } : {});
          }, () => {
            toast(T("„{0}“ wiederhergestellt", [entry.label]));
            if (result.href !== "#/") location.hash = result.href;
            else render();
          });
        },
      }, T("Wiederherstellen")),
      h("button", {
        type: "button",
        class: "compact quiet",
        onclick: () => {
          if (confirm(T("„{0}“ endgültig löschen? Das lässt sich nicht rückgängig machen.", [entry.label]))) {
            act(() => api("DELETE", `api/trash/${entry.id}`), () => { toast(T("Endgültig gelöscht")); render(); });
          }
        },
      }, T("Endgültig löschen"))));
}

// Ansicht: Einstellungen

function viewSettings() {
  const cover = coverage();
  const counts = data.event_counts;
  const baseInput = h("input", { type: "url", value: baseUrl(), "aria-label": T("Adresse für QR-Codes") });
  app.replaceChildren(...shell(
    backLink("#/", T("Zurück")),
    h("h1", {}, T("Einstellungen")),
    recognitionSection(),
    settingsLink("#/unterwegs", "camera", T("Für unterwegs einrichten"), window.isSecureContext && location.protocol === "https:" ? T("Sichere Verbindung aktiv") : T("Bestand im Baumarkt ansehen, auch ohne WLAN")),
    settingsLink("#/sicherungen", "check", T("Sicherungen"), T("Automatisch, Takt und Speicherort einstellbar")),
    settingsLink("#/teilen", "share", T("Teilen und Mitbringliste"), T("Für eine zweite Person")),
    settingsLink("#/bearbeiten", "check", T("Schnellbearbeitung"), T("Viele Einträge auf einmal ändern, verschieben oder löschen")),
    settingsLink("#/import", "plus", T("Massenimport"), T("Hunderte Gegenstände per Tabelle erfassen, mit Vorlage und Anleitung")),
    settingsLink("#/blick", "blick", T("Im Blick"), T("Verliehenes, Wartung und Garantie, dazu alle Steckbriefe")),
    settingsLink("#/dashboard", "plan", T("Dashboard anpassen"), T("Bereiche und Räume auf der Startseite ein- oder ausblenden")),
    h("section", { class: "card stack" },
      h("h2", {}, T("Fotos im findling-Look")),
      h("p", { class: "muted small" }, T("Eine einheitliche Farbe über allen Schrank- und Inhaltsfotos. Die Originale bleiben unverändert, ein Tipp auf ein Foto zeigt sie.")),
      h("div", { class: "look-choices", role: "group", "aria-label": T("Farbe der Überlagerung") }, PHOTO_LOOKS.map(([key, name, color]) => h("button", {
        type: "button",
        class: "look-choice",
        "aria-pressed": String(prefs().photo_look === key),
        onclick: () => savePreferences({ photo_look: key }),
      }, h("i", { class: `look-swatch${color ? "" : " none"}`, style: color ? { background: color } : undefined }), name)))),
    h("section", { class: "card stack" },
      h("h2", {}, T("Druckmappe")),
      h("p", { class: "muted small" }, T("Etiketten mit QR-Code zum Ausschneiden und das ganze Inventar, jeweils als PDF zum Ausdrucken oder Ablegen.")),
      h("div", { class: "row" },
        h("button", { type: "button", class: "primary", onclick: () => downloadPrintPdf("labels") }, icon("printer"), T("Etiketten drucken")),
        h("button", { type: "button", class: "primary", onclick: () => downloadPrintPdf("inventory") }, icon("printer"), T("Inventar drucken")))),
    h("a", { class: "card result-link", href: "#/papierkorb" },
      h("span", { class: "number" }, icon("trash")),
      h("span", { class: "grow" },
        h("strong", {}, T("Papierkorb")),
        h("span", { class: "muted small block" }, data.trash_count ? T("{0}, bleiben 30 Tage", [plural(data.trash_count, T("Eintrag"), T("Einträge"))]) : T("Leer. Gelöschtes bleibt hier 30 Tage."))),
      icon("next")),
    h("section", { class: "card stack" },
      h("h2", {}, T("Sichern und weitergeben")),
      h("div", { class: "row" },
        h("a", { class: "button", href: "api/backup.zip" }, T("Sicherung laden")),
        h("a", { class: "button", href: "api/export.csv" }, T("Bestand als Liste"))),
      h("p", { class: "muted small" }, T("Die Sicherung enthält alle Daten, Fotos und Dokumente. Die Liste kannst du einer zweiten Person schicken."))),
    h("section", { class: "card stack" },
      h("h2", {}, T("Stand")),
      h("p", {}, T("{0} von {1} Plätzen vollständig erfasst, {2}.", [cover.done, cover.total, plural(data.items.length, T("Eintrag"), T("Einträge"))])),
      h("p", { class: "muted small" },
        T("Suchen: {0} · Gefunden: {1} · Nicht da: {2} · Erkennungen: {3} · Per Chat: {4}", [counts.search || 0, counts.found || 0, counts.missing || 0, counts.recognize || 0, counts.chat_answer || 0])),
      data.failed_searches.length ? h("div", {},
        h("strong", {}, T("Das fand die App nicht:")),
        h("ul", {}, data.failed_searches.map((row) => h("li", {}, T("{0} ({1}-mal)", [row.q, row.times])))),
        h("p", { class: "muted small" }, T("Trag diese Wörter beim passenden Eintrag unter „Auch genannt“ ein."))) : null),
    data.server.ha ? null : h("details", { class: "more" },
      h("summary", {}, T("Erweitert")),
      h("div", { class: "stack" },
        h("label", { class: "field" }, T("Adresse in den QR-Codes"), baseInput),
        h("p", { class: "muted small" },
          T("Gedruckte Etiketten behalten ihre alte Adresse. "),
          data.server.lan ? T("Die PIN steht im Startfenster und im Datenordner.") : T("Die App läuft gerade nur auf diesem Rechner.")),
        h("button", {
          type: "button",
          onclick: () => act(() => api("PATCH", "api/settings", { base_url: baseInput.value }), () => { toast(T("Gespeichert")); render(); }),
        }, T("Adresse speichern")))),
    makerLine()));
}

function settingsLink(href, iconName, title, text) {
  return h("a", { class: "card result-link", href },
    h("span", { class: "number" }, icon(iconName)),
    h("span", { class: "grow" }, h("strong", {}, title), h("span", { class: "muted small block" }, text)),
    icon("next"));
}

// Ansicht: Für unterwegs

function viewTravel() {
  const { https_base: secure, suggested_base: plain, certificate, stable_name: stable, lan } = data.server;
  const here = location.protocol === "https:";
  const installed = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  const hasWorker = Boolean(navigator.serviceWorker?.controller);
  let body;
  if (data.server.ha && !secure) {
    body = h("section", { class: "card stack" },
      h("h2", {}, T("Direktzugang ist aus")),
      h("p", { class: "muted small" }, T("Über Home Assistant ist die App bereits geschützt erreichbar. Die Kopie für unterwegs braucht zusätzlich einen eigenen Eingang im Heimnetz. Er ist bewusst aus, weil jeder offene Eingang ein Risiko ist.")),
      h("ol", { class: "steps" },
        h("li", {}, h("strong", {}, T("Konfiguration öffnen")), h("span", {}, T("Einstellungen › Apps › findling › Konfiguration."))),
        h("li", {}, h("strong", {}, T("Direktzugang einschalten")), h("span", {}, T("„Direktzugang“ an, eine PIN mit mindestens 8 Zeichen setzen."))),
        h("li", {}, h("strong", {}, T("Ports eintragen")), h("span", {}, T("Unter „Netzwerk“ bei 8787 und 8788 dieselben Zahlen eintragen und speichern."))),
        h("li", {}, h("strong", {}, T("App neu starten")), h("span", {}, T("Danach stehen hier die nächsten Schritte.")))),
      h("p", { class: "muted small" }, T("Gib diese Ports niemals im Router für das Internet frei.")));
  } else if (!lan || !secure) {
    body = h("p", { class: "notice" }, T("Starte die App mit start.command, dann steht HTTPS bereit. Dafür braucht der Mac das Programm openssl."));
  } else {
    const phoneUrl = data.server.ha ? `${plain}${certificate}` : `${plain}/#/unterwegs`;
    body = [
      here && hasWorker ? h("p", { class: "notice" }, installed
        ? T("Fertig eingerichtet. Öffne die App einmal im WLAN, dann ist die Kopie aktuell.")
        : T("Die sichere Verbindung steht, die Kopie wird gespeichert. Füge die App jetzt noch zum Home-Bildschirm hinzu.")) : null,
      here ? null : h("section", { class: "card stack" },
        h("h2", {}, T("Am Telefon öffnen")),
        h("p", { class: "muted small" }, data.server.ha
          ? T("Scanne diesen Code im WLAN mit dem Telefon. Er lädt das Zertifikat, danach folgen die Schritte unten.")
          : T("Scanne diesen Code im WLAN mit dem Telefon und folge dort den Schritten.")),
        h("div", { class: "travel-qr" }, qrSvg(phoneUrl)),
        h("p", { class: "small" }, phoneUrl)),
      h("section", { class: "card stack" },
        h("h2", {}, T("So richtest du es ein")),
        h("ol", { class: "steps" },
          h("li", {},
            h("strong", {}, T("Zertifikat laden")),
            h("a", { class: "button compact", href: `${plain}${certificate}`, target: "_blank", rel: "noopener noreferrer" }, T("Zertifikat laden")),
            h("span", {}, T("Am iPhone erscheint die Frage, ob das Profil geladen werden soll: Erlauben."))),
          h("li", {},
            h("strong", {}, T("Am Telefon installieren und vertrauen")),
            h("span", {}, T("iPhone: Einstellungen › Allgemein › VPN und Geräteverwaltung › Profil installieren. Danach Einstellungen › Allgemein › Info › Zertifikatsvertrauenseinstellungen › „findling lokal“ einschalten."))),
          h("li", {},
            h("strong", {}, T("Sichere Adresse öffnen")),
            h("a", { class: "button compact primary", href: `${secure}/#/unterwegs`, target: "_blank", rel: "noopener noreferrer" }, T("Sichere Adresse öffnen")),
            h("span", {}, T("PIN eingeben. Ab jetzt speichert das Telefon eine Kopie."))),
          h("li", {},
            h("strong", {}, T("Zum Home-Bildschirm hinzufügen")),
            h("span", {}, T("In Safari auf Teilen tippen, dann „Zum Home-Bildschirm“. So bleibt die Kopie auch erhalten, wenn du die App länger nicht öffnest."))))),
      h("section", { class: "card stack" },
        h("h2", {}, T("Gut zu wissen")),
        h("ul", { class: "plain small stacked" },
          h("li", {}, T("Unterwegs kannst du suchen und alles lesen. Ändern geht wieder im Heimnetz, denn das Original liegt auf {0}.", [hostOn()])),
          h("li", {}, T("Die Kopie hat den Stand, als du die App zuletzt im WLAN geöffnet hast. Fotos vom Inhalt sind nur dabei, wenn du sie schon einmal geöffnet hast.")),
          h("li", {}, T("Das Zertifikat gilt nur für den Namen dieser App und läuft nach gut zwei Jahren ab. Der Schlüssel, mit dem es ausgestellt wurde, ist bereits gelöscht, damit niemand damit fremde Seiten fälschen kann. Du kannst das Profil jederzeit in den Einstellungen des Telefons wieder entfernen.")),
          h("li", {}, T("Die Daten liegen dann auch auf dem Telefon. Schütze es mit einer Code-Sperre.")),
          stable ? null : h("li", {}, T("Der feste Name findling.local ist auf diesem Rechner nicht verfügbar. Die Adresse hängt deshalb am Rechnernamen.")))),
    ];
  }
  app.replaceChildren(...shell(backLink("#/daten", T("Einstellungen")), h("h1", {}, T("Für unterwegs")), body));
}

// Ansicht: Sicherungen

const INTERVAL_TEXT = { 6: T("alle 6 Stunden"), 12: T("alle 12 Stunden"), 24: T("täglich"), 168: T("wöchentlich") };

function backupSize(bytes) {
  return bytes > 1048576 ? `${(bytes / 1048576).toFixed(1).replace(".", ",")} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Sicherung als Datei einspielen, zum Beispiel beim Umzug oder auf einem neuen Server.
function backupUploadButton(label = T("Sicherung einspielen"), primary = false) {
  return h("label", { class: `button file-button${primary ? " primary" : ""}` }, label, h("input", {
    type: "file",
    accept: ".zip,application/zip",
    onchange: (event) => {
      const file = event.target.files[0];
      event.target.value = "";
      if (!file) return;
      const empty = !data.rooms.length;
      if (!empty && !confirm(T("„{0}“ einspielen? Der aktuelle Stand wird durch diese Sicherung ersetzt und vorher gesichert.", [file.name]))) return;
      toast(T("Sicherung wird übertragen ..."));
      act(() => api("POST", "api/backups/upload", undefined, file), () => { toast(T("Sicherung eingespielt")); location.hash = "#/"; render(); });
    },
  }));
}

function backupList(entries, local, source) {
  return h("ul", { class: "place-list backup-list" }, entries.map((entry) => h("li", {},
    h("div", { class: "backup-row" },
      h("span", { class: "grow" },
        h("strong", {}, formatDateTime(entry.created)),
        h("span", { class: "muted small block" }, entry.before_version
          ? T("{0}, automatisch vor Version {1}", [backupSize(entry.size), entry.before_version])
          : backupSize(entry.size))),
      local ? h("button", {
        type: "button",
        class: "compact",
        onclick: () => {
          const empty = !data.rooms.length;
          if (empty || confirm(T("Den Stand vom {0} einspielen? Der aktuelle Stand wird vorher gesichert.", [formatDateTime(entry.created)]))) {
            act(() => api("POST", `api/backups/${entry.name}/restore`, { source }), () => { toast(T("Stand eingespielt")); location.hash = "#/"; render(); });
          }
        },
      }, source === "target" ? T("Von hier einspielen") : T("Wiederherstellen")) : null))));
}

async function viewBackups() {
  const request = ++reportRequest;
  let info;
  let folders = null;
  try {
    info = await api("GET", "api/backups");
    if (info.local && info.ha) folders = (await api("GET", "api/backups/ordner")).folders;
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
    return;
  }
  if (request !== reportRequest || !location.hash.startsWith("#/sicherungen")) return;

  const interval = h("select", { "aria-label": T("Wie oft sichern") }, info.intervals.map((hours) =>
    h("option", { value: hours, selected: hours === info.interval }, INTERVAL_TEXT[hours] || T("alle {0} Stunden", [hours]))));
  const keepOptions = [];
  for (let n = info.keep_range[0]; n <= info.keep_range[1]; n += 1) keepOptions.push(n);
  const keep = h("select", { "aria-label": T("Wie viele Stände behalten") }, keepOptions.map((n) =>
    h("option", { value: n, selected: n === info.keep }, T("die letzten {0}", [n]))));
  const choices = folders ? [...new Set([...(info.target ? [info.target] : []), ...folders])] : [];
  const target = folders
    ? h("select", { "aria-label": T("Speicherort") },
      h("option", { value: "", selected: !info.target }, T("Kein Speicherort")),
      choices.map((path) => h("option", { value: path, selected: path === info.target }, path.replace(`${info.target_root}/`, ""))))
    : h("input", { type: "text", value: info.target, placeholder: "/Volumes/NAS/findling", "aria-label": T("Speicherort") });

  const status = info.last
    ? T("Letzter Stand: {0}. Nächster frühestens {1}, sobald sich etwas geändert hat.", [formatDateTime(info.last), formatDateTime(info.next)])
    : info.empty ? T("Die erste Sicherung entsteht, sobald es etwas zu sichern gibt.") : T("Die erste Sicherung entsteht in den nächsten Minuten.");

  app.replaceChildren(...shell(
    backLink("#/daten", T("Einstellungen")),
    h("h1", {}, T("Sicherungen")),
    h("section", { class: "card stack" },
      h("div", { class: "section-head" },
        h("h2", {}, T("Automatisch")),
        h("span", { class: "status on" }, INTERVAL_TEXT[info.interval] || "aktiv")),
      h("p", { class: "muted small" }, T("findling sichert {0} von selbst, Inventar und Fotos zusammen, und behält die letzten {1} Stände. Ändert sich nichts, entsteht kein neuer Stand.", [INTERVAL_TEXT[info.interval] || "", info.keep])),
      h("p", { class: "small" }, status),
      info.error ? h("p", { class: "notice" }, T("Letzte Sicherung fehlgeschlagen: {0}", [info.error])) : null,
      h("div", { class: "row" },
        h("button", {
          type: "button",
          class: "primary",
          onclick: () => act(() => api("POST", "api/backups", {}), () => { toast(T("Gesichert")); render(); }),
        }, T("Jetzt sichern")),
        h("a", { class: "button", href: "api/backup.zip" }, T("Sicherung herunterladen")),
        info.local ? backupUploadButton() : null)),
    info.local ? h("form", {
      class: "card stack backup-settings",
      onsubmit: (event) => {
        event.preventDefault();
        const body = { interval: Number(interval.value), keep: Number(keep.value), target: target.value.trim() };
        act(() => api("PATCH", "api/backups", body), () => { toast(T("Gespeichert")); render(); });
      },
    },
      h("h2", {}, T("Einstellungen")),
      h("label", { class: "field" }, T("Wie oft"), interval),
      h("label", { class: "field" }, T("Aufbewahren"), keep),
      h("label", { class: "field" }, T("Speicherort, zum Beispiel ein Netzlaufwerk"), target),
      info.ha
        ? h("p", { class: "muted small" }, T("Ein Netzlaufwerk bindest du in Home Assistant ein: Einstellungen › System › Speicher › Netzwerkspeicher hinzufügen, Verwendung „Freigabe“. Danach erscheint es hier. Dort bleiben ebenfalls die letzten Stände."))
        : h("p", { class: "muted small" }, T("Ein Ordner auf einer externen Platte, einem Netzlaufwerk oder in einem Cloud-Ordner. Dort bleiben ebenfalls die letzten Stände. So überstehen die Daten auch einen Ausfall dieses Geräts.")),
      h("button", { type: "submit" }, T("Speichern"))) : null,
    info.target ? h("section", { class: "card stack" },
      h("h2", {}, T("Am Speicherort")),
      h("p", { class: "small" }, info.target),
      info.target_error
        ? h("p", { class: "notice" }, info.target_error)
        : info.target_at ? h("p", { class: "muted small" }, T("Zuletzt abgeglichen: {0}", [formatDateTime(info.target_at)])) : null,
      info.target_backups.length ? backupList(info.target_backups, info.local, "target") : h("p", { class: "muted small" }, T("Noch keine Sicherung an diesem Ort."))) : null,
    h("h2", {}, T("Auf diesem Gerät")),
    info.backups.length ? backupList(info.backups, info.local, "local") : h("p", { class: "notice" }, T("Noch keine Sicherung. Die erste entsteht, sobald es etwas zu sichern gibt.")),
    info.ha ? h("p", { class: "muted small" }, T("Der aktuelle Datenbestand ist auch in den Sicherungen von Home Assistant enthalten.")) : null,
    !info.local ? h("p", { class: "muted small" }, T("Einstellen, Wiederherstellen und Einspielen gibt es nur am Mac selbst oder angemeldet in Home Assistant.")) : null,
    info.folder ? h("p", { class: "muted small" }, T("Ordner: {0}", [info.folder])) : null));
}

// Ansicht: Teilen

function shoppingText() {
  const low = data.items.filter(runsLow).map((item) => `- ${item.name} (${fillLabel(item.fill)})`);
  const extra = data.shopping_extra.map((name) => `- ${name}`);
  return [T("Bitte mitbringen:"), ...low, ...extra].join("\n");
}

// Besorgt: Gleich festhalten, wo die Sache hinkommt. Ein Eintrag wird dort aufgefüllt oder dorthin verlegt,
// ein freier Wunsch wird dort als neuer Eintrag erfasst. „Nur abhaken“ geht weiter ohne Platz.
let storing = null; // Der Listenpunkt, für den gerade ein Lagerplatz gewählt wird.
let lastStorePlace = null;

function shoppingKey(entry) {
  return entry.item ? `item:${entry.item.id}` : `wish:${entry.name}`;
}

function placePicker(selected) {
  const options = placesInOrder().map((place) => [place.id, `${placePath(place)} (${place.code})`]);
  const select = h("select", { "aria-label": T("Lagerplatz") }, options.map(([id, text]) => h("option", { value: id }, text)));
  if (selected && options.some(([id]) => id === selected)) select.value = selected;
  const filter = h("input", {
    type: "search",
    placeholder: T("Platz suchen, z. B. Keller oder W-R-03"),
    "aria-label": T("Platz suchen"),
    oninput: () => {
      const terms = words(filter.value);
      const visible = options.filter(([, text]) => terms.every((term) => normalize(text).includes(term)));
      select.replaceChildren(...visible.map(([id, text]) => h("option", { value: id }, text)));
    },
  });
  return { filter, select };
}

function storeForm(entry) {
  const name = entry.item ? entry.item.name : entry.name;
  const { filter, select } = placePicker(entry.item ? entry.item.place_id : lastStorePlace);
  const close = () => { storing = null; render(); };
  const store = () => {
    const placeId = select.value;
    if (!placeId) {
      toast(T("Bitte einen Platz wählen"));
      return;
    }
    const place = data.places.find((candidate) => candidate.id === placeId);
    act(async () => {
      if (entry.item) {
        if (entry.item.place_id !== placeId) await api("POST", "api/items/move", { item_ids: [entry.item.id], place_id: placeId });
        await reload();
        // Beim Verlegen kann der Eintrag mit einem gleichnamigen am Ziel zusammengelegt werden.
        const target = data.items.find((item) => item.place_id === placeId && normalize(item.name) === normalize(entry.item.name));
        if (target) await api("PATCH", `api/items/${target.id}`, { fill: "voll" });
      } else {
        const existing = data.items.find((item) => item.place_id === placeId && normalize(item.name) === normalize(entry.name));
        if (existing) await api("PATCH", `api/items/${existing.id}`, { fill: "voll" });
        else await api("POST", "api/items", { place_id: placeId, name: entry.name, fill: "voll" });
        await api("DELETE", "api/shopping", { name: entry.name });
      }
    }, () => {
      lastStorePlace = placeId;
      storing = null;
      toast(T("„{0}“ liegt jetzt an {1}", [name, placeName(place)]));
      render();
    });
  };
  const tick = () => act(() => (entry.item
    ? api("PATCH", `api/items/${entry.item.id}`, { fill: "voll" })
    : api("DELETE", "api/shopping", { name: entry.name })), () => {
    storing = null;
    toast(entry.item ? T("Füllstand auf voll gesetzt") : T("Abgehakt"));
    render();
  });
  return h("div", { class: "store-form stack tight-stack" },
    h("strong", {}, T("Wohin kommt „{0}“?", [name])),
    entry.item ? h("p", { class: "muted small" }, T("Bisher: {0}", [placePath(placeOf(entry.item))])) : null,
    filter,
    select,
    h("div", { class: "row tight" },
      h("button", { type: "button", class: "primary compact", onclick: store }, icon("check"), T("Einlagern")),
      h("button", { type: "button", class: "compact", onclick: tick }, T("Nur abhaken")),
      h("button", { type: "button", class: "compact quiet", onclick: close }, T("Abbrechen"))));
}

function shoppingEntry(entry, label) {
  const key = shoppingKey(entry);
  const open = storing === key;
  return h("li", { class: open ? "storing" : "" },
    h("div", { class: "row shopping-line" },
      label,
      open ? null : h("button", {
        type: "button",
        class: "compact",
        onclick: () => {
          if (!data.places.length) {
            act(() => (entry.item ? api("PATCH", `api/items/${entry.item.id}`, { fill: "voll" }) : api("DELETE", "api/shopping", { name: entry.name })));
            return;
          }
          storing = key;
          render();
          document.querySelector(".store-form select")?.focus();
        },
      }, T("Besorgt"))),
    open ? storeForm(entry) : null);
}

function viewShare() {
  const low = data.items.filter(runsLow);
  const extra = data.shopping_extra;
  const count = low.length + extra.length;
  const nameInput = h("input", { type: "text", placeholder: T("Was soll noch mit?"), "aria-label": T("Weiterer Wunsch") });
  app.replaceChildren(...shell(
    backLink("#/", T("Zurück")),
    h("h1", {}, T("Teilen")),
    h("section", { class: "card stack" },
      h("h2", {}, T("Mitbringliste")),
      h("p", { class: "muted small" }, T("Was als wenig oder leer markiert ist, steht von selbst darauf.")),
      count ? h("ul", { class: "shopping" },
        low.map((item) => shoppingEntry({ item }, h("span", { class: "grow" }, item.name, " ", fillChip(item.fill)))),
        extra.map((name) => shoppingEntry({ name }, h("span", { class: "grow" }, name)))) : h("p", { class: "muted" }, T("Gerade fehlt nichts.")),
      h("form", {
        class: "add-row",
        onsubmit: (event) => {
          event.preventDefault();
          if (nameInput.value.trim()) act(() => api("POST", "api/shopping", { name: nameInput.value }));
        },
      }, nameInput, h("button", { class: "primary", type: "submit", "aria-label": T("Hinzufügen") }, icon("plus"))),
      count ? h("button", {
        type: "button",
        class: "primary",
        onclick: async () => {
          const text = shoppingText();
          if (navigator.share) {
            try {
              await navigator.share({ text });
              return;
            } catch (error) {
              if (error.name === "AbortError") return;
            }
          }
          toast(await copyText(text) ? T("Liste kopiert. Füge sie in eine Nachricht ein.") : T("Kopieren hat nicht geklappt"));
        },
      }, icon("share"), T("Liste weitergeben")) : null,
      // Als PDF in einem eigenen Fenster: Auf dem iPhone öffnet sich die Vorschau, von dort lässt sie sich teilen oder drucken.
      count ? h("a", { class: "button", href: "api/mitbringliste.pdf", target: "_blank", rel: "noopener" }, icon("printer"), T("Als PDF öffnen")) : null,
      count ? h("p", { class: "muted small" }, T("Das PDF öffnet sich in einem neuen Fenster. Über Teilen kannst du es dort weiterschicken oder drucken.")) : null),
    h("section", { class: "card stack" },
      h("h2", {}, T("Bestand als Datei")),
      h("p", { class: "muted small" }, T("Eine einzelne Datei mit dem aktuellen Stand und der Mitbringliste. Schick sie zum Beispiel per Nachricht. Die andere Person braucht keine App. Im Browser kann sie darin suchen, in einer Vorschau, etwa in einer Nachrichten-App, erscheint je nach Telefon nur die Liste.")),
      h("a", { class: "button primary", href: "api/share.html" }, T("Datei herunterladen")),
      h("p", { class: "muted small" }, T("Die Datei ist nicht verschlüsselt und enthält Namen, Notizen und Plätze, aber keine Fotos. Sie zeigt den Stand von jetzt und aktualisiert sich nicht von selbst."))),
    h("section", { class: "card stack" },
      h("h2", {}, T("Bestand als Liste")),
      h("p", { class: "muted small" }, T("Für Tabellenprogramme.")),
      h("a", { class: "button", href: "api/export.csv" }, T("CSV herunterladen")))));
}

function recognitionSection() {
  const { installed, configured, can_set_key: canSetKey } = data.recognition;
  const keyInput = h("input", {
    type: "password",
    autocomplete: "off",
    placeholder: T("API-Schlüssel von console.anthropic.com"),
    "aria-label": T("API-Schlüssel"),
  });
  return h("section", { class: "card stack" },
    h("div", { class: "section-head" },
      h("h2", {}, T("Automatische Erkennung")),
      h("span", { class: `status${installed && configured ? " on" : ""}` }, installed && configured ? T("Eingerichtet") : T("Nicht eingerichtet"))),
    h("p", { class: "muted small" },
      T("Ein Foto geht nur an Anthropic (Claude), wenn du beim Foto auf „Inhalt erkennen“ tippst. Das kostet Guthaben auf deinem API-Konto. Ein schon erkanntes Foto kostet beim Ansehen nichts mehr. Der Schlüssel bleibt auf {0} und ist nicht in der Sicherung.", [hostOn()])),
    h("p", { class: "small" }, T("Bisherige Kosten laut Listenpreis: ungefähr {0} US-Dollar. Verbindlich ist die Abrechnung bei Anthropic.", [data.api_cost_usd.toLocaleString(LOCALE, { minimumFractionDigits: 2 })])),
    h("p", { class: "muted small" }, T("Ohne Schlüssel geht es kostenlos: Beim Foto „Kostenlos per Chat“ wählen und dein eigenes Claude- oder ChatGPT-Konto nutzen.")),
    !installed ? h("p", { class: "small" }, data.server.ha ? T("Das Paket für die Erkennung fehlt in dieser Version.") : T("Starte die App mit start.command, damit die Erkennung installiert wird.")) : null,
    canSetKey ? h("form", {
      class: "add-row",
      onsubmit: (event) => {
        event.preventDefault();
        act(() => api("POST", "api/recognition-key", { key: keyInput.value }), () => { toast(T("Schlüssel gespeichert")); render(); });
      },
    }, keyInput, h("button", { type: "submit" }, T("Speichern"))) :
      h("p", { class: "muted small" }, data.server.ha
        ? T("Den Schlüssel trägst du in Home Assistant unter Einstellungen › Apps › findling › Konfiguration ein.")
        : T("Den Schlüssel trägst du am Mac selbst ein, damit er nicht durchs WLAN geht.")),
    canSetKey && configured ? h("button", {
      type: "button",
      class: "linklike small",
      onclick: () => { if (confirm(T("Gespeicherten Schlüssel löschen?"))) act(() => api("DELETE", "api/recognition-key")); },
    }, T("Schlüssel löschen")) : null);
}

// Ansicht: Etikett scannen. Live mit der Kamera, wo der Browser es erlaubt, sonst per Foto oder Code.

let scanStream = null;
let scanTimer = null;

function stopScan() {
  clearTimeout(scanTimer);
  scanTimer = null;
  if (scanStream) {
    scanStream.getTracks().forEach((track) => track.stop());
    scanStream = null;
  }
}

// Der QR-Leser (jsQR) wird erst geladen, wenn er gebraucht wird.
function loadQrReader() {
  if (window.jsQR) return Promise.resolve(window.jsQR);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "vendor/jsQR.js";
    script.onload = () => (window.jsQR ? resolve(window.jsQR) : reject(new Error(T("Der QR-Leser ließ sich nicht laden"))));
    script.onerror = () => reject(new Error(T("Der QR-Leser ließ sich nicht laden")));
    document.head.append(script);
  });
}

// Aus dem Inhalt eines Etiketts wird nur die Platznummer gelesen. Fremde Adressen werden nie geöffnet.
function placeCodeFromQr(text) {
  const value = String(text || "").trim();
  const match = value.match(/(?:^|[/#])p\/([A-Za-z0-9]{1,5}-[A-Za-z0-9]{1,5}-\d{1,4})\/?(?:[?#].*)?$/)
    || value.match(/^([A-Za-z0-9]{1,5}-[A-Za-z0-9]{1,5}-\d{1,4})$/);
  if (!match) return null;
  const [room, map, number] = match[1].toUpperCase().split("-");
  return `${room}-${map}-${number.padStart(2, "0")}`;
}

function openScannedPlace(text, status) {
  const code = placeCodeFromQr(text);
  if (!code) {
    status.textContent = T("Das ist kein Etikett von findling.");
    return false;
  }
  if (!data.places.some((place) => place.code === code)) {
    status.textContent = T("{0} gibt es hier nicht (mehr). Vielleicht liegt der Platz im Papierkorb.", [code]);
    return false;
  }
  stopScan();
  if (navigator.vibrate) navigator.vibrate(40);
  location.hash = `#/p/${code}`;
  return true;
}

// Liest einen QR-Code aus dem Bild. share < 1 nimmt nur die Bildmitte, falls mehrere Etiketten im Bild sind.
function readQr(jsQR, source, size, canvas, attempts, share = 1) {
  const fullW = source.videoWidth || source.width;
  const fullH = source.videoHeight || source.height;
  const cropW = fullW * share;
  const cropH = fullH * share;
  const scale = Math.min(1, size / Math.max(cropW, cropH));
  const w = Math.max(1, Math.round(cropW * scale));
  const hgt = Math.max(1, Math.round(cropH * scale));
  canvas.width = w;
  canvas.height = hgt;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.drawImage(source, (fullW - cropW) / 2, (fullH - cropH) / 2, cropW, cropH, 0, 0, w, hgt);
  const found = jsQR(context.getImageData(0, 0, w, hgt).data, w, hgt, { inversionAttempts: attempts });
  return found ? found.data : null;
}

async function decodeQrPhoto(file) {
  const jsQR = await loadQrReader();
  if (typeof createImageBitmap !== "function") throw new Error(T("Dieser Browser kann das Foto nicht lesen. Tipp den Code unten ein."));
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement("canvas");
  try {
    for (const [size, share] of [[1200, 1], [800, 1], [1800, 1], [1000, 0.6], [800, 0.4]]) {
      const text = readQr(jsQR, bitmap, size, canvas, "attemptBoth", share);
      if (text) return text;
    }
    return null;
  } finally {
    if (bitmap.close) bitmap.close();
  }
}

async function startLiveScan(video, status) {
  if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return false;
  try {
    scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
  } catch {
    return false;
  }
  if (!location.hash.startsWith("#/scan")) {
    stopScan();
    return false;
  }
  video.srcObject = scanStream;
  await video.play().catch(() => {});
  const jsQR = await loadQrReader();
  const canvas = document.createElement("canvas");
  const tick = () => {
    if (!scanStream) return;
    if (video.readyState >= 2 && video.videoWidth) {
      const text = readQr(jsQR, video, 640, canvas, "dontInvert");
      if (text && openScannedPlace(text, status)) return;
    }
    scanTimer = setTimeout(tick, 160);
  };
  tick();
  return true;
}

function viewScan() {
  const status = h("p", { class: "small scan-status", role: "status" });
  const video = h("video", { playsinline: true, muted: true, autoplay: true, "aria-label": T("Kamerabild") });
  video.muted = true;
  const live = h("div", { class: "scan-live", hidden: true }, video, h("div", { class: "scan-frame", "aria-hidden": "true" }));
  const code = h("input", { type: "text", placeholder: "W-S-01", autocapitalize: "characters", autocomplete: "off", "aria-label": T("Code vom Etikett") });
  const photo = h("label", { class: "button primary large file-button" }, icon("camera"), T("Etikett fotografieren"), h("input", {
    type: "file",
    accept: "image/*",
    capture: "environment",
    onchange: async (event) => {
      const file = event.target.files[0];
      event.target.value = "";
      if (!file) return;
      status.textContent = T("Foto erhalten, lese das Etikett ...");
      try {
        const text = await decodeQrPhoto(file);
        if (!text) status.textContent = T("Im Foto war kein QR-Code zu finden. Fotografiere das Etikett noch einmal etwas näher und scharf, oder tipp den Code unten ein.");
        else openScannedPlace(text, status);
      } catch (error) {
        status.textContent = T(error.message) || T("Das Foto ließ sich nicht lesen.");
      }
    },
  }));
  app.replaceChildren(...shell(
    backLink("#/", T("Zurück")),
    h("h1", {}, T("Etikett scannen")),
    live,
    h("ol", { class: "steps scan-steps" },
      h("li", {}, h("strong", {}, T("Etikett fotografieren")), h("span", {}, T("Die Kamera erkennt den Code dabei nicht selbst. Einfach auslösen."))),
      h("li", {}, h("strong", {}, T("„Foto verwenden“ tippen")), h("span", {}, T("Erst dann liest findling den Code."))),
      h("li", {}, h("strong", {}, T("Platz öffnet sich")), h("span", {}, T("Dort kannst du gleich den Inhalt fotografieren.")))),
    photo,
    status,
    h("form", {
      class: "add-row scan-code",
      onsubmit: (event) => {
        event.preventDefault();
        openScannedPlace(code.value, status);
      },
    }, code, h("button", { type: "submit" }, T("Öffnen")))));
  startLiveScan(video, status).then((running) => {
    if (running) {
      live.hidden = false;
      document.querySelector(".scan-steps")?.setAttribute("hidden", "");
      status.textContent = T("Kamera läuft. Halte das Etikett in den Rahmen, der Platz öffnet sich von selbst.");
    }
  });
}

// Druckmappe: alle Etiketten und das ganze Inventar als PDF. Ohne Bibliothek, direkt im Browser:
// Text in Helvetica, QR-Codes als Rechtecke. Die Zeichen werden in WinAnsi kodiert (Umlaute, ß, €, ›).
const WIN_ANSI = { "€": 128, "‚": 130, "„": 132, "…": 133, "‹": 139, "‘": 145, "’": 146, "“": 147, "”": 148, "•": 149, "–": 150, "—": 151, "™": 153, "›": 155 };

function pdfString(text) {
  let out = "";
  for (const char of String(text)) {
    let code = WIN_ANSI[char] || char.codePointAt(0);
    if (!WIN_ANSI[char] && (code > 255 || (code >= 128 && code < 160))) code = 63;
    if (code === 40 || code === 41 || code === 92) out += `\\${String.fromCharCode(code)}`;
    else if (code < 32) out += " ";
    else out += String.fromCharCode(code);
  }
  return out;
}

const pdfMeasure = (() => {
  let context = null;
  return (text, size, bold) => {
    context ||= document.createElement("canvas").getContext("2d");
    context.font = `${bold ? "bold " : ""}${size}px Helvetica, Arial, sans-serif`;
    return context.measureText(String(text)).width;
  };
})();

function pdfFit(text, size, bold, width) {
  let value = String(text);
  if (pdfMeasure(value, size, bold) <= width) return value;
  while (value.length > 1 && pdfMeasure(`${value}…`, size, bold) > width) value = value.slice(0, -1);
  return `${value.trimEnd()}…`;
}

function pdfWrap(text, size, bold, width) {
  const lines = [];
  let line = "";
  for (const word of String(text).split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word;
    if (line && pdfMeasure(next, size, bold) > width) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines.map((entry) => pdfFit(entry, size, bold, width));
}

const PDF_W = 595.28;
const PDF_H = 841.89;
const PDF_MARGIN = 36;

function pdfPage() {
  const ops = [];
  const n = (value) => Number(value.toFixed(2));
  return {
    ops,
    text(x, y, size, value, { bold = false, gray = 0 } = {}) {
      ops.push(`${gray} g BT /${bold ? "F2" : "F1"} ${size} Tf ${n(x)} ${n(PDF_H - y)} Td (${pdfString(value)}) Tj ET`);
    },
    textRight(x, y, size, value, options = {}) {
      this.text(x - pdfMeasure(value, size, options.bold), y, size, value, options);
    },
    box(x, y, w, h, gray) {
      ops.push(`${gray} g ${n(x)} ${n(PDF_H - y - h)} ${n(w)} ${n(h)} re f`);
    },
    frame(x, y, w, h, gray, dashed) {
      ops.push(`${dashed ? "[3 3] 0 d " : ""}${gray} G 0.5 w ${n(x)} ${n(PDF_H - y - h)} ${n(w)} ${n(h)} re S${dashed ? " [] 0 d" : ""}`);
    },
    qr(x, y, size, value) {
      const qr = window.qrcode(0, "Q");
      qr.addData(value);
      qr.make();
      const count = qr.getModuleCount();
      const cell = size / count;
      const parts = ["0 g"];
      for (let row = 0; row < count; row += 1) {
        let start = -1;
        for (let col = 0; col <= count; col += 1) {
          const dark = col < count && qr.isDark(row, col);
          if (dark && start < 0) start = col;
          if (!dark && start >= 0) {
            parts.push(`${n(x + start * cell)} ${n(PDF_H - y - (row + 1) * cell)} ${n((col - start) * cell)} ${n(cell)} re`);
            start = -1;
          }
        }
      }
      parts.push("f");
      ops.push(parts.join("\n"));
    },
  };
}

function pdfDocument(pages) {
  const objects = [];
  const add = (body) => { objects.push(body); return objects.length; };
  const catalog = add(null);
  const tree = add(null);
  const regular = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
  const bold = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
  const kids = [];
  for (const page of pages) {
    const stream = page.ops.join("\n");
    const content = add(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
    kids.push(add(`<< /Type /Page /Parent ${tree} 0 R /MediaBox [0 0 ${PDF_W} ${PDF_H}] /Resources << /Font << /F1 ${regular} 0 R /F2 ${bold} 0 R >> >> /Contents ${content} 0 R >>`));
  }
  objects[catalog - 1] = `<< /Type /Catalog /Pages ${tree} 0 R >>`;
  objects[tree - 1] = `<< /Type /Pages /Kids [${kids.map((id) => `${id} 0 R`).join(" ")}] /Count ${kids.length} >>`;
  let out = "%PDF-1.4\n%âãÏÓ\n";
  const offsets = [];
  objects.forEach((body, index) => {
    offsets.push(out.length);
    out += `${index + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = out.length;
  out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("")}`;
  out += `trailer\n<< /Size ${objects.length + 1} /Root ${catalog} 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  const bytes = new Uint8Array(out.length);
  for (let index = 0; index < out.length; index += 1) bytes[index] = out.charCodeAt(index) & 0xff;
  return bytes;
}

function placesInOrder() {
  const rank = (place) => {
    const map = mapOf(place);
    const room = roomOf(map);
    const site = data.sites.findIndex((entry) => entry.id === room.site_id);
    return [site, room.name.toLocaleLowerCase("de"), map.name.toLocaleLowerCase("de"), place.code];
  };
  return [...data.places].sort((a, b) => {
    const [x, y] = [rank(a), rank(b)];
    for (let i = 0; i < x.length; i += 1) {
      if (x[i] < y[i]) return -1;
      if (x[i] > y[i]) return 1;
    }
    return 0;
  });
}

const PRINT_ALL = { cover: true, labels: true, inventory: true };

function buildPrintPdf(parts = PRINT_ALL) {
  const today = new Date().toLocaleDateString(LOCALE);
  const places = placesInOrder();
  const pages = [];
  const usable = PDF_W - 2 * PDF_MARGIN;

  // Deckblatt
  if (parts.cover) {
    const cover = pdfPage();
    cover.text(PDF_MARGIN, 120, 30, "findling", { bold: true });
    cover.text(PDF_MARGIN, 150, 16, T("Etiketten und Inventar"), { gray: 0.25 });
    cover.text(PDF_MARGIN, 175, 10, T("Stand {0}", [today]), { gray: 0.4 });
    const facts = [
      `${plural(data.rooms.length, T("Raum"), T("Räume"))} · ${plural(data.maps.length, T("Schrank"), T("Schränke"))} · ${plural(places.length, T("Platz"), T("Plätze"))}`,
      T("{0}, davon {1} zum Nachkaufen", [plural(data.items.length, T("Eintrag"), T("Einträge")), data.items.filter(runsLow).length]),
    ];
    facts.forEach((line, index) => cover.text(PDF_MARGIN, 230 + index * 18, 12, line));
    const steps = [
      T("1. Etiketten an den gestrichelten Linien ausschneiden und auf die Plätze kleben."),
      T("2. Mit dem Kamera-Button in findling ein Etikett scannen: Der Platz öffnet sich direkt."),
      T("3. Das Inventar hinter den Etiketten hilft auch ohne Telefon."),
    ];
    steps.forEach((line, index) => cover.text(PDF_MARGIN, 300 + index * 16, 10, line, { gray: 0.25 }));
    cover.text(PDF_MARGIN, PDF_H - 60, 8, T("Die QR-Codes führen zu findling im eigenen Heimnetz."), { gray: 0.5 });
    pages.push(cover);
  }

  // Etiketten: 3 Spalten, 7 Reihen je Seite, mit Schnittlinien.
  if (parts.labels) {
    const cols = 3;
    const rows = 7;
    const cellW = usable / cols;
    const cellH = (PDF_H - 2 * PDF_MARGIN - 24) / rows;
    for (let start = 0; start < places.length; start += cols * rows) {
      const page = pdfPage();
      page.text(PDF_MARGIN, PDF_MARGIN + 6, 9, T("Etiketten"), { bold: true, gray: 0.35 });
      places.slice(start, start + cols * rows).forEach((place, index) => {
        const x = PDF_MARGIN + (index % cols) * cellW;
        const y = PDF_MARGIN + 18 + Math.floor(index / cols) * cellH;
        page.frame(x, y, cellW, cellH, 0.75, true);
        const qrSize = Math.min(cellH - 16, 74);
        page.qr(x + 8, y + (cellH - qrSize) / 2, qrSize, labelLink(place.code));
        const textX = x + 16 + qrSize;
        const textW = cellW - qrSize - 24;
        page.text(textX, y + 26, 13, pdfFit(place.code, 13, true, textW), { bold: true });
        page.text(textX, y + 42, 9, pdfFit(placeName(place), 9, false, textW));
        pdfWrap(placePath(place), 7, false, textW).slice(0, 3).forEach((line, lineIndex) => page.text(textX, y + 56 + lineIndex * 9, 7, line, { gray: 0.45 }));
      });
      pages.push(page);
    }
  }

  // Inventar: Raum, Schrank, Platz und Inhalt, fortlaufend.
  if (parts.inventory) {
    let page = pdfPage();
    let y = PDF_MARGIN + 6;
    const newPage = () => {
      pages.push(page);
      page = pdfPage();
      y = PDF_MARGIN + 6;
    };
    const need = (space) => { if (y + space > PDF_H - PDF_MARGIN - 20) newPage(); };
    page.text(PDF_MARGIN, y + 10, 18, T("Inventar"), { bold: true });
    y += 34;
    let lastRoom = null;
    let lastMap = null;
    for (const place of places) {
      const map = mapOf(place);
      const room = roomOf(map);
      const items = itemsOf(place).sort((a, b) => a.name.localeCompare(b.name, "de"));
      if (room.id !== lastRoom) {
        need(60);
        const site = data.sites.length > 1 ? ` (${data.sites.find((entry) => entry.id === room.site_id).name})` : "";
        page.text(PDF_MARGIN, y + 12, 14, `${room.name}${site}`, { bold: true });
        y += 22;
        lastRoom = room.id;
        lastMap = null;
      }
      if (map.id !== lastMap) {
        need(40);
        page.text(PDF_MARGIN, y + 10, 11, map.name, { bold: true, gray: 0.2 });
        page.box(PDF_MARGIN, y + 15, usable, 0.6, 0.8);
        y += 22;
        lastMap = map.id;
      }
      need(28);
      page.text(PDF_MARGIN, y + 9, 9, place.code, { bold: true });
      page.text(PDF_MARGIN + 62, y + 9, 9, pdfFit(placeName(place), 9, true, usable - 140), { bold: true });
      page.textRight(PDF_W - PDF_MARGIN, y + 9, 7, place.surveyed ? T("bestätigt") : T("offen"), { gray: 0.45 });
      y += 14;
      if (!items.length) {
        page.text(PDF_MARGIN + 62, y + 8, 8, T("nichts erfasst"), { gray: 0.5 });
        y += 12;
      }
      for (const item of items) {
        const detail = [item.note, deviceLine(item), item.synonyms ? T("auch: {0}", [item.synonyms]) : "", item.away ? T("gerade: {0}", [awayText(item)]) : ""].filter(Boolean).join(" · ");
        const contents = detailLines(item).length ? T("Inhalt: {0}", [detailLines(item).join(", ")]) : "";
        const lines = [detail, contents].filter(Boolean).flatMap((text) => pdfWrap(text, 7, false, usable - 140));
        need(12 + lines.length * 9);
        page.text(PDF_MARGIN + 62, y + 8, 9, `• ${pdfFit(`${quantityOf(item) > 1 ? `${quantityOf(item)}× ` : ""}${item.name}`, 9, false, usable - 150)}`);
        if (item.fill !== "ok") page.textRight(PDF_W - PDF_MARGIN, y + 8, 8, fillLabel(item.fill, item), { bold: ["wenig", "leer"].includes(item.fill), gray: 0.2 });
        y += 12;
        for (const line of lines) {
          page.text(PDF_MARGIN + 72, y + 7, 7, line, { gray: 0.45 });
          y += 9;
        }
      }
      y += 6;
    }
    pages.push(page);
  }

  // Kopf- und Fußzeile mit Seitenzahl auf allen Seiten außer dem Deckblatt.
  pages.forEach((entry, index) => {
    if (parts.cover && index === 0) return;
    entry.textRight(PDF_W - PDF_MARGIN, PDF_MARGIN - 12, 7, T("findling · Stand {0}", [today]), { gray: 0.5 });
    entry.textRight(PDF_W - PDF_MARGIN, PDF_H - 18, 7, T("Seite {0} von {1}", [index + 1, pages.length]), { gray: 0.5 });
  });
  return pdfDocument(pages);
}

// Die ganze Druckmappe, oder nur Etiketten oder nur das Inventar.
const PRINT_JOBS = {
  all: { parts: PRINT_ALL, file: "druckmappe", done: T("Druckmappe erstellt") },
  labels: { parts: { labels: true }, file: "etiketten", done: T("Etiketten als PDF erstellt") },
  inventory: { parts: { inventory: true }, file: "inventar", done: T("Inventar als PDF erstellt") },
};

function downloadPrintPdf(kind = "all") {
  const job = PRINT_JOBS[kind] || PRINT_JOBS.all;
  if (!data.places.length) {
    toast(kind === "inventory" ? T("Noch keine Plätze, also auch kein Inventar.") : T("Noch keine Plätze, also auch keine Etiketten."));
    return;
  }
  let bytes;
  try {
    bytes = buildPrintPdf(job.parts);
  } catch (error) {
    toast(T("Die PDF ließ sich nicht erstellen: {0}", [T(error.message)]));
    return;
  }
  const date = new Date().toISOString().slice(0, 10);
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
  const link = h("a", { href: url, download: `findling-${job.file}-${date}.pdf`, hidden: true });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
  toast(job.done);
}

// Ansicht: Schnellbearbeitung. Alle Einträge eines Raums (oder aller Räume) auf einen Blick, mehrere
// auf einmal ändern, verschieben oder löschen. Änderungen sammeln sich und gehen mit „Speichern“ zusammen raus.
const quickEdits = new Map(); // Eintrag → geänderte Felder
const quickDeletes = new Set();
const quickSelected = new Set();
let quickFilter = "";

function quickValue(item, key) {
  const edit = quickEdits.get(item.id);
  return edit && key in edit ? edit[key] : item[key];
}

function quickSet(item, key, value) {
  const edit = { ...(quickEdits.get(item.id) || {}) };
  if (value === item[key]) delete edit[key];
  else edit[key] = value;
  if (Object.keys(edit).length) quickEdits.set(item.id, edit);
  else quickEdits.delete(item.id);
}

function quickPending() {
  return quickEdits.size + [...quickDeletes].filter((id) => !quickEdits.has(id)).length;
}

function roomOfItem(item) {
  const place = data.places.find((candidate) => candidate.id === quickValue(item, "place_id"));
  return place ? roomOf(mapOf(place)) : null;
}

// Kleine Raumkarte: die Räume an ihren Plätzen aus der Standorte-Karte, ein Tipp springt hinüber.
function roomJumpMap(currentId) {
  const rooms = data.rooms;
  const count = (room) => data.items.filter((item) => roomOfItem(item)?.id === room.id).length;
  const pending = (room) => data.items.some((item) => (quickEdits.has(item.id) || quickDeletes.has(item.id)) && roomOfItem(item)?.id === room.id);
  const most = Math.max(1, ...rooms.map(count));
  const columns = Math.ceil(Math.sqrt(rooms.length || 1));
  const nodes = rooms.map((room, index) => {
    const x = room.map_x ?? ((index % columns) + 0.5) / columns;
    const y = room.map_y ?? (Math.floor(index / columns) + 0.5) / Math.ceil(rooms.length / columns);
    const size = 28 + Math.round(Math.sqrt(count(room) / most) * 18);
    return h("a", {
      class: `jump-node${room.id === currentId ? " current" : ""}${pending(room) ? " pending" : ""}`,
      href: `#/bearbeiten/${room.id}`,
      title: `${room.name}: ${plural(count(room), T("Eintrag"), T("Einträge"))}`,
      style: { left: `${Math.min(92, Math.max(8, x * 100))}%`, top: `${Math.min(80, Math.max(20, y * 100))}%`, width: `${size}px`, height: `${size}px` },
    }, h("span", { class: "jump-count" }, String(count(room))), h("span", { class: "jump-name" }, room.name));
  });
  return h("nav", { class: "jump-map", "aria-label": T("Räume") },
    h("div", { class: "jump-stage" }, nodes),
    h("a", { class: `chip jump-all${currentId ? "" : " current"}`, href: "#/bearbeiten", "aria-current": currentId ? undefined : "page" }, T("Alle Räume")));
}

function viewQuickEdit(roomId) {
  const room = roomId ? data.rooms.find((candidate) => candidate.id === roomId) : null;
  // Was gelöscht oder verschwunden ist, fällt aus Auswahl und Änderungen.
  for (const id of [...quickEdits.keys(), ...quickDeletes, ...quickSelected]) {
    if (!data.items.some((item) => item.id === id)) {
      quickEdits.delete(id);
      quickDeletes.delete(id);
      quickSelected.delete(id);
    }
  }
  const needle = normalize(quickFilter);
  const items = data.items.filter((item) => {
    if (room && roomOfItem(item)?.id !== room.id) return false;
    return !needle || normalize(`${quickValue(item, "name")} ${quickValue(item, "note")}`).includes(needle);
  });
  const groups = new Map();
  for (const item of items) {
    const place = data.places.find((candidate) => candidate.id === quickValue(item, "place_id"));
    if (!groups.has(place.id)) groups.set(place.id, { place, items: [] });
    groups.get(place.id).items.push(item);
  }
  const ordered = placesInOrder().filter((place) => groups.has(place.id)).map((place) => groups.get(place.id));

  const bar = h("div", { class: "quick-bar" });
  const drawBar = () => {
    const selected = [...quickSelected];
    const fill = h("select", { "aria-label": T("Füllstand für die Auswahl") },
      h("option", { value: "" }, T("Füllstand …")), FILL_LEVELS.map((level) => h("option", { value: level }, bothLabels(level))));
    fill.addEventListener("change", () => {
      for (const id of selected) quickSet(data.items.find((item) => item.id === id), "fill", fill.value);
      render();
    });
    const move = placeSelect();
    move.prepend(h("option", { value: "", selected: true }, T("Verschieben nach …")));
    move.addEventListener("change", () => {
      for (const id of selected) quickSet(data.items.find((item) => item.id === id), "place_id", move.value);
      render();
    });
    const pendingCount = quickPending();
    bar.replaceChildren(...[
      selected.length ? h("div", { class: "quick-actions" },
        h("strong", { class: "small" }, T("{0} ausgewählt", [selected.length])),
        fill, move,
        h("button", {
          type: "button",
          class: "compact danger",
          onclick: () => {
            for (const id of selected) quickDeletes.add(id);
            quickSelected.clear();
            render();
          },
        }, T("Löschen")),
        h("button", { type: "button", class: "linklike small", onclick: () => { quickSelected.clear(); render(); } }, T("Auswahl aufheben"))) : null,
      h("div", { class: "quick-save" },
        h("span", { class: "small muted" }, pendingCount ? T("{0} noch nicht gespeichert", [plural(pendingCount, T("Änderung"), T("Änderungen"))]) : T("Alles gespeichert")),
        pendingCount ? h("button", {
          type: "button",
          class: "linklike small",
          onclick: () => {
            if (!confirm(T("Alle ungespeicherten Änderungen verwerfen?"))) return;
            quickEdits.clear();
            quickDeletes.clear();
            render();
          },
        }, T("Verwerfen")) : null,
        h("button", {
          type: "button",
          class: "primary",
          disabled: !pendingCount,
          onclick: () => {
            const deletes = [...quickDeletes];
            if (deletes.length && !confirm(T("{0} in den Papierkorb legen?", [plural(deletes.length, T("Eintrag"), T("Einträge"))]))) return;
            const updates = [...quickEdits].filter(([id]) => !quickDeletes.has(id)).map(([id, change]) => ({ id, ...change }));
            act(() => api("POST", "api/items/batch", { updates, delete: deletes }), () => {
              quickEdits.clear();
              quickDeletes.clear();
              quickSelected.clear();
              toast(T("Gespeichert: {0}{1}", [plural(updates.length, T("Änderung"), T("Änderungen")), deletes.length ? T(", {0} im Papierkorb", [deletes.length]) : ""]));
              render();
            });
          },
        }, pendingCount ? `${pendingCount} speichern` : T("Speichern"))),
    ].filter(Boolean));
  };

  const row = (item) => {
    const deleted = quickDeletes.has(item.id);
    const moved = quickValue(item, "place_id") !== item.place_id;
    const mark = () => {
      element.classList.toggle("dirty", quickEdits.has(item.id));
      drawBar();
    };
    const check = h("input", {
      type: "checkbox",
      checked: quickSelected.has(item.id),
      "aria-label": T("{0} auswählen", [item.name]),
      onchange: (event) => {
        if (event.target.checked) quickSelected.add(item.id);
        else quickSelected.delete(item.id);
        drawBar();
      },
    });
    const name = h("input", { type: "text", value: quickValue(item, "name"), "aria-label": T("Name"), disabled: deleted,
      oninput: (event) => { quickSet(item, "name", event.target.value); mark(); } });
    const fill = h("select", { "aria-label": T("Füllstand"), disabled: deleted,
      onchange: (event) => { quickSet(item, "fill", event.target.value); mark(); } },
      FILL_LEVELS.map((level) => h("option", { value: level, selected: quickValue(item, "fill") === level }, fillLabel(level, item))));
    const note = h("input", { type: "text", value: quickValue(item, "note"), placeholder: T("Notiz"), "aria-label": T("Notiz"), disabled: deleted,
      oninput: (event) => { quickSet(item, "note", event.target.value); mark(); } });
    const quantity = h("input", { type: "number", class: "quick-qty", min: "1", max: String(QUANTITY_MAX), inputmode: "numeric", value: String(quantityOf({ quantity: quickValue(item, "quantity") })), "aria-label": T("Anzahl"), title: T("Anzahl"), disabled: deleted,
      oninput: (event) => {
        const value = Number.parseInt(event.target.value, 10);
        if (Number.isInteger(value) && value >= 1 && value <= QUANTITY_MAX) { quickSet(item, "quantity", value); mark(); }
      } });
    const element = h("li", { class: `quick-row${quickEdits.has(item.id) ? " dirty" : ""}${deleted ? " deleted" : ""}` },
      check,
      h("div", { class: "quick-fields" },
        h("div", { class: "quick-line" }, quantity, name, fill),
        note,
        moved ? h("span", { class: "small accent-text" }, T("wird verschoben nach {0}", [data.places.find((place) => place.id === quickValue(item, "place_id")).code])) : null,
        deleted ? h("button", { type: "button", class: "linklike small", onclick: () => { quickDeletes.delete(item.id); render(); } }, T("Löschen rückgängig")) : null));
    return element;
  };

  const filter = h("input", {
    type: "search",
    class: "quick-filter",
    value: quickFilter,
    placeholder: T("Einträge filtern"),
    "aria-label": T("Einträge filtern"),
    oninput: (event) => {
      quickFilter = event.target.value;
      const position = event.target.selectionStart;
      render();
      const again = document.querySelector(".quick-filter");
      again?.focus();
      again?.setSelectionRange(position, position);
    },
  });
  drawBar();
  app.replaceChildren(...shell(
    backLink(room ? roomHref(room) : "#/", room ? room.name : T("Zum Dashboard")),
    h("h1", {}, T("Schnellbearbeitung")),
    roomJumpMap(room ? room.id : null),
    h("div", { class: "quick-tools" }, filter,
      items.length ? h("button", {
        type: "button",
        class: "compact",
        onclick: () => {
          const all = items.every((item) => quickSelected.has(item.id));
          for (const item of items) {
            if (all) quickSelected.delete(item.id);
            else quickSelected.add(item.id);
          }
          render();
        },
      }, items.length && items.every((item) => quickSelected.has(item.id)) ? T("Keine wählen") : T("Alle wählen")) : null),
    ordered.length ? ordered.map(({ place, items: list }) => h("section", { class: "card quick-group" },
      h("div", { class: "section-head" },
        h("a", { href: `#/p/${place.code}` }, h("strong", {}, placeName(place)), h("span", { class: "muted small" }, ` ${placePath(place)} · ${place.code}`)),
        h("button", {
          type: "button",
          class: "linklike small",
          onclick: () => {
            const all = list.every((item) => quickSelected.has(item.id));
            for (const item of list) {
              if (all) quickSelected.delete(item.id);
              else quickSelected.add(item.id);
            }
            render();
          },
        }, T("alle"))),
      h("ul", { class: "quick-list" }, list.map(row)))) : h("p", { class: "notice" }, quickFilter ? T("Nichts passt zum Filter.") : T("Hier gibt es noch keine Einträge.")),
    bar));
}

function viewMissing(message) {
  app.replaceChildren(...shell(h("p", { class: "notice" }, message), backLink("#/", T("Zur Startseite"))));
}

// Anmeldung

function renderLogin() {
  const pin = h("input", {
    type: "password",
    inputmode: "numeric",
    autocomplete: "current-password",
    "aria-label": "PIN",
    placeholder: "PIN",
  });
  const submit = async (event) => {
    event.preventDefault();
    try {
      await api("POST", "api/login", { pin: pin.value });
      await reload();
      render();
    } catch (error) {
      toast(error.message);
    }
  };
  app.replaceChildren(h("main", {},
    h("form", { class: "card login stack", onsubmit: submit },
      brandHero(),
      h("p", { class: "muted" }, T("Die PIN steht im Startfenster auf dem Rechner oder in den Einstellungen der App in Home Assistant.")),
      pin,
      h("button", { class: "primary large", type: "submit" }, T("Anmelden")),
      makerLine())));
  pin.focus();
}

// Navigation

function render() {
  if (!data) return;
  const hash = location.hash.replace(/^#\/?/, "");
  const [route, argument] = hash.split("/");
  stopScan();
  pageCamera = null;
  if (route !== "steckbrief" && route !== "s") passportEdit = null;
  if (route !== "teilen") storing = null;
  if (route !== "eingang") intake = null;
  if (route === "neuer-raum") viewNewRoom(argument);
  else if (route === "neu") viewNewMap(argument);
  else if (route === "karte") viewMap(argument);
  else if (route === "raum") viewRoom(argument);
  else if (route === "p") viewPlace(decodeURIComponent(argument || ""));
  else if (route === "detail") viewDetail(argument);
  else if (route === "steckbrief" || route === "s") viewPassport(argument);
  else if (route === "blick") viewWatch();
  else if (route === "import") viewImport();
  else if (route === "eingang") viewIntake();
  else if (route === "etiketten") viewLabels(argument);
  else if (route === "daten") viewSettings();
  else if (route === "auswertung") viewReport();
  else if (route === "papierkorb") viewTrash();
  else if (route === "runde") viewRound();
  else if (route === "serie") viewSeries(argument);
  else if (route === "unterwegs") viewTravel();
  else if (route === "sicherungen") viewBackups();
  else if (route === "teilen") viewShare();
  else if (route === "scan") viewScan();
  else if (route === "dashboard") viewDashboardSettings();
  else if (route === "titelbild") viewCover(argument);
  else if (route === "bearbeiten") viewQuickEdit(argument);
  else viewDashboard();
}

window.addEventListener("hashchange", async () => {
  // Frisch laden, denn am Telefon oder am Rechner kann sich inzwischen etwas geändert haben.
  await reload().catch(() => {});
  render();
  window.scrollTo(0, 0);
});

// Anpassungen der Oberfläche. Sie liegen auf dem Server und sind damit in jeder Sicherung.
const PREFERENCE_DEFAULTS = {
  dashboard: { hidden_rooms: [], progress: true, minimap: true, rooms: true, low: true, watch: true, checkin: true },
  checkin_days: 90,
  checkin_next: "",
  photo_look: "gruen",
  chat: "chatgpt",
  label_size: "size-m",
};

function prefs() {
  return (data && data.preferences) || PREFERENCE_DEFAULTS;
}

async function savePreferences(change, quiet = false) {
  try {
    data.preferences = await api("PATCH", "api/preferences", change);
  } catch (error) {
    if (error.message !== "PIN erforderlich") toast(error.message);
    return;
  }
  applyPhotoLook();
  if (!quiet) render();
}

// Frühere Versionen hielten manches nur im Browser. Das kommt einmal auf den Server.
const PHOTO_LOOK_KEY = "findling-fotolook";

async function moveLocalPreferences() {
  const change = {};
  try {
    if (localStorage.getItem(PHOTO_LOOK_KEY) === "aus" && prefs().photo_look === "gruen") change.photo_look = "aus";
    const chat = localStorage.getItem(CHAT_KEY);
    if (chat && chat !== prefs().chat && CHATS.some((entry) => entry.key === chat)) change.chat = chat;
    localStorage.removeItem(PHOTO_LOOK_KEY);
    localStorage.removeItem(CHAT_KEY);
  } catch {
    return;
  }
  if (Object.keys(change).length) await savePreferences(change, true);
}

// Einheitlicher Look für Schrank- und Inhaltsfotos. Nur die Anzeige, das Original bleibt unverändert.
const PHOTO_LOOKS = [
  ["gruen", T("Grün"), "#2f6b22"],
  ["blau", T("Blau"), "#1f4f7a"],
  ["bernstein", T("Bernstein"), "#8a5a1c"],
  ["violett", T("Violett"), "#4b3577"],
  ["grau", T("Grau"), "#5f6361"],
  ["aus", T("Aus"), null],
];

function applyPhotoLook() {
  document.body.dataset.photoLook = prefs().photo_look;
}

window.addEventListener("beforeunload", (event) => {
  if (quickPending()) event.preventDefault();
});

async function start() {
  try {
    await reload();
    await moveLocalPreferences();
    render();
  } catch (error) {
    if (error.message !== "PIN erforderlich") {
      app.replaceChildren(h("main", {}, h("p", { class: "notice" }, T("Die App konnte nicht starten: {0}", [T(error.message)]))));
    }
  }
}

start();
