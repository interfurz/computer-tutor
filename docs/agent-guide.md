# Agenten-Leitfaden

1. `tutor_list_monitors` aufrufen und einen existierenden Monitor wählen.
2. `tutor_capture_screen` aufrufen. Nur beobachtete Elemente markieren.
3. Pixelrechtecke relativ zur gelieferten Bildbreite/-höhe umrechnen.
4. `tutor_present_tutorial` mit klaren Handlungsschritten senden.
5. Nach Nutzerinteraktion `tutor_get_state` prüfen. Geänderte `revision` kann auch
   Sichtbarkeit oder Eingabefreigabe bedeuten; immer den eigentlichen Schritt prüfen.
6. Nach einer Bildschirmänderung erneut aufnehmen und `tutor_update_step` verwenden.

Beispielargumente für `tutor_present_tutorial`. Die Monitor-ID und alle Koordinaten
müssen aus der tatsächlichen Aufnahme stammen; die Werte hier sind nur das Schema:

```json
{
  "tutorial": {
    "title": "Eine Datei speichern",
    "monitor_id": "\\\\.\\DISPLAY1",
    "steps": [
      {
        "title": "Öffne das Dateimenü",
        "explanation": "Klicke auf Datei. Dort findest du die Befehle zum Öffnen und Speichern. Sobald das Menü geöffnet ist, prüfen wir gemeinsam den nächsten Schritt.",
        "annotations": [
          {
            "id": "file-menu",
            "target": {"x": 0.012, "y": 0.03, "width": 0.04, "height": 0.025},
            "label": "Hier öffnest du das Dateimenü.",
            "style": "rectangle",
            "placement": "below"
          }
        ]
      },
      {
        "title": "Wir prüfen das geöffnete Menü",
        "explanation": "Der Agent soll jetzt erneut auf den Bildschirm schauen und den passenden Speichern-Befehl markieren. Noch kein geratenes Ziel einzeichnen.",
        "annotations": []
      }
    ]
  }
}
```

Koordinaten eines erkannten Rechtecks bei einer 1920 × 1080-Aufnahme:

```text
linker Rand 240 px  → x      = 240 / 1920
oberer Rand 108 px  → y      = 108 / 1080
Breite      96 px  → width  =  96 / 1920
Höhe        54 px  → height =  54 / 1080
```

`point` setzt einen nummerierten Hinweis an die Mitte des Zielrechtecks.
`spotlight` dunkelt den restlichen Bildschirm ab. Alle Markierungen bleiben
durchklickbar. `placement` ist eine bevorzugte Kartenposition; die App versucht,
Bildschirmränder und die Lernleiste zu vermeiden. Dichte Markierungen können
weiterhin überlappen.

Tutorialtexte sind Plaintext, kein HTML. Keine Shell-Befehle als Ersatz für ein
fehlendes Tool ausführen. Desktopaktionen nur auf Wunsch des Nutzers und bei
lokal freigegebener Steuerung ausführen; nach jeder relevanten Aktion neu prüfen.
