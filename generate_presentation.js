const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Alexander Kornbrust";
pres.title = "Detecto - Entwicklung mit Claude AI";

// === COLOR PALETTE ===
const C = {
  navy: "1E2761",
  blue: "2F5496",
  ice: "CADCFC",
  white: "FFFFFF",
  lightGray: "F5F7FA",
  gray: "6B7280",
  darkText: "1F2937",
  accent: "3B82F6",
  green: "059669",
  red: "DC2626",
  orange: "EA580C",
  yellow: "D97706",
  teal: "0891B2",
};

// === HELPERS ===
const mkShadow = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.12 });

function addDarkSlide(title, subtitle) {
  const s = pres.addSlide();
  s.background = { color: C.navy };
  // Left accent bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.08, h: 5.625, fill: { color: C.accent } });
  s.addText(title, { x: 0.8, y: 1.5, w: 8.5, h: 1.2, fontSize: 36, fontFace: "Georgia", color: C.white, bold: true, margin: 0 });
  if (subtitle) {
    s.addText(subtitle, { x: 0.8, y: 2.8, w: 8.5, h: 0.8, fontSize: 18, fontFace: "Calibri", color: C.ice, margin: 0 });
  }
  return s;
}

function addContentSlide(title) {
  const s = pres.addSlide();
  s.background = { color: C.white };
  // Top bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.blue } });
  // Title area
  s.addText(title, { x: 0.6, y: 0.2, w: 8.8, h: 0.6, fontSize: 24, fontFace: "Georgia", color: C.navy, bold: true, margin: 0 });
  // Separator line
  s.addShape(pres.shapes.LINE, { x: 0.6, y: 0.85, w: 2.5, h: 0, line: { color: C.accent, width: 2 } });
  return s;
}

function addPhaseSlide(phaseNum, title, subtitle) {
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.08, h: 5.625, fill: { color: C.accent } });
  s.addText("PHASE " + phaseNum, { x: 0.8, y: 1.0, w: 8, h: 0.6, fontSize: 16, fontFace: "Calibri", color: C.accent, charSpacing: 6, margin: 0 });
  s.addText(title, { x: 0.8, y: 1.6, w: 8.5, h: 1.2, fontSize: 34, fontFace: "Georgia", color: C.white, bold: true, margin: 0 });
  if (subtitle) {
    s.addText(subtitle, { x: 0.8, y: 2.9, w: 8.5, h: 0.8, fontSize: 16, fontFace: "Calibri", color: C.ice, margin: 0 });
  }
  return s;
}

function bullets(items, opts = {}) {
  return items.map((item, i) => ({
    text: item,
    options: { bullet: true, breakLine: i < items.length - 1, fontSize: opts.fontSize || 14, fontFace: "Calibri", color: opts.color || C.darkText, indentLevel: opts.indent || 0 }
  }));
}

function addCard(slide, x, y, w, h, title, bodyLines, accentColor) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.white }, shadow: mkShadow() });
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.06, h, fill: { color: accentColor || C.accent } });
  slide.addText(title, { x: x + 0.2, y: y + 0.1, w: w - 0.3, h: 0.4, fontSize: 14, fontFace: "Calibri", color: C.navy, bold: true, margin: 0 });
  if (bodyLines && bodyLines.length > 0) {
    slide.addText(bullets(bodyLines, { fontSize: 11 }), { x: x + 0.2, y: y + 0.45, w: w - 0.35, h: h - 0.55, margin: 0 });
  }
}

function addSummarySlide(title, items) {
  const s = addContentSlide(title);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.1, w: 8.8, h: items.length * 0.4 + 0.4, fill: { color: C.lightGray }, shadow: mkShadow() });
  s.addText(bullets(items, { fontSize: 14 }), { x: 0.9, y: 1.3, w: 8.2, h: items.length * 0.4, margin: 0 });
  return s;
}

function addPromptSlide(title, promptText) {
  const s = addContentSlide(title);
  // Prompt box with quote style
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.15, w: 8.8, h: 3.5, fill: { color: "F0F4FF" }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.15, w: 0.06, h: 3.5, fill: { color: C.accent } });
  s.addText("PROMPT", { x: 0.9, y: 1.25, w: 2, h: 0.35, fontSize: 11, fontFace: "Calibri", color: C.accent, charSpacing: 4, margin: 0 });
  s.addText(promptText, { x: 0.9, y: 1.6, w: 8.2, h: 2.9, fontSize: 13, fontFace: "Calibri", color: C.darkText, italic: true, valign: "top", margin: 0 });
  return s;
}

function addStatBox(slide, x, y, number, label, color) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.0, h: 1.2, fill: { color: C.white }, shadow: mkShadow() });
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.0, h: 0.06, fill: { color: color || C.accent } });
  slide.addText(number, { x, y: y + 0.15, w: 2.0, h: 0.6, fontSize: 32, fontFace: "Georgia", color: color || C.accent, bold: true, align: "center", margin: 0 });
  slide.addText(label, { x, y: y + 0.75, w: 2.0, h: 0.35, fontSize: 11, fontFace: "Calibri", color: C.gray, align: "center", margin: 0 });
}

// ============================================================
// SLIDE 1 - TITLE
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.navy } });
  // Decorative elements
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.8, w: 10, h: 0.06, fill: { color: C.accent } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.08, h: 5.625, fill: { color: C.accent } });
  s.addText("DETECTO", { x: 0.8, y: 0.8, w: 8, h: 1.0, fontSize: 52, fontFace: "Georgia", color: C.white, bold: true, charSpacing: 8, margin: 0 });
  s.addText("Entwicklung einer Log-Analyse-Software\nmit Claude AI", { x: 0.8, y: 1.9, w: 8, h: 1.0, fontSize: 22, fontFace: "Calibri", color: C.ice, margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 0.8, y: 3.1, w: 3, h: 0, line: { color: C.accent, width: 2 } });
  s.addText("Alexander Kornbrust", { x: 0.8, y: 3.4, w: 5, h: 0.4, fontSize: 16, fontFace: "Calibri", color: C.white, margin: 0 });
  s.addText("April 2026", { x: 0.8, y: 3.85, w: 5, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.ice, margin: 0 });
  // Bottom stats
  addStatBox(s, 0.8, 4.2, "121", "Prompts", C.accent);
  addStatBox(s, 3.1, 4.2, "v1.4", "Version", C.teal);
  addStatBox(s, 5.4, 4.2, "2.058", "Lines of Code", C.green);
  addStatBox(s, 7.7, 4.2, "92", "Tests", C.orange);
}

// ============================================================
// SLIDE 2 - AGENDA
// ============================================================
{
  const s = addContentSlide("Agenda");
  const items = [
    ["1", "Einleitung", "Was ist Detecto und warum?"],
    ["2", "Phase 1: Grundlagen", "v0.1-v0.5 | Prompts 1-42"],
    ["3", "Phase 2: Field-Erkennung", "v0.5-v0.9 | Prompts 43-88"],
    ["4", "Phase 3: Modularisierung", "v1.0 | Prompts 89-117"],
    ["5", "Phase 4: Performance", "v1.2-v1.4 | Prompts 118-121"],
    ["6", "Erzeugte Dokumente", "Word, Excel, Markdown"],
    ["7", "Technische Architektur", "Module, Datenfluss, Security"],
    ["8", "Erkenntnisse & Fazit", "Lessons Learned"],
  ];
  items.forEach((item, i) => {
    const yy = 1.15 + i * 0.53;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 0.5, h: 0.43, fill: { color: C.navy } });
    s.addText(item[0], { x: 0.6, y: yy, w: 0.5, h: 0.43, fontSize: 16, fontFace: "Georgia", color: C.white, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(item[1], { x: 1.3, y: yy, w: 3.5, h: 0.43, fontSize: 15, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(item[2], { x: 5.0, y: yy, w: 4.5, h: 0.43, fontSize: 13, fontFace: "Calibri", color: C.gray, valign: "middle", margin: 0 });
  });
}

// ============================================================
// SLIDE 3 - WAS IST DETECTO?
// ============================================================
{
  const s = addContentSlide("Was ist Detecto?");
  addCard(s, 0.6, 1.15, 4.1, 2.0, "Log-Scanner", [
    "Python 3.9+ Anwendung",
    "Scannt Log-Dateien automatisch",
    "Erkennt kritische Daten",
    "Erkennt personenbezogene Daten",
    "MIT-Lizenz, Open Source"
  ], C.blue);
  addCard(s, 5.1, 1.15, 4.3, 2.0, "Unterstuetzte Log-Formate", [
    "WebSphere / Liberty",
    "Apache / Tomcat",
    "Spring Boot",
    "Kubernetes",
    "JSON-Logs"
  ], C.teal);
  addCard(s, 0.6, 3.4, 8.8, 1.8, "3 Erkennungstechniken", [
    "Regexp-Muster: Email, JWT, SSH-Keys, Kreditkarten, IBAN, ...",
    "Field-Erkennung: Passwort-Felder, API-Keys, Tokens, Credentials",
    "String-Suche: Vornamen, Nachnamen, Orte, Diagnosen, Sicherheitsbegriffe"
  ], C.accent);
}

// ============================================================
// SLIDE 4 - WARUM DETECTO?
// ============================================================
{
  const s = addContentSlide("Warum Detecto?");
  s.addText("Sensible Daten in Log-Dateien sind ein ernstes Sicherheitsrisiko", { x: 0.6, y: 1.15, w: 8.8, h: 0.5, fontSize: 15, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.8, 2.7, 1.7, "Sicherheit", [
    "Passwoerter im Klartext",
    "API-Keys und Tokens",
    "SSH/TLS Private Keys",
    "Session-IDs"
  ], C.red);
  addCard(s, 3.65, 1.8, 2.7, 1.7, "Compliance", [
    "DSGVO / GDPR",
    "Personenbezogene Daten",
    "Gesundheitsdaten",
    "Meldepflichten"
  ], C.orange);
  addCard(s, 6.7, 1.8, 2.7, 1.7, "Finanzdaten", [
    "Kreditkartennummern",
    "IBAN / Bankdaten",
    "Steuer-IDs",
    "Versicherungsnummern"
  ], C.yellow);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.8, w: 8.8, h: 1.4, fill: { color: "FEF2F2" } });
  s.addText([
    { text: "Risiko: ", options: { bold: true, color: C.red, fontSize: 14 } },
    { text: "Log-Dateien werden oft zentral gesammelt (ELK-Stack), archiviert und an Dritte weitergegeben. Sensible Daten koennten dabei unkontrolliert verbreitet werden.", options: { fontSize: 14, color: C.darkText } }
  ], { x: 0.9, y: 3.9, w: 8.2, h: 1.2, fontFace: "Calibri", valign: "top", margin: 0 });
}

// ============================================================
// SLIDE 5 - ENTWICKLUNGSANSATZ
// ============================================================
{
  const s = addContentSlide("Entwicklungsansatz: AI-gestuetzte Entwicklung");
  s.addText("Von der Idee zur produktionsreifen Software mit Claude AI", { x: 0.6, y: 1.15, w: 8.8, h: 0.4, fontSize: 15, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  // Timeline
  const steps = [
    { num: "1", label: "Prompt", desc: "Anforderung\nbeschreiben" },
    { num: "2", label: "Generate", desc: "Claude erzeugt\nCode" },
    { num: "3", label: "Test", desc: "Ergebnis\npruefen" },
    { num: "4", label: "Iterate", desc: "Verfeinern &\nerweitern" },
  ];
  steps.forEach((st, i) => {
    const xx = 0.8 + i * 2.3;
    s.addShape(pres.shapes.RECTANGLE, { x: xx, y: 1.8, w: 1.8, h: 1.5, fill: { color: C.lightGray }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: xx, y: 1.8, w: 1.8, h: 0.06, fill: { color: C.accent } });
    s.addText(st.num, { x: xx, y: 1.9, w: 1.8, h: 0.4, fontSize: 22, fontFace: "Georgia", color: C.accent, bold: true, align: "center", margin: 0 });
    s.addText(st.label, { x: xx, y: 2.3, w: 1.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.navy, bold: true, align: "center", margin: 0 });
    s.addText(st.desc, { x: xx, y: 2.65, w: 1.8, h: 0.55, fontSize: 11, fontFace: "Calibri", color: C.gray, align: "center", margin: 0 });
    if (i < 3) {
      s.addText(">", { x: xx + 1.85, y: 2.1, w: 0.4, h: 0.5, fontSize: 24, color: C.accent, align: "center", valign: "middle", margin: 0 });
    }
  });
  // Stats
  addStatBox(s, 0.6, 3.8, "121", "Prompts insgesamt", C.accent);
  addStatBox(s, 3.0, 3.8, "4", "Entwicklungsphasen", C.teal);
  addStatBox(s, 5.4, 3.8, "3 Tage", "Entwicklungszeit", C.green);
  addStatBox(s, 7.8, 3.8, "v1.4", "Finale Version", C.orange);
}

// ============================================================
// PHASE 1 - GRUNDLAGEN (Folien 6-15)
// ============================================================
addPhaseSlide("1", "Grundlagen", "v0.1 - v0.5  |  Prompts 1-42  |  Erste Scanning-Funktionalitaet");

// Slide 7 - Phase 1 Uebersicht
{
  const s = addContentSlide("Phase 1: Ueberblick");
  s.addText("42 Prompts fuer die Grundfunktionen", { x: 0.6, y: 1.15, w: 8.8, h: 0.4, fontSize: 15, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.7, 4.1, 1.6, "Kernfunktionen", [
    "Log-Dateien einlesen und tokenisieren",
    "Regexp-basierte Suche (regexp.csv)",
    "String-basierte Suche (Woerterbuecher)",
    "Konsolenausgabe mit Farbhervorhebung"
  ], C.blue);
  addCard(s, 5.1, 1.7, 4.3, 1.6, "CLI-Parameter", [
    "--help, --examplecount, --anon",
    "--full, --minlen, --status",
    "--logresult, --logresultanon",
    "--nocolor"
  ], C.teal);
  addCard(s, 0.6, 3.55, 4.1, 1.6, "Datenbereinigung", [
    "3.436 Vornamen bereinigt",
    "4.051 Nachnamen bereinigt",
    "4.502 Orte bereinigt",
    "Duplikate und Ueberschneidungen entfernt"
  ], C.green);
  addCard(s, 5.1, 3.55, 4.3, 1.6, "Dokumentation", [
    "readme.md - Projektdokumentation",
    "firststeps.md - Schnellstartanleitung",
    "changelog.md - Versionshistorie",
    "prompt_documentation.md"
  ], C.orange);
}

// Slide 8 - Prompt 1 Der Startschuss
{
  const s = addPromptSlide("Prompt 1 - Der Startschuss");
  s.addText("\"Es soll eine neue Python 3.9 Anwendung unter MIT Lizenz erstellt werden, welche mehrere Log-Dateien (Websphere/Liberty) nach dem Vorhandensein von kritischen Daten durchsucht (z.B. personenbezogene Daten, schuetzenswerte Daten, ...) und diese identifiziert. Die Logs werden zuerst gelesen, dann in einzelne Token aufgesplittet und danach die aufgesplitteten Token nach einer Liste von Regexp bzw. festen Strings durchsucht.\"", { x: 0.9, y: 1.6, w: 8.2, h: 2.9, fontSize: 13, fontFace: "Calibri", color: C.darkText, italic: true, valign: "top", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.85, w: 8.8, h: 0.5, fill: { color: "EFF6FF" } });
  s.addText("Dieser eine Prompt legte den Grundstein fuer die gesamte Anwendung", { x: 0.9, y: 4.85, w: 8.2, h: 0.5, fontSize: 13, fontFace: "Calibri", color: C.blue, bold: true, valign: "middle", margin: 0 });
}

// Slide 9 - Erste Ergebnisse
{
  const s = addContentSlide("Erste Ergebnisse (Prompts 2-6)");
  const items = [
    ["Prompt 2", "test.log angepasst, erneut laufen lassen"],
    ["Prompt 3", "Versicherungsnummern erkennen (mehrteilige Token)"],
    ["Prompt 4", "Aufruf und Output des Programms zeigen"],
    ["Prompt 5", "Aktualisierte Suchmuster, case-insensitive Suche"],
    ["Prompt 6", "Art der Erkennung anzeigen: [regexp] / [string], Header mit Version"],
  ];
  items.forEach((item, i) => {
    const yy = 1.15 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.6, fill: { color: i % 2 === 0 ? C.lightGray : C.white } });
    s.addText(item[0], { x: 0.8, y: yy, w: 1.6, h: 0.6, fontSize: 13, fontFace: "Calibri", color: C.accent, bold: true, valign: "middle", margin: 0 });
    s.addText(item[1], { x: 2.5, y: yy, w: 6.7, h: 0.6, fontSize: 13, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.85, w: 8.8, h: 0.5, fill: { color: "EFF6FF" } });
  s.addText("Iterativer Prozess: Kleine Schritte, sofortiges Feedback, kontinuierliche Verbesserung", { x: 0.9, y: 4.85, w: 8.2, h: 0.5, fontSize: 12, fontFace: "Calibri", color: C.blue, italic: true, valign: "middle", margin: 0 });
}

// Slide 10 - CLI Parameter
{
  const s = addContentSlide("CLI-Parameter (Prompts 7-11)");
  const params = [
    ["--help", "Hilfeseite anzeigen", "7-8"],
    ["--examplecount=N", "Anzahl der Beispiele pro Finding", "7"],
    ["--anon", "Anonymisierung (sss**sss**sss**)", "9"],
    ["--full", "Log-Zeilen mit Farbhervorhebung", "10"],
  ];
  // Table
  const tableRows = [
    [
      { text: "Parameter", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
      { text: "Beschreibung", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
      { text: "Prompt", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
    ],
    ...params.map(p => [
      { text: p[0], options: { fontSize: 12, fontFace: "Consolas", color: C.darkText } },
      { text: p[1], options: { fontSize: 12, fontFace: "Calibri", color: C.darkText } },
      { text: p[2], options: { fontSize: 12, fontFace: "Calibri", color: C.gray, align: "center" } },
    ])
  ];
  s.addTable(tableRows, { x: 0.6, y: 1.15, w: 8.8, colW: [3.0, 4.5, 1.3], border: { pt: 0.5, color: "DEE2E6" }, rowH: [0.4, 0.4, 0.4, 0.4, 0.4] });
  // Anonymisierung Beispiel
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.5, w: 8.8, h: 1.5, fill: { color: C.lightGray }, shadow: mkShadow() });
  s.addText("Anonymisierung - Beispiel:", { x: 0.9, y: 3.6, w: 8, h: 0.35, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, margin: 0 });
  s.addText([
    { text: "Original:      ", options: { fontFace: "Consolas", fontSize: 12, color: C.gray, breakLine: true } },
    { text: "max.mustermann@firma.de", options: { fontFace: "Consolas", fontSize: 12, color: C.red, breakLine: true } },
    { text: "Anonymisiert:  ", options: { fontFace: "Consolas", fontSize: 12, color: C.gray, breakLine: true } },
    { text: "max**ust**man**fir**de", options: { fontFace: "Consolas", fontSize: 12, color: C.green } },
  ], { x: 0.9, y: 4.0, w: 8, h: 0.9, margin: 0 });
}

// Slide 11 - Suchmuster-Optimierung
{
  const s = addContentSlide("Suchmuster-Optimierung (Prompts 12-24)");
  s.addText("13 Prompts fuer die Bereinigung der Woerterbuecher", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.65, 4.1, 2.0, "Orte bereinigen (Prompts 12-22)", [
    "CSV auf 1 Spalte reduzieren",
    "Zusaetze entfernen (Universitaetsstadt)",
    "Mehrteilige Namen kuerzen",
    "Bad/St./Sankt Praefix entfernen",
    "Strings nach Bindestrich entfernen"
  ], C.blue);
  addCard(s, 5.1, 1.65, 4.3, 2.0, "Vornamen/Nachnamen (Prompts 23-24)", [
    "Bindestrich-Suffixe entfernen",
    "Duplikate aus allen CSVs entfernen",
    "Ueberschneidungen Vornamen/Orte",
    "Ueberschneidungen Nachnamen/Orte",
    "Ueberschneidungen Vornamen/Nachnamen"
  ], C.teal);
  // Stats
  addStatBox(s, 0.6, 3.95, "3.436", "Vornamen", C.accent);
  addStatBox(s, 3.0, 3.95, "4.051", "Nachnamen", C.teal);
  addStatBox(s, 5.4, 3.95, "4.502", "Orte", C.green);
  addStatBox(s, 7.8, 3.95, "11.989", "Gesamt", C.orange);
}

// Slide 12 - Umlaut-Normalisierung
{
  const s = addContentSlide("Umlaut-Normalisierung (Prompt 25)");
  const mappings = [
    ["ae / ae", "a"], ["oe / oe", "o"], ["ue / ue", "u"],
    ["c (Hatschek)", "c"], ["sz (ss)", "ss"], ["e (accent)", "e"]
  ];
  s.addText("Case-insensitive Suche mit Unicode-Normalisierung", { x: 0.6, y: 1.15, w: 8.8, h: 0.4, fontSize: 15, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  const tbl = [
    [
      { text: "Eingabe", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
      { text: "Normalisiert", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } }
    ],
    ...mappings.map(m => [
      { text: m[0], options: { fontSize: 13, fontFace: "Consolas" } },
      { text: m[1], options: { fontSize: 13, fontFace: "Consolas", color: C.green } }
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.7, w: 5, colW: [3, 2], border: { pt: 0.5, color: "DEE2E6" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.0, y: 1.7, w: 3.4, h: 2.5, fill: { color: "F0FDF4" }, shadow: mkShadow() });
  s.addText("Vorteil", { x: 6.2, y: 1.8, w: 3, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.green, bold: true, margin: 0 });
  s.addText(bullets([
    "Mueller findet Mueller, mueller, MUELLER",
    "Koeln findet Koeln, koeln",
    "Keine Treffer gehen verloren"
  ], { fontSize: 12 }), { x: 6.2, y: 2.2, w: 3, h: 1.8, margin: 0 });
}

// Slide 13 - Parameter-Erweiterung
{
  const s = addContentSlide("Weitere Funktionen (Prompts 26-35)");
  const items = [
    ["Prompt 26", "--status: Zusammenfassung der Suchdaten"],
    ["Prompt 27", "Header immer anzeigen"],
    ["Prompt 28", "Bugfix: Glob-Expansion fuer mehrere Logdateien"],
    ["Prompt 29", "Logname in --full Ausgabe"],
    ["Prompt 32", "Bugfix: UnicodeDecodeError bei nicht-UTF-8"],
    ["Prompt 33", "JSON-Log Unterstuetzung (Liberty JSON-Format)"],
    ["Prompt 35", "--full mit --anon: auch Log-Zeilen anonymisieren"],
  ];
  items.forEach((item, i) => {
    const yy = 1.15 + i * 0.55;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.45, fill: { color: i % 2 === 0 ? C.lightGray : C.white } });
    s.addText(item[0], { x: 0.8, y: yy, w: 1.6, h: 0.45, fontSize: 12, fontFace: "Calibri", color: C.accent, bold: true, valign: "middle", margin: 0 });
    s.addText(item[1], { x: 2.5, y: yy, w: 6.7, h: 0.45, fontSize: 12, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
}

// Slide 14 - Dokumentation Phase 1
{
  const s = addContentSlide("Dokumentation (Prompts 36-42)");
  addCard(s, 0.6, 1.15, 4.1, 2.0, "Markdown-Dokumentation", [
    "prompt_documentation.md",
    "changelog.md",
    "readme.md",
    "firststeps.md"
  ], C.blue);
  addCard(s, 5.1, 1.15, 4.3, 2.0, "Neue Features v0.5", [
    "--logresult: Ergebnis in Datei speichern",
    "--logresultanon: Anonymisiert speichern",
    "Statistik am Ende (Dateien, Zeilen, Dauer)",
    "Buendige Ausgabe-Formatierung"
  ], C.teal);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.4, w: 8.8, h: 1.0, fill: { color: "EFF6FF" } });
  s.addText("Phase 1 Ergebnis: Funktionierende Grundversion mit Regexp- und String-Suche, Anonymisierung, CLI-Parametern und vollstaendiger Dokumentation.", { x: 0.9, y: 3.5, w: 8.2, h: 0.8, fontSize: 14, fontFace: "Calibri", color: C.navy, valign: "middle", margin: 0 });
}

// ============================================================
// PHASE 2 - FIELD-ERKENNUNG (Folien 16-30)
// ============================================================
addPhaseSlide("2", "Field-Erkennung &\nKonfiguration", "v0.5 - v0.9  |  Prompts 43-88  |  Neue Erkennungstechnik, Excel-Export");

// Slide 17 - Field-Erkennung
{
  const s = addContentSlide("Field-Erkennung (Prompts 43-53)");
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.15, w: 8.8, h: 1.6, fill: { color: "FFFBEB" }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.15, w: 0.06, h: 1.6, fill: { color: C.yellow } });
  s.addText("Neue Erkennungstechnik: Field-basierte Suche", { x: 0.9, y: 1.2, w: 8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.yellow, bold: true, margin: 0 });
  s.addText(bullets([
    "field.csv: Regulaere Ausdruecke fuer kritische Feldnamen",
    "Erkennt z.B. password = GeHeIm123, identified by MySecret",
    "Separatoren (->  =>  :  =) werden automatisch uebersprungen",
    "Stopwort-Listen filtern False Positives"
  ], { fontSize: 13 }), { x: 0.9, y: 1.6, w: 8, h: 1.0, margin: 0 });

  // Example
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.0, w: 8.8, h: 1.6, fill: { color: C.lightGray }, shadow: mkShadow() });
  s.addText("Beispiel aus einem Log:", { x: 0.9, y: 3.1, w: 8, h: 0.3, fontSize: 12, fontFace: "Calibri", color: C.navy, bold: true, margin: 0 });
  s.addText([
    { text: "password", options: { fontFace: "Consolas", fontSize: 12, color: C.green, bold: true } },
    { text: " => ", options: { fontFace: "Consolas", fontSize: 12, color: C.gray } },
    { text: "Produktiv!1", options: { fontFace: "Consolas", fontSize: 12, color: C.red, bold: true } },
  ], { x: 0.9, y: 3.5, w: 8, h: 0.3, margin: 0 });
  s.addText([
    { text: "[field] Passwort ", options: { fontFace: "Calibri", fontSize: 12, color: C.yellow, bold: true } },
    { text: "[kritisch] ", options: { fontFace: "Calibri", fontSize: 12, color: C.red, bold: true } },
    { text: "Produktiv!1", options: { fontFace: "Consolas", fontSize: 12, color: C.darkText } },
  ], { x: 0.9, y: 3.9, w: 8, h: 0.3, margin: 0 });
  s.addText("11 Prompts fuer die Perfektionierung der Field-Erkennung (Stopwords, Separatoren, Oracle, PostgreSQL)", { x: 0.9, y: 4.4, w: 8, h: 0.3, fontSize: 11, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
}

// Slide 18 - 20 kritische Finding-Kategorien
{
  const s = addContentSlide("20 Kritische Finding-Kategorien (Prompt 54)");
  const cats = [
    "Klartext-Passwoerter", "API-Keys", "Access Tokens", "Refresh Tokens",
    "Session-IDs", "JSON Web Tokens", "OAuth Client Secrets", "Datenbank-Credentials",
    "SSH Private Keys", "TLS Private Keys", "Kreditkarten", "IBAN/Bankdaten",
    "Steuer-IDs", "Reisepass/Personalausweis", "E-Mail-Adressen", "Telefonnummern",
    "Postadressen", "Geburtsdaten", "Gesundheitsdaten", "Sicherheitsrelevante Infos"
  ];
  cats.forEach((cat, i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const xx = 0.6 + col * 2.3;
    const yy = 1.15 + row * 0.75;
    const colors = [C.red, C.red, C.orange, C.orange, C.yellow];
    s.addShape(pres.shapes.RECTANGLE, { x: xx, y: yy, w: 2.1, h: 0.6, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: xx, y: yy, w: 0.05, h: 0.6, fill: { color: colors[row] || C.accent } });
    s.addText((i + 1) + ". " + cat, { x: xx + 0.12, y: yy, w: 1.95, h: 0.6, fontSize: 10, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  s.addText("Basierend auf kritische_logdaten_findings.md mit je 20 Beispielen pro Kategorie", { x: 0.6, y: 5.0, w: 8.8, h: 0.35, fontSize: 11, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
}

// Slide 19 - Drei Erkennungstechniken
{
  const s = addContentSlide("Drei Erkennungstechniken im Ueberblick");
  addCard(s, 0.6, 1.15, 2.8, 3.8, "Regexp (12 Muster)", [
    "E-Mail-Adressen",
    "Versicherungsnummern",
    "Strassennamen",
    "JSON Web Tokens",
    "SSH Private Keys",
    "TLS Private Keys",
    "Kreditkarten",
    "IBAN",
    "Steuer-IDs",
    "Telefonnummern",
    "Postleitzahlen",
    "JDBC Connections"
  ], C.green);
  addCard(s, 3.6, 1.15, 2.8, 3.8, "Field (17 Muster)", [
    "Passwort-Felder",
    "Oracle identified by",
    "API-Keys",
    "Access/Refresh Tokens",
    "Session-IDs",
    "Client Secrets",
    "DB-Passwoerter",
    "Reisepass/Ausweis",
    "Diagnosen",
    "Geburtsdaten",
    "Generische Credentials",
    "HTTP Authorization",
    "Cloud-Keys (AWS/Azure/GCP)",
    "Proxy/SMTP/LDAP Auth"
  ], C.yellow);
  addCard(s, 6.6, 1.15, 2.8, 3.8, "String (5 Kategorien)", [
    "Vornamen (3.436)",
    "Nachnamen (4.051)",
    "Orte (4.502)",
    "Diagnosen (100)",
    "Sicherheitsbegriffe (52)"
  ], C.teal);
}

// Slide 20 - Regexp-Muster Details
{
  const s = addContentSlide("Regexp-Muster im Detail");
  const patterns = [
    ["email", "4", "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"],
    ["JWT", "1", "eyJ[A-Za-z0-9_-]+\\.eyJ[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+"],
    ["SSHPrivateKey", "1", "-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"],
    ["Kreditkarte", "1", "\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b"],
    ["IBAN", "3", "\\b[A-Z]{2}\\d{2}[\\s]?[A-Z0-9]{4}..."],
    ["JDBC", "3", "jdbc:[a-z]+://[^\\s]+"],
  ];
  const tbl = [
    [
      { text: "Name", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Krit.", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Regulaerer Ausdruck", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
    ],
    ...patterns.map(p => [
      { text: p[0], options: { fontSize: 11, fontFace: "Calibri", bold: true } },
      { text: p[1], options: { fontSize: 11, fontFace: "Calibri", align: "center", color: p[1] === "1" ? C.red : C.orange } },
      { text: p[2], options: { fontSize: 9, fontFace: "Consolas" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.15, w: 8.8, colW: [1.5, 0.6, 6.7], border: { pt: 0.5, color: "DEE2E6" } });
}

// Slide 21 - Field-Muster Details
{
  const s = addContentSlide("Field-Muster im Detail");
  const fields = [
    ["Passwort", "1", "(passw|kennw)"],
    ["OraclePasswort", "1", "\\bidentified\\b (Offset 2)"],
    ["APIKey", "1", "(api.?key|api.?token|x-api-key)"],
    ["AccessToken", "1", "(access.?token|bearer)"],
    ["SessionID", "2", "(jsessionid|session.?id)"],
    ["ClientSecret", "1", "(client.?secret)"],
    ["DBPasswort", "1", "(db\\.password|jdbc\\.password)"],
    ["CloudKey", "1", "(aws.?key|azure.?secret|gcp.?key)"],
  ];
  const tbl = [
    [
      { text: "Name", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Krit.", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Pattern", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
    ],
    ...fields.map(f => [
      { text: f[0], options: { fontSize: 11, fontFace: "Calibri", bold: true } },
      { text: f[1], options: { fontSize: 11, fontFace: "Calibri", align: "center", color: f[1] === "1" ? C.red : C.orange } },
      { text: f[2], options: { fontSize: 10, fontFace: "Consolas" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.15, w: 8.8, colW: [1.8, 0.6, 6.4], border: { pt: 0.5, color: "DEE2E6" } });
  s.addText("Gesamt: 17 Field-Muster, davon 12 mit Kritikalitaet 1 (kritisch)", { x: 0.6, y: 4.8, w: 8.8, h: 0.35, fontSize: 12, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
}

// Slide 22 - Kritikalitaetsstufen
{
  const s = addContentSlide("Kritikalitaetsstufen (Prompt 60)");
  const levels = [
    ["1", "kritisch", "FF9999", "Passwoerter, Private Keys, API-Keys"],
    ["2", "hoch", "FFCC99", "Session-IDs, Tokens"],
    ["3", "mittel", "FFFF99", "IBAN, Steuer-ID, Diagnosen"],
    ["4", "niedrig", "E2EFDA", "E-Mail, Telefon, PLZ, Strasse"],
    ["5", "info", "F5F5F5", "Vornamen, Nachnamen, Orte"],
  ];
  levels.forEach((l, i) => {
    const yy = 1.15 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.6, fill: { color: l[2] } });
    s.addText(l[0], { x: 0.8, y: yy, w: 0.5, h: 0.6, fontSize: 20, fontFace: "Georgia", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(l[1], { x: 1.4, y: yy, w: 1.5, h: 0.6, fontSize: 14, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(l[3], { x: 3.2, y: yy, w: 6, h: 0.6, fontSize: 13, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  s.addText("Parameter --critical=N filtert Findings nach Mindestkritikalitaet", { x: 0.6, y: 4.85, w: 8.8, h: 0.35, fontSize: 12, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
}

// Slide 23 - Konfiguration
{
  const s = addContentSlide("Konfiguration: detecto.ini (Prompt 63)");
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.15, w: 8.8, h: 3.8, fill: { color: C.lightGray }, shadow: mkShadow() });
  s.addText([
    { text: "[defaults]", options: { fontFace: "Consolas", fontSize: 11, color: C.accent, bold: true, breakLine: true } },
    { text: "examplecount = 10", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "minlen = 5", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "critical = 5", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "anon = false", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "search_regexp = on", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "search_field = on", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "search_suchmuster = on", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "parse_json = false", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "workers = 1", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "prefilter = all", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "[files]", options: { fontFace: "Consolas", fontSize: 11, color: C.accent, bold: true, breakLine: true } },
    { text: "regexp = regexp.csv", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText, breakLine: true } },
    { text: "field = field.csv", options: { fontFace: "Consolas", fontSize: 11, color: C.darkText } },
  ], { x: 0.9, y: 1.25, w: 8.2, h: 3.6, valign: "top", margin: 0 });
}

// Slide 24 - Excel-Export Uebersicht
{
  const s = addContentSlide("Excel-Export (Prompts 70-82)");
  s.addText("13 Prompts fuer den vollstaendigen Excel-Export", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  const sheets = [
    ["Findings", "Hauptuebersicht mit Kundenbearbeitungs-Spalten", C.red],
    ["Full", "Vollstaendige Log-Zeilen mit Farbmarkierung", C.orange],
    ["Tool", "Scan-Informationen und Konfiguration", C.blue],
    ["Regexp", "Alle Regexp-Muster mit Beschreibung", C.green],
    ["Field", "Alle Field-Muster mit Beschreibung", C.yellow],
    ["String", "Alle String-Kategorien mit Anzahl", C.teal],
  ];
  sheets.forEach((sh, i) => {
    const yy = 1.7 + i * 0.6;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.5, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 0.06, h: 0.5, fill: { color: sh[2] } });
    s.addText(sh[0], { x: 0.9, y: yy, w: 1.8, h: 0.5, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(sh[1], { x: 2.8, y: yy, w: 6.4, h: 0.5, fontSize: 13, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  s.addText("Parameter: --xlsx erzeugt Excel-Datei, --excelanon anonymisiert Werte im Excel", { x: 0.6, y: 5.0, w: 8.8, h: 0.35, fontSize: 11, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
}

// Slide 25 - Excel Rich Text Probleme
{
  const s = addContentSlide("Excel-Kompatibilitaet (Prompts 79-82)");
  s.addText("4 Iterationen fuer Excel-Reparaturmeldungen", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.7, 4.1, 2.0, "Problem", [
    "CellRichText erzeugte fehlerhaftes XML",
    "Excel meldete Reparaturbedarf",
    "<b val=\"1\"/> statt <b/>",
    "Falsche Tag-Reihenfolge in rPr"
  ], C.red);
  addCard(s, 5.1, 1.7, 4.3, 2.0, "Loesung (Prompt 87)", [
    "Rich Text komplett entfernt",
    "Plain-Text mit >>>WERT<<< Markierung",
    "PatternFill fuer Farbmarkierung",
    "Keine Reparaturmeldung mehr"
  ], C.green);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.0, w: 8.8, h: 0.8, fill: { color: "FEF2F2" } });
  s.addText("Lesson Learned: Einfache Loesungen (Plain-Text + Hintergrundfarben) sind robuster als komplexe (Rich Text XML)", { x: 0.9, y: 4.1, w: 8.2, h: 0.6, fontSize: 13, fontFace: "Calibri", color: C.red, valign: "middle", margin: 0 });
}

// Slide 26 - Bugfixes & Tests Prompt 87
{
  const s = addContentSlide("Bugfixes & Testsuite (Prompt 87)");
  addCard(s, 0.6, 1.15, 4.1, 2.0, "4 Bugfixes", [
    "Excel-Export: Rich Text -> Plain-Text",
    "anon_muster Crash bei leerem Muster",
    "Field-Separatoren korrekt ueberspringen",
    "JSON-Fragmente vollstaendig erhalten"
  ], C.red);
  addCard(s, 5.1, 1.15, 4.3, 2.0, "34 Tests erstellt", [
    "TestAnonMuster (Anonymisierung)",
    "TestFieldErkennung (Feld-Suche)",
    "TestTokenisierung (JSON-Parsing)",
    "TestXlsxExport (Excel-Ausgabe)",
    "TestEndToEnd (Integration)"
  ], C.green);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.4, w: 8.8, h: 1.0, fill: { color: "EFF6FF" } });
  s.addText("Phase 2 Ergebnis: Field-Erkennung, Kritikalitaet, Excel-Export, Konfiguration und erste Testsuite", { x: 0.9, y: 3.5, w: 8.2, h: 0.8, fontSize: 14, fontFace: "Calibri", color: C.navy, valign: "middle", margin: 0 });
}

// ============================================================
// PHASE 3 - MODULARISIERUNG & SECURITY (Folien 27-40)
// ============================================================
addPhaseSlide("3", "Modularisierung &\nSecurity-Hardening", "v1.0 - v1.1  |  Prompts 89-117  |  Produktionsreife Software");

// Slide 28 - Komplett-Refactoring
{
  const s = addContentSlide("Komplett-Refactoring (Prompt 89)");
  s.addText([
    { text: "Monolithisch: ", options: { bold: true, color: C.red, fontSize: 15 } },
    { text: "1 Datei, 1.255 Zeilen", options: { fontSize: 15, color: C.darkText } },
    { text: "  -->  ", options: { fontSize: 15, color: C.gray } },
    { text: "Modular: ", options: { bold: true, color: C.green, fontSize: 15 } },
    { text: "10 Module", options: { fontSize: 15, color: C.darkText } },
  ], { x: 0.6, y: 1.15, w: 8.8, h: 0.5, fontFace: "Calibri", margin: 0 });
  const modules = [
    ["config.py", "DetectoConfig Dataclass, INI-Laden"],
    ["utils.py", "normalize(), find_logfiles(), krit_color()"],
    ["anonymizer.py", "Anonymizer-Klasse"],
    ["loaders.py", "Pattern-Laden mit Validierung"],
    ["tokenizer.py", "Tokenisierung, JSON-Extraktion"],
    ["analyzer.py", "LogAnalyzer (Kern-Engine)"],
    ["formatter.py", "Konsolen-Ausgabe, Farben"],
    ["exporter.py", "Excel + Log-Export"],
    ["cli.py", "parse_args(), main()"],
    ["__main__.py", "Entry-Point"],
  ];
  const tbl = [
    [
      { text: "Modul", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Verantwortlichkeit", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
    ],
    ...modules.map(m => [
      { text: m[0], options: { fontSize: 11, fontFace: "Consolas", color: C.accent } },
      { text: m[1], options: { fontSize: 11, fontFace: "Calibri" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.8, w: 8.8, colW: [2.2, 6.6], border: { pt: 0.5, color: "DEE2E6" } });
}

// Slide 29 - AI Slop
{
  const s = addContentSlide("AI Slop erkennen & korrigieren (Prompts 93-94)");
  addCard(s, 0.6, 1.15, 4.1, 2.5, "Gefundene Probleme", [
    "5x AI-typische Trenn-Kommentare",
    "4x untypisierte Type-Hints (object/list)",
    "6x Magic Numbers im Code",
    "Sprach-Inkonsistenzen (DE/EN)",
    "2x DRY-Verletzungen",
    "Fehlende Dokumentation"
  ], C.red);
  addCard(s, 5.1, 1.15, 4.3, 2.5, "Korrekturen", [
    "Trenn-Kommentare entfernt",
    "krit_farbe() nach utils.py (DRY)",
    "Magic Numbers -> Konstanten",
    "LABEL_WIDTH, _KRIT_COLORS",
    "Docstrings mit Args ergaenzt",
    "Konsistente Sprache (Englisch)"
  ], C.green);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.9, w: 8.8, h: 0.8, fill: { color: "FFFBEB" } });
  s.addText("Lesson Learned: AI-generierter Code muss gezielt auf typische Schwaechen geprueft werden", { x: 0.9, y: 4.0, w: 8.2, h: 0.6, fontSize: 13, fontFace: "Calibri", color: C.yellow, bold: true, valign: "middle", margin: 0 });
}

// Slide 30 - Security-Hardening
{
  const s = addContentSlide("Security-Hardening (Prompt 96)");
  const secItems = [
    ["Regex DoS Protection", "SIGALRM Timeout (2 Sek.) fuer Regexp-Kompilierung", C.red],
    ["Path Traversal Prevention", "Path.resolve() validiert alle Dateipfade", C.orange],
    ["CSV/Excel Injection", "_sanitize_cell() escaped Formelzeichen (=, +, -, @)", C.yellow],
    ["Memory Limits", "MAX_HITS_PER_PATTERN = 10.000", C.blue],
    ["UTF-8 Safety", "Binary Reading mit Warnung bei Non-UTF-8", C.teal],
  ];
  secItems.forEach((item, i) => {
    const yy = 1.15 + i * 0.75;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.65, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 0.06, h: 0.65, fill: { color: item[2] } });
    s.addText(item[0], { x: 0.9, y: yy, w: 3.0, h: 0.65, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(item[1], { x: 4.0, y: yy, w: 5.2, h: 0.65, fontSize: 12, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  addStatBox(s, 1.5, 4.3, "62", "Tests nach Security", C.red);
  addStatBox(s, 4.0, 4.3, "69", "Tests nach Feinschliff", C.green);
}

// Slide 31 - Benutzer-Perspektive
{
  const s = addContentSlide("Benutzer-Perspektive (Prompt 100)");
  s.addText("Rollenwechsel: Claude analysiert Detecto als ELK-Team-Benutzer", { x: 0.6, y: 1.15, w: 8.8, h: 0.4, fontSize: 15, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.7, 4.1, 2.0, "Was funktioniert gut?", [
    "28 Pattern (12 Regexp, 11 Field, 5 String)",
    "Farbige Konsolenausgabe",
    "Excel-Export mit 6 Sheets",
    "Konfigurierbare Kritikalitaet"
  ], C.green);
  addCard(s, 5.1, 1.7, 4.3, 2.0, "Identifizierte Luecken", [
    "Regexp-Anker erzwingen Vollmatch",
    "Fehlende Feldnamen (pwd/secret)",
    "Kreditkarte/IBAN ohne Leerzeichen",
    "Keine Cloud-Provider-Keys",
    "Wenig Diagnosen (nur 10)",
    "Wenig Sicherheitsbegriffe (nur 8)"
  ], C.red);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.0, w: 8.8, h: 0.7, fill: { color: "EFF6FF" } });
  s.addText("Diese Analyse fuehrte zum Verbesserungskonzept mit 10 Massnahmen in 4 Phasen", { x: 0.9, y: 4.1, w: 8.2, h: 0.5, fontSize: 13, fontFace: "Calibri", color: C.blue, valign: "middle", margin: 0 });
}

// Slide 32 - Verbesserungskonzept
{
  const s = addContentSlide("Verbesserungskonzept (Prompt 101)");
  s.addText("Detecto_Verbesserungskonzept.docx - 10 Massnahmen, 4 Phasen", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  const phases = [
    ["Phase 1", "Quick Wins", "Regexp-Anker, Field-Pattern, Formate, Woerterbuecher", C.green],
    ["Phase 2", "Tokenizer", "Credentials aus URLs, Base64-Erkennung", C.blue],
    ["Phase 3", "Heuristik", "Entropy-Analyse fuer unbekannte Secrets", C.orange],
    ["Phase 4", "Liberty", "Message-Codes, Plugin-System", C.red],
  ];
  phases.forEach((p, i) => {
    const yy = 1.7 + i * 0.8;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.65, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 0.06, h: 0.65, fill: { color: p[3] } });
    s.addText(p[0], { x: 0.9, y: yy, w: 1.2, h: 0.65, fontSize: 13, fontFace: "Calibri", color: p[3], bold: true, valign: "middle", margin: 0 });
    s.addText(p[1], { x: 2.2, y: yy, w: 1.8, h: 0.65, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(p[2], { x: 4.2, y: yy, w: 5.0, h: 0.65, fontSize: 12, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  addStatBox(s, 3.0, 4.2, "~45h", "Geschaetzter Aufwand", C.accent);
  addStatBox(s, 5.5, 4.2, "6 Wochen", "Geplante Dauer", C.teal);
}

// Slide 33 - Quick Wins umgesetzt
{
  const s = addContentSlide("Quick Wins umgesetzt (Prompts 103-107)");
  const wins = [
    ["Prompt 103", "Regexp-Anker entfernt", "6 Pattern: Email, JWT, Kreditkarte, IBAN, Steuer-ID, PLZ"],
    ["Prompt 104", "6 neue Field-Pattern", "Credential, AuthHeader, CloudKey, ProxyAuth, SmtpAuth, BindPW"],
    ["Prompt 105", "Formatvarianten", "Kreditkarte/IBAN mit Leerzeichen/Bindestrichen"],
    ["Prompt 106", "Woerterbuecher erweitert", "Diagnosen: 10 -> 100, Sicherheitsbegriffe: 8 -> 52"],
    ["Prompt 107", "URL-Credentials", "Extrahiert User+Passwort aus JDBC/HTTP/Proxy-URLs"],
  ];
  const tbl = [
    [
      { text: "Prompt", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Massnahme", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Details", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
    ],
    ...wins.map(w => [
      { text: w[0], options: { fontSize: 11, fontFace: "Calibri", color: C.accent, bold: true } },
      { text: w[1], options: { fontSize: 11, fontFace: "Calibri", bold: true } },
      { text: w[2], options: { fontSize: 11, fontFace: "Calibri" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.15, w: 8.8, colW: [1.3, 2.5, 5.0], border: { pt: 0.5, color: "DEE2E6" } });
  s.addText("Field-Muster: 11 -> 17 | Diagnosen: 10 -> 100 | Sicherheitsbegriffe: 8 -> 52", { x: 0.6, y: 4.5, w: 8.8, h: 0.35, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, margin: 0 });
}

// Slide 34 - Datenarten-Erkennungsmatrix
{
  const s = addContentSlide("Datenarten-Erkennungsmatrix (Prompts 108-113)");
  s.addText("Datenarten_Erkennungsmatrix.xlsx", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addStatBox(s, 0.6, 1.7, "166", "Datenvarianten", C.accent);
  addStatBox(s, 3.0, 1.7, "16", "Kategorien", C.teal);
  addStatBox(s, 5.4, 1.7, "18", "RV-spezifisch", C.green);
  addStatBox(s, 7.8, 1.7, "0", "Nicht erkannt", C.red);
  addCard(s, 0.6, 3.2, 4.1, 2.0, "3 Excel-Sheets", [
    "Uebersicht: Zusammenfassung",
    "Detailmatrix: 166 Varianten",
    "Statistik: Erkennungsquote"
  ], C.blue);
  addCard(s, 5.1, 3.2, 4.3, 2.0, "RV-spezifische Datenarten", [
    "Versicherungsverlauf, Entgeltpunkte",
    "Rentenart, Rentenbescheid, DEUEV",
    "Grundrente, Flexi-Rente, Riester/bAV",
    "Nachversicherung, Auslandsrente, BBG"
  ], C.orange);
}

// Slide 35 - Zielgruppen-Dokumente
{
  const s = addContentSlide("3 Zielgruppen-Dokumente (Prompt 114)");
  addCard(s, 0.6, 1.15, 8.8, 1.15, "Dok1: Datenschutz-Pruefscope", [
    "Pruefscope, Datenarten-Katalog, Pruefauftrag-Vorlage, Massnahmen, Meldepflichten"
  ], C.blue);
  addCard(s, 0.6, 2.5, 8.8, 1.15, "Dok2: ELK-Betriebshandbuch", [
    "Installation, Scan, Excel-Report, Verschluesselung, Ruecklaeufer, Pattern-Pflege, Troubleshooting"
  ], C.teal);
  addCard(s, 0.6, 3.85, 8.8, 1.15, "Dok3: Fachbereich Finding-Bewertung", [
    "Excel verstehen, Findings bewerten, Bewertungsbeispiele, Massnahmen im Verfahren"
  ], C.orange);
}

// ============================================================
// PHASE 4 - PERFORMANCE (Folien 36-45)
// ============================================================
addPhaseSlide("4", "Performance-Optimierung", "v1.2 - v1.4  |  Prompts 118-121  |  Von 165k auf 700k+ Zeilen/Sek.");

// Slide 37 - Version 1.2
{
  const s = addContentSlide("Version 1.2: Multiprocessing (Prompt 118)");
  addCard(s, 0.6, 1.15, 4.1, 2.5, "Neue Features", [
    "Multiprocessing fuer mehrere Dateien",
    "Pre-Filter (off / regexp_field / all)",
    "JSON-Parsing konfigurierbar",
    "LRU-Cache fuer normalize()",
    "Konfigurierbar via detecto.ini"
  ], C.blue);
  addCard(s, 5.1, 1.15, 4.3, 2.5, "Pre-Filter Modi", [
    "off: Kein Filter (alle Zeilen pruefen)",
    "regexp_field: Nur Regexp+Field pruefen",
    "all: Alle Techniken vorfiltern",
    "regexp_field: ~15-25% schneller",
    "all: ~30-50% schneller"
  ], C.teal);
  addStatBox(s, 1.5, 4.0, "2.5-7x", "Speedup", C.green);
  addStatBox(s, 4.0, 4.0, "~258k", "Zeilen/Sek.", C.accent);
}

// Slide 38 - Version 1.3
{
  const s = addContentSlide("Version 1.3: Reverse-Index (Prompt 119)");
  addCard(s, 0.6, 1.15, 4.1, 2.5, "Optimierungen", [
    "Reverse-Index dict fuer O(1) Matching",
    "Ersetzt Aho-Corasick-Missbrauch",
    "Single-Pass Token-Verarbeitung",
    "Min-Length Guards (<5 / <3 Zeichen)",
    "Chunk-basierte Parallelisierung >10MB"
  ], C.blue);
  addCard(s, 5.1, 1.15, 4.3, 2.5, "Reverse-Index Prinzip", [
    "Dict: Wert -> [Pattern-Name]",
    "hamburg -> [Ort]",
    "mueller -> [Nachnamen]",
    "O(1) Lookup pro Token",
    "Statt O(n) Schleife ueber alle Muster"
  ], C.teal);
  addStatBox(s, 1.5, 4.0, "~507k", "Z/s mit Prefilter", C.green);
  addStatBox(s, 4.0, 4.0, "92", "Tests (20 neue)", C.accent);
  addStatBox(s, 6.5, 4.0, "0", "Neue Dependencies", C.orange);
}

// Slide 39 - Version 1.4
{
  const s = addContentSlide("Version 1.4: Hot-Path-Optimierung (Prompt 120)");
  const opts = [
    ["Method-Inlining", "~1 Mrd. Methodenaufrufe eliminiert"],
    ["Lokale Variable-Caches", "self.*-Lookups vor Token-Schleife"],
    ["ASCII-Fast-Path", "str.isascii() fuer ~80% der Tokens"],
    ["findall statt split", "Direkt saubere Token-Liste"],
    ["Prefilter-Konstanten", "Tuple statt Liste fuer Marker"],
  ];
  opts.forEach((o, i) => {
    const yy = 1.15 + i * 0.65;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.55, fill: { color: i % 2 === 0 ? C.lightGray : C.white } });
    s.addText(o[0], { x: 0.9, y: yy, w: 3.0, h: 0.55, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(o[1], { x: 4.0, y: yy, w: 5.2, h: 0.55, fontSize: 13, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  addStatBox(s, 1.5, 4.3, "360-440k", "Z/s Single-Core", C.green);
  addStatBox(s, 4.5, 4.3, "700k+", "Z/s Multi-Core", C.accent);
}

// Slide 40 - Performance-Vergleich
{
  const s = addContentSlide("Performance-Vergleich");
  // Bar chart
  s.addChart(pres.charts.BAR, [{
    name: "Zeilen/Sekunde (Single-Core)",
    labels: ["v1.0", "v1.2", "v1.3", "v1.4"],
    values: [165000, 258000, 360000, 440000]
  }], {
    x: 0.6, y: 1.15, w: 8.8, h: 3.5,
    barDir: "col",
    chartColors: [C.accent],
    chartArea: { fill: { color: C.white }, roundedCorners: true },
    catAxisLabelColor: C.gray,
    valAxisLabelColor: C.gray,
    valGridLine: { color: "E2E8F0", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelColor: C.darkText,
    showLegend: false,
    valAxisNumFmt: "#,##0",
  });
  s.addText("2.7x Steigerung der Verarbeitungsgeschwindigkeit von v1.0 zu v1.4", { x: 0.6, y: 4.85, w: 8.8, h: 0.4, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, align: "center", margin: 0 });
}

// Slide 41 - 92 Tests
{
  const s = addContentSlide("Testsuite: 92 Tests in 6 Modulen");
  // Pie chart
  s.addChart(pres.charts.PIE, [{
    name: "Tests",
    labels: ["Analyzer (42)", "Loaders (14)", "Tokenizer (12)", "Exporter (10)", "Anonymizer (7)", "Performance (4)"],
    values: [42, 14, 12, 10, 7, 4]
  }], {
    x: 0.5, y: 1.1, w: 4.5, h: 3.5,
    showPercent: true,
    chartColors: [C.accent, C.teal, C.green, C.orange, C.yellow, C.red],
    showLegend: true,
    legendPos: "b",
  });
  addCard(s, 5.3, 1.1, 4.3, 3.5, "Test-Abdeckung", [
    "test_analyzer.py: 42 Tests",
    "test_loaders.py: 14 Tests",
    "test_tokenizer.py: 12 Tests",
    "test_exporter.py: 10 Tests",
    "test_anonymizer.py: 7 Tests",
    "test_performance_smoke.py: 4 Tests",
    "",
    "Security-Tests enthalten:",
    "  Regex DoS, Path Traversal",
    "  CSV Injection Prevention"
  ], C.blue);
}

// ============================================================
// TEIL 6 - ERZEUGTE DOKUMENTE (Folien 42-48)
// ============================================================
addDarkSlide("Erzeugte Dokumente", "Word-Dokumente, Excel-Dateien und Markdown-Dokumentation");

// Slide 43 - Uebersicht Dokumente
{
  const s = addContentSlide("Uebersicht: Erzeugte Dokumente");
  const docs = [
    ["Word", "Detecto_Verbesserungskonzept.docx", "10 Massnahmen, 4 Phasen"],
    ["Word", "Dok1_Datenschutz_Pruefscope.docx", "Datenschutz & Pruefauftrag"],
    ["Word", "Dok2_ELK_Betriebshandbuch.docx", "Installation & Betrieb"],
    ["Word", "Dok3_Fachbereich_Finding_Bewertung.docx", "Finding-Bewertung"],
    ["Excel", "Datenarten_Erkennungsmatrix.xlsx", "166 Datenvarianten, 16 Kategorien"],
  ];
  const tbl = [
    [
      { text: "Typ", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
      { text: "Dateiname", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
      { text: "Inhalt", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
    ],
    ...docs.map(d => [
      { text: d[0], options: { fontSize: 12, color: d[0] === "Excel" ? C.green : C.blue, bold: true } },
      { text: d[1], options: { fontSize: 11, fontFace: "Consolas" } },
      { text: d[2], options: { fontSize: 12, fontFace: "Calibri" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.15, w: 8.8, colW: [0.8, 4.5, 3.5], border: { pt: 0.5, color: "DEE2E6" } });
  s.addText("Alle Dokumente wurden mit Claude AI generiert und sind sofort einsatzbereit", { x: 0.6, y: 4.5, w: 8.8, h: 0.35, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, align: "center", margin: 0 });
}

// Slide 44 - Verbesserungskonzept Detail
{
  const s = addContentSlide("Detecto_Verbesserungskonzept.docx");
  s.addText("~8 Seiten Konzeptdokument mit konkreten Massnahmen", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.7, 4.1, 1.6, "Quick Wins (Phase 1)", [
    "Regexp-Anker entfernen",
    "Field-Pattern ergaenzen",
    "Kreditkarte/IBAN Formate",
    "Woerterbuecher erweitern"
  ], C.green);
  addCard(s, 5.1, 1.7, 4.3, 1.6, "Tokenizer (Phase 2)", [
    "Credentials aus URLs extrahieren",
    "Base64-Erkennung",
    "URL-Parameter analysieren"
  ], C.blue);
  addCard(s, 0.6, 3.55, 4.1, 1.6, "Heuristik (Phase 3)", [
    "Entropy-Analyse",
    "Erkennung unbekannter Secrets",
    "Statistische Bewertung"
  ], C.orange);
  addCard(s, 5.1, 3.55, 4.3, 1.6, "Liberty-spezifisch (Phase 4)", [
    "Liberty Message-Codes",
    "Plugin-System",
    "Erweiterbare Architektur"
  ], C.red);
}

// Slide 45 - Dok1 Detail
{
  const s = addContentSlide("Dok1: Datenschutz-Pruefscope");
  s.addText("Dok1_Datenschutz_Pruefscope.docx - Zielgruppe: Datenschutzbeauftragte", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.7, 8.8, 3.3, "Inhalte", [
    "Pruefscope: Was wird geprueft und warum?",
    "Datenarten-Katalog: Welche Datenarten werden erkannt?",
    "Pruefauftrag-Vorlage: Formular fuer den Pruefauftrag",
    "Massnahmen: Was tun bei Findings?",
    "Meldepflichten: Wann muss gemeldet werden?",
    "Rechtliche Grundlagen: DSGVO-Bezug"
  ], C.blue);
}

// Slide 46 - Dok2 Detail
{
  const s = addContentSlide("Dok2: ELK-Betriebshandbuch");
  s.addText("Dok2_ELK_Betriebshandbuch.docx - Zielgruppe: ELK-Team / Administratoren", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.7, 8.8, 3.3, "Inhalte", [
    "Installation und Konfiguration von Detecto",
    "Scan durchfuehren: Parameter, Optionen, Best Practices",
    "Excel-Report erstellen und interpretieren",
    "Vorab-Bereinigung: Stopwort-Listen pflegen (Kap. 4)",
    "Verschluesselung und Datenschutz",
    "Ruecklaeufer: Umgang mit Findings",
    "Pattern-Pflege: Neue Muster hinzufuegen",
    "Troubleshooting: Haeufige Probleme und Loesungen"
  ], C.teal);
}

// Slide 47 - Dok3 Detail
{
  const s = addContentSlide("Dok3: Fachbereich Finding-Bewertung");
  s.addText("Dok3_Fachbereich_Finding_Bewertung.docx - Zielgruppe: Fachbereich / Verfahrenseigner", { x: 0.6, y: 1.15, w: 8.8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
  addCard(s, 0.6, 1.7, 8.8, 3.3, "Inhalte", [
    "Excel verstehen: Spalten, Sheets, Farbcodierung",
    "Findings bewerten: Kriterien und Vorgehensweise",
    "Bewertungsbeispiele: Praxisnahe Szenarien",
    "Massnahmen im Verfahren: Was aendern, wer ist zustaendig?",
    "Eskalationswege: Wann und wohin eskalieren?"
  ], C.orange);
}

// Slide 48 - Markdown-Dokumentation
{
  const s = addContentSlide("Markdown-Dokumentation");
  const mds = [
    ["readme.md", "296 Zeilen", "Vollstaendige Projektdokumentation"],
    ["firststeps.md", "253 Zeilen", "Schnellstartanleitung mit 14 Szenarien"],
    ["changelog.md", "~200 Zeilen", "Versionshistorie v0.1 bis v1.4"],
    ["prompt_documentation.md", "~380 Zeilen", "Alle 121 Prompts chronologisch"],
    ["RELEASE-v1.0.md", "~100 Zeilen", "Release Notes fuer v1.0"],
    ["kritische_logdaten_findings.md", "~1000 Zeilen", "20 Kategorien mit je 20 Beispielen"],
  ];
  const tbl = [
    [
      { text: "Datei", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Umfang", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
      { text: "Inhalt", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 11 } },
    ],
    ...mds.map(m => [
      { text: m[0], options: { fontSize: 11, fontFace: "Consolas", color: C.accent } },
      { text: m[1], options: { fontSize: 11, fontFace: "Calibri", align: "center" } },
      { text: m[2], options: { fontSize: 11, fontFace: "Calibri" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.15, w: 8.8, colW: [3.0, 1.3, 4.5], border: { pt: 0.5, color: "DEE2E6" } });
}

// ============================================================
// TEIL 7 - TECHNISCHE ARCHITEKTUR (Folien 49-55)
// ============================================================
addDarkSlide("Technische Architektur", "Module, Datenfluss, Security-Features, Technologie-Stack");

// Slide 50 - Architekturuebersicht
{
  const s = addContentSlide("Architekturuebersicht: 12 Module");
  // Module flow
  const mods = [
    { name: "cli.py", desc: "Entry Point", x: 4.0, y: 1.1, color: C.navy },
    { name: "config.py", desc: "Konfiguration", x: 0.6, y: 2.0, color: C.blue },
    { name: "loaders.py", desc: "Pattern laden", x: 2.6, y: 2.0, color: C.blue },
    { name: "tokenizer.py", desc: "Tokenisierung", x: 4.6, y: 2.0, color: C.teal },
    { name: "analyzer.py", desc: "Analyse-Engine", x: 6.6, y: 2.0, color: C.teal },
    { name: "formatter.py", desc: "Konsole", x: 1.5, y: 3.3, color: C.green },
    { name: "exporter.py", desc: "Excel/Log", x: 3.5, y: 3.3, color: C.green },
    { name: "anonymizer.py", desc: "Redaction", x: 5.5, y: 3.3, color: C.orange },
    { name: "constants.py", desc: "Konstanten", x: 7.5, y: 3.3, color: C.gray },
    { name: "utils.py", desc: "Hilfsfunktionen", x: 0.6, y: 3.3, color: C.gray },
  ];
  mods.forEach(m => {
    s.addShape(pres.shapes.RECTANGLE, { x: m.x, y: m.y, w: 1.8, h: 0.7, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: m.x, y: m.y, w: 1.8, h: 0.06, fill: { color: m.color } });
    s.addText(m.name, { x: m.x, y: m.y + 0.1, w: 1.8, h: 0.3, fontSize: 10, fontFace: "Consolas", color: m.color, align: "center", margin: 0 });
    s.addText(m.desc, { x: m.x, y: m.y + 0.38, w: 1.8, h: 0.25, fontSize: 9, fontFace: "Calibri", color: C.gray, align: "center", margin: 0 });
  });
  // Arrows
  s.addText("v", { x: 4.6, y: 1.7, w: 0.5, h: 0.3, fontSize: 16, color: C.accent, align: "center", margin: 0 });
  s.addText(">", { x: 4.3, y: 2.1, w: 0.3, h: 0.5, fontSize: 16, color: C.accent, align: "center", margin: 0 });
  s.addText(">", { x: 6.3, y: 2.1, w: 0.3, h: 0.5, fontSize: 16, color: C.accent, align: "center", margin: 0 });
  // Bottom info
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.3, w: 8.8, h: 0.9, fill: { color: C.lightGray } });
  s.addText("2.058 Lines of Code  |  Python 3.9+  |  Einzige Abhaengigkeit: openpyxl", { x: 0.6, y: 4.3, w: 8.8, h: 0.9, fontSize: 14, fontFace: "Calibri", color: C.navy, bold: true, align: "center", valign: "middle", margin: 0 });
}

// Slide 51 - Datenfluss
{
  const s = addContentSlide("Datenfluss");
  const flow = [
    { label: "Log-Datei\neinlesen", x: 0.3, color: C.navy },
    { label: "Tokenizer\n(Split + JSON)", x: 2.3, color: C.blue },
    { label: "Analyzer\n(3 Techniken)", x: 4.3, color: C.teal },
    { label: "Results\n(OrderedDict)", x: 6.3, color: C.green },
    { label: "Export\n(Console/Excel)", x: 8.3, color: C.orange },
  ];
  flow.forEach((f, i) => {
    s.addShape(pres.shapes.RECTANGLE, { x: f.x, y: 1.3, w: 1.5, h: 1.0, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: f.x, y: 1.3, w: 1.5, h: 0.06, fill: { color: f.color } });
    s.addText(f.label, { x: f.x, y: 1.4, w: 1.5, h: 0.85, fontSize: 11, fontFace: "Calibri", color: C.navy, bold: true, align: "center", valign: "middle", margin: 0 });
    if (i < flow.length - 1) {
      s.addText(">", { x: f.x + 1.55, y: 1.5, w: 0.4, h: 0.6, fontSize: 20, color: C.accent, align: "center", valign: "middle", margin: 0 });
    }
  });
  // Detail boxes
  addCard(s, 0.6, 2.7, 2.7, 2.3, "Konfiguration", [
    "detecto.ini",
    "regexp.csv (12 Muster)",
    "field.csv (17 Muster)",
    "suchmuster.csv (5 Kat.)",
    "3 Stopwort-Listen"
  ], C.blue);
  addCard(s, 3.6, 2.7, 2.7, 2.3, "Analyse pro Token", [
    "1. Regexp-Matching",
    "2. Field-Erkennung",
    "3. String-Suche (O(1))",
    "Stopwort-Filterung",
    "Normalisierung"
  ], C.teal);
  addCard(s, 6.6, 2.7, 2.8, 2.3, "Ausgabe", [
    "Konsole (farbig)",
    "Excel (6 Sheets)",
    "Log-Datei",
    "Anonymisiert optional",
    "Kritikalitaet filterbar"
  ], C.orange);
}

// Slide 52 - CLI-Parameter
{
  const s = addContentSlide("CLI-Parameter: Vollstaendige Uebersicht");
  const params = [
    ["logdateien", "Log-Datei(en) zum Scannen"],
    ["--examplecount=N", "Anzahl Beispiele pro Finding"],
    ["--minlen=N", "Min. Stringlaenge (Default: 5)"],
    ["--critical=N", "Kritikalitaetsfilter (1-5)"],
    ["--anon", "Konsolenausgabe anonymisieren"],
    ["--full", "Log-Zeilen mit Farbhervorhebung"],
    ["--nocolor", "Farbausgabe deaktivieren"],
    ["--xlsx", "Excel-Report erstellen"],
    ["--excelanon", "Excel anonymisiert"],
    ["--logresult=FILE", "Ergebnis in Datei speichern"],
    ["--logresultanon=FILE", "Ergebnis anon. speichern"],
    ["--status", "Konfiguration anzeigen"],
    ["--showskipped", "Muster ohne Treffer zeigen"],
    ["--verbose", "Debug-Ausgabe"],
  ];
  const tbl = [
    [
      { text: "Parameter", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 10 } },
      { text: "Beschreibung", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 10 } },
    ],
    ...params.map(p => [
      { text: p[0], options: { fontSize: 10, fontFace: "Consolas", color: C.accent } },
      { text: p[1], options: { fontSize: 10, fontFace: "Calibri" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.15, w: 8.8, colW: [3.0, 5.8], border: { pt: 0.5, color: "DEE2E6" }, rowH: [0.3, ...Array(14).fill(0.28)] });
}

// Slide 53 - Security Features
{
  const s = addContentSlide("Security-Features im Detail");
  addCard(s, 0.6, 1.15, 4.1, 1.8, "Regex DoS Protection", [
    "SIGALRM Timeout (2 Sek.)",
    "Test-String: 1000x 'a'",
    "Verhindert ReDoS-Angriffe",
    "Validierung bei Pattern-Laden"
  ], C.red);
  addCard(s, 5.1, 1.15, 4.3, 1.8, "Path Traversal Prevention", [
    "Path.resolve() validiert Pfade",
    "Keine ../../../etc/passwd",
    "Sichere Datei-Referenzen",
    "In loaders.py implementiert"
  ], C.orange);
  addCard(s, 0.6, 3.2, 4.1, 1.8, "CSV/Excel Injection", [
    "_sanitize_cell() escaped =, +, -, @",
    "Verhindert Formelausfuehrung",
    "Schuetzt Excel-Benutzer",
    "Automatisch in allen Exporten"
  ], C.yellow);
  addCard(s, 5.1, 3.2, 4.3, 1.8, "Memory & UTF-8 Safety", [
    "MAX_HITS_PER_PATTERN = 10.000",
    "MAX_EXAMPLES_PER_VALUE = 100",
    "Binary Reading mit Warnung",
    "INI-Werte Clamping"
  ], C.blue);
}

// Slide 54 - Technologie-Stack
{
  const s = addContentSlide("Technologie-Stack");
  const stack = [
    ["Python", "3.9+", "Hauptsprache", C.blue],
    ["openpyxl", ">= 3.1", "Excel-Erzeugung (einzige Abhaengigkeit)", C.green],
    ["pytest", ">= 7.0", "Unit-Tests (92 Tests)", C.teal],
    ["setuptools", ">= 68.0", "Build-System, Entry-Points", C.orange],
    ["Make", "-", "Build-Automatisierung (dist, test, clean)", C.red],
    ["ruff", ">= 0.4", "Linting", C.yellow],
    ["mypy", ">= 1.10", "Type-Checking", C.accent],
  ];
  const tbl = [
    [
      { text: "Tool", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
      { text: "Version", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
      { text: "Zweck", options: { fill: { color: C.navy }, color: C.white, bold: true, fontSize: 12 } },
    ],
    ...stack.map(s => [
      { text: s[0], options: { fontSize: 12, fontFace: "Calibri", bold: true, color: s[3] } },
      { text: s[1], options: { fontSize: 12, fontFace: "Consolas" } },
      { text: s[2], options: { fontSize: 12, fontFace: "Calibri" } },
    ])
  ];
  s.addTable(tbl, { x: 0.6, y: 1.15, w: 8.8, colW: [1.5, 1.3, 6.0], border: { pt: 0.5, color: "DEE2E6" } });
}

// ============================================================
// TEIL 8 - ERKENNTNISSE & FAZIT (Folien 55-65)
// ============================================================
addDarkSlide("Erkenntnisse & Fazit", "Lessons Learned aus der AI-gestuetzten Entwicklung");

// Slide 56 - Lessons Learned
{
  const s = addContentSlide("Lessons Learned: AI-gestuetzte Entwicklung");
  addCard(s, 0.6, 1.15, 4.1, 2.0, "Was gut funktioniert", [
    "Iterativer Ansatz: kleine Schritte",
    "Klare, praezise Prompts",
    "Sofortiges Testen nach jedem Prompt",
    "AI erzeugt Doku automatisch mit",
    "Schnelle Prototypen moeglich"
  ], C.green);
  addCard(s, 5.1, 1.15, 4.3, 2.0, "Herausforderungen", [
    "AI Slop erkennen und korrigieren",
    "Excel Rich Text Kompatibilitaet",
    "Performance-Tuning erfordert Wissen",
    "Security muss explizit gefordert werden",
    "Konsistenz ueber viele Prompts"
  ], C.orange);
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 3.4, w: 8.8, h: 1.5, fill: { color: "EFF6FF" } });
  s.addText("Wichtigste Erkenntnis:", { x: 0.9, y: 3.5, w: 8, h: 0.3, fontSize: 14, fontFace: "Calibri", color: C.navy, bold: true, margin: 0 });
  s.addText("AI ist ein maechtigere Werkzeug fuer die Softwareentwicklung, aber der Mensch muss die Richtung vorgeben, die Qualitaet pruefen und die Architektur-Entscheidungen treffen.", { x: 0.9, y: 3.85, w: 8.2, h: 0.9, fontSize: 14, fontFace: "Calibri", color: C.darkText, margin: 0 });
}

// Slide 57 - Prompt-Statistik
{
  const s = addContentSlide("121 Prompts - Verteilung nach Kategorie");
  s.addChart(pres.charts.PIE, [{
    name: "Prompts",
    labels: ["Features (45)", "Datenbereinigung (20)", "Bugfixes (15)", "Dokumentation (15)", "Optimierung (12)", "Refactoring (8)", "Security (6)"],
    values: [45, 20, 15, 15, 12, 8, 6]
  }], {
    x: 0.5, y: 1.1, w: 5, h: 3.8,
    showPercent: true,
    chartColors: [C.accent, C.teal, C.red, C.green, C.orange, C.yellow, C.navy],
    showLegend: true,
    legendPos: "r",
  });
  s.addText("Schwerpunkt auf Feature-Entwicklung und Datenqualitaet", { x: 0.6, y: 5.0, w: 8.8, h: 0.35, fontSize: 12, fontFace: "Calibri", color: C.gray, italic: true, margin: 0 });
}

// Slide 58 - AI als Entwicklungspartner
{
  const s = addContentSlide("AI als Entwicklungspartner");
  const aspects = [
    ["Schnelle Iteration", "Von Idee zu funktionierendem Code in Minuten statt Stunden", C.green],
    ["Konsistenz", "Einheitlicher Code-Stil, automatische Dokumentation", C.blue],
    ["Breites Wissen", "Regex, Excel-XML, Security Best Practices, Performance", C.teal],
    ["Parallele Arbeit", "Code + Tests + Doku + Konfiguration in einem Prompt", C.orange],
    ["Qualitaetskontrolle", "AI prueft eigenen Code auf Probleme (Prompt 93: AI Slop)", C.accent],
  ];
  aspects.forEach((a, i) => {
    const yy = 1.15 + i * 0.8;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 8.8, h: 0.65, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: yy, w: 0.06, h: 0.65, fill: { color: a[2] } });
    s.addText(a[0], { x: 0.9, y: yy, w: 2.5, h: 0.65, fontSize: 13, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", margin: 0 });
    s.addText(a[1], { x: 3.5, y: yy, w: 5.7, h: 0.65, fontSize: 12, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
}

// Slide 59 - Qualitaetssicherung
{
  const s = addContentSlide("Qualitaetssicherung");
  addStatBox(s, 0.6, 1.15, "92", "Automatische Tests", C.green);
  addStatBox(s, 3.0, 1.15, "5", "Security-Massnahmen", C.red);
  addStatBox(s, 5.4, 1.15, "3", "Stopwort-Listen", C.orange);
  addStatBox(s, 7.8, 1.15, "1", "AI Slop Check", C.accent);
  addCard(s, 0.6, 2.7, 4.1, 2.5, "Automatisierte Qualitaet", [
    "pytest mit 92 Tests",
    "Security-Tests integriert",
    "Performance-Smoke-Tests",
    "ruff Linting + mypy Type-Checks",
    "Makefile fuer CI/CD"
  ], C.green);
  addCard(s, 5.1, 2.7, 4.3, 2.5, "Manuelle Qualitaet", [
    "AI Slop Check (Prompt 93)",
    "Benutzer-Perspektive (Prompt 100)",
    "Lueckenanalyse (28 Pattern)",
    "Excel-Kompatibilitaet geprueft",
    "Synthetische Test-Logs"
  ], C.blue);
}

// Slide 60 - Projektergebnis
{
  const s = addContentSlide("Projektergebnis: Detecto v1.4");
  addStatBox(s, 0.6, 1.15, "12", "Module", C.accent);
  addStatBox(s, 3.0, 1.15, "2.058", "Lines of Code", C.blue);
  addStatBox(s, 5.4, 1.15, "92", "Tests", C.green);
  addStatBox(s, 7.8, 1.15, "39+", "Erkennungsmuster", C.orange);

  addStatBox(s, 0.6, 2.6, "700k+", "Zeilen/Sek.", C.teal);
  addStatBox(s, 3.0, 2.6, "5", "Dokumente", C.yellow);
  addStatBox(s, 5.4, 2.6, "6", "Markdown-Dateien", C.gray);
  addStatBox(s, 7.8, 2.6, "121", "Prompts", C.red);

  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.1, w: 8.8, h: 1.2, fill: { color: "EFF6FF" } });
  s.addText("Von einem einzelnen Prompt zu einer produktionsreifen, getesteten und dokumentierten Software - entwickelt in 3 Tagen mit Claude AI", { x: 0.9, y: 4.2, w: 8.2, h: 1.0, fontSize: 15, fontFace: "Calibri", color: C.navy, bold: true, valign: "middle", align: "center", margin: 0 });
}

// Slide 61 - Naechste Schritte
{
  const s = addContentSlide("Naechste Schritte");
  addCard(s, 0.6, 1.15, 4.1, 2.0, "Kurzfristig", [
    "Base64-Erkennung (Phase 2)",
    "Entropy-Analyse (Phase 3)",
    "Weitere Woerterbuecher",
    "Community-Feedback einarbeiten"
  ], C.green);
  addCard(s, 5.1, 1.15, 4.3, 2.0, "Mittelfristig", [
    "Liberty Message-Codes (Phase 4)",
    "Plugin-System",
    "CI/CD-Integration",
    "Docker-Container"
  ], C.blue);
  addCard(s, 0.6, 3.4, 8.8, 1.5, "Langfristig", [
    "Erweiterung auf weitere Log-Formate und Datenquellen",
    "Integration in bestehende Security-Toolchains",
    "Machine Learning fuer Pattern-Erkennung"
  ], C.accent);
}

// Slide 62 - Zusammenfassung
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.08, h: 5.625, fill: { color: C.accent } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.8, w: 10, h: 0.06, fill: { color: C.accent } });
  s.addText("Zusammenfassung", { x: 0.8, y: 0.6, w: 8, h: 0.8, fontSize: 36, fontFace: "Georgia", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 0.8, y: 1.5, w: 3, h: 0, line: { color: C.accent, width: 2 } });
  const summary = [
    "121 Prompts: Vom ersten Prompt zur produktionsreifen Software",
    "3 Erkennungstechniken: Regexp, Field, String-Suche",
    "39+ Erkennungsmuster: Passwoerter, Keys, Tokens, PII",
    "700k+ Zeilen/Sek.: Hochperformante Verarbeitung",
    "92 Tests: Automatisierte Qualitaetssicherung",
    "5 Dokumente: Word + Excel fuer verschiedene Zielgruppen",
    "Security-Hardened: DoS, Injection, Path Traversal",
    "AI-Entwicklung: Schnell, iterativ, dokumentiert",
  ];
  s.addText(bullets(summary, { fontSize: 15, color: C.ice }), { x: 0.8, y: 1.8, w: 8.5, h: 3.0, margin: 0 });
}

// Slide 63 - Fragen
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.08, h: 5.625, fill: { color: C.accent } });
  s.addText("Fragen?", { x: 0.8, y: 1.5, w: 8, h: 1.2, fontSize: 52, fontFace: "Georgia", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 0.8, y: 2.9, w: 3, h: 0, line: { color: C.accent, width: 2 } });
  s.addText("Alexander Kornbrust", { x: 0.8, y: 3.3, w: 5, h: 0.5, fontSize: 20, fontFace: "Calibri", color: C.white, margin: 0 });
  s.addText("Detecto v1.4  |  April 2026", { x: 0.8, y: 3.8, w: 5, h: 0.4, fontSize: 16, fontFace: "Calibri", color: C.ice, margin: 0 });
}

// ============================================================
// ANHANG - Vollstaendige Prompt-Liste (Folien 64-80)
// ============================================================
addDarkSlide("Anhang", "Vollstaendige Prompt-Liste (121 Prompts)");

// Helper for prompt list slides
function addPromptListSlide(title, prompts) {
  const s = addContentSlide(title);
  prompts.forEach((p, i) => {
    const yy = 1.15 + i * 0.33;
    s.addText(p[0], { x: 0.6, y: yy, w: 1.0, h: 0.3, fontSize: 9, fontFace: "Calibri", color: C.accent, bold: true, valign: "middle", margin: 0 });
    s.addText(p[1], { x: 1.6, y: yy, w: 7.8, h: 0.3, fontSize: 9, fontFace: "Calibri", color: C.darkText, valign: "middle", margin: 0 });
  });
  return s;
}

// Prompts 1-12
addPromptListSlide("Anhang: Prompts 1-12", [
  ["#1", "Initiale Erstellung: Python 3.9, MIT-Lizenz, Log-Scanner"],
  ["#2", "test.log geaendert, erneut laufen lassen"],
  ["#3", "Versicherungsnummern erkennen (mehrteilige Token)"],
  ["#4", "Ausgabe zeigen (Aufruf + Output)"],
  ["#5", "Aktualisierte Suchmuster-Dateien, case-insensitive"],
  ["#6", "Art der Erkennung [regexp]/[string], Header"],
  ["#7", "Hilfefunktion --help, Parameter --examplecount"],
  ["#8", "Hilfe bei Aufruf ohne Parameter"],
  ["#9", "Parameter --anon (Redaction: sss**sss**)"],
  ["#10", "Parameter --full (Log-Zeilen mit Farbhervorhebung)"],
  ["#11", "Version auf 0.4 aendern"],
  ["#12", "CSV-Dateien auf eine Spalte reduzieren"],
]);

// Prompts 13-24
addPromptListSlide("Anhang: Prompts 13-24", [
  ["#13", "Orte bereinigen (Zusaetze, mehrteilige Namen)"],
  ["#14", "Berlin, Stadt selbst bereinigen"],
  ["#15", "ort.csv angepasst, erneut laufen lassen"],
  ["#16", "Kuerzester Ort in der Liste"],
  ["#17", "Parameter --minlen (min. Stringlaenge)"],
  ["#18", "Orte: Strings nach Bindestrich entfernen"],
  ["#19", "suchmuster.txt: ort.csv -> orte.csv"],
  ["#20", "Orte: Bad-Praefix entfernen"],
  ["#21", "Orte: mehrteilige Namen kuerzen"],
  ["#22", "Orte: St./Sankt Praefix entfernen"],
  ["#23", "Vornamen: Strings nach Bindestrich entfernen"],
  ["#24", "Duplikate aus allen 3 CSV-Dateien entfernen"],
]);

// Prompts 25-36
addPromptListSlide("Anhang: Prompts 25-36", [
  ["#25", "Umlaut-Normalisierung und case-insensitive Suche"],
  ["#26", "Parameter --status (Zusammenfassung Suchdaten)"],
  ["#27", "Header immer anzeigen"],
  ["#28", "Bugfix: Glob-Expansion fuer mehrere Logdateien"],
  ["#29", "Logname in --full Ausgabe"],
  ["#30", "Vornamen/Orte Ueberschneidungen entfernen"],
  ["#31", "Nachnamen/Orte Ueberschneidungen entfernen"],
  ["#32", "Bugfix: UnicodeDecodeError beheben"],
  ["#33", "JSON-Log Unterstuetzung"],
  ["#34", "Vornamen/Nachnamen Ueberschneidungen entfernen"],
  ["#35", "--full mit --anon: auch Log-Zeilen anonymisieren"],
  ["#36", "Dokumentation erstellen (prompt_doc, changelog)"],
]);

// Prompts 37-48
addPromptListSlide("Anhang: Prompts 37-48", [
  ["#37", "Statistik am Ende der Ausgabe"],
  ["#38", "Statistik buendig ausgeben"],
  ["#39", "Version 0.5, --logresult/--logresultanon"],
  ["#40", "--logresult mit Dateiname"],
  ["#41", "readme.md, firststeps.md erstellen"],
  ["#42", "prompt_documentation.md aktualisieren"],
  ["#43", "Field-Erkennung (field.csv)"],
  ["#44", "Pfade und Sternchen bei Field ignorieren"],
  ["#45", "Stopwort-Listen erstellen"],
  ["#46", "Sonderzeichen bei Field-Werten entfernen"],
  ["#47", "Tilde-Pfade bei Field ignorieren"],
  ["#48", "Stopwoerter erweitern (YES, at, invalid, ...)"],
]);

// Prompts 49-60
addPromptListSlide("Anhang: Prompts 49-60", [
  ["#49", "Stopwoerter erweitern (check, for, found, ...)"],
  ["#50", "Readme aktualisieren"],
  ["#51", "Oracle-Passwort (identified by)"],
  ["#52", "PostgreSQL-Passwort (nicht noetig)"],
  ["#53", "Stopwoerter erweitern (WITH)"],
  ["#54", "20 kritische Finding-Kategorien"],
  ["#55", "Test mit synthetic_logs (alle 20 Kategorien)"],
  ["#56", "Telefon-Regexp tunen"],
  ["#57", "Farbige Konsolenausgabe und --nocolor"],
  ["#58", "Stopwoerter erweitern (message, note, ...)"],
  ["#59", "Version 0.7, alle MD-Dateien aktualisieren"],
  ["#60", "Kritikalitaet (1-5) in allen Pattern-Dateien"],
]);

// Prompts 61-72
addPromptListSlide("Anhang: Prompts 61-72", [
  ["#61", "suchmuster.txt -> suchmuster.csv, Syntax pruefen"],
  ["#62", "Parameter --critical=N"],
  ["#63", "detecto.ini Konfigurationsdatei"],
  ["#64", "Minimale Stringlaenge aus Status entfernen"],
  ["#65", "Farbige Kritikalitaet in --status"],
  ["#66", "Parameter --showskipped"],
  ["#67", "Alle MD-Dateien aktualisieren"],
  ["#68", "showskipped in detecto.ini"],
  ["#69", "Version 0.8"],
  ["#70", "Excel-Export (--xlsx)"],
  ["#71", "Excel-Sortierung"],
  ["#72", "Excel Textumbruch und 3 neue Arbeitsblaetter"],
]);

// Prompts 73-84
addPromptListSlide("Anhang: Prompts 73-84", [
  ["#73", "Excel Spaltenbreite und Timestamp"],
  ["#74", "Full-Sheet in Excel"],
  ["#75", "Farbige Markierung im Excel Logeintrag"],
  ["#76", "Parameter --excelanon"],
  ["#77", "Excel-Ausgabe anpassen (anonymisiert)"],
  ["#78", "Dunkelgruene Feldnamen in Konsole und Excel"],
  ["#79-82", "Excel-Kompatibilitaet (Rich Text Fixes)"],
  ["#83", "Suchtypen ein-/ausschaltbar"],
  ["#84", "Kommentare in detecto.ini"],
  ["", ""],
  ["", ""],
  ["", ""],
]);

// Prompts 85-96
addPromptListSlide("Anhang: Prompts 85-96", [
  ["#85", "Konfigurierbares Anonymisierungsmuster"],
  ["#86", "Version 0.9, alle MD-Dateien aktualisieren"],
  ["#87", "4 Bugfixes und Testsuite (34 Tests)"],
  ["#88", "Dokumentation aktualisieren"],
  ["#89", "Komplett-Refactoring in modulares Package"],
  ["#90", "Version 1.0, Dokumentation aktualisieren"],
  ["#91", "Optimierungen 1-6 (DRY, Naming, Tests, ...)"],
  ["#92", "make dist (Makefile)"],
  ["#93", "AI Slop und Unschoenheiten finden"],
  ["#94", "AI Slop korrigieren"],
  ["#95", "Dokumentation aktualisieren"],
  ["#96", "Security-Fixes und Optimierungen"],
]);

// Prompts 97-108
addPromptListSlide("Anhang: Prompts 97-108", [
  ["#97", "INI-Werte Clamping, UTF-8 Binary, Memory Limits"],
  ["#98", "Finaler Feinschliff (englische API, verbose, ...)"],
  ["#99", "Dokumentation und Makefile aktualisieren"],
  ["#100", "Detecto-Analyse aus Benutzerperspektive"],
  ["#101", "Verbesserungskonzept (10 Massnahmen, 4 Phasen)"],
  ["#102", "Version 1.0 finalisieren"],
  ["#103", "v1.1: Regexp-Anker entfernen"],
  ["#104", "Fehlende Field-Pattern ergaenzen (17 total)"],
  ["#105", "Kreditkarte/IBAN mit Formatierung"],
  ["#106", "Diagnosen/Sicherheitsbegriffe erweitern"],
  ["#107", "Credentials aus URLs extrahieren"],
  ["#108", "Datenarten-Erkennungsmatrix (Excel)"],
]);

// Prompts 109-121
addPromptListSlide("Anhang: Prompts 109-121", [
  ["#109-113", "Datenarten-Matrix vervollstaendigen (166 Varianten)"],
  ["#114", "3 Zielgruppen-Dokumente (Word)"],
  ["#115", "Dok2: Stopwort-Vorab-Bereinigung"],
  ["#116", "Fortschrittsanzeige bei grossen Datenmengen"],
  ["#117", "Dokumentation aktualisieren"],
  ["#118", "v1.2: Pre-Filter und Statistik"],
  ["#119", "v1.3: Reverse-Index, Single-Pass, Chunk-Parallel"],
  ["#120", "v1.4: Method-Inlining, ASCII-Fast-Path"],
  ["#121", "Dokumentation aktualisieren, Release Notes"],
  ["", ""],
  ["", ""],
  ["", ""],
]);

// ============================================================
// FINAL SLIDE - Danke
// ============================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.08, h: 5.625, fill: { color: C.accent } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.8, w: 10, h: 0.06, fill: { color: C.accent } });
  s.addText("Vielen Dank!", { x: 0.8, y: 1.5, w: 8, h: 1.2, fontSize: 52, fontFace: "Georgia", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 0.8, y: 2.9, w: 3, h: 0, line: { color: C.accent, width: 2 } });
  s.addText("Detecto v1.4", { x: 0.8, y: 3.3, w: 5, h: 0.5, fontSize: 22, fontFace: "Calibri", color: C.ice, margin: 0 });
  s.addText("Entwickelt mit Claude AI  |  121 Prompts  |  3 Tage", { x: 0.8, y: 3.8, w: 8, h: 0.4, fontSize: 16, fontFace: "Calibri", color: C.ice, margin: 0 });
  s.addText("Alexander Kornbrust  |  April 2026", { x: 0.8, y: 4.3, w: 8, h: 0.4, fontSize: 14, fontFace: "Calibri", color: C.ice, margin: 0 });
}

// ============================================================
// SAVE
// ============================================================
pres.writeFile({ fileName: "/Users/alexanderkornbrust/Documents/Claude/Projects/Detecto/Detecto_Entwicklung_Praesentation.pptx" })
  .then(() => console.log("Presentation saved successfully!"))
  .catch(err => console.error("Error:", err));
