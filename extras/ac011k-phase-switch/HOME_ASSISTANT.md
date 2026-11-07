# MQTT and Home Assistant

The firmware uses the existing WARP MQTT bridge. Set a unique client name and
a per-device API prefix, then enable Home Assistant discovery in the web UI.
Discovery announcements are retained and periodically refreshed. IDs are based
on the configured client name; keep that name stable across upgrades.

Examples below use `AC011K/DEVICE` as the API prefix and `AC011K-DEVICE` as the
client name. Replace them with your own configuration.

The 7 November migration moved all working entities to the discovery device;
see [deployment status and remaining cleanup](DEPLOYMENT_2026-11-07.md).

## Daily controls

| Control | State | Command |
|---|---|---|
| Charging power limit, kW | `evse/power_manager` | `evse/power_target_update` |
| Start | — | `evse/start_charging` |
| Stop | — | `evse/stop_charging` |
| Autostart | `evse/auto_start_charging` | `evse/auto_start_charging_update` |
| Rounding | `evse/power_manager_config` | `evse/power_manager_config_update` |

```json
{"power_w": 5000}
```

The power slider displays the *effective nominal limit*, so 5.00 kW settles at
5.52 kW with upward rounding. Zero pauses power. A positive value below 1.38 kW
saturates to 1.38 kW, including in round-down mode; an EMS that cannot allow grid
import must send zero below the minimum. A power target does not replace Start.

Start and Stop accept `null`. Autostart accepts
`{"auto_start_charging": false}`. Commands must be non-retained; retained
start/stop/power/phase actions are rejected on subscription replay. Do not use
retained commands as an automation memory.

## What discovery exposes

Alongside the existing total power, energy, vehicle state, start/stop and
configuration controls, the AC011K additions provide:

- power-limit slider, requested/rounded power, target current and phases;
- applied current limit, separately from the calculated target;
- phase and rounding selectors, placed in the configuration category;
- GD charging state, IEC state, logical contactor state and allowed current;
- L1/L2/L3 current in A and voltage in V, with measurement state classes;
- start/stop release, pending power target, phase-switch stage and error text;
- raw CP and GD fault diagnostics.

The existing manually configured charger-state sensor duplicates the discovery
vehicle-state sensor. Start and Stop are duplicates too. The manual power
slider and GD-state text sensor need new discovery counterparts. The old
EVSE-error-code, contactor-error, lock-state and DC-fault-current fields are zero-initialized
placeholders in this AC011K adapter; they are not independent working safety
measurements and are not promoted into new discovery sensors.

The `active_phases` legacy sensor describes the last verified phase count.
For live current, use the new current sensors from `meter/all_values`, not the
previously frozen phase-verification snapshot. External Shelly/three-phase
meters are separate instruments and must remain separate devices.

## Migration from manual YAML

The old installation had two MQTT device identifiers: a generic manual one
and the serial-specific discovery identifier. That split, plus duplicate
start/stop/state definitions, explains the parallel entities.

Migration order matters:

1. Back up YAML, entity/device registry metadata, discovery payloads, dashboards
   and affected automation/script configurations. Keep private exports out of Git.
2. Install the new ESP firmware and verify every replacement topic and value.
   The old firmware deletes discovery topics it does not recognize under its
   own node ID; publishing new topics from a temporary helper is not a durable fix.
3. Map each old entity to one canonical discovery entity. Search YAML packages,
   UI automations, scripts, dashboards, helper options, device triggers and any
   Node-RED/AppDaemon configuration. MCP search alone can miss YAML definitions.
4. Remove only the old wallbox MQTT YAML definitions, validate the complete HA
   configuration, and reload MQTT. Avoid a whole-HA restart.
5. Update all consumers through HA APIs and give the discovery entities a
   consistent `ac011k_*` naming scheme. Replace device actions with entity actions
   where the old MQTT device will disappear.
6. Remove orphan registry entries only after consumer verification. Do not delete
   the old device blindly: unrelated helpers may have been attached to it.
7. Read back the written configuration, check for stale references and compare
   state with the wallbox API. Do not press Start merely to test an entity rename.

The repository includes a read-only [migration planner](tools/plan_ha_migration.py).
It generates the entity mapping and reports references from exported files;
execution still needs the live checks above. See [the review](REVIEW_2026-09.md)
and working plan for this installation's actual deployment status.

## EMS integration

Let the EMS publish a single power target, rather than coordinating phase
select and current controls independently. Keep forecast/PV hysteresis in the
EMS; the ESP owns the physical stop/switch/restart sequence. Rate-limit target
changes around the 1P/3P boundary. Deliberately grant a session after plugging
in, and revoke it on Stop/unplug. No production EMHASS automation is enabled
by the examples or this firmware review.

The current bridge retains state, but has no general MQTT last-will availability
for every entity. Its online sensor has an expiry; other retained values can
remain visible while disconnected. Treat online status as a prerequisite for
control. General LWT availability remains a documented improvement, not a
claim made by this revision.

Reference: [Home Assistant MQTT discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
and [MQTT number configuration](https://www.home-assistant.io/integrations/number.mqtt/).
