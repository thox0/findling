#!/bin/sh
# Kopierdienst für Sicherungen. Läuft als root, weil Netzlaufwerke unter /share meist nur root
# beschreiben darf. Er tut genau eins: die letzten Sicherungen aus /data/sicherungen an den
# eingestellten Speicherort kopieren und dort nur die letzten Stände behalten.
#
# Schutz, weil der Auftrag (spiegel.conf) von der App ohne Root-Rechte kommt:
# - Ziel nur unter /share, ohne „..“, vorher vollständig aufgelöst.
# - Die App darf /share laut AppArmor nur lesen. Sie kann dort also nichts unterschieben.
# - Kopiert und löscht nur Dateien mit dem Namensmuster der Sicherungen, nie Verknüpfungen.
# Aufruf: spiegel.sh [einmal]

DATA="${SPIEGEL_DATA:-/data}"
SHARE="${SPIEGEL_SHARE:-/share}"
QUELLE="$DATA/sicherungen"
MUSTER='^findling-[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]{4,6}|-vor-[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4})?\.zip$'

melde() {
    printf '%s\n' "$*" > "$DATA/.spiegel-status.tmp" && mv -f "$DATA/.spiegel-status.tmp" "$DATA/spiegel-status"
}

durchlauf() {
    [ -f "$DATA/spiegel.conf" ] || return 0
    ziel=$(sed -n 1p "$DATA/spiegel.conf")
    behalten=$(sed -n 2p "$DATA/spiegel.conf")
    case "$behalten" in ''|*[!0-9]*) melde "fehler $(date +%s) Ungültige Zahl der Stände"; return 0 ;; esac
    if [ "$behalten" -lt 3 ] || [ "$behalten" -gt 30 ]; then
        melde "fehler $(date +%s) Ungültige Zahl der Stände"; return 0
    fi
    case "$ziel" in
        *..*|'') melde "fehler $(date +%s) Ungültiger Speicherort"; return 0 ;;
        "$SHARE"/?*) ;;
        *) melde "fehler $(date +%s) Speicherort liegt nicht unter $SHARE"; return 0 ;;
    esac
    echt=$(realpath "$ziel" 2>/dev/null) || { melde "fehler $(date +%s) Speicherort nicht erreichbar"; return 0; }
    case "$echt" in
        "$SHARE"/?*) ;;
        *) melde "fehler $(date +%s) Speicherort liegt nicht unter $SHARE"; return 0 ;;
    esac
    [ -d "$echt" ] || { melde "fehler $(date +%s) Speicherort nicht erreichbar"; return 0; }

    fehler=""
    auswahl=$( (ls -1t "$QUELLE" 2>/dev/null | grep -E "$MUSTER" | grep -v -- '-vor-' | head -n "$behalten"
                ls -1t "$QUELLE" 2>/dev/null | grep -E "$MUSTER" | grep -- '-vor-' | head -n 2) )
    for name in $auswahl; do
        datei="$QUELLE/$name"
        [ -f "$datei" ] && [ ! -L "$datei" ] || continue
        if [ -f "$echt/$name" ] && [ ! -L "$echt/$name" ] && \
           [ "$(wc -c < "$echt/$name")" = "$(wc -c < "$datei")" ]; then
            continue
        fi
        zwischen=$(mktemp "$echt/.findling.XXXXXX" 2>/dev/null) || { fehler="Keine Schreibrechte am Speicherort"; break; }
        # Lesbar auch für die App ohne Root-Rechte, damit sie auf einem neuen Server von hier einspielen kann.
        if cat -- "$datei" > "$zwischen" && chmod 0644 "$zwischen" && touch -r "$datei" "$zwischen" && mv -f "$zwischen" "$echt/$name"; then
            :
        else
            rm -f -- "$zwischen"
            fehler="Kopieren nach $echt fehlgeschlagen"
            break
        fi
    done

    # Am Speicherort nur die letzten Stände behalten, dazu die beiden letzten vor einem Update.
    ls -1t "$echt" 2>/dev/null | grep -E "$MUSTER" | grep -v -- '-vor-' | tail -n +$((behalten + 1)) | while read -r alt; do
        [ -L "$echt/$alt" ] || rm -f -- "$echt/$alt"
    done
    ls -1t "$echt" 2>/dev/null | grep -E "$MUSTER" | grep -- '-vor-' | tail -n +3 | while read -r alt; do
        [ -L "$echt/$alt" ] || rm -f -- "$echt/$alt"
    done

    if [ -n "$fehler" ]; then
        melde "fehler $(date +%s) $fehler"
    else
        melde "ok $(date +%s)"
    fi
}

if [ "${1:-}" = "einmal" ]; then
    durchlauf
    exit 0
fi
while true; do
    durchlauf || true
    sleep 60
done
