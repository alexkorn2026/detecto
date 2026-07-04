Betreff: Detecto – Warum Rentenversicherungsnummern nicht erkannt wurden (behoben in v1.6.0)

Hallo zusammen,

kurze Erklärung, warum Detecto bis v1.4 keine Rentenversicherungsnummern (VSNR) gefunden hat – und wie es behoben wurde.

**Ursache 1: Der Pre-Filter hat die Zeilen verworfen (Hauptursache).**
Detecto war mit `prefilter = all` konfiguriert. Dieser Vorfilter lässt nur Zeilen zur Analyse durch, die einen bekannten Text-Marker enthalten (z.B. "passw", "@", "jdbc:"). Für rein numerische Daten wie die VSNR gab es keinen einzigen Marker – eine Zeile wie `Antrag fuer RVNR 65 170839 J 008` wurde also verworfen, bevor die VSNR-Regel überhaupt laufen konnte. Betroffen waren auch IBAN, Kreditkarten, Steuer-ID, Telefonnummern und PLZ.

**Ursache 2: Die VSNR-Regel konnte technisch nie greifen.**
Detecto prüft reguläre Ausdrücke pro Token (Wort). Die alte Regel `^\s*\d{2}\s*\d{6}\s*[A-Z]\s*\d{2}\s*\d{1}\s*$` erwartete aber Leerzeichen und exakte Wortgrenzen:

- `65 170839 J 008` (amtliches Format) wird vom Tokenizer in vier Wörter zerlegt – keines matcht.
- `RVNR:65170839J008` bleibt ein Wort inklusive Doppelpunkt – die Anker `^`/`$` schlagen fehl.
- `65170839j008` (Kleinbuchstabe) scheiterte an `[A-Z]`.

**Behebung (v1.6.0):**

1. Zwei neue VSNR-Regeln: kompakt (`65170839J008`, auch mit angeklebtem `RVNR:`) und amtlich formatiert (`65 170839 J 008`) – letztere läuft zeilenbasiert statt tokenbasiert.
2. Der Pre-Filter lässt Zeilen mit Ziffernfolgen (≥5 Ziffern) immer durch; Standard ist jetzt `prefilter = off`.
3. `key:value` in einem Token (z.B. `RVNR:…`, `"password":"…"`) wird jetzt korrekt zerlegt.

**Verifikation:**
Im Projektordner liegt `test_findings.log` (60 Zeilen, jede Zeile liefert ein Finding). Die ersten vier Zeilen decken alle VSNR-Varianten ab:

    python3 detecto_cli.py test_findings.log --critical 2

Erwartete Ausgabe (Auszug):

    [regexp] [hoch] vsnr: 15070649m524, 65170839J008, RVNR:65170839J008
    [regexp] [hoch] vsnr_formatiert: 65 170839 J 008

Alle 104 automatisierten Tests laufen weiterhin grün.

Viele Grüße
Alex
