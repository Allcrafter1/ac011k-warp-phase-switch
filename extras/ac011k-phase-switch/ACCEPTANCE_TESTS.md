# Test results

## 2026-08-16 — build and deployment

- ESP32 build `361e3b7`: passed.
- Firmware precondition: IEC state A, charger state 0, GD state 1, no fault: passed.
- ESP32 OTA update: passed (`Update OK`, HTTP 200).
- Reboot/version: passed (`2.0.12-6a81fadc`).
- Hardware/GD compatibility: passed (`AC011K-AE-25`, GD `1.2.460`, phase switching supported).
- GD firmware was not changed during this deployment.

## Power mapping while unplugged

Requested value: 5.00 kW.

- Round up: 5.52 kW, 3 phases, 8 A: passed.
- Round down: 4.83 kW, 3 phases, 7 A: passed.
- Nearest: 4.83 kW, 3 phases, 7 A: passed.
- Rounding mode restored to round up: passed.

## Unplugged phase switching

- HTTP target 2.00 kW mapped to 2.07 kW, 1 phase, 9 A: passed.
- State sequence reached switching stages and returned to idle: passed.
- Final commanded phase count 1, no GD/ESP fault: passed.
- Home Assistant target 5.00 kW mapped to 5.52 kW, 3 phases, 8 A: passed.
- Final commanded phase count 3, no GD/ESP fault: passed.
- User confirmation that all three output lamps remained off in IEC state A: pending.

## Home Assistant

- Existing power-number unique ID retained: passed.
- Existing slider state follows effective target (2.07 kW and then 5.52 kW): passed.
- MQTT reload without HA restart: passed.
- Auto-discovered rounding select: passed (`Aufrunden`).
- Auto-discovered effective power, target current and phase diagnostics: passed.
- Phase-switch binary sensor returns to `off`: passed.
- Active stop-notification automation now has a native condition requiring the phase-switch sensor to be `off`: passed.
- Dynamic connected 1p/3p transition and notification suppression: pending physical test.

## Next physical test

1. Confirm state A has all lamps off.
2. Select simulator state B; all lamps must remain off.
3. Select simulator state C at 5.52 kW; L1, L2 and L3 must turn on.
4. While C is active, command 2.00 kW. Expected sequence: all phases off, then only L1 on; no fault.
5. While C is active, command 5.00 kW. Expected sequence: L1 off as part of the stop, then L1/L2/L3 on; no fault.
6. Return through B to A; all outputs must remain off and no unplug fault may appear.

Do not use a real vehicle until the connected lamp tests pass.

## Dynamic lamp test failure and correction

The first connected test disproved the original stop criterion:

- A 3p to 1p request made the GD report a logical remote stop, but all three output lamps remained energized.
- The phase change only completed after the passive CP simulator was manually changed from C to B/A.
- A 1p to 3p request likewise required a manual C to B to C cycle in the observed test, even though the GD log claimed a logical stop/resume sequence.
- Therefore synthesized IEC/GD state and current below 0.5 A are not proof that the contactors are open.

Commit `dfbf8f2` only corrected a racing retry timeout and is superseded.

Commit `9f0e2ad` adds a fail-closed raw-CP guard:

- Every transition clears its CP release proof.
- A fresh AC011K charging-parameter report must show raw CP state B (live threshold: at least 800; measured B about 906 and C about 609) after the stop request.
- Without this proof, no GD phase-mode command is sent; the transition errors after 30 seconds.
- The passive simulator must be moved to B manually. A real EV is expected to perform the C to B response itself, but this must be verified with the lamp simulator before any vehicle test.

ESP image `2.0.12-6a820141` / commit `9f0e2ad` was flashed successfully in state A. Post-flash state: contactors open, idle, no fault. Dynamic validation is pending.

## Raw-CP guarded dynamic validation

The passive CP simulator and lamp load subsequently completed three guarded transitions:

- Initial 3p to 1p transition: completed after a valid manual B interval; the earlier too-fast switch movement was not accepted as sufficient release proof.
- 1p to 3p: stop requested at 20:33:26, fresh raw CP B observed at 20:33:43 (`918`), 3p mode applied at 20:33:45, charging resumed at 20:33:48.
- 3p to 1p: stop requested at 20:34:04, fresh raw CP B observed at 20:34:29 (`918`), 1p mode applied at 20:34:32, charging resumed at 20:34:34.
- 1p final close hook was physically reached and read back as `0x61`.
- Final unplug: IEC A, GD state 1, idle, no fault, one phase selected, 1.38 kW / 6 A target.

Home Assistant validation:

- All three long phase interruptions produced a stop-notification trace with `failed_conditions` while the phase-switch binary sensor was on.
- The final genuine unplug produced the normal running stop-notification trace.
- No phase-switch-specific Home Assistant error was logged.

The simulator/lamp acceptance test is passed. Remaining production acceptance is a low-current real-EV handshake in both directions (3p/6 A to 1p/6 A and back), followed later by edge-case tests for changed targets or disconnects during a transition.

## Real-MG4 acceptance test

The supervised low-current vehicle test passed on 2026-08-16 with ESP image
`2.0.12-6a820141` / commit `9f0e2ad` and unchanged GD `1.2.460`:

- Initial 1p/6 A operation: L1 `5.9 A`, L2/L3 `0 A`, meter `1.382 kW`, physically verified, no fault.
- 1p to 3p: the MG4 autonomously returned CP from C to B (`925` raw) before the ESP changed the phase command. After the vehicle ramp, L1/L2/L3 were each `5.7 A`, meter `3.982 kW`, physically verified, no fault.
- 3p to 1p: the guarded stop/switch/restart sequence completed without manual intervention. After the vehicle ramp, L1 was `5.9 A`, L2/L3 were `0 A`, meter `1.393 kW`, phase marker `0x61`, physically verified, no fault.
- Final controlled stop: CP B (`925` raw), contactor state open, meter `0 W`, charger error `0`, GD fault `0`.

Both phase directions and the final stop therefore passed against the real vehicle. The MG4 took roughly 40--45 seconds after each restart to ramp from a small pilot draw to the requested 6 A; the ESP remained in a valid charging state throughout.

Remaining tests are resilience/edge-case acceptance rather than proof of the basic phase mechanism: target replacement during a transition, unplug during a transition, restart/power loss recovery, timeout handling, and anti-chatter policy under rapidly varying EMS targets.
