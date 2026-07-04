# Beitragen zu Detecto

Danke für dein Interesse an Detecto! Beiträge – Bugfixes, neue Suchmuster,
Doku – sind willkommen.

## Wichtig: keine echten Daten

Detecto findet personenbezogene und kritische Daten. Poste in Issues, Pull
Requests, Tests und Beispiel-Logs deshalb **niemals echte** personenbezogene
Daten, Secrets oder Kundendaten. Nutze ausschließlich **synthetische** Werte –
Vorlagen findest du unter [`synthetic_logs/`](synthetic_logs/).

## Entwicklungsumgebung

```bash
git clone https://github.com/alexkorn2026/detecto.git
cd detecto
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

Vor jedem Pull Request müssen die Tests grün sein:

```bash
pytest tests/ -q          # oder: make test
```

Neue Funktionalität bitte mit Tests abdecken. Die Testsuite umfasst aktuell
126 Tests in `tests/`.

## Code-Stil

Das Projekt ist auf `ruff` und `black` (line-length 100) konfiguriert
(siehe `pyproject.toml`):

```bash
ruff check src/ tests/
black src/ tests/
```

Der Lint-Job in der CI ist derzeit beratend (nicht-blockierend); trotzdem
freuen wir uns über sauber formatierte Beiträge.

## Neue Suchmuster hinzufügen

Detecto kennt drei Muster-Typen. Format jeweils mit `::` als Trenner.

- **regexp** in `regexp.csv` – `name::kritikalitaet::beschreibung::regexp`
- **field** in `field.csv` – `name::kritikalitaet::beschreibung::regexp[::offset]`
- **string** in `suchmuster/*.csv`, registriert in `suchmuster.csv` –
  `name::kritikalitaet::dateiname.csv`

Kritikalität ist 1 (kritisch) bis 5 (info). Bitte jedes neue Muster mit einem
synthetischen Beispiel gegen `detecto` prüfen und – wo sinnvoll – einen Test
in `tests/` ergänzen. Für neue synthetische Findings kannst du
`synthetic_logs/generate_samples.py` erweitern.

## Pull Requests

1. Branch von `main` erstellen.
2. Änderung + Tests committen.
3. `pytest` grün, keine echten Daten enthalten.
4. PR gegen `main` öffnen und die Vorlage ausfüllen.

## Lizenz

Mit einem Beitrag stimmst du zu, dass dieser unter der
[MIT-Lizenz](LICENSE) des Projekts veröffentlicht wird.
