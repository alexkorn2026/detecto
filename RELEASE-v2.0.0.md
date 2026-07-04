# Detecto v2.0.0

Behebt die Review-Befunde 1–42 ohne grundlegenden Architekturumbau. Major-Release
wegen sicherer Default-Änderungen, neuem Regexp-Scope-Format und geänderter
`parse_json`-Semantik.

## Highlights
- Laufzeit-Regex-DoS-Timeout; expliziter Scan-Status + Exit-Codes 0/2/3/4/5
- Sensible Werte standardmäßig anonymisiert (Klartext nur mit `--show-sensitive-values`),
  Reports mit 0600-Rechten
- Globale Limits, überlange-Zeilen-Schutz, Excel-Formula-Injection-Härtung
- Validatoren: Kreditkarte (Luhn), IBAN (Mod 97), Steuer-ID, JWT, Private Key,
  Straßen-Kontext; Confidence-Stufen für Namen/Orte
- Robuster Tokenizer (URL/IPv6/JDBC), JSON-Modus `auto`, expliziter Regex-Scope
- Container-bewusster Worker-Cap, Multiprocessing-Schwellen, Encoding-Optionen,
  Binär-/Pipe-/Symlink-/gz-Behandlung
- openpyxl optional (`detecto[excel]`), Supply-Chain (Constraints, CI, SBOM),
  strikte Config, sichere Config-Priorität
- Reproduzierbare Qualitäts-/Performance-Benchmarks, Property/Fuzz-Tests,
  symlink-sicheres Öffnen der Pattern-Dateien, korrigierte Sicherheitsaussagen

## Qualität
- 295 Tests grün (vorher 126), `ruff check src/` sauber
- Qualitäts-Benchmark (synthetisch): Precision/Recall/F1 = 1.00
- Wheel enthält alle Datenfiles, läuft nach Installation außerhalb des Repos

## Breaking Changes / Migration
- Klartext benötigt `--show-sensitive-values`
- Regexp-Dateien: Scope-Feld ergänzen (Alt-Format lädt mit Warnung)
- `./detecto.ini` nur mit `--use-local-config`
- Ungültige Config-Werte sind standardmäßig Fehler (`--lenient-config` für Altverhalten)
- openpyxl separat: `pip install detecto[excel]`

Details je Finding: `DETECTO_FINDINGS_1_42_IMPLEMENTATION_REPORT.md`.
Website-Textkorrekturen: `WEBSITE_TEXT_CHANGES.md`.
