# Manueller Windows-Prüfplan

Diese Prüfungen ergänzen die automatisierten Protokoll- und Offscreen-Qt-Tests.
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
