"""A self-contained tutorial about the HUD, without invented application targets."""

from computer_tutor.models import Annotation, Rect, Step, Tutorial


def demo_tutorial(monitor_id: str) -> Tutorial:
    return Tutorial(
        title="Dein Bildschirm wird zum Lernraum",
        monitor_id=monitor_id,
        steps=[
            Step(
                title="Ein Hinweis. Direkt am richtigen Ort.",
                explanation=(
                    "So kann ein Agent dir ein Programm erklären: Ein Rahmen markiert das Ziel, "
                    "daneben steht ein kurzer Hinweis. Hier siehst du nur eine Beispielmarkierung "
                    "auf deinem Desktop – noch keine erkannte Schaltfläche.\n\n"
                    "Die Markierungen sind durchklickbar. Du kannst die Anwendung darunter ganz "
                    "normal bedienen. Mit Weiter siehst du die nächste Darstellungsart."
                ),
                annotations=[
                    Annotation(
                        id="example",
                        target=Rect(x=0.15, y=0.2, width=0.22, height=0.12),
                        label="Hier könnte der Agent eine Schaltfläche erklären.",
                    )
                ],
            ),
            Step(
                title="Konzentriere dich auf den nächsten Schritt.",
                explanation=(
                    "Ein Spotlight hebt den wichtigen Bereich hervor und dunkelt die Umgebung ab. "
                    "Auch dabei bleibt der Desktop bedienbar.\n\n"
                    "Ein echter Agent nimmt zuerst einen Screenshot auf, findet das Ziel und "
                    "setzt die Markierung passend. Nach dem Öffnen eines Menüs sollte er den "
                    "Bildschirm erneut prüfen und den Hinweis aktualisieren."
                ),
                annotations=[
                    Annotation(
                        id="focus",
                        style="spotlight",
                        target=Rect(x=0.56, y=0.2, width=0.2, height=0.15),
                        label="Ein Schritt nach dem anderen.",
                        placement="below",
                    )
                ],
            ),
            Step(
                title="Du behältst die Kontrolle.",
                explanation=(
                    "Zurück und Weiter wechseln nur die Erklärung. Sie führen keine Aktion aus "
                    "und machen keine Änderungen in deinen Programmen rückgängig.\n\n"
                    "Maus- und Tastatureingaben durch den Agenten sind standardmäßig gesperrt. "
                    "Du kannst sie über den Schalter unten erlauben. Stopp oder Strg+Alt+Esc "
                    "sperrt sie wieder und blendet die Hinweise aus.\n\n"
                    "Für ein echtes Tutorial starte Computer Tutor über deinen MCP-Client. "
                    "Eine Beispielkonfiguration steht in der README."
                ),
            ),
        ],
    )
