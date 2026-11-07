# November 2026 — deployed locally

ESP `2.0.12-6aefa6d4` is running. AXITEC device metadata and 40 discovery
entities are live; manual wallbox entities have been removed. Error-limit,
fresh-current and obsolete-restart protections are included. Unloaded command
checks passed in both directions; vehicle-load tests remain outstanding.
The broken unused helper and empty legacy MQTT device were removed after approval.
See [deployment details](DEPLOYMENT_2026-11-07.md).

# September candidate history

- Session-slot checks on every low-level start and phase restart/retry.
- Clear disconnect-scoped permission at boot; closed default for new installations.
- MQTT publication fix for states unchanged beyond 24.8 days.
- Discovery power slider, phase currents/voltages and working state diagnostics.
- English architecture, installation, migration and troubleshooting guides.
- Host regressions and ESP build passed; physical tests and live migration pending.
- GD unchanged; no firmware deployment or GitHub push in this review session.

See [the review](REVIEW_2026-09.md) for evidence and remaining automation work.

# Historical release

# v0.1.0-experimental

## What works on the tested hardware

- Stable one-phase charging on N+L1 from 1.38 kW / 6 A.
- Stock three-phase charging up to 11.04 kW / 16 A.
- Dynamic 1p→3p and 3p→1p switching with an MG4.
- One kW power target mapped to valid 1/3-phase, 6–16 A combinations.
- Controlled stop, fresh raw CP-B proof, minimum off time and restart.
- GD mode-handler and final-close marker verification.
- Independent phase-current verification with fail-closed mismatch handling.
- MQTT state/commands and partial Home Assistant Auto Discovery.
- ESP application and GD HEX update through the WARP web UI.

## Compatibility warning

This prerelease is verified on one `AC011K-AE-25 V1` PCB dated `2021-11-29`
with black K9/K6/K7/K8 relays and exact GD base `1.2.460`. Product names and
enclosures are not sufficient evidence for other revisions. Read the full
compatibility table before flashing.

## Remaining acceptance work

- target replacement and unplug during an active transition;
- ESP/GD/power restart recovery;
- timeout and vehicle-refuses-resume behavior;
- longer soak testing and additional vehicles;
- other PCB reports;
- full Home Assistant Auto Discovery for the writable kW slider.
