# Synthetic Log Samples

Dieses Verzeichnis enthält synthetische Logdateien mit denselben Findings,
gerendert in mehrere gängige Logformate. **Alle Werte sind fiktiv** und
ausschließlich für Test-, Demo- und Erkennungszwecke gedacht.

## Regenerieren

Die Beispiele werden reproduzierbar aus einem gemeinsamen Satz Findings erzeugt:

```bash
python3 synthetic_logs/generate_samples.py
```

Neue Findings oder Formate lassen sich in `generate_samples.py` ergänzen.

## Enthaltene Formate

| Datei | Format |
|---|---|
| `kritische_findings_websphere_application.log` | WebSphere Application Log (Textformat) |
| `kritische_findings_liberty_messages.log`      | Open Liberty `messages.log` (Textformat) |
| `kritische_findings_liberty_json.log`          | Open Liberty JSON-Logformat |
| `kritische_findings_tomcat_application.log`     | Tomcat Application Log |
| `kritische_findings_apache_error.log`          | Apache Error Log |
| `kritische_findings_kubernetes.log`            | Kubernetes/Container Log (JSON) |
| `kritische_findings_spring_boot.log`           | Spring Boot Log |

Pro Format dieselben Inhalte in unterschiedlicher technischer Darstellung.

## Ausprobieren

```bash
detecto synthetic_logs/kritische_findings_websphere_application.log
detecto synthetic_logs/kritische_findings_liberty_json.log --critical=2
```

## Zweck

- Testdaten für den Logscanner
- Vergleich unterschiedlicher Logformate
- Training und Validierung von Suchmustern
- Demo-Daten für Workshops und Dokumentation
