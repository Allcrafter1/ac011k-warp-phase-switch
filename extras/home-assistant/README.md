# AC011K mit Home Assistant und EMHASS

Die Wallbox enthält experimentelle Diagnose-Entities für eine spätere
Phasenumschaltung:

- Auswahl `Ladephasen` (`1` oder `3`)
- Sensor `Aktive Ladephasen`
- Binärsensor `Phasenumschaltung aktiv`

**Die Phasenumschaltung ist für AC011K-AE-25 derzeit absichtlich gesperrt.**
GD 1.7.186 quittiert die Phasenangabe, schaltet auf der geprüften Hardware
aber weiterhin alle drei Phasen. Das zusätzliche Package
[`ac011k_emhass.yaml`](ac011k_emhass.yaml) ist deshalb nur eine Vorbereitung
und darf noch nicht aktiviert werden.

## Installation

1. `ac011k_emhass.yaml` nach `/config/packages/` in Home Assistant kopieren.
2. Falls Packages noch nicht aktiviert sind, unter `homeassistant:` ergänzen:

   ```yaml
   packages: !include_dir_named packages
   ```

3. Konfiguration prüfen und Home Assistant neu starten.
4. EMHASS soll die geplante Wallboxleistung in Watt in
   `input_number.ac011k_emhass_target_power` schreiben.
5. `input_boolean.ac011k_emhass_control` ausgeschaltet lassen. Es darf erst
   nach einem spannungsfreien Hardware-Nachweis und einem lastfreien
   1-/3-Phasen-Test eingeschaltet werden.

Ein Beispiel, falls der relevante EMHASS-Wert bereits als Sensor vorliegt
(den Entity-Namen an die eigene Installation anpassen):

```yaml
automation:
  - alias: EMHASS Sollleistung an AC011K übergeben
    triggers:
      - trigger: state
        entity_id: sensor.emhass_ev_charger_power
    actions:
      - action: input_number.set_value
        target:
          entity_id: input_number.ac011k_emhass_target_power
        data:
          value: "{{ states('sensor.emhass_ev_charger_power') | float(0) }}"
```

## Regelverhalten

- unterhalb der technisch möglichen Mindestleistung wird `0 mA` angefordert;
- ansonsten werden aus Sollleistung, 230 V und aktiver Phasenzahl 8–16 A
  berechnet;
- ab 6 kW für fünf Minuten wird auf drei Phasen gewechselt;
- unter 5 kW für zehn Minuten wird auf eine Phase gewechselt;
- die Firmware erzwingt zusätzlich mindestens 300 Sekunden zwischen zwei
  Umschaltungen und fünf Sekunden lastfreie Relaiszeit.

Die Hysterese verhindert Pendeln um die für diese Wallbox praktisch ermittelte
dreiphasige Mindestleistung von etwa 5,52 kW bei 8 A. Das Package schaltet die EMHASS-Regelung absichtlich nicht automatisch
ein: Zuerst müssen L2/L3 am realen Fahrzeug elektrisch verifiziert werden.
