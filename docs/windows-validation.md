# Manueller Windows-Prüfplan

Diese interaktiven Prüfungen ergänzen die automatisierten Protokoll-, DPAPI-, Installer- und Offscreen-Qt-Tests.
Sie sind noch nicht als bestanden dokumentiert. Vor einer stabilen Veröffentlichung
auf einem echten Windows-10/11-Desktop ausführen und Ergebnisse festhalten.

- Demo starten: Leiste unten mittig, Texte lesbar, alle drei Schritte erreichbar.
- Durch Rahmen, Spotlight und Textkarte hindurch auf eine harmlose Zielanwendung klicken.
- Im MCP-Client verbinden; Screenshot enthält weder Leiste noch Markierungen.
- Nach absichtlich fehlgeschlagener Aufnahme erscheint das HUD wieder.
- Normalbetrieb bei 100 %, 150 % und 200 % Skalierung prüfen.
- Zweiten Monitor links/oberhalb des Hauptmonitors anschließen; negative Koordinaten prüfen.
- Monitore mit unterschiedlicher Skalierung prüfen: Screenshot-Ziel und Rahmen stimmen überein.
- Steuerung aus: Klick, Text, Hotkey und Scrollen werden abgewiesen.
- Steuerung an: einen gezielten Klick, „Grüße 👋“, Strg+A und Scrollen in einer Test-App prüfen.
- Agent kann nicht auf die Leiste klicken; Tastatureingaben bei Leistenfokus sind gesperrt.
- Strg+Alt+Esc sowie lokaler Stopp sperren neue Aktionen und blenden Hinweise aus.
- Bereits belegten Hotkey simulieren; Leiste meldet fehlenden Hotkey, lokaler Stopp funktioniert.
- Monitor entfernen oder Skalierung ändern: alte Lektion und Freigabe werden verworfen.
- MCP-Client beenden: HUD-Prozess endet. HUD schließen: MCP-Client erhält EOF.
- Gebauten Ordner auf einem Windows-Rechner ohne Python starten und per MCP verbinden.
- UAC/elevierte Anwendung: keine Erfolgsmeldung behaupten, wenn Windows Eingaben blockiert.

- Installation über Setup und Start aus dem Windows-Startmenü; keine Konsole sichtbar.
- Zweiter App-Start öffnet dieselbe Instanz; MCP-Starter nutzt deren HUD.
- Eigenen gültigen API-Key speichern, App neu starten, einen echten Lernschritt erzeugen.
- Falschen API-Key, nicht verfügbares Modell und unterbrochenes Netzwerk prüfen.
- Während eines KI-Aufrufs stoppen; verspätete Antwort verändert das Tutorial nicht.
- Direkte Lektion: Weiter nimmt neu auf, Zurück zeigt den bisherigen Schritt, Abschluss bleibt erreichbar.
- Lernleiste ziehen/einklappen; Ziel am unteren Bildschirmrand lässt die Leiste ausweichen.
- Hauptfenster bei 200 % DPI und kleinen logischen Auflösungen über Scrollen vollständig bedienen.
- MCP-Prozess hart beenden; nach zwölf Sekunden ist die Eingabefreigabe gesperrt.
- API-Key löschen, Tutorial exportieren/importieren und Deinstallation prüfen.
