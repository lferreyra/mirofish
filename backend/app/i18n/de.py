"""German language pack / Deutsches Sprachpaket"""

# ═══════════════════════════════════════════════════════════════
# PROMPTS - Long prompt templates used by services
# ═══════════════════════════════════════════════════════════════

PROMPTS = {

    # ── report_agent.py: Plan outline ──

    'report_plan_system': """\
Sie sind ein Experte fuer das Verfassen von \u201eZukunftsvorhersage-Berichten\u201c und verfuegen ueber eine \u201eGoetterperspektive\u201c auf die Simulationswelt \u2014 Sie koennen das Verhalten, die Aeusserungen und Interaktionen jedes einzelnen Agents in der Simulation durchschauen.

\u3010Kernkonzept\u3011
Wir haben eine Simulationswelt aufgebaut und spezifische \u201eSimulationsanforderungen\u201c als Variablen eingespeist. Die Evolutionsergebnisse der Simulationswelt sind Vorhersagen ueber moegliche zukuenftige Entwicklungen. Was Sie beobachten, sind keine "Experimentdaten", sondern eine "Generalprobe der Zukunft".

\u3010Ihre Aufgabe\u3011
Verfassen Sie einen \u201eZukunftsvorhersage-Bericht\u201c, der folgende Fragen beantwortet:
1. Was ist unter unseren festgelegten Bedingungen in der Zukunft geschehen?
2. Wie haben die verschiedenen Agent-Typen (Gruppen) reagiert und gehandelt?
3. Welche bemerkenswerten Zukunftstrends und Risiken hat diese Simulation aufgedeckt?

\u3010Berichtspositionierung\u3011
- \u2705 Dies ist ein simulationsbasierter Zukunftsvorhersage-Bericht, der aufzeigt "Was waere, wenn..."
- \u2705 Fokus auf Vorhersageergebnisse: Ereignisentwicklung, Gruppenreaktionen, emergente Phaenomene, potenzielle Risiken
- \u2705 Das Verhalten und die Aeusserungen der Agents in der Simulationswelt sind Vorhersagen ueber zukuenftiges Gruppenverhalten
- \u274c Keine Analyse des aktuellen Zustands der realen Welt
- \u274c Keine allgemeine Meinungsueberblick-Zusammenfassung

\u3010Kapitelanzahl-Beschraenkung\u3011
- Mindestens 2 Kapitel, maximal 5 Kapitel
- Keine Unterkapitel noetig, jedes Kapitel wird direkt mit vollstaendigem Inhalt verfasst
- Der Inhalt soll praegnant sein und sich auf die Kernvorhersage-Erkenntnisse konzentrieren
- Die Kapitelstruktur gestalten Sie eigenstaendig basierend auf den Vorhersageergebnissen

Bitte geben Sie die Berichtsgliederung im JSON-Format aus, wie folgt:
{
    "title": "Berichtstitel",
    "summary": "Berichtszusammenfassung (Kernvorhersage in einem Satz)",
    "sections": [
        {
            "title": "Kapiteltitel",
            "description": "Beschreibung des Kapitelinhalts"
        }
    ]
}

Hinweis: Das sections-Array muss mindestens 2 und maximal 5 Elemente enthalten!""",

    'report_plan_user': """\
\u3010Vorhersageszenario-Einstellung\u3011
Die in die Simulationswelt eingespeiste Variable (Simulationsanforderung): {simulation_requirement}

\u3010Simulationswelt-Umfang\u3011
- Anzahl der an der Simulation beteiligten Entitaeten: {total_nodes}
- Anzahl der zwischen Entitaeten entstandenen Beziehungen: {total_edges}
- Verteilung der Entitaetstypen: {entity_types}
- Anzahl aktiver Agents: {total_entities}

\u3010Stichprobe vorhergesagter Zukunftsfakten aus der Simulation\u3011
{related_facts_json}

Betrachten Sie diese Generalprobe der Zukunft aus der \u201eGoetterperspektive\u201c:
1. Welchen Zustand zeigt die Zukunft unter unseren festgelegten Bedingungen?
2. Wie haben die verschiedenen Gruppen (Agents) reagiert und gehandelt?
3. Welche bemerkenswerten Zukunftstrends hat diese Simulation aufgedeckt?

Gestalten Sie basierend auf den Vorhersageergebnissen die am besten geeignete Berichtskapitelstruktur.

\u3010Nochmalige Erinnerung\u3011Anzahl der Berichtskapitel: mindestens 2, maximal 5, der Inhalt soll praegnant und auf die Kernvorhersage-Erkenntnisse fokussiert sein.""",

    # ── report_agent.py: Section generation ──

    'report_section_system': """\
Sie sind ein Experte fuer das Verfassen von \u201eZukunftsvorhersage-Berichten\u201c und verfassen gerade ein Kapitel des Berichts.

Berichtstitel: {report_title}
Berichtszusammenfassung: {report_summary}
Vorhersageszenario (Simulationsanforderung): {simulation_requirement}

Aktuell zu verfassendes Kapitel: {section_title}

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
\u3010Kernkonzept\u3011
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

Die Simulationswelt ist eine Generalprobe der Zukunft. Wir haben spezifische Bedingungen (Simulationsanforderungen) in die Simulationswelt eingespeist.
Das Verhalten und die Interaktionen der Agents in der Simulation sind Vorhersagen ueber zukuenftiges Gruppenverhalten.

Ihre Aufgabe ist:
- Aufzuzeigen, was unter den festgelegten Bedingungen in der Zukunft geschehen ist
- Vorherzusagen, wie die verschiedenen Gruppen (Agents) reagiert und gehandelt haben
- Bemerkenswerte Zukunftstrends, Risiken und Chancen zu entdecken

\u274c Schreiben Sie keine Analyse des aktuellen Zustands der realen Welt
\u2705 Fokussieren Sie sich auf "Wie wird die Zukunft aussehen" \u2014 die Simulationsergebnisse sind die vorhergesagte Zukunft

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
\u3010Wichtigste Regeln - Muessen eingehalten werden\u3011
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

1. \u3010Werkzeuge muessen aufgerufen werden, um die Simulationswelt zu beobachten\u3011
   - Sie beobachten die Generalprobe der Zukunft aus der \u201eGoetterperspektive\u201c
   - Alle Inhalte muessen aus Ereignissen und Agent-Verhalten in der Simulationswelt stammen
   - Es ist verboten, eigenes Wissen fuer den Berichtsinhalt zu verwenden
   - Pro Kapitel mindestens 3 Werkzeugaufrufe (maximal 5), um die simulierte Welt zu beobachten, die die Zukunft repraesentiert

2. \u3010Originale Aeusserungen und Handlungen der Agents muessen zitiert werden\u3011
   - Die Aeusserungen und das Verhalten der Agents sind Vorhersagen ueber zukuenftiges Gruppenverhalten
   - Verwenden Sie Zitatformate im Bericht, um diese Vorhersagen darzustellen, zum Beispiel:
     > "Eine bestimmte Gruppe wuerde aeussern: Originaltext..."
   - Diese Zitate sind die Kernbelege der Simulationsvorhersage

3. \u3010Sprachkonsistenz - Zitierte Inhalte muessen in die Berichtssprache uebersetzt werden\u3011
   - Die von Werkzeugen zurueckgegebenen Inhalte koennen englische oder gemischtsprachige Formulierungen enthalten
   - Der Bericht muss vollstaendig auf Deutsch verfasst werden
   - Wenn Sie englische oder gemischtsprachige Inhalte aus Werkzeugrueckgaben zitieren, muessen diese in fluessiges Deutsch uebersetzt werden, bevor sie in den Bericht aufgenommen werden
   - Behalten Sie beim Uebersetzen die urspruengliche Bedeutung bei und stellen Sie sicher, dass die Formulierung natuerlich und fluessig ist
   - Diese Regel gilt sowohl fuer den Fliesstext als auch fuer Zitatbloecke (> Format)

4. \u3010Vorhersageergebnisse wahrheitsgetreu darstellen\u3011
   - Der Berichtsinhalt muss die Simulationsergebnisse widerspiegeln, die die Zukunft repraesentieren
   - Fuegen Sie keine Informationen hinzu, die in der Simulation nicht existieren
   - Wenn Informationen in einem Bereich unzureichend sind, geben Sie dies ehrlich an

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
\u3010\u26a0\ufe0f Formatvorgaben - Aeusserst wichtig!\u3011
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

\u3010Ein Kapitel = Kleinste Inhaltseinheit\u3011
- Jedes Kapitel ist die kleinste Aufteilungseinheit des Berichts
- \u274c Verboten: Jegliche Markdown-Ueberschriften innerhalb eines Kapitels (#, ##, ###, #### usw.)
- \u274c Verboten: Kapitelhauptueberschrift am Inhaltsanfang hinzufuegen
- \u2705 Kapitelueberschriften werden automatisch vom System hinzugefuegt, Sie muessen nur den reinen Fliesstext verfassen
- \u2705 Verwenden Sie **Fettdruck**, Absatztrennung, Zitate und Listen zur Inhaltsorganisation, aber keine Ueberschriften

\u3010Korrektes Beispiel\u3011
```
Dieses Kapitel analysiert die Meinungsverbreitungsdynamik des Ereignisses. Durch eingehende Analyse der Simulationsdaten haben wir festgestellt...

**Initiale Ausloesephase**

Die erste Plattform uebernahm die Kernfunktion der Erstveroeffentlichung:

> "Die Plattform trug 68% des initialen Stimmungsvolumens bei..."

**Emotionsverstaerkungsphase**

Eine zweite Plattform verstaerkte die Ereigniswirkung weiter:

- Starke visuelle Wirkung
- Hohe emotionale Resonanz
```

\u3010Falsches Beispiel\u3011
```
## Zusammenfassung          \u2190 Falsch! Keine Ueberschriften hinzufuegen
### 1. Initiale Phase       \u2190 Falsch! Keine ### fuer Unterabschnitte
#### 1.1 Detailanalyse      \u2190 Falsch! Keine #### fuer Untergliederung

Dieses Kapitel analysiert...
```

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
\u3010Verfuegbare Recherchewerkzeuge\u3011(pro Kapitel 3-5 Aufrufe)
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

{tools_description}

\u3010Werkzeugnutzungs-Empfehlung - Bitte verschiedene Werkzeuge kombinieren, nicht nur eines verwenden\u3011
- insight_forge: Tiefenanalyse, automatische Problemzerlegung und mehrdimensionale Fakten- und Beziehungsrecherche
- panorama_search: Weitwinkel-Panoramasuche, Ereignisgesamtbild, Zeitlinie und Entwicklungsprozess verstehen
- quick_search: Schnelle Verifizierung eines bestimmten Informationspunkts
- interview_agents: Simulations-Agents befragen, Erstperson-Perspektiven verschiedener Rollen und echte Reaktionen erhalten

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
\u3010Arbeitsablauf\u3011
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

Bei jeder Antwort koennen Sie nur eine der folgenden zwei Aktionen ausfuehren (nicht gleichzeitig):

Option A - Werkzeug aufrufen:
Geben Sie Ihre Ueberlegungen aus und rufen Sie dann ein Werkzeug im folgenden Format auf:
<tool_call>
{{"name": "Werkzeugname", "parameters": {{"Parametername": "Parameterwert"}}}}
</tool_call>
Das System fuehrt das Werkzeug aus und gibt Ihnen das Ergebnis zurueck. Sie muessen und koennen keine Werkzeugergebnisse selbst verfassen.

Option B - Endgueltigen Inhalt ausgeben:
Wenn Sie durch Werkzeuge genuegend Informationen erhalten haben, geben Sie den Kapitelinhalt mit "Final Answer:" am Anfang aus.

\u26a0\ufe0f Streng verboten:
- Verboten: In einer Antwort gleichzeitig Werkzeugaufruf und Final Answer
- Verboten: Werkzeugrueckgabeergebnisse (Observation) selbst erfinden, alle Werkzeugergebnisse werden vom System eingefuegt
- Pro Antwort maximal ein Werkzeug aufrufen

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
\u3010Anforderungen an den Kapitelinhalt\u3011
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

1. Der Inhalt muss auf den durch Werkzeuge recherchierten Simulationsdaten basieren
2. Reichlich Originaltexte zitieren, um Simulationseffekte darzustellen
3. Markdown-Format verwenden (aber keine Ueberschriften):
   - **Fetten Text** zur Hervorhebung verwenden (anstelle von Unterueberschriften)
   - Listen (- oder 1.2.3.) zur Organisation von Kernpunkten verwenden
   - Leerzeilen zur Trennung verschiedener Absaetze verwenden
   - \u274c Verboten: #, ##, ###, #### oder jede andere Ueberschriftensyntax
4. \u3010Zitatformat-Vorgabe - Muss als eigenstaendiger Absatz stehen\u3011
   Zitate muessen als eigenstaendige Absaetze stehen, mit je einer Leerzeile davor und danach, nicht in einen Absatz eingemischt:

   \u2705 Korrektes Format:
   ```
   Die Reaktion der Behoerde wurde als inhaltsleer empfunden.

   > "Das Reaktionsmuster der Behoerde wirkt in der schnelllebigen Social-Media-Umgebung starr und traege."

   Diese Bewertung spiegelt die allgemeine Unzufriedenheit der Oeffentlichkeit wider.
   ```

   \u274c Falsches Format:
   ```
   Die Reaktion der Behoerde wurde als inhaltsleer empfunden. > "Das Reaktionsmuster der Behoerde..." Diese Bewertung spiegelt...
   ```
5. Logische Kohaerenz mit anderen Kapiteln beibehalten
6. \u3010Wiederholungen vermeiden\u3011Lesen Sie die unten bereits verfassten Kapitelinhalte sorgfaeltig und beschreiben Sie nicht dieselben Informationen erneut
7. \u3010Nochmalige Betonung\u3011Keine Ueberschriften hinzufuegen! **Fettdruck** anstelle von Unterabschnittsueberschriften verwenden""",

    'report_section_user': """\
Bereits verfasste Kapitelinhalte (bitte sorgfaeltig lesen, Wiederholungen vermeiden):
{previous_content}

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
\u3010Aktuelle Aufgabe\u3011Kapitel verfassen: {section_title}
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

\u3010Wichtiger Hinweis\u3011
1. Lesen Sie die oben bereits verfassten Kapitel sorgfaeltig, um Wiederholungen zu vermeiden!
2. Vor dem Start muessen zuerst Werkzeuge aufgerufen werden, um Simulationsdaten zu erhalten
3. Bitte verwenden Sie verschiedene Werkzeuge kombiniert, nicht nur eines
4. Der Berichtsinhalt muss aus Rechercheergebnissen stammen, verwenden Sie nicht Ihr eigenes Wissen

\u3010\u26a0\ufe0f Formatwarnung - Muss eingehalten werden\u3011
- \u274c Keine Ueberschriften schreiben (#, ##, ###, #### sind alle verboten)
- \u274c Nicht "{section_title}" als Anfang schreiben
- \u2705 Kapitelueberschriften werden automatisch vom System hinzugefuegt
- \u2705 Direkt den Fliesstext schreiben, **Fettdruck** anstelle von Unterabschnittsueberschriften verwenden

Bitte beginnen Sie:
1. Zuerst ueberlegen (Thought), welche Informationen dieses Kapitel benoetigt
2. Dann Werkzeuge aufrufen (Action), um Simulationsdaten zu erhalten
3. Nach ausreichender Informationssammlung Final Answer ausgeben (reiner Fliesstext, ohne jegliche Ueberschriften)""",

    # ── report_agent.py: Tool descriptions ──

    'tool_desc_insight_forge': """\
\u3010Tiefenanalyse-Suche - Leistungsstarkes Recherchewerkzeug\u3011
Dies ist unsere leistungsstarke Recherchefunktion, speziell fuer Tiefenanalysen konzipiert. Sie wird:
1. Ihre Frage automatisch in mehrere Teilfragen zerlegen
2. Informationen aus dem Simulationsgraphen aus mehreren Dimensionen abrufen
3. Ergebnisse aus semantischer Suche, Entitaetsanalyse und Beziehungskettenverfolgung integrieren
4. Die umfassendsten und tiefgruendigsten Rechercheergebnisse liefern

\u3010Einsatzszenarien\u3011
- Wenn ein Thema eingehend analysiert werden muss
- Wenn mehrere Aspekte eines Ereignisses verstanden werden muessen
- Wenn reichhaltiges Material zur Unterstuetzung von Berichtskapiteln benoetigt wird

\u3010Rueckgabeinhalte\u3011
- Relevante Fakten im Originaltext (direkt zitierbar)
- Kernentitaets-Erkenntnisse
- Beziehungskettenanalyse""",

    'tool_desc_panorama_search': """\
\u3010Breitensuche - Gesamtueberblick erhalten\u3011
Dieses Werkzeug dient dazu, ein vollstaendiges Gesamtbild der Simulationsergebnisse zu erhalten, besonders geeignet um Ereignisentwicklungen zu verstehen. Es wird:
1. Alle relevanten Knoten und Beziehungen abrufen
2. Zwischen aktuell gueltigen Fakten und historischen/abgelaufenen Fakten unterscheiden
3. Ihnen helfen zu verstehen, wie sich die Meinungslage entwickelt hat

\u3010Einsatzszenarien\u3011
- Wenn der vollstaendige Entwicklungsverlauf eines Ereignisses verstanden werden muss
- Wenn Meinungsaenderungen in verschiedenen Phasen verglichen werden muessen
- Wenn umfassende Entitaets- und Beziehungsinformationen benoetigt werden

\u3010Rueckgabeinhalte\u3011
- Aktuell gueltige Fakten (neueste Simulationsergebnisse)
- Historische/abgelaufene Fakten (Entwicklungsprotokoll)
- Alle beteiligten Entitaeten""",

    'tool_desc_quick_search': """\
\u3010Einfache Suche - Schnellrecherche\u3011
Leichtgewichtiges Schnellrecherche-Werkzeug, geeignet fuer einfache, direkte Informationsabfragen.

\u3010Einsatzszenarien\u3011
- Wenn eine bestimmte Information schnell gefunden werden muss
- Wenn ein Fakt verifiziert werden muss
- Einfache Informationsrecherche

\u3010Rueckgabeinhalte\u3011
- Liste der zur Abfrage relevantesten Fakten""",

    'tool_desc_interview_agents': """\
\u3010Tiefeninterview - Echte Agent-Befragung (Dual-Plattform)\u3011
Ruft die Interview-API der OASIS-Simulationsumgebung auf, um laufende Simulations-Agents real zu befragen!
Dies ist keine LLM-Simulation, sondern ein Aufruf der echten Interview-Schnittstelle fuer originale Antworten der Simulations-Agents.
Standardmaessig werden Interviews auf beiden Plattformen Twitter und Reddit gleichzeitig gefuehrt, um umfassendere Standpunkte zu erhalten.

Funktionsablauf:
1. Automatisches Lesen der Persona-Datei, um alle Simulations-Agents kennenzulernen
2. Intelligente Auswahl der zum Interviewthema relevantesten Agents (z.B. Studenten, Medien, Behoerden usw.)
3. Automatische Generierung von Interviewfragen
4. Aufruf der /api/simulation/interview/batch-Schnittstelle fuer echte Interviews auf beiden Plattformen
5. Integration aller Interviewergebnisse mit Mehrperspektiven-Analyse

\u3010Einsatzszenarien\u3011
- Wenn Ereignismeinungen aus verschiedenen Rollenperspektiven verstanden werden muessen (Wie sehen Studenten das? Wie die Medien? Was sagen die Behoerden?)
- Wenn Meinungen und Standpunkte mehrerer Parteien gesammelt werden muessen
- Wenn echte Antworten von Simulations-Agents benoetigt werden (aus der OASIS-Simulationsumgebung)
- Wenn der Bericht lebendiger sein soll und "Interviewprotokolle" enthalten soll

\u3010Rueckgabeinhalte\u3011
- Identitaetsinformationen der befragten Agents
- Interviewantworten der einzelnen Agents auf beiden Plattformen Twitter und Reddit
- Schluesselzitate (direkt zitierbar)
- Interviewzusammenfassung und Standpunktvergleich

\u3010Wichtig\u3011Die OASIS-Simulationsumgebung muss aktiv sein, um diese Funktion nutzen zu koennen!""",

    # ── report_agent.py: ReACT loop messages ──

    'react_observation': """\
Observation (Suchergebnisse):

\u2550\u2550\u2550 Werkzeug {tool_name} Ergebnis \u2550\u2550\u2550
{result}

\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
Werkzeuge aufgerufen: {tool_calls_count}/{max_tool_calls} (Verwendet: {used_tools_str}){unused_hint}
- Bei ausreichenden Informationen: Kapitelinhalt mit "Final Answer:" beginnen (obige Originaltexte muessen zitiert werden)
- Bei Bedarf an mehr Informationen: Ein Werkzeug aufrufen und weiter recherchieren
\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550""",

    'react_insufficient_tools': (
        "\u3010Achtung\u3011Sie haben nur {tool_calls_count} Werkzeuge aufgerufen, mindestens {min_tool_calls} sind erforderlich. "
        "Bitte rufen Sie weitere Werkzeuge auf, um mehr Simulationsdaten zu erhalten, bevor Sie Final Answer ausgeben. {unused_hint}"
    ),

    'react_insufficient_tools_alt': (
        "Bisher wurden nur {tool_calls_count} Werkzeuge aufgerufen, mindestens {min_tool_calls} sind erforderlich. "
        "Bitte rufen Sie Werkzeuge auf, um Simulationsdaten zu erhalten. {unused_hint}"
    ),

    'react_tool_limit': (
        "Werkzeugaufruf-Limit erreicht ({tool_calls_count}/{max_tool_calls}), keine weiteren Werkzeugaufrufe moeglich. "
        'Bitte geben Sie sofort basierend auf den bereits erhaltenen Informationen den Kapitelinhalt mit "Final Answer:" am Anfang aus.'
    ),

    'react_unused_tools_hint': "\n\U0001f4a1 Noch nicht verwendet: {unused_list}, Empfehlung: verschiedene Werkzeuge ausprobieren fuer Informationen aus mehreren Perspektiven",

    'react_force_final': "Werkzeugaufruf-Limit erreicht, bitte geben Sie direkt Final Answer: aus und erstellen Sie den Kapitelinhalt.",

    # ── report_agent.py: Chat prompt ──

    'chat_system': """\
Sie sind ein praeziser und effizienter Simulationsvorhersage-Assistent.

\u3010Hintergrund\u3011
Vorhersagebedingungen: {simulation_requirement}

\u3010Bereits erstellter Analysebericht\u3011
{report_content}

\u3010Regeln\u3011
1. Fragen bevorzugt basierend auf dem obigen Berichtsinhalt beantworten
2. Fragen direkt beantworten, ausfuehrliche Denkausfuehrungen vermeiden
3. Werkzeuge nur aufrufen, wenn der Berichtsinhalt zur Beantwortung nicht ausreicht
4. Antworten sollen praegnant, klar und strukturiert sein

\u3010Verfuegbare Werkzeuge\u3011(nur bei Bedarf verwenden, maximal 1-2 Aufrufe)
{tools_description}

\u3010Werkzeugaufruf-Format\u3011
<tool_call>
{{"name": "Werkzeugname", "parameters": {{"Parametername": "Parameterwert"}}}}
</tool_call>

\u3010Antwortstil\u3011
- Praegnant und direkt, keine langen Abhandlungen
- > Format fuer Zitate wichtiger Inhalte verwenden
- Zuerst die Schlussfolgerung geben, dann die Begruendung erlaeutern""",

    'chat_observation_suffix': "\n\nBitte beantworten Sie die Frage praegnant.",

    # ── zep_tools.py: InsightForge sub-query generation ──

    'insight_forge_sub_query_system': """Sie sind ein professioneller Experte f\u00fcr Fragenanalyse. Ihre Aufgabe ist es, eine komplexe Frage in mehrere Teilfragen zu zerlegen, die in der simulierten Welt unabh\u00e4ngig beobachtet werden k\u00f6nnen.

Anforderungen:
1. Jede Teilfrage sollte spezifisch genug sein, um in der simulierten Welt relevante Agent-Verhaltensweisen oder Ereignisse zu finden
2. Die Teilfragen sollten verschiedene Dimensionen der urspr\u00fcnglichen Frage abdecken (z.B.: Wer, Was, Warum, Wie, Wann, Wo)
3. Die Teilfragen sollten mit dem Simulationsszenario zusammenh\u00e4ngen
4. R\u00fcckgabe im JSON-Format: {"sub_queries": ["Teilfrage1", "Teilfrage2", ...]}""",

    'insight_forge_sub_query_user': """Hintergrund der Simulationsanforderung:
{simulation_requirement}

{report_context_line}

Bitte zerlegen Sie die folgende Frage in {max_queries} Teilfragen:
{query}

Geben Sie die Teilfragenliste im JSON-Format zur\u00fcck.""",

    # ── zep_tools.py: Interview agent selection ──

    'interview_select_system': """Sie sind ein professioneller Interview-Planungsexperte. Ihre Aufgabe ist es, basierend auf den Interview-Anforderungen die am besten geeigneten Interviewpartner aus der Liste der simulierten Agents auszuw\u00e4hlen.

Auswahlkriterien:
1. Die Identit\u00e4t/der Beruf des Agents ist relevant f\u00fcr das Interviewthema
2. Der Agent k\u00f6nnte einzigartige oder wertvolle Standpunkte vertreten
3. W\u00e4hlen Sie vielf\u00e4ltige Perspektiven (z.B.: Bef\u00fcrworter, Gegner, Neutrale, Fachleute etc.)
4. Bevorzugen Sie Rollen, die direkt mit dem Ereignis zusammenh\u00e4ngen

R\u00fcckgabe im JSON-Format:
{
    "selected_indices": [Indexliste der ausgew\u00e4hlten Agents],
    "reasoning": "Erkl\u00e4rung der Auswahlgr\u00fcnde"
}""",

    'interview_select_user': """Interview-Anforderung:
{interview_requirement}

Simulationshintergrund:
{simulation_requirement}

Verf\u00fcgbare Agent-Liste (insgesamt {agent_count}):
{agent_summaries_json}

Bitte w\u00e4hlen Sie maximal {max_agents} der am besten geeigneten Agents f\u00fcr das Interview aus und erkl\u00e4ren Sie die Auswahlgr\u00fcnde.""",

    # ── zep_tools.py: Interview question generation ──

    'interview_questions_system': """Sie sind ein professioneller Journalist/Interviewer. Generieren Sie basierend auf den Interview-Anforderungen 3-5 tiefgehende Interviewfragen.

Anforderungen an die Fragen:
1. Offene Fragen, die zu ausf\u00fchrlichen Antworten ermutigen
2. Fragen, die je nach Rolle unterschiedliche Antworten hervorrufen k\u00f6nnen
3. Abdeckung mehrerer Dimensionen wie Fakten, Meinungen, Gef\u00fchle etc.
4. Nat\u00fcrliche Sprache, wie in einem echten Interview
5. Jede Frage sollte maximal 50 W\u00f6rter umfassen, kurz und pr\u00e4gnant
6. Direkte Fragestellung, ohne Hintergrundbeschreibung oder Pr\u00e4fix

R\u00fcckgabe im JSON-Format: {"questions": ["Frage1", "Frage2", ...]}""",

    'interview_questions_user': """Interview-Anforderung: {interview_requirement}

Simulationshintergrund: {simulation_requirement}

Rollen der Interviewpartner: {agent_roles}

Bitte generieren Sie 3-5 Interviewfragen.""",

    # ── zep_tools.py: Interview summary generation ──

    'interview_summary_system': """Sie sind ein professioneller Nachrichtenredakteur. Bitte erstellen Sie basierend auf den Antworten mehrerer Befragter eine Interviewzusammenfassung.

Anforderungen an die Zusammenfassung:
1. Destillieren Sie die Hauptstandpunkte aller Parteien
2. Weisen Sie auf Konsens und Meinungsverschiedenheiten hin
3. Heben Sie wertvolle Zitate hervor
4. Bleiben Sie objektiv und neutral, bevorzugen Sie keine Seite
5. Maximal 1000 W\u00f6rter

Formatvorgaben (m\u00fcssen eingehalten werden):
- Verwenden Sie Klartext-Abs\u00e4tze, trennen Sie verschiedene Abschnitte mit Leerzeilen
- Verwenden Sie keine Markdown-\u00dcberschriften (wie #, ##, ###)
- Verwenden Sie keine Trennlinien (wie ---, ***)
- Verwenden Sie beim Zitieren von Befragten deutsche Anf\u00fchrungszeichen \u201e\u201c
- Sie k\u00f6nnen **Fettdruck** f\u00fcr Schl\u00fcsselw\u00f6rter verwenden, aber keine andere Markdown-Syntax""",

    'interview_summary_user': """Interviewthema: {interview_requirement}

Interviewinhalte:
{interview_texts}

Bitte erstellen Sie eine Interviewzusammenfassung.""",

    # ── zep_tools.py: Interview prompt prefix (sent to OASIS agents) ──

    'interview_prompt_prefix': (
        "Sie werden gerade interviewt. Bitte beantworten Sie die folgenden Fragen "
        "basierend auf Ihrer Pers\u00f6nlichkeit, allen bisherigen Erinnerungen und Handlungen "
        "direkt als Klartext.\n"
        "Antwortanforderungen:\n"
        "1. Antworten Sie direkt in nat\u00fcrlicher Sprache, rufen Sie keine Werkzeuge auf\n"
        "2. Bleiben Sie in Ihrer Rolle, antworten Sie aus Ihrer Perspektive\n"
        "3. Antworten Sie ausf\u00fchrlich und detailliert, mindestens 3-5 S\u00e4tze pro Frage\n"
        "4. Beantworten Sie jede Frage der Reihe nach, beginnen Sie jede Antwort mit \u201eFrage X:\u201c (X = Fragenummer)\n"
        "5. Wenn Sie sich bei einer Frage unsicher sind, antworten Sie basierend auf Ihrer Pers\u00f6nlichkeit und Ihren Erfahrungen\n\n"
    ),

    # ── simulation.py: Interview prompt prefix (API endpoint) ──

    'simulation_interview_prompt_prefix': "Basierend auf Ihrer Pers\u00f6nlichkeit, allen bisherigen Erinnerungen und Handlungen, antworten Sie direkt als Text ohne Werkzeugaufrufe:",

    # ── ontology_generator.py ──

    'ontology_system': """Sie sind ein professioneller Experte fuer Wissensgraph-Ontologie-Design. Ihre Aufgabe ist es, den gegebenen Textinhalt und die Simulationsanforderungen zu analysieren und geeignete Entitaets- und Beziehungstypen fuer eine **Social-Media-Meinungssimulation** zu entwerfen.

**Wichtig: Sie muessen gueltige JSON-Daten ausgeben und keinen anderen Inhalt.**

## Kernaufgabe - Hintergrund

Wir bauen ein **Social-Media-Meinungssimulationssystem** auf. In diesem System:
- Jede Entitaet ist ein "Konto" oder "Akteur", der in sozialen Medien posten, interagieren und Informationen verbreiten kann
- Entitaeten beeinflussen sich gegenseitig, teilen, kommentieren und reagieren aufeinander
- Wir muessen die Reaktionen verschiedener Parteien bei Meinungsereignissen und die Wege der Informationsverbreitung simulieren

Daher **muessen Entitaeten real existierende Akteure sein, die in sozialen Medien posten und interagieren koennen**:

**Erlaubt**:
- Konkrete Einzelpersonen (oeffentliche Persoenlichkeiten, Beteiligte, Meinungsfuehrer, Experten, normale Buerger)
- Unternehmen und Firmen (einschliesslich ihrer offiziellen Konten)
- Organisationen (Universitaeten, Verbaende, NGOs, Gewerkschaften usw.)
- Regierungsbehoerden, Aufsichtsbehoerden
- Medienorganisationen (Zeitungen, Fernsehsender, unabhaengige Medien, Webseiten)
- Social-Media-Plattformen selbst
- Vertreter bestimmter Gruppen (z.B. Alumni-Vereine, Fangruppen, Interessengruppen usw.)

**Nicht erlaubt**:
- Abstrakte Konzepte (z.B. "oeffentliche Meinung", "Stimmung", "Trend")
- Themen/Diskussionsgegenstaende (z.B. "akademische Integritaet", "Bildungsreform")
- Standpunkte/Haltungen (z.B. "Befuerworter", "Gegner")

## Ausgabeformat

Bitte geben Sie JSON im folgenden Format aus:

```json
{
    "entity_types": [
        {
            "name": "Entitaetstypname (Englisch, PascalCase)",
            "description": "Kurzbeschreibung (Englisch, max. 100 Zeichen)",
            "attributes": [
                {
                    "name": "Attributname (Englisch, snake_case)",
                    "type": "text",
                    "description": "Attributbeschreibung"
                }
            ],
            "examples": ["Beispielentitaet1", "Beispielentitaet2"]
        }
    ],
    "edge_types": [
        {
            "name": "Beziehungstypname (Englisch, UPPER_SNAKE_CASE)",
            "description": "Kurzbeschreibung (Englisch, max. 100 Zeichen)",
            "source_targets": [
                {"source": "Quellentitaetstyp", "target": "Zielentitaetstyp"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Kurze Analysebeschreibung des Textinhalts (auf Deutsch)"
}
```

## Designrichtlinien (aeusserst wichtig!)

### 1. Entitaetstyp-Design - Muss strikt eingehalten werden

**Mengenanforderung: Es muessen genau 10 Entitaetstypen sein**

**Hierarchieanforderung (muss sowohl spezifische als auch Auffangtypen enthalten)**:

Ihre 10 Entitaetstypen muessen folgende Hierarchie aufweisen:

A. **Auffangtypen (muessen enthalten sein, als letzte 2 in der Liste)**:
   - `Person`: Auffangtyp fuer jede natuerliche Person. Wenn eine Person keinem spezifischeren Personentyp zugeordnet werden kann, wird sie hier eingeordnet.
   - `Organization`: Auffangtyp fuer jede Organisation. Wenn eine Organisation keinem spezifischeren Organisationstyp zugeordnet werden kann, wird sie hier eingeordnet.

B. **Spezifische Typen (8, basierend auf dem Textinhalt entworfen)**:
   - Entwerfen Sie spezifischere Typen fuer die Hauptakteure im Text
   - Beispiel: Bei akademischen Ereignissen koennen `Student`, `Professor`, `University` verwendet werden
   - Beispiel: Bei wirtschaftlichen Ereignissen koennen `Company`, `CEO`, `Employee` verwendet werden

**Warum Auffangtypen benoetigt werden**:
- Im Text tauchen verschiedene Personen auf, wie "Grundschullehrer", "Passanten", "anonyme Internetnutzer"
- Wenn kein spezifischer Typ passt, sollten sie unter `Person` eingeordnet werden
- Ebenso sollten kleine Organisationen, temporaere Gruppen usw. unter `Organization` eingeordnet werden

**Designprinzipien fuer spezifische Typen**:
- Identifizieren Sie haeufig auftretende oder wichtige Akteurtypen im Text
- Jeder spezifische Typ sollte klare Grenzen haben, Ueberschneidungen vermeiden
- Die description muss den Unterschied zwischen diesem Typ und dem Auffangtyp klar beschreiben

### 2. Beziehungstyp-Design

- Anzahl: 6-10
- Beziehungen sollten reale Verbindungen in Social-Media-Interaktionen widerspiegeln
- Stellen Sie sicher, dass die source_targets der Beziehungen Ihre definierten Entitaetstypen abdecken

### 3. Attribut-Design

- 1-3 Schluesselattribute pro Entitaetstyp
- **Achtung**: Attributnamen duerfen nicht `name`, `uuid`, `group_id`, `created_at`, `summary` verwenden (diese sind Systemreservierungen)
- Empfohlen: `full_name`, `title`, `role`, `position`, `location`, `description` usw.

## Entitaetstyp-Referenz

**Personentypen (spezifisch)**:
- Student: Student
- Professor: Professor/Wissenschaftler
- Journalist: Journalist
- Celebrity: Prominenter/Influencer
- Executive: Fuehrungskraft
- Official: Regierungsbeamter
- Lawyer: Rechtsanwalt
- Doctor: Arzt

**Personentypen (Auffang)**:
- Person: Jede natuerliche Person (wird verwendet, wenn kein spezifischerer Typ passt)

**Organisationstypen (spezifisch)**:
- University: Hochschule
- Company: Unternehmen
- GovernmentAgency: Regierungsbehoerde
- MediaOutlet: Medienorganisation
- Hospital: Krankenhaus
- School: Schule
- NGO: Nichtregierungsorganisation

**Organisationstypen (Auffang)**:
- Organization: Jede Organisation (wird verwendet, wenn kein spezifischerer Typ passt)

## Beziehungstyp-Referenz

- WORKS_FOR: Arbeitet bei
- STUDIES_AT: Studiert an
- AFFILIATED_WITH: Gehoert zu
- REPRESENTS: Vertritt
- REGULATES: Beaufsichtigt
- REPORTS_ON: Berichtet ueber
- COMMENTS_ON: Kommentiert
- RESPONDS_TO: Reagiert auf
- SUPPORTS: Unterstuetzt
- OPPOSES: Widerspricht
- COLLABORATES_WITH: Kooperiert mit
- COMPETES_WITH: Konkurriert mit""",

    'ontology_user_suffix': """
Bitte entwerfen Sie auf Basis des obigen Inhalts geeignete Entitaets- und Beziehungstypen fuer eine Meinungssimulation.

**Verbindliche Regeln**:
1. Es muessen genau 10 Entitaetstypen ausgegeben werden
2. Die letzten 2 muessen Auffangtypen sein: Person (Personen-Auffang) und Organization (Organisations-Auffang)
3. Die ersten 8 sind spezifische Typen, die auf dem Textinhalt basieren
4. Alle Entitaetstypen muessen real existierende Akteure sein, keine abstrakten Konzepte
5. Attributnamen duerfen keine Reservierungen wie name, uuid, group_id verwenden, stattdessen full_name, org_name usw.""",

    # ── simulation_config_generator.py ──

    'sim_config_time_system': "Sie sind ein Experte fuer Social-Media-Simulation. Reine JSON-Ausgabe, die Zeitkonfiguration muss passend zu deutschen Tagesablaeufen sein.",

    'sim_config_event_system': "Sie sind ein Experte fuer Meinungsanalyse. Reine JSON-Ausgabe. Beachten Sie, dass poster_type exakt mit den verfuegbaren Entitaetstypen uebereinstimmen muss.",

    'sim_config_agent_system': "Sie sind ein Experte fuer Social-Media-Verhaltensanalyse. Reine JSON-Ausgabe, die Konfiguration muss passend zu deutschen Tagesablaeufen sein.",

    # ── oasis_profile_generator.py ──

    'profile_system': "Sie sind ein Experte fuer die Erstellung von Social-Media-Nutzerprofilen. Generieren Sie detaillierte, realistische Personenbeschreibungen fuer Meinungssimulationen, die die reale Situation bestmoeglich abbilden. Es muss gueltiges JSON-Format zurueckgegeben werden, alle Zeichenkettenwerte duerfen keine unescapten Zeilenumbrueche enthalten. Verwenden Sie Deutsch.",

    'profile_individual_user': """Generieren Sie eine detaillierte Social-Media-Nutzerpersona fuer die Entitaet, die die reale Situation bestmoeglich abbildet.

Entitaetsname: {entity_name}
Entitaetstyp: {entity_type}
Entitaetszusammenfassung: {entity_summary}
Entitaetsattribute: {attrs_str}

Kontextinformationen:
{context_str}

Bitte generieren Sie JSON mit folgenden Feldern:

1. bio: Social-Media-Kurzbiografie, 200 Zeichen
2. persona: Detaillierte Personenbeschreibung (2000 Zeichen Klartext), muss enthalten:
   - Basisinformationen (Alter, Beruf, Bildungshintergrund, Wohnort)
   - Personenhintergrund (wichtige Erfahrungen, Verbindung zum Ereignis, soziale Beziehungen)
   - Persoenlichkeitsmerkmale (MBTI-Typ, Kernpersoenlichkeit, Art des emotionalen Ausdrucks)
   - Social-Media-Verhalten (Beitragshaeufigkeit, Inhaltspraeferenzen, Interaktionsstil, Sprachmerkmale)
   - Standpunkte (Haltung zu Themen, Inhalte die provozieren/beruehren koennten)
   - Einzigartige Merkmale (Redewendungen, besondere Erfahrungen, persoenliche Hobbys)
   - Persoenliche Erinnerungen (wichtiger Teil der Persona, die Verbindung dieser Person zum Ereignis sowie deren bisherige Aktionen und Reaktionen im Ereignis beschreiben)
3. age: Alter als Zahl (muss eine Ganzzahl sein)
4. gender: Geschlecht, muss auf Englisch sein: "male" oder "female"
5. mbti: MBTI-Typ (z.B. INTJ, ENFP usw.)
6. country: Land (auf Deutsch, z.B. "Deutschland")
7. profession: Beruf
8. interested_topics: Array von Interessenthemen

Wichtig:
- Alle Feldwerte muessen Zeichenketten oder Zahlen sein, keine Zeilenumbrueche verwenden
- persona muss eine zusammenhaengende Textbeschreibung sein
- Verwenden Sie Deutsch (ausser beim gender-Feld, das muss auf Englisch male/female sein)
- Inhalt muss mit den Entitaetsinformationen uebereinstimmen
- age muss eine gueltige Ganzzahl sein, gender muss "male" oder "female" sein""",

    'profile_group_user': """Generieren Sie eine detaillierte Social-Media-Kontoeinstellung fuer eine Institutions-/Gruppenentitaet, die die reale Situation bestmoeglich abbildet.

Entitaetsname: {entity_name}
Entitaetstyp: {entity_type}
Entitaetszusammenfassung: {entity_summary}
Entitaetsattribute: {attrs_str}

Kontextinformationen:
{context_str}

Bitte generieren Sie JSON mit folgenden Feldern:

1. bio: Offizielle Konto-Kurzbiografie, 200 Zeichen, professionell und angemessen
2. persona: Detaillierte Kontobeschreibung (2000 Zeichen Klartext), muss enthalten:
   - Grundinformationen der Institution (offizieller Name, Art der Institution, Gruendungshintergrund, Hauptfunktionen)
   - Kontopositionierung (Kontotyp, Zielgruppe, Kernfunktion)
   - Kommunikationsstil (Sprachmerkmale, haeufig verwendete Ausdruecke, Tabuthemen)
   - Veroeffentlichungsmerkmale (Inhaltstypen, Veroeffentlichungshaeufigkeit, aktive Zeitraeume)
   - Standpunkt und Haltung (offizielle Position zu Kernthemen, Umgang mit Kontroversen)
   - Besondere Hinweise (vertretenes Gruppenprofil, Betriebsgewohnheiten)
   - Institutionelle Erinnerungen (wichtiger Teil der Institutions-Persona, die Verbindung dieser Institution zum Ereignis sowie deren bisherige Aktionen und Reaktionen im Ereignis beschreiben)
3. age: Fest auf 30 (virtuelles Alter des Institutionskontos)
4. gender: Fest auf "other" (Institutionskonten verwenden other fuer nicht-persoenlich)
5. mbti: MBTI-Typ, zur Beschreibung des Kontostils, z.B. ISTJ fuer streng konservativ
6. country: Land (auf Deutsch, z.B. "Deutschland")
7. profession: Beschreibung der Institutionsfunktion
8. interested_topics: Array der Interessenbereiche

Wichtig:
- Alle Feldwerte muessen Zeichenketten oder Zahlen sein, keine null-Werte erlaubt
- persona muss eine zusammenhaengende Textbeschreibung sein, keine Zeilenumbrueche verwenden
- Verwenden Sie Deutsch (ausser beim gender-Feld, das muss auf Englisch "other" sein)
- age muss die Ganzzahl 30 sein, gender muss die Zeichenkette "other" sein
- Institutionskonten muessen ihrer Identitaet und Positionierung entsprechend kommunizieren""",
}


# ═══════════════════════════════════════════════════════════════
# FORMATS - Short format strings with placeholders
# ═══════════════════════════════════════════════════════════════

FORMATS = {
    # ── zep_tools.py: SearchResult.to_text() ──
    'search_query': 'Suchanfrage: {query}',
    'search_results_found': '{count} relevante Ergebnisse gefunden',
    'search_relevant_facts_header': '\n### Relevante Fakten:',

    # ── zep_tools.py: NodeInfo.to_text() ──
    'node_info': 'Entit\u00e4t: {name} (Typ: {entity_type})\nZusammenfassung: {summary}',
    'node_unknown_type': 'Unbekannter Typ',

    # ── zep_tools.py: EdgeInfo.to_text() ──
    'edge_info': 'Beziehung: {source} --[{name}]--> {target}\nFakt: {fact}',
    'edge_validity': '\nG\u00fcltigkeit: {valid_at} - {invalid_at}',
    'edge_expired': ' (Abgelaufen: {expired_at})',
    'edge_valid_at_unknown': 'Unbekannt',
    'edge_invalid_at_default': 'Bis heute',

    # ── zep_tools.py: InsightForgeResult.to_text() ──
    'insight_header': '## Tiefenanalyse der Zukunftsvorhersage',
    'insight_query': 'Analysefrage: {query}',
    'insight_scenario': 'Vorhersageszenario: {simulation_requirement}',
    'insight_stats_header': '\n### Vorhersagedatenstatistik',
    'insight_stats_facts': '- Relevante Vorhersagefakten: {count}',
    'insight_stats_entities': '- Beteiligte Entit\u00e4ten: {count}',
    'insight_stats_relations': '- Beziehungsketten: {count}',
    'insight_sub_queries_header': '\n### Analysierte Teilfragen',
    'insight_key_facts_header': '\n### \u3010Schl\u00fcsselfakten\u3011(Bitte diese Originaltexte im Bericht zitieren)',
    'insight_core_entities_header': '\n### \u3010Kernentit\u00e4ten\u3011',
    'insight_entity_line': '- **{name}** ({entity_type})',
    'insight_entity_summary': '  Zusammenfassung: "{summary}"',
    'insight_entity_facts_count': '  Relevante Fakten: {count}',
    'insight_relationship_chains_header': '\n### \u3010Beziehungsketten\u3011',

    # ── zep_tools.py: PanoramaResult.to_text() ──
    'panorama_header': '## Breitensuchergebnisse (Zukunfts-Panorama)',
    'panorama_query': 'Abfrage: {query}',
    'panorama_stats_header': '\n### Statistikinformationen',
    'panorama_stats_nodes': '- Gesamtknoten: {count}',
    'panorama_stats_edges': '- Gesamtkanten: {count}',
    'panorama_stats_active': '- Aktuell g\u00fcltige Fakten: {count}',
    'panorama_stats_historical': '- Historische/abgelaufene Fakten: {count}',
    'panorama_active_header': '\n### \u3010Aktuell g\u00fcltige Fakten\u3011(Originale Simulationsergebnisse)',
    'panorama_historical_header': '\n### \u3010Historische/abgelaufene Fakten\u3011(Aufzeichnung des Entwicklungsverlaufs)',
    'panorama_entities_header': '\n### \u3010Beteiligte Entit\u00e4ten\u3011',
    'panorama_entity_line': '- **{name}** ({entity_type})',
    'panorama_entity_type_default': 'Entit\u00e4t',

    # ── zep_tools.py: AgentInterview.to_text() ──
    'interview_agent_profile': '_Kurzprofil: {bio}_',
    'interview_key_quotes_header': '\n**Schl\u00fcsselzitate:**\n',

    # ── zep_tools.py: InterviewResult.to_text() ──
    'interview_result_header': '## Tiefeninterview-Bericht',
    'interview_topic': '**Interviewthema:** {topic}',
    'interview_respondent_count': '**Anzahl Befragte:** {interviewed} / {total} simulierte Agenten',
    'interview_selection_reasoning_header': '\n### Begr\u00fcndung der Interviewpartner-Auswahl',
    'interview_record_header': '\n### Interviewprotokoll',
    'interview_entry_header': '\n#### Interview #{index}: {name}',
    'interview_no_record': '(Kein Interviewprotokoll)\n\n---',
    'interview_summary_header': '\n### Interviewzusammenfassung und Kernaussagen',

    # ── zep_tools.py: Dual platform markers ──
    'interview_twitter_response': '\u3010Twitter-Plattform-Antwort\u3011\n{text}',
    'interview_reddit_response': '\u3010Reddit-Plattform-Antwort\u3011\n{text}',
    'interview_no_platform_response': '(Keine Antwort von dieser Plattform)',

    # ── zep_graph_memory_updater.py: Activity descriptions ──
    'activity_create_post': 'hat einen Beitrag veroeffentlicht: \u300c{content}\u300d',
    'activity_create_post_empty': 'hat einen Beitrag veroeffentlicht',
    'activity_like_post': 'hat den Beitrag von {author} geliked: \u300c{content}\u300d',
    'activity_like_post_content_only': 'hat einen Beitrag geliked: \u300c{content}\u300d',
    'activity_like_post_author_only': 'hat einen Beitrag von {author} geliked',
    'activity_like_post_empty': 'hat einen Beitrag geliked',
    'activity_dislike_post': 'hat den Beitrag von {author} gedisliked: \u300c{content}\u300d',
    'activity_dislike_post_content_only': 'hat einen Beitrag gedisliked: \u300c{content}\u300d',
    'activity_dislike_post_author_only': 'hat einen Beitrag von {author} gedisliked',
    'activity_dislike_post_empty': 'hat einen Beitrag gedisliked',
    'activity_repost': 'hat den Beitrag von {author} weitergeleitet: \u300c{content}\u300d',
    'activity_repost_content_only': 'hat einen Beitrag weitergeleitet: \u300c{content}\u300d',
    'activity_repost_author_only': 'hat einen Beitrag von {author} weitergeleitet',
    'activity_repost_empty': 'hat einen Beitrag weitergeleitet',
    'activity_quote_post': 'hat den Beitrag von {author} zitiert \u300c{content}\u300d',
    'activity_quote_post_content_only': 'hat einen Beitrag zitiert \u300c{content}\u300d',
    'activity_quote_post_author_only': 'hat einen Beitrag von {author} zitiert',
    'activity_quote_post_empty': 'hat einen Beitrag zitiert',
    'activity_quote_comment': ', und kommentierte: \u300c{content}\u300d',
    'activity_follow': 'folgt dem Benutzer \u300c{name}\u300d',
    'activity_follow_empty': 'folgt einem Benutzer',
    'activity_create_comment': 'hat unter dem Beitrag von {author} \u300c{post_content}\u300d kommentiert: \u300c{content}\u300d',
    'activity_create_comment_post_only': 'hat unter dem Beitrag \u300c{post_content}\u300d kommentiert: \u300c{content}\u300d',
    'activity_create_comment_author_only': 'hat unter dem Beitrag von {author} kommentiert: \u300c{content}\u300d',
    'activity_create_comment_content_only': 'hat kommentiert: \u300c{content}\u300d',
    'activity_create_comment_empty': 'hat einen Kommentar veroeffentlicht',
    'activity_like_comment': 'hat den Kommentar von {author} geliked: \u300c{content}\u300d',
    'activity_like_comment_content_only': 'hat einen Kommentar geliked: \u300c{content}\u300d',
    'activity_like_comment_author_only': 'hat einen Kommentar von {author} geliked',
    'activity_like_comment_empty': 'hat einen Kommentar geliked',
    'activity_dislike_comment': 'hat den Kommentar von {author} gedisliked: \u300c{content}\u300d',
    'activity_dislike_comment_content_only': 'hat einen Kommentar gedisliked: \u300c{content}\u300d',
    'activity_dislike_comment_author_only': 'hat einen Kommentar von {author} gedisliked',
    'activity_dislike_comment_empty': 'hat einen Kommentar gedisliked',
    'activity_search': 'hat nach \u300c{query}\u300d gesucht',
    'activity_search_empty': 'hat eine Suche durchgefuehrt',
    'activity_search_user': 'hat nach Benutzer \u300c{query}\u300d gesucht',
    'activity_search_user_empty': 'hat nach Benutzern gesucht',
    'activity_mute': 'hat den Benutzer \u300c{name}\u300d stummgeschaltet',
    'activity_mute_empty': 'hat einen Benutzer stummgeschaltet',
    'activity_generic': 'hat die Aktion {action_type} ausgefuehrt',

    # ── oasis_profile_generator.py: Zep search query ──
    'zep_entity_search_query': 'Alle Informationen, Aktivitaeten, Ereignisse, Beziehungen und Hintergruende zu {entity_name}',

    # ── simulation_config_generator.py: Progress messages ──
    'sim_progress_time': 'Zeitkonfiguration wird generiert...',
    'sim_progress_events': 'Ereigniskonfiguration und Trendthemen werden generiert...',
    'sim_progress_agents': 'Agent-Konfiguration wird generiert ({start}-{end}/{total})...',
    'sim_progress_platform': 'Plattformkonfiguration wird generiert...',
}


# ═══════════════════════════════════════════════════════════════
# STRINGS - UI labels, status messages, defaults
# ═══════════════════════════════════════════════════════════════

STRINGS = {
    # ── report_agent.py: Defaults ──
    'report_default_title': 'Zukunftsvorhersage-Bericht',
    'report_default_summary': 'Analyse zukuenftiger Trends und Risiken basierend auf Simulationsvorhersagen',
    'report_fallback_section_1': 'Vorhersageszenarien und Kernerkenntnisse',
    'report_fallback_section_2': 'Analyse des vorhergesagten Gruppenverhaltens',
    'report_fallback_section_3': 'Trendausblick und Risikohinweise',
    'report_first_chapter_marker': '(Dies ist das erste Kapitel)',

    # ── report_agent.py: Log messages ──
    'log_report_start': 'Berichtsgenerierungsaufgabe gestartet',
    'log_planning_start': 'Planung der Berichtsgliederung beginnt',
    'log_planning_context': 'Simulations-Kontextinformationen werden abgerufen',
    'log_planning_complete': 'Gliederungsplanung abgeschlossen',
    'log_section_start': 'Abschnittsgenerierung beginnt: {title}',
    'log_react_thought': 'ReACT Runde {iteration} Denken',
    'log_tool_call': 'Werkzeug aufgerufen: {tool_name}',
    'log_tool_result': 'Werkzeug {tool_name} hat Ergebnis zurueckgegeben',
    'log_llm_response': 'LLM-Antwort (Werkzeugaufruf: {has_tool_calls}, Endgueltige Antwort: {has_final_answer})',
    'log_section_content': 'Abschnitt {title} Inhaltsgenerierung abgeschlossen',
    'log_section_complete': 'Abschnitt {title} Generierung abgeschlossen',
    'log_report_complete': 'Berichtsgenerierung abgeschlossen',
    'log_error': 'Fehler aufgetreten: {error}',

    # ── report_agent.py: Progress callbacks ──
    'progress_analyzing': 'Simulationsanforderungen werden analysiert...',
    'progress_outline': 'Berichtsgliederung wird erstellt...',
    'progress_outline_parsing': 'Gliederungsstruktur wird analysiert...',
    'progress_outline_complete': 'Gliederungsplanung abgeschlossen',
    'progress_generating': 'Tiefenrecherche und Verfassen ({tool_calls_count}/{max_tool_calls})',

    # ── report_agent.py: Tool parameter descriptions ──
    'tool_param_insight_query': 'Die Frage oder das Thema, das Sie eingehend analysieren moechten',
    'tool_param_insight_context': 'Kontext des aktuellen Berichtskapitels (optional, hilft bei der Generierung praeziserer Teilfragen)',
    'tool_param_panorama_query': 'Suchabfrage, fuer Relevanzsortierung',
    'tool_param_panorama_expired': 'Ob abgelaufene/historische Inhalte einbezogen werden sollen (Standard: True)',
    'tool_param_quick_query': 'Suchabfrage-Zeichenkette',
    'tool_param_quick_limit': 'Anzahl der zurueckgegebenen Ergebnisse (optional, Standard: 10)',
    'tool_param_interview_topic': "Interviewthema oder Anforderungsbeschreibung (z.B.: 'Meinungen der Studenten zum Formaldehyd-Vorfall im Wohnheim erfahren')",
    'tool_param_interview_max': 'Maximale Anzahl der zu befragenden Agents (optional, Standard: 5, Maximum: 10)',

    # ── report_agent.py: Error messages ──
    'error_unknown_tool': 'Unbekanntes Werkzeug: {tool_name}. Bitte eines der folgenden verwenden: insight_forge, panorama_search, quick_search',
    'error_tool_execution': 'Werkzeugausfuehrung fehlgeschlagen: {error}',

    # ── zep_tools.py: Fallback sub-queries ──
    'fallback_sub_query_main': 'Hauptbeteiligte bei {query}',
    'fallback_sub_query_cause': 'Ursachen und Auswirkungen von {query}',
    'fallback_sub_query_progress': 'Entwicklungsverlauf von {query}',

    # ── zep_tools.py: Interview fallback strings ──
    'interview_no_profiles': 'Keine Agent-Profildateien f\u00fcr Interviews gefunden',
    'interview_api_failed': 'Interview-API-Aufruf fehlgeschlagen: {error}. Bitte OASIS-Simulationsumgebung pr\u00fcfen.',
    'interview_env_failed': 'Interview fehlgeschlagen: {error}. Simulationsumgebung m\u00f6glicherweise beendet, bitte sicherstellen, dass OASIS l\u00e4uft.',
    'interview_exception': 'Fehler w\u00e4hrend des Interviews: {error}',
    'interview_no_completed': 'Kein Interview abgeschlossen',
    'interview_fallback_question': 'Was ist Ihre Meinung zu {topic}?',
    'interview_fallback_question_2': 'Welche Auswirkungen hat dies auf Sie oder die Gruppe, die Sie vertreten?',
    'interview_fallback_question_3': 'Wie sollte dieses Problem Ihrer Meinung nach gel\u00f6st oder verbessert werden?',
    'interview_fallback_summary': 'Insgesamt {count} Befragte interviewt, darunter: {names}',
    'interview_auto_selection': 'Automatische Auswahl basierend auf Relevanz',
    'interview_default_selection': 'Standardauswahlstrategie verwendet',
    'interview_auto_reasoning': '(Automatische Auswahl)',

    # ── zep_tools.py: Misc ──
    'profession_unknown': 'Unbekannt',

    # ── zep_graph_memory_updater.py ──
    'platform_twitter': 'Welt 1',
    'platform_reddit': 'Welt 2',

    # ── simulation.py: API error messages ──
    'error_zep_not_configured': 'ZEP_API_KEY nicht konfiguriert',
    'error_entity_not_found': 'Entitaet existiert nicht: {uuid}',
    'error_project_not_found': 'Projekt existiert nicht: {project_id}',
    'error_no_project_id': 'Bitte geben Sie eine project_id an',
    'error_no_graph': 'Fuer das Projekt wurde noch kein Graph aufgebaut, bitte zuerst /api/graph/build aufrufen',

    # ── oasis_profile_generator.py ──
    'default_country': 'Deutschland',

    # ── simulation_config_generator.py: Default reasoning ──
    'sim_default_time_reasoning': 'Standard-Konfiguration basierend auf chinesischem Tagesablauf (1 Stunde pro Runde)',
    'sim_default_event_reasoning': 'Standard-Konfiguration verwendet',

    # ── ontology_generator.py: Text truncation notice ──
    'ontology_text_truncated': '...(Originaltext umfasst {original_length} Zeichen, die ersten {max_length} Zeichen wurden fuer die Ontologie-Analyse verwendet)...',
}


# ═══════════════════════════════════════════════════════════════
# PATTERNS - Regex patterns that match German FORMATS
# ═══════════════════════════════════════════════════════════════

PATTERNS = {
    # ── Matches FORMATS['insight_query'] ──
    'insight_query': r'Analysefrage:\s*(.+?)(?:\n|$)',

    # ── Matches FORMATS['insight_scenario'] ──
    'insight_scenario': r'Vorhersageszenario:\s*(.+?)(?:\n|$)',

    # ── Matches FORMATS['search_query'] ──
    'search_query': r'Suchanfrage:\s*(.+?)(?:\n|$)',

    # ── Matches FORMATS['search_results_found'] ──
    'search_results_found': r'(\d+)\s*relevante Ergebnisse gefunden',

    # ── Matches FORMATS['panorama_query'] ──
    'panorama_query': r'Abfrage:\s*(.+?)(?:\n|$)',

    # ── "Final Answer:" is a technical marker that stays in English,
    #    but we also match the German translation ──
    'final_answer': r'(?:Final Answer|Endg\u00fcltige Antwort)\s*:\s*',

    # ── Matches interview question numbering pattern (used in key_quotes cleanup) ──
    'interview_question_prefix': r'Frage\s*\d+[:\uff1a]\s*',

    # ── Matches platform response markers in interview output ──
    'interview_twitter_marker': r'\u3010Twitter-Plattform-Antwort\u3011',
    'interview_reddit_marker': r'\u3010Reddit-Plattform-Antwort\u3011',

    # ── Tool call XML tag ──
    'tool_call_xml': r'<tool_call>\s*(\{.*?\})\s*</tool_call>',
}
