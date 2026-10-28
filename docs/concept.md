# Ursprüngliches Brainstorming und weitere Produktideen

Dieses Dokument hält die erste Ideensammlung fest. Den umgesetzten Stand der App 1.0 beschreibt die README.

## Der Kern

Eine Erklärung im Chat setzt voraus, dass Menschen den beschriebenen Knopf selbst
finden. Computer Tutor verkürzt diesen Weg: Der Agent erklärt dort, wo die Handlung
stattfindet. Die Oberfläche darunter bleibt benutzbar.

Ein typischer Ablauf:

1. „Bring mir bei, wie ich in diesem Programm ein PDF exportiere.“
2. Der Agent betrachtet den ausgewählten Monitor und klärt das Lernziel.
3. Ein Rahmen und ein kurzer Hinweis zeigen auf das erste Ziel.
4. Die Lernleiste erklärt Handlung, Zweck und erwartetes Ergebnis.
5. Der Nutzer klickt selbst und wechselt weiter. Der Agent prüft bei Bedarf neu.
6. Bei Abweichungen erklärt er den tatsächlich sichtbaren Zustand.

## Drei Betriebsarten

| Modus | Verhalten | Stand |
| --- | --- | --- |
| Erklären | Oberfläche beschreiben und einzelne Bereiche zeigen | MCP-Werkzeuge vorhanden |
| Gemeinsam lernen | Schritte zeigen, der Mensch führt sie aus | MVP-Kern |
| Vorführen | Agent führt angeforderte Aktionen aus und erklärt sie | Eingabewerkzeuge mit lokaler Freigabe |

Ein eigener Moduswähler und getrennte Aktionsfreigaben pro Schritt sind spätere
Erweiterungen. Der MVP unterscheidet Erklärung und Ausführung technisch durch
separate Werkzeuge und die lokale Eingabefreigabe.

## Gestaltungsentscheidungen

- **Kurz am Ziel, ausführlich unten.** Textkarten beantworten „Wo?“, die Lernleiste
  beantwortet „Was, warum und woran erkenne ich das Ergebnis?“
- **Ein aktiver Schritt.** Mehrere Markierungen sind für zusammengehörige Bereiche
  möglich, aber der Agent soll den Bildschirm nicht mit Anweisungen überladen.
- **Die App gehört dem Nutzer.** Hinweise ausblenden, zurückgehen und stoppen sind
  immer lokale Bedienhandlungen. Agenteneingaben sind zunächst aus.
- **Kein eingebauter Modellzwang.** Ein vorhandener MCP-Agent liefert das Denken,
  die Windows-App liefert Sehen, Zeigen und optional Handeln.
- **Keine erfundene Erfolgsmeldung.** Der Schrittzähler ist Navigation, kein Beleg,
  dass ein Vorgang im Zielprogramm abgeschlossen ist.

## Nächste sinnvolle Ausbaustufen

### 1. Zuverlässige Ziele und Rückmeldung

- Windows UI Automation: Rollen, Namen und Bounding Rects statt nur Pixel erkennen.
- Markierungen an UIA-Elemente/Fenster binden und bei Bewegung nachführen.
- Bei veralteten Zielen pausieren statt an einer falschen Stelle weiterzuzeigen.
- Schrittwechsel als Ereignisse/ausstehende Nutzeraktion für Agenten bereitstellen.
- Erfolg mit expliziten Bedingungen prüfen, etwa „Dialog mit Titel X sichtbar“.

### 2. Alltagstauglicher Lernbegleiter

- Verschiebbare und einklappbare Leiste für verdeckte Zielbereiche.
- Tray-Icon, Pause/Fortsetzen und eine klare Verbindung-/Wartet-Anzeige.
- „Ich finde das nicht“, „Warum?“ und „Zeig es mir“ pro Schritt.
- Monitor- und Fensterauswahl direkt in der App.
- Unterschiedliche Detaillierung für Einsteiger und Fortgeschrittene.
- Vorlesen, Tastaturbedienung und individuell einstellbare Kontraste/Textgrößen.

### 3. Wiederverwendbare Lektionen

- Tutorials lokal speichern und importieren; private Inhalte vor Teilen prüfen.
- Lektionen nach App, Version und Sprache kennzeichnen.
- Übungsmodus: Hinweise schrittweise reduzieren, Lernerfolg aktiv abfragen.
- Ein kleiner Editor zum manuellen Setzen und Korrigieren von Markierungen.
- Signierter Installer und ein getesteter Updatepfad.

## Bewusst offen

Noch keine automatische Dauerbeobachtung, kein eigenes Sprachmodell und keine
komplexe Kursplattform. Zuerst soll ein einziger Lernschritt vom Screenshot bis
zur passenden Markierung auf einem echten Windows-Desktop zuverlässig funktionieren.
