# Home Assistant, MQTT and the current migration state

The wallbox implementation deliberately keeps energy strategy and physical
switching on different levels:

- Home Assistant/EMHASS decides the desired charging power.
- The ESP32 converts power to phases/current and owns the safe transition.
- The GD32 continues normal low-level EVSE control.

## MQTT added by this fork

The code registers ordinary WARP API state and command objects. The existing
WARP MQTT bridge publishes them below the configured device prefix, normally:

```text
AC011K/<device-id>/evse/...
```

Important paths:

| Path | Direction | Purpose |
|---|---|---|
| `power_manager` | state | requested/effective W, current, phases, pending/error |
| `power_target_update` | command | one desired power in W |
| `power_manager_config` | state | rounding mode |
| `power_manager_config_update` | command | change rounding mode |
| `phase_switch` | state | stage, active/requested phases, markers, raw CP, errors |
| `phase_switch_update` | command | low-level diagnostic/manual phase request |

Example command:

```json
{"power_w": 5000}
```

The returned effective value may be 5,520 W because the vehicle is controlled
in whole amperes and the ESP only selects valid 1/3-phase combinations.

## What Auto Discovery already provides

The ESP firmware auto-discovers:

- phase-mode select;
- active-phase sensor;
- phase-switching binary sensor;
- rounding-mode select;
- requested and effective power sensors;
- calculated current sensor;
- calculated phase-count sensor.

The manual phase select cannot bypass the stop/CP-B/off-delay/restart state
machine. It remains useful for diagnostics but is not the intended normal UI;
normal users should set only a power target.

## Why the main kW slider is still manual

On the first production Home Assistant instance, a large power slider already
existed with this stable identity:

```text
unique_id: axitec_wallbox_power_limit
entity: number.ac0011k_axitec_wallbox_ladeleistung_kw
```

Changing the control path and its HA identity at the same time would have made
it harder to tell a wallbox bug from an entity migration bug. The existing
number, dashboard position and automations were therefore retained while only
its MQTT topics and templates changed.

The installation-specific entity is equivalent to:

```yaml
mqtt:
  number:
    - name: AC011K Axitec Wallbox Ladeleistung kW
      unique_id: axitec_wallbox_power_limit
      state_topic: "AC011K/REPLACE_DEVICE_ID/evse/power_manager"
      command_topic: "AC011K/REPLACE_DEVICE_ID/evse/power_target_update"
      value_template: "{{ (value_json.effective_power_w / 1000) | round(2) }}"
      command_template: '{"power_w": {{ (value | float * 1000) | round(0) | int }}}'
      min: 1.38
      max: 11.04
      step: 0.01
      mode: slider
      unit_of_measurement: kW
      device_class: power
      icon: mdi:ev-station
```

Replace `REPLACE_DEVICE_ID`; never copy another installation's serial/device
prefix. The displayed slider intentionally follows `effective_power_w`, so it
settles on the value the 1-A grid can really produce.

## Other Home Assistant changes on the tested installation

- The existing charging-stop notification remains enabled.
- It now requires the auto-discovered `phase_switching` binary sensor to be
  off, preventing an intended phase transition from looking like an unexpected
  charging stop.
- The raw/transliterated GD state remains unchanged. ESP phase-switch state is
  separate because the GD cannot report an ESP orchestration state.
- The large power number is rendered as a slider in the existing
  `Wallbox & Ladeplanung` entities card.
- Old disabled prototype automations were not reactivated.
- EMHASS is not yet in charge of production targets.

## Why this feature matters for smaller PV systems

Three-phase charging at the IEC minimum of 6 A needs approximately:

```text
3 × 230 V × 6 A = 4.14 kW
```

One-phase charging begins at approximately:

```text
1 × 230 V × 6 A = 1.38 kW
```

A relatively small PV system can spend many hours between those values. Before
this patch, that surplus could not be used without importing power or cycling
charging off. The kW interface was built so EMHASS can later publish one target
without needing to understand the GD relay protocol.

## Planned full Auto Discovery migration

The next HA-focused version should:

1. add the writable kW number to ESP Auto Discovery;
2. remove or mark the raw phase select as diagnostic;
3. migrate the existing manual number without duplicating entities;
4. provide a generic EMHASS example with no fixed device ID;
5. keep high-level hysteresis/solar strategy in HA while the ESP retains the
   non-bypassable physical switching sequence.
