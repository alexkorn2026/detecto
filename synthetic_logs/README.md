# Synthetic Log Samples

Dieses Verzeichnis enthaelt synthetische Logdateien mit denselben 400 Findings aus 20 Kategorien kritischer Logdaten.

Die Beispiele basieren auf:

- `/Users/alexanderkornbrust/Documents/Claude/Projects/Detecto/kritische_logdaten_findings.md`

Alle Werte sind fiktiv und fuer Test-, Demo- und Erkennungszwecke gedacht.

## Enthaltene Formate

- `kritische_findings_websphere_application.log`
  WebSphere Application Log mit klassischem Textformat

- `kritische_findings_liberty_messages.log`
  Open Liberty `messages.log` Textformat

- `kritische_findings_liberty_json.log`
  Open Liberty JSON-Logformat mit `liberty_message`

- `kritische_findings_tomcat_application.log`
  Tomcat Application Log

- `kritische_findings_apache_error.log`
  Apache Error Log Format

- `kritische_findings_kubernetes.log`
  Kubernetes/Container Log Format mit JSON-Payload

- `kritische_findings_spring_boot.log`
  Spring Boot Log Format

## Inhalt

- 20 Kategorien kritischer Informationen
- 400 synthetische Findings insgesamt
- pro Format dieselben Inhalte in unterschiedlicher technischer Darstellung

## Zweck

- Testdaten fuer Logscanner
- Vergleich unterschiedlicher Logformate
- Training und Validierung von Suchmustern
- Demo-Daten fuer Workshops und Dokumentation
