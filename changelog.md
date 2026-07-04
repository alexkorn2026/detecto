# Detecto - Changelog

## v2.0.0 (2026-07-04) – Review-Befunde 1–42

Umfangreiche Korrektur der Review-Befunde 1–42. Wichtige, teils inkompatible
Änderungen (daher Major-Bump):

Sicherheit & Korrektheit
- Runtime-Regex-Timeout via `regex`-Paket; wiederholt auslösende Muster werden
  deaktiviert (Finding 1)
- Expliziter Scan-Status (complete/partial/failed) + Exit-Codes 0/2/3/4/5
  (Finding 2)
- Sensible Werte standardmäßig anonymisiert; Klartext nur mit
  `--show-sensitive-values`; Reports mit 0600-Rechten (Finding 3)
- Globale Speicher-/Ergebnislimits mit transparenter Zählung (Finding 4)
- Credential-Werte mit `/`/`C:` nicht mehr fälschlich verworfen; maskierte
  Werte als eigener, niedriger eingestufter Fund (Finding 5)
- Doppelte Pattern-IDs sind ein fataler Konfigurationsfehler (Finding 6)
- Originalwert + Positionen + Zeilennummer je Fund; deterministische
  Parallelverarbeitung; positionsbasierte Anonymisierung (Findings 7, 20, 24)

Erkennung
- Expliziter Regex-Scope (`token|line`); Tokenizer-Robustheit (URL/IPv6/JDBC);
  JSON-Modus `auto` (Findings 8, 9, 10)
- Validatoren für Kreditkarte (Luhn), IBAN (Mod 97), Steuer-ID, JWT, Private
  Key, Straßen-Kontext (Findings 11–17)
- Confidence-Stufen für Namen/Orte; technische Begriffe nicht als Namen
  (Findings 18, 19)

Betrieb
- Container-bewusste Worker-Begrenzung; Multiprocessing-Schwellen;
  Kontextausschnitt statt ganzer Zeile; Excel-Formula-Injection-Härtung
  (Findings 21, 22, 23, 25)
- Encoding-Optionen; Umgang mit überlangen Zeilen; Binär-/Pipe-/Symlink-/
  gz-Behandlung (Findings 26, 27, 28)

Packaging & Konfiguration
- openpyxl optional (`detecto[excel]`); Supply-Chain (Constraints, CI, SBOM);
  sichere Config-Priorität; strikte Config-Validierung (Findings 29–32)
- Reproduzierbare Qualitäts-/Performance-Benchmarks; Property/Fuzz-Tests;
  konsistente Defaults; Packaging-Tests (Findings 33–40)
- Symlink-sicheres Öffnen von Pattern-Dateien; korrigierte, nicht-absolute
  Sicherheitsaussagen (Findings 41, 42)

## v1.6.1 (2026-07-04) – Initial public release

Erste öffentliche Veröffentlichung auf GitHub.
