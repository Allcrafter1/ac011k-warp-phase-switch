# AC011K mit Home Assistant und EMHASS

Die Wallbox veröffentlicht seit dem gepatchten Build automatisch folgende
Home-Assistant-Discovery-Entities:

- Auswahl `Ladephasen` (`1` oder `3`)
- Sensor `Aktive Ladephasen`
- Binärsensor `Phasenumschaltung aktiv`

Die Discovery-Konfiguration ist auf der Wallbox bereits aktiviert. Das
zusätzliche Package [`ac011k_emhass.yaml`](ac011k_emhass.yaml) bildet eine
stabile Schnittstelle zu EMHASS und verwendet absichtlich die MQTT-Topics
direkt, damit es nicht von automatisch vergebenen Home-Assistant-Entity-IDs
abhängt.

## Installation

1. `ac011k_emhass.yaml` nach `/config/packages/` in Home Assistant kopieren.
2. Falls Packages noch nicht aktiviert sind, unter `homeassistant:` ergänzen:

   ```yaml
   packages: !include_dir_named packages
   ```

3. Konfiguration prüfen und Home Assistant neu starten.
4. EMHASS soll die geplante Wallboxleistung in Watt in
   `input_number.ac011k_emhass_target_power` schreiben.
5. Erst nach dem elektrischen 1-/3-Phasen-Test
   `input_boolean.ac011k_emhass_control` einschalten.

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
