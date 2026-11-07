# The tested AC011K

The enclosure does not tell the whole story. Several AC011K/AC011E products
share similar names while their relay wiring and GD firmware differ. This
project is based on one particular board:

| Part | Tested version |
|---|---|
| Product | AC011K-AE-25 |
| PCB | AC011K-AE-25 V1, EA01010188-00, 2021-11-29 |
| Relays | Black K9/K6/K7/K8; N+L1, L2 and L3 drive groups |
| GD base | 1.2.460 |
| Base BIN SHA-256 | `181e1ba228848a778d9e5639b8732bf14659ef7e52577ce74fcecdd15fa72909` |
| Patched BIN SHA-256 | `38a7c6364d7940d274ca2c8712cd38465f518fa4ebddb9575df75fd2b37f4f9b` |
| Vehicle used for acceptance | MG4 |

The stock opening path stays intact. The GD patch only changes the selected
closing sequence and adds readback markers. Neither the reported version nor
a matching product label proves compatibility with another PCB. V2 boards,
AE-35 hardware and other GD images are outside the tested scope.

## Why change phases?

Three-phase charging at 6 A needs roughly 4.14 kW. A small PV installation can
spend much of a day below that value. One-phase operation brings the threshold
down to 1.38 kW, without asking Home Assistant to manage individual relays.

The ESP chooses among 22 combinations: one or three phases, each at 6–16 A in
whole-ampere steps. A 5.00 kW target rounds up to 5.52 kW, or down to 4.83 kW.
These are nominal control values based on 230 V. Actual measured power is a
separate sensor and depends on voltage and the vehicle.

## The hardware decided which theory survived

Early patches produced no change, brief pulses, or outputs that stayed on.
The decisive test isolated the PB3 differential path: only L1 pulsed. Keeping
that path active until the original stop sequence ran gave stable N+L1
charging. The [reverse-engineering report](REVERSE_ENGINEERING.md) follows
those experiments, including the wrong turns.

![CP simulator and separate phase loads](images/test-rig.jpg)

The subsequent MG4 test reached about 1.39 kW on L1 and 3.98 kW across three
phases at a 6 A setting. The vehicle released CP during both phase changes;
no manual unplug was needed. Those August tests validate the physical
mechanism. They do not replace the [September regression checklist](TESTING.md).

## People and upstream work

Jonas / Allcrafter1 supplied and documented the hardware, traced the relay
network, built the CP/lamp rig and performed the physical tests. Codex assisted
with firmware analysis, patches, ESP control logic and documentation. WARP
More and Tinkerforge contributors supplied the firmware foundation.

Continue with [architecture](ARCHITECTURE.md), [installation](INSTALLATION.md)
or [Home Assistant](HOME_ASSISTANT.md). Historical observations are preserved
in [the August acceptance log](ACCEPTANCE_TESTS.md) and
[the relay experiment log](LIVE_TEST_RESULTS.de.md).
