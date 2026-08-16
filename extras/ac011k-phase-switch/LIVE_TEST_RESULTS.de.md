# AC011K GD 1.2.460 live relay tests — 2026-08-16

Testaufbau:

- L1: 230-V-LED
- L2 und L3: je eine 60-W-Glühlampe
- CP-Simulator mit den Zuständen A, B und C
- Kein echtes Fahrzeug angeschlossen

## Referenz: unveränderte GD 1.2.460

| Zustand | Physische Ausgabe |
|---|---|
| A / ausgesteckt | L1, L2 und L3 aus |
| B / angesteckt | L1, L2 und L3 aus |
| C / Laden gestartet | L1, L2 und L3 an |
| Stop und zurück zu A | alle aus, kein Fehler |

## PA8: beide späteren RESET-Aufrufe zu SET geändert

- L1, L2 und L3 wurden um beziehungsweise nach dem Flashen eingeschaltet.
- Alle drei Ausgänge blieben auch nach Stop und Neustart eingeschaltet.
- Die Firmware meldete logisch offene Schütze, obwohl physisch Spannung anlag.

## PB3: beide späteren RESET-Aufrufe zu SET geändert

| Zustand | Physische Ausgabe |
|---|---|
| A | nur L1 an; L2 und L3 aus |
| B | unverändert |
| C | L1, L2 und L3 an |
| Stop / A | L1 blieb an; anschließend Fehler |

## PC6 und PB9: beide späteren RESET-Blöcke zu SET geändert

| Zustand | Physische Ausgabe |
|---|---|
| A | L1 aus; L2 und L3 an |
| B | unverändert |
| C | zusätzlich L1 an, damit alle drei an |
| Stop / A | L2 und L3 blieben an; anschließend Fehler |

## PC6/PB9: vier frühere SET-Pulse unterdrückt

Artefakt: `AC011K-AE-25_V1.2.460-GD-suppress-PC6-PB9-set-pulses-test.bin`

| Zustand | Physische Ausgabe |
|---|---|
| A | alle aus |
| B | alle aus |
| C | alle drei an |
| Stop / A | alle aus, kein Fehler |

Ergebnis: Keine Änderung gegenüber Stock. Die vier geänderten SET-Stellen
werden im hier aktiven Relaistiming offenbar nicht verwendet beziehungsweise
sind nicht allein für die physische Schließung von L2/L3 verantwortlich.

## Nur PC6/PB9 im vermuteten Close-Puls high gehalten

Artefakt: `AC011K-AE-25_V1.2.460-GD-L1-only-close-pulse-test.bin`

SHA-256: `bdac39622b67b35a63d5aad7c3fd88f9936c0f2529a0f3e35d981165b8cde4fb`

Geänderte Aufrufe:

- `0x0801F3C0`: PC6 RESET → SET
- `0x0801F3CA`: PB9 RESET → SET

| Zustand | Physische Ausgabe |
|---|---|
| A | alle aus |
| B | alle aus |
| C | alle drei an |
| Stop / A | alle aus, kein Fehler |

Ergebnis: Ebenfalls keine Änderung gegenüber Stock. Zusammen mit dem
vorherigen Ergebnis spricht das dafür, dass auf dieser Box die Timing-Variante
1 aktiv ist. In dieser Variante werden vor PA8 nur PB3 und PA8 geschaltet;
die separaten PC6-/PB9-SET-Stellen der Timing-Varianten 2 und 3 werden nicht
durchlaufen. Der nächste Test ergänzt deshalb PC6/PB9 direkt im aktiven
Variante-1-Pfad und hält sie während des abschließenden L1-Pulses high.

## Timing-Variante-1-Hook mit PC6/PB9-Neutralisierung

Artefakt: `AC011K-AE-25_V1.2.460-GD-L1-only-variant1-test.bin`

SHA-256: `b5c7cf507997495c3b52d44551548aab38fd9371aa4f5b87c18ffeb9cec159b1`

Der Patch setzte PC6 und PB9 unmittelbar vor dem PA8-Aufruf im vermuteten
Variante-1-Pfad high und hielt sie im späteren Gruppenblock high. Der
ursprüngliche PB3-Aufruf und die komplette Öffnungssequenz blieben erhalten.

| Zustand | Physische Ausgabe |
|---|---|
| A | alle aus |
| B | alle aus |
| C | alle drei an |
| Stop / A | alle aus, kein Fehler |

Ergebnis: Wieder keine Änderung gegenüber Stock. Damit ist die Annahme
widerlegt, dass dieser Teil von `FUN_0801F0BE` den normalen physischen
Schließvorgang beim Ladebeginn bestimmt. Die früheren Dauerein-Effekte zeigen,
dass seine GPIOs hardwarewirksam sind; der reguläre Ladebeginn benutzt aber
offenbar einen anderen Relaispfad beziehungsweise die unmittelbar vorherige
Zustandsmaschine.

## Nur PB3-Differentialpuls; alle PA8-/PC6-/PB9-SET-Pulse unterdrückt

Artefakt: `AC011K-AE-25_V1.2.460-GD-PB3-only-drive-test.bin`

SHA-256: `2aa8b53a98c269cede062af16c0447376d595ba80ab6f4b0618f5affeb5b6052`

| Zustand | Physische Ausgabe |
|---|---|
| A | alle aus |
| B | alle aus |
| C | nur L1 schaltet für ungefähr 0,1 Sekunden ein und wieder aus |
| weiterer Startversuch | reproduzierbar erneut nur der kurze L1-Puls |
| L2 und L3 | durchgehend aus |
| Fehler | keiner |

Der L1-Puls war sowohl an der 230-V-LED als auch am Relaisklicken eindeutig
erkennbar. WARP/GD wechselte bei den Versuchen zwischen Status 3 (Charging)
und 5 (Suspended by EV), ohne einen Fehler zu setzen. Nach dem Zurückschalten
auf A wurde sauber Zustand 1 erreicht.

Ergebnis: **Erster eindeutiger Nachweis der selektiven Einphasenschaltung.**
PB3 gegenüber dem gemeinsamen PA8-Pegel betätigt die physische Gruppe K9/N +
K6/L1, während PC6 und PB9 für L2/L3 inaktiv bleiben. Der kurze Puls endet an
dem noch originalen PB3-RESET im späteren Sequenzblock. Der nächste Build hält
PB3 in Zustand C gesetzt, lässt aber den getrennten originalen Öffnungspfad
für Stop/A unverändert.

## PB3 während C gehalten; originaler Stop-/Öffnungspfad erhalten

Artefakt: `AC011K-AE-25_V1.2.460-GD-L1-held-until-stop-test.bin`

SHA-256: `c50b084d6245768d375eeba25587f255d7b875ce4f914974cedb7638fed492cb`

| Zustand | Physische Ausgabe |
|---|---|
| A | L1, L2 und L3 aus |
| B | L1, L2 und L3 aus |
| C | L1 dauerhaft an; L2 und L3 aus |
| zurück zu B | L1 aus; L2 und L3 aus |
| zurück zu A | L1, L2 und L3 aus |
| Fehler | keiner |

Ergebnis: **Vollständiger Hardware-Nachweis der Einphasenfähigkeit.** Die
Wallbox kann N+L1 während des gesamten freigegebenen Ladezustands unabhängig
von L2 und L3 schließen und über den vorhandenen Stop-/Öffnungspfad wieder
sauber trennen. Der Test bestätigt außerdem die wirksame Zuordnung PB3 →
K9/N + K6/L1 sowie die getrennte Ansteuerbarkeit der L2-/L3-Gruppen.

## Umschaltbarer 1p-/3p-Build mit WARP-Steuerung

GD-Artefakt: `AC011K-AE-25_V1.2.460-GD-selectable-1p-3p-test.bin`

GD-SHA-256: `38a7c6364d7940d274ca2c8712cd38465f518fa4ebddb9575df75fd2b37f4f9b`

WARP-Commit: `7c8616dca7fc002`

Der GD-Build verwendet StartPowerMode Bit 0 als Selektor. Modus 0 führt an
allen acht gepatchten Schließstellen den originalen 3p-Zugriff aus; Modus 1
reproduziert die zuvor praktisch bestätigte PB3-/N+L1-Sequenz. Der separate
Stop-/Öffnungspfad bei `0x0801F424` ist unverändert. Marker `0x20` bestätigt
die Verarbeitung des Selektors, Marker `0x40` später den finalen Schließhook.

Flash- und Leerlaufprüfung:

- GD-Flash vollständig bis 100 %; Neustart mit GD 1.2.460, Fehlercode 0.
- WARP-OTA erfolgreich; Hardware-/Firmware-Paar wird als unterstützt erkannt.
- StartPowerMode-Readback `0x21`: Modus 1 und Handler-Marker bestätigt.
- Zustand A laut GD/WARP, Schütze offen, kein Fehler.
- Physischer Modus-1-Test des umschaltbaren Builds bestätigt:

| Zustand | Physische Ausgabe |
|---|---|
| A | L1, L2 und L3 aus |
| B | L1, L2 und L3 aus |
| C | L1 dauerhaft an; L2 und L3 aus |
| zurück zu B | L1 aus; L2 und L3 aus |
| zurück zu A | L1, L2 und L3 aus |
| Fehler | keiner |

Damit reproduziert der dynamisch ausgewählte Modus 1 exakt den zuvor
bestätigten festen Einphasen-Build. Physischer Modus-3-Test: ausstehend.

Physischer Modus-3-Test des umschaltbaren Builds bestätigt:

| Zustand | Physische Ausgabe |
|---|---|
| A | L1, L2 und L3 aus |
| B | L1, L2 und L3 aus |
| C | L1, L2 und L3 dauerhaft an |
| zurück zu B | L1, L2 und L3 aus |
| zurück zu A | L1, L2 und L3 aus |
| Fehler | keiner |

Damit sind beide statisch vorgewählten Betriebsarten desselben GD-Builds
physisch bestätigt. Noch ausstehend ist die softwaregesteuerte Umschaltung
1p↔3p bei dauerhaft simuliertem Fahrzeugzustand einschließlich automatischem
Stoppen, Totzeit, Modus-Readback, Neustart und Fehlerpfaden.
