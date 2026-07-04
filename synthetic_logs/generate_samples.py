#!/usr/bin/env python3
"""Generate small, GitHub-friendly synthetic log samples for Detecto.

All values are fictional and exist purely for testing, demos and pattern
validation. The same set of findings is rendered into several common log
formats so the scanner can be exercised against each.

Usage:
    python3 generate_samples.py
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

# (level, logger, message) - message bodies carry the fictional findings.
FINDINGS: list[tuple[str, str, str]] = [
    ("INFO",  "AntragService",   "Antrag mit RVNR 65 170839 J 008 eingegangen"),
    ("INFO",  "AntragService",   "Verarbeitung vsnr=65170839J008 abgeschlossen"),
    ("INFO",  "StammdatenDAO",   "Stammsatz geladen RVNR:65170839J008"),
    ("INFO",  "KontaktService",  "Rueckruf unter +49 30 1234 5678 vereinbart"),
    ("INFO",  "ZahlungService",  "Ueberweisung auf DE89 3704 0044 0532 0130 00 veranlasst"),
    ("WARN",  "ZahlungService",  "Zahlung mit Karte 4532 1111 2222 3333 abgelehnt"),
    ("ERROR", "DumpWriter",      "Dump enthaelt -----BEGIN RSA PRIVATE KEY----- Fragment"),
    ("INFO",  "AuthController",  'Request {"login":"m.weber","password":"W1nter#Geh31m"} verarbeitet'),
    ("INFO",  "AuthController",  "Anmeldung fehlgeschlagen password = Fr3itag$2026"),
    ("INFO",  "DBAdmin",         "Skript ausgefuehrt identified by S3cret#99 durch DBA"),
    ("INFO",  "SecurityFilter",  "Header authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.sflKxwRJSMeKKF2QT4"),
    ("INFO",  "SessionManager",  "Neue Session JSESSIONID:9A3B2C1D4E5F6789 erstellt"),
    ("INFO",  "ConnectionPool",  "Verbindung jdbc:oracle://db01:1521/PROD aufgebaut"),
    ("INFO",  "DeployJob",       "Deployment api_key=Xk29fLpQ7 erfolgreich"),
    ("WARN",  "SecretScanner",   "Key im Repo gefunden AKIAIOSFODNN7EXAMPLE bitte rotieren"),
    ("WARN",  "SecretScanner",   "Commit enthaelt ghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"),
    ("WARN",  "SecretScanner",   "Webhook nutzt xoxb-123456789012-AbCdEfGhIjKl"),
    ("INFO",  "StorageConfig",   "Storage konfiguriert AccountKey aBcDeF1234567890aBcDeF1234567890aBcDeF12345678=="),
    ("INFO",  "CiRunner",        "Checkout von git@intranet.example:detecto/core.git"),
    ("INFO",  "KontaktService",  "Kontakt max.mustermann@example.org hinterlegt"),
    ("INFO",  "VersandService",  "Zustellung an Hauptstrasse 12 beauftragt"),
    ("INFO",  "VersandService",  "Meldeanschrift 10115 Berlin uebernommen"),
    ("INFO",  "SteuerService",   "Steuerbescheid zur Steuer-ID 12345678901 versendet"),
    ("INFO",  "KrankenkasseDAO", "Versichertenkarte A123456789 eingelesen"),
    ("INFO",  "AusweisPruefer",  "Ausweis L01X00T471 geprueft"),
    ("INFO",  "FirmenService",   "Firma erfasst HRB 98765 Amtsgericht Muenchen"),
    ("INFO",  "RechnungService", "Rechnung mit USt-IdNr DE811907980 gestellt"),
    ("INFO",  "ZahlungService",  "Ueberweisung via COBADEFFXXX gebucht"),
    ("INFO",  "SGVerfahren",     "Verfahren S 12 R 345/20 terminiert"),
    ("INFO",  "AccessLog",       "Zugriff von 203.0.113.42 protokolliert"),
    ("INFO",  "AccessLog",       "Backend erreichbar unter 192.168.1.100"),
    ("INFO",  "DeviceRegistry",  "Geraet 00:1A:2B:3C:4D:5E registriert"),
    ("INFO",  "DeviceRegistry",  "Endgeraet mit IMEI 490154203237518 gemeldet"),
    ("INFO",  "FuhrparkService", "Fahrzeug B-XY 987 zugeordnet"),
    ("INFO",  "LizenzService",   "Aktivierung mit ABCD1-EF234-GH567 erfolgreich"),
    ("WARN",  "ClassifyService", "Dokument als VS-NfD eingestuft"),
    ("WARN",  "ClassifyService", "Anlage traegt Vermerk STRENG GEHEIM"),
    ("WARN",  "ClassifyService", "Datei klassifiziert als NATO SECRET"),
    ("INFO",  "MelderegisterDAO","Sperrvermerk im Melderegister gesetzt"),
    ("INFO",  "FormularService", "Vorname Anna im Formular uebernommen"),
    ("INFO",  "VorgangService",  "Sachbearbeiter Schmidt hat Vorgang uebernommen"),
    ("INFO",  "MelderegisterDAO","Umzug nach Hamburg gemeldet"),
    ("INFO",  "BefundService",   "Befund Diabetes dokumentiert"),
    ("INFO",  "BefundService",   "Diagnose:F32.1 an Kasse uebermittelt"),
    ("INFO",  "NotfallService",  "Blutgruppe: AB+ im Notfallpass vermerkt"),
    ("INFO",  "PflegeService",   "Pflegegrad 3 bewilligt"),
    ("INFO",  "SchwerbehService","GdB 50 anerkannt"),
    ("INFO",  "GehaltService",   "Gehalt 4850 EUR ausgezahlt"),
    ("INFO",  "SterbefallDAO",   "Sterbedatum 2025-11-03 nacherfasst"),
    ("INFO",  "RenteService",    "Entgeltpunkte 34.5 berechnet"),
    ("INFO",  "GeburtsdatumDAO", "Geburtsdatum 1983-05-17 verifiziert"),
]

BASE_TS = datetime(2026, 7, 4, 10, 0, 1)


def timestamps() -> list[datetime]:
    return [BASE_TS + timedelta(seconds=i) for i in range(len(FINDINGS))]


def write(name: str, lines: list[str]) -> None:
    path = OUT_DIR / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {name:<44} {len(lines):>3} lines")


def gen_websphere() -> None:
    lines = []
    for ts, (lvl, logger, msg) in zip(timestamps(), FINDINGS):
        stamp = ts.strftime("[%d.%m.%y %H:%M:%S:%f")[:-3] + " CEST]"
        lines.append(f"{stamp} 00000042 {logger:<18} {lvl[0]} {msg}")
    write("kritische_findings_websphere_application.log", lines)


def gen_liberty_messages() -> None:
    lines = []
    for ts, (lvl, logger, msg) in zip(timestamps(), FINDINGS):
        stamp = ts.strftime("[%d.%m.%y, %H:%M:%S:%f")[:-3] + " CEST]"
        lines.append(f"{stamp} 0000002a {logger:<18} {lvl[0]:<2} {msg}")
    write("kritische_findings_liberty_messages.log", lines)


def gen_liberty_json() -> None:
    lines = []
    for ts, (lvl, logger, msg) in zip(timestamps(), FINDINGS):
        rec = {
            "type": "liberty_message",
            "ibm_datetime": ts.strftime("%Y-%m-%dT%H:%M:%S.000+0200"),
            "loglevel": lvl,
            "module": f"de.rvbund.detecto.{logger}",
            "message": msg,
        }
        lines.append(json.dumps(rec, ensure_ascii=False))
    write("kritische_findings_liberty_json.log", lines)


def gen_tomcat() -> None:
    lines = []
    for ts, (lvl, logger, msg) in zip(timestamps(), FINDINGS):
        stamp = ts.strftime("%d-%b-%Y %H:%M:%S.000")
        lines.append(f"{stamp} {lvl:<5} [http-nio-8080-exec-1] de.app.{logger}.run {msg}")
    write("kritische_findings_tomcat_application.log", lines)


def gen_apache_error() -> None:
    lines = []
    lvl_map = {"INFO": "notice", "WARN": "warn", "ERROR": "error"}
    for ts, (lvl, _logger, msg) in zip(timestamps(), FINDINGS):
        stamp = ts.strftime("[%a %b %d %H:%M:%S.000000 %Y]")
        lines.append(f"{stamp} [core:{lvl_map[lvl]}] [pid 1234:tid 5678] [client 203.0.113.42:52014] {msg}")
    write("kritische_findings_apache_error.log", lines)


def gen_kubernetes() -> None:
    lines = []
    for ts, (lvl, logger, msg) in zip(timestamps(), FINDINGS):
        rec = {
            "log": msg,
            "stream": "stdout",
            "time": ts.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
            "kubernetes": {"pod_name": "detecto-app-7d9f", "namespace": "prod",
                           "container_name": logger.lower()},
            "level": lvl.lower(),
        }
        lines.append(json.dumps(rec, ensure_ascii=False))
    write("kritische_findings_kubernetes.log", lines)


def gen_spring_boot() -> None:
    lines = []
    for ts, (lvl, logger, msg) in zip(timestamps(), FINDINGS):
        stamp = ts.strftime("%Y-%m-%d %H:%M:%S.000")
        lines.append(f"{stamp}  {lvl:<5} 12345 --- [main] de.app.{logger:<18}: {msg}")
    write("kritische_findings_spring_boot.log", lines)


def main() -> None:
    print(f"Generating synthetic log samples ({len(FINDINGS)} findings each):")
    gen_websphere()
    gen_liberty_messages()
    gen_liberty_json()
    gen_tomcat()
    gen_apache_error()
    gen_kubernetes()
    gen_spring_boot()
    print("Done.")


if __name__ == "__main__":
    main()
