# Working plan: ESP32, MQTT and Home Assistant

Started 2026-09-26. ESP deployed on 2026-11-07; HA migration and legacy-device
cleanup are complete. Physical vehicle acceptance and GitHub push remain
outstanding. Current documentation is English, as requested.

## Completed locally

- [x] Identify worktrees, community base and deployed firmware; preserve unrelated work.
- [x] Compare community MQTT/ESP implementation and later project changes.
- [x] Inspect project documentation, propose structure and implement approved English guides.
- [x] Trace ESP/GD protocol, slot permission, power targets and phase transitions.
- [x] Inventory live HA through MCP, registry, YAML, dashboards and discovery diagnostics.
- [x] Back up configuration/history/logs privately and reconstruct September incidents.
- [x] Disable autostart; confirm direct API false and slot 4 closed/clear-on-disconnect.
- [x] Fix MQTT long-uptime publication and guard starts/restarts with live slot permission.
- [x] Add discovery controls/measurements supported by real adapter data.
- [x] Prepare read-only migration mapping and privately staged manual-YAML removal.
- [x] Run four host regression tests and build warpAC011K successfully.
- [x] Document hardware tests, rollback, outstanding concerns and next-session order.

## Original deployment checklist (see dated status below)

- [ ] Refresh backups/state; confirm unplugged vehicle before ESP update.
- [ ] Flash ESP candidate; verify version, MQTT, autostart off and closed release.
- [ ] Correct retry automation: cancel on Stop/disconnect, bind retries to original
      session and reject restored button-state triggers. Firmware alone cannot
      reject a new authorized MQTT Start sent by this automation.
- [ ] Migrate all eight working manual entities and existing discovery entities to
      canonical IDs; retire four unimplemented placeholder sensors.
- [ ] Update automations/scripts/dashboard/device actions through supported HA APIs.
- [x] Remove the broken unused helper and the empty legacy MQTT device.
- [ ] Validate/reload HA, scan stale references and verify discovery recovery.
- [ ] Execute physical acceptance checklist and record results/logs.
- [ ] Review final diff, commit and push to GitHub after testing and migration.

## Findings to retain

- Replug on 26 September reused 8 A with autostart enabled; ESP log confirms it.
- HA stale autostart display is explained by a separate >24.8-day publication bug.
- 21 September shows fresh-CP timeout, ordinary Start bypassing phase error, then
  recovery on a new target. Missing CP cause remains unproven; retain guard.
- The retry automation can issue delayed Start without session cancellation;
  migration must address it before claiming the reconnect issue fully resolved.
- 21 discovery + 12 manual entities; four manual fields are unsupported placeholders.
- Older ESP deletes new unknown discovery topics: firmware deployment precedes migration.
- General MQTT last-will availability remains a future improvement; use online status.
- No GD changes justified. No calibrated temperature/leakage or true per-phase
  active-power sensors invented from unsupported data.

Detailed evidence and rollback: [September review](extras/ac011k-phase-switch/REVIEW_2026-09.md).
Private backups: ../backups/2026-09-26-ha-review (never commit these).

## 2026-10-06: live power-limit incident

- [x] Capture event log, live slots/phase/power/CP/meter/version before user Stop.
- [x] Save HA history, exact retry and child MQTT Start traces, MQTT diagnostics
      and current automation YAML privately in ../backups/2026-10-06-power-incident.
- [x] Confirm 17:44:49 CP timeout followed by HA retry Start at 17:45:17.
      Target changed from 1P/15 A to 1P/12 A during the pending transition;
      old firmware resumed at unchanged 3P/15 A. HA 2.76 kW is calculated target,
      not proof that it was applied. Meter history peaks at 9.79 kW externally.
- [x] Add regression for reopening slot 4 with stale 15 A limit in phase ERROR.
- [ ] Investigate fresh CP sampling while already stopped: no CP report appears
      between today's Stop request and timeout; do not weaken the CP guard.
- [ ] Ensure retry automation checks phase fault/pending state as well as session
      cancellation before restart; expose target-vs-applied distinction clearly.
- [ ] Test replacement targets during transitions physically after flashing.

No live settings changed, no flash, no push during the October capture.
Details: [October incident](extras/ac011k-phase-switch/INCIDENT_2026-10-06.md).

## 2026-11-07: final review and deployment (authorized)

- [x] Review remaining ESP state-machine gaps and add meaningful regressions.
- [x] Refresh private backups, live state and HA consumer inventory.
- [x] Build candidate, verify idle wallbox, deploy ESP only and verify boot.
- [x] Migrate all functional entities and consumers; charge check now monitors only.
- [x] Remove invalid legacy helper and delete empty old device after approval.
- [x] Record deployment evidence and remaining physical tests.

The owner now authorizes flashing and HA migration. Previous deployment deferral
is superseded; practical load/vehicle tests still need the available setup.

### November results

- Firmware `2.0.12-6aefa6d4` deployed; GD unchanged. 40 discovery entities,
  twelve manual definitions/registry entries removed; eight automations, two
  scripts and dashboard migrated. All previous automation enable states restored.
- Applied error limit set to zero; fresh current proof required before switching;
  obsolete restart cancelled on new target. Four host tests/build pass.
- Unloaded HA command path verified at 2.76 kW/1P and restored to 5.52 kW/3P.
  Release remained closed and measured power zero. Vehicle tests still pending.
- Corrected OTA documentation: existing updater REQUIRES merged container with
  firmware info, then writes application only. Raw app precheck rejected safely.
- The invalid `lolololo` template helper had no entity or consumers and only
  summed three unrelated `*_energy2` sensors. It and the empty old device were
  removed on 2026-11-08 after explicit approval; no stale IDs remain.
- Full HA backup `9af0f065` includes database. Private evidence in
  ../backups/2026-11-07-deployment.
- [x] Re-run host regressions and compile the current source before publication.
- [x] Publish reviewed source and the exact deployed merged image as the
  `v0.2.0-experimental` GitHub prerelease. Keep vehicle-load tests open.

[Deployment details](extras/ac011k-phase-switch/DEPLOYMENT_2026-11-07.md).
