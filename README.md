# Computer Tutor

**Ein Lern-HUD für Windows, das KI-Agenten über MCP steuern können.** Der Agent
markiert Bedienelemente direkt auf deinem Bildschirm, schreibt Hinweise daneben
und erklärt die Aufgabe Schritt für Schritt in einer Lernleiste unten mittig.

Erster Prototyp · Windows 10/11 x64 · Python 3.11+ · kein eingebautes KI-Modell.

![Die tatsächliche Lernleiste, unter Linux mit Qt gerendert](docs/lesson-dock.png)

## Was schon funktioniert

- Transparente, durchklickbare Markierungen mit nummerierten Textkarten.
- Rahmen, Spotlight und Punktmarkierungen; mehrere Hinweise pro Schritt.
- Lernleiste mit ausführlichem Text, Zurück/Weiter und Schrittzähler.
- Ein Monitor pro Tutorial, auswählbar über MCP. Negative Desktopkoordinaten und
  unterschiedliche Skalierungen werden über getrennte physische/logische Geometrie behandelt.
- MCP über **lokales stdio**, einschließlich Bildschirmaufnahme ohne das HUD.
- Optionale Maus- und Tastatursteuerung über Windows `SendInput`, einschließlich Unicode.
- Steuerung ist beim Start **gesperrt**. Nur der lokale Schalter erlaubt sie.
  **Stopp** oder **Strg+Alt+Esc** sperrt Eingaben und blendet Hinweise aus.
- Ein eigenständiges Demo-Tutorial ohne KI-Verbindung.

## Unter Windows starten

In PowerShell, mit installiertem Python 3.11 oder neuer:

```powershell
git clone https://github.com/interfurz/computer-tutor.git
cd computer-tutor
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m computer_tutor --demo
```

Du brauchst weder Administratorrechte noch einen API-Key für die App. Die Demo zeigt
ausdrücklich Beispielbereiche auf dem Desktop; sie erkennt noch keine Schaltflächen.
Ein echter MCP-Agent übernimmt das Sehen, Planen und Erklären.

## Mit einem MCP-Agenten verbinden

In einem Windows-MCP-Client mit **lokalen stdio-Servern** eine Konfiguration wie diese
eintragen. Den absoluten Pfad anpassen:

```json
{
  "mcpServers": {
    "computer-tutor": {
      "command": "C:\\Users\\DEINNAME\\computer-tutor\\.venv\\Scripts\\python.exe",
      "args": ["-m", "computer_tutor", "--mcp"]
    }
  }
}
```

Der Client startet die App zusammen mit dem MCP-Server. Nicht zusätzlich dieselbe
Instanz manuell starten. Nach dem Beenden der Verbindung schließt sich auch das HUD.
Ein Linux-/WSL-MCP-Prozess steuert damit nicht automatisch den Windows-Desktop:
**Server und HUD müssen auf dem Windows-PC des Nutzers laufen.**

Beispielauftrag an den Agenten:

> Erkläre mir Schritt für Schritt, wie ich in meinem geöffneten Programm eine Datei
> speichere. Nutze Computer Tutor. Schau zuerst auf den Bildschirm, markiere jeweils
> die passende Schaltfläche und lass mich selbst klicken. Prüfe den Bildschirm nach
> Änderungen erneut, bevor du den nächsten Hinweis setzt.

| Werkzeug | Zweck |
| --- | --- |
| `tutor_list_monitors` | Monitore und ihre IDs ermitteln |
| `tutor_capture_screen` | Screenshot eines Monitors, ohne das HUD |
| `tutor_present_tutorial` | Tutorial mit Schritten und Markierungen laden |
| `tutor_update_step` | Aktuellen Hinweis an eine veränderte Oberfläche anpassen |
| `tutor_get_state` | Schritt, Nutzer-Navigation und Eingabefreigabe abfragen |
| `tutor_navigate` | Zum vorherigen/nächsten Erklärungsschritt wechseln |
| `tutor_set_annotations_visible` | Hinweise ein-/ausblenden |
| `tutor_stop` | Eingaben sperren und Hinweise ausblenden |
| `desktop_click` / `desktop_type_text` | Klicken / Unicode-Text eingeben |
| `desktop_hotkey` / `desktop_scroll` | Tastenkombination / Mausrad |

Vollständiges Beispiel und Koordinatenkonvention: [Agenten-Leitfaden](docs/agent-guide.md).

## Bedienung und Grenzen

**Weiter** wechselt die Erklärung. Es bestätigt nicht, dass der Schritt erfolgreich
ausgeführt wurde. **Zurück** macht keine Änderungen in einem Programm rückgängig.
Der Agent kann den aktuellen Schritt abfragen und anhand neuer Screenshots prüfen.
Die App sendet momentan keine proaktiven Schritt-Ereignisse an den Agenten.

Die App speichert keine Screenshots auf der Festplatte. Ein angeforderter Screenshot
wird an den verbundenen MCP-Client übergeben und kann von dessen Modell verarbeitet
werden. Es gibt keinen HTTP-Port, keine Telemetrie und keinen eigenen Cloud-Dienst.

Die Freigabe erlaubt Eingaben in normale Desktop-Anwendungen; sie ist keine Sandbox
für deren Folgen. Administratorfenster, UAC, Sperrbildschirm und geschützte Videoinhalte
werden nicht unterstützt. Der Agent kann die Freigabe nicht per Tool aktivieren.
Tastatureingaben werden abgewiesen, solange die Lernleiste selbst den Fokus hat;
ein Klick des Agenten auf die Zielanwendung kann den Fokus wechseln. Agentenklicks
auf die Lernleiste sind gesperrt.

Ein Tutorial verwendet einen Monitor. Bei Änderung der Bildschirmgeometrie oder
Skalierung werden die Freigabe und alte Markierungen verworfen; der Agent muss neu
aufnehmen. Markierungen hängen momentan an Bildschirmkoordinaten, nicht an Fenstern.
Nach Verschieben, Scrollen oder Öffnen eines Menüs braucht es eine neue Aufnahme.
Viele eng beieinanderliegende Hinweise können überlappen. Die Lernleiste kann Ziele
unten verdecken; für solche Schritte die Hinweise kurz ausblenden und das Ziel nach
Möglichkeit aus dem Bereich der Leiste verschieben.

Strg+Alt+Esc ist ein globaler Stopp-Hotkey, solange die App läuft. Kann Windows ihn
nicht registrieren, zeigt die Leiste das an; die Schaltfläche Stopp bleibt verfügbar.
Aktuelle Builds sind ein Prototyp und noch nicht auf einem echten Windows-Desktop
mit mehreren DPI-Skalierungen abgenommen. [Manueller Prüfplan](docs/windows-validation.md).

## Entwicklung und Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Mit [uv](https://docs.astral.sh/uv/) sind die Abhängigkeiten reproduzierbar aus
`uv.lock` installierbar: `uv sync --locked --extra dev`.

Unter Linux lassen sich die Protokoll- und Qt-Tests mit `QT_QPA_PLATFORM=offscreen`
ausführen. `--allow-non-windows` ist ausschließlich für diese Entwicklungsprüfungen;
native Eingaben funktionieren nur auf Windows.

## Windows-App bauen

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[build]"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --name computer-tutor --collect-all mcp --collect-submodules computer_tutor --manifest packaging/windows.manifest src/computer_tutor/__main__.py
.\dist\computer-tutor\computer-tutor.exe --demo
```

Den **gesamten** Ordner `dist/computer-tutor` verteilen, nicht nur die EXE. Für einen
MCP-Client ist diese EXE mit `args: ["--mcp"]` verwendbar. Der Build verwendet eine
Konsole für stdio; ein reiner `--windowed`-Build ist kein stdio-MCP-Server.
GitHub Actions prüft Windows/Linux und erzeugt ein herunterladbares Windows-Buildartefakt.

## Wie es weitergehen kann

Die Produktidee und priorisierte Ausbaustufen stehen in [Konzept & Roadmap](docs/concept.md).
Die technische Aufteilung steht in [Architektur](docs/architecture.md).
