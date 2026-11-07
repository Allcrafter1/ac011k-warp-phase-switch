# Tests and troubleshooting

The November deployed image and unloaded HA/GD checks are recorded in
[DEPLOYMENT_2026-11-07.md](DEPLOYMENT_2026-11-07.md). Vehicle-load acceptance
below remains open.

## What has actually been tested

The August 2026 lamp and MG4 tests passed both phase directions on ESP commit
`9f0e2ad` with the verified GD 1.2.460 patch. The chronological records remain
in [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) and
[LIVE_TEST_RESULTS.de.md](LIVE_TEST_RESULTS.de.md). Earlier “pending” statements
in those records describe that date, not the final result of the later tests.

The September revision has a successful `warpAC011K` build and host tests:

```sh
python3 -m unittest discover -s extras/ac011k-phase-switch/tests -v
```

The harness compiles actual C++ method bodies with fake transport/configuration
objects. It checks vetoes from every active current slot, disconnected/faulted
starts, cancelled phase-restart retries and MQTT publication after 41 days and
across the 32-bit timer wrap. Discovery tests check unique object IDs, nested
JSON/C++ escaping, power command routing and the six supported meter indices.
They do not simulate the GD, analog CP or contactors.

## Physical regression checklist for the new image

- Autostart off: connect without Start; no charging. Start, then unplug while
  charging; reconnect without Start; no charging. Repeat after a completed EV
  session and after a deliberate Stop.
- Restart ESP with a previously released session and autostart off; no restored
  permission. Confirm the configured power limit can remain without granting Start.
- At 6 A, switch 1P→3P and 3P→1P; record raw CP, all currents and stage changes.
- Stop or unplug during stopping, off delay, applying, confirming and each
  restart attempt. No later restart may escape the cleared permission.
- Replace a target during switching, including zero. Verify the newest target
  is applied and no obsolete intermediate target restarts charging.
- Hold another slot at zero: changing power or phase must not grant charging.
- Force a controlled missing-CP/readback timeout using the test setup; no phase
  command or ordinary Start may bypass the error. A deliberate fresh target is
  the recovery action after the cause has been checked.
- Verify current/voltage units under real 1P and 3P load; compare to the independent
  meter. Check zero-current readings after Stop.
- Restart/reconnect MQTT and HA: no replayed charge request, no duplicate entities,
  correct autostart/release states and retained discovery recovery.

These checks are pending for the September image until recorded as performed.
Do not infer physical acceptance from a successful build.

## Capture the next stuck transition

Before touching the slider, save `/event_log` and poll these API states together
with timestamps (roughly once per second):

```text
evse/state
evse/slots
evse/auto_start_charging
evse/power_manager
evse/phase_switch
evse/low_level_state
meter/values
meter/all_values
info/version
```

Also save MQTT command timestamps/payloads and HA automation traces. Record
whether the vehicle was already waiting in B, actively charging in C, stopped
by the driver, unplugged, or at its target SoC. Raw CP reports after the Stop
request matter more than a single later screenshot. Record which controller
changed the power target: dashboard, automation, external EMS or API client.

The 21 September log contains a 30-second missing-fresh-CP timeout, followed by
charging in the previous phase mode and recovery on a new target. It does not
prove why the GD failed to send the fresh CP report. Keep that distinction when
comparing the next incident; do not relax the guard to hide the symptom.
