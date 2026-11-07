# 7 November 2026: ESP deployment and HA migration

## Deployed and verified

ESP `2.0.12-6aefa6d4` was installed through the WARP web updater while the car
was disconnected and all charge permission was closed. GD 1.2.460 is unchanged.
The post-boot API confirmed autostart off, slot 4 at zero with disconnect
clearing enabled, no phase fault and zero measured power.

Merged upload SHA-256: `1d6f6c64c7ebda84142b1ae58831a7c2cfe2fa20d0a33d387825b2e783d9c409`.
The embedded Git revision is the base revision; this image includes the reviewed
working-tree changes. A private source snapshot and deployment manifest identify
the exact files. Do not identify this image by the base Git hash alone.

Final review added three protections beyond September's candidate:

- Phase errors send Stop and zero the power-manager slot, preventing a later
  current update or GD limit query from retaining the previous power limit.
- Switching waits for fresh zero-current evidence; stale data or continuing
  current produces a bounded timeout instead of authorizing a relay-mode change.
- A replacement power target cancels a pending restart of the old target.

CP reports received while stopping/off-delay are now logged even if duty did
not change. The cause of missing fresh CP reports while already stopped remains
unproven; the safety condition was not weakened.

## Home Assistant

Forty discovery entities now use consistent `ac011k_*` IDs on the serial-specific
MQTT device. Device metadata is generated as escaped JSON and identifies AXITEC,
AC011K (EN+ AC011K-AE-25), and the installed ESP version. The identifier remains
stable. The twelve manual MQTT definitions and their orphan registry entries
were removed after replacement entities appeared. Eight affected automations,
two charge scripts and the car dashboard were migrated. Device actions became
entity actions. A read-back scan found no old entity/device references in the
active YAML or dashboard files. Previously disabled automations stayed disabled.

The dashboard distinguishes measured power, rounded target, applied current,
release and pending/error state. The renamed target is not a claim that the
requested phase/current combination has already reached the vehicle.

The charge-check automation now monitors an explicit Start and can report a
failure; it does not issue additional Stop/Start requests. Stop/disconnect/offline
cancel the wait. A fresh-button timestamp guard rejects restored timestamps and
unavailable states. The ESP retains its own bounded phase-restart sequence.
The old automation entity ID was retained for callers, with a corrected display
name. Start/Stop scripts now invoke the discovery buttons.

### Legacy-device cleanup completed on 8 November

All wallbox functions are on the discovery device. The remaining `lolololo`
template helper was already in `setup_error`, created no entity, had no consumers
and only summed three unrelated `*_energy2` sensors. After explicit approval it
was removed, followed by the empty generic MQTT device. Read-back checks found
neither the helper/config entry nor the old device and identifier. The active
configuration contains no manual `axitec_wallbox_*` definitions or stale legacy
references. The pre-migration full backup remains the recovery path for these
registry deletions.

The discovery entity `number.ac011k_current_limit` is the inherited WARP global
current-slot ceiling. Its 32 A value does not override this wallbox's independent
16 A cable/hardware slot. Normal operation uses `number.ac011k_power_limit`; the
ESP maps that kW target to the external current slot and phase controller.

## Validation

- Four host tests pass, compiling actual start, phase-state-machine, error-handler
  and MQTT methods; discovery metadata and command routing are also checked.
- `warpAC011K` build passes. HA core configuration check passes before MQTT reload.
- All forty discovery states are present; untouched buttons correctly show unknown
  until pressed. Autostart/release/power agree with the direct ESP API.
- With the vehicle unplugged, HA set 2.76 kW: 1P/12 A was acknowledged by GD
  (mode marker 0x21), pending cleared and release remained zero.
- HA then restored 5.52 kW: 3P/8 A was acknowledged (0x20), pending cleared;
  measured power and allowed current remained zero throughout.
- The charge-check timestamp template was evaluated in HA with fresh, restored
  and unavailable inputs: true, false, false respectively. No notification was
  sent and no Start button was pressed to test migration.

These are unloaded command-path tests. They do not prove physical phase count
under vehicle load, reconnect behavior or EV recovery from a CP timeout. Those
checks remain in [TESTING.md](TESTING.md).

## Recovery and artifact correction

A Home Assistant backup including configuration and recorder database was created
before migration. Object/file copies and logs are held privately in the research
workspace. Restore individual edited objects through APIs where possible; a full
backup restore requires a separate decision because it affects unrelated work.

The existing updater validates a firmware-info page in the merged container and
then skips its boot prefix when writing the application. Earlier documentation
and the release filename `web-ota` incorrectly referred to the raw application.
The raw-image precheck rejected it before flashing; the validated merged upload
then returned `Update OK`. [INSTALLATION.md](INSTALLATION.md) now documents the
correct format. The known-working merged image is preserved for rollback.

The reviewed source and this exact tested merged image were published in the
`v0.2.0-experimental` GitHub prerelease after the migration cleanup. The release
does not include or require a new GD image.
