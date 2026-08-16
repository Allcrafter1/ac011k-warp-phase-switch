# GD32 reverse engineering: from four GPIO calls to verified N+L1

This document separates what the binary proves, what the live hardware proves,
and what remains an electrical interpretation. It also records failed ideas;
without them, the successful PB3 result looks much more magical than it was.

## 1. What kind of firmware is this?

`AC011K-AE-25_V1.2.460.hex` is ordinary Intel HEX, not encrypted source code.
Converting its addressed records gives a 262,144-byte GD32 application image.
The vector table and instruction patterns identify little-endian ARM
Thumb/Thumb-2 code for the GD32F103 Cortex-M3.

The image was loaded into Ghidra as `ARM:LE:32:Cortex` at `0x08000000`.
Capstone independently decoded the same instructions. The memory references
also match the controller family:

| Region/address | Role |
|---|---|
| `0x08000000…` | internal flash/program |
| `0x20000000…` | RAM |
| `0x40010800` | GPIOA peripheral block |
| `0x40010C00` | GPIOB peripheral block |
| `0x40011000` | GPIOC peripheral block |

Ghidra reconstructs control flow and approximate C. It cannot recover the
manufacturer's original variable names, types or comments. Helpful surviving
strings such as `relayControl_11KW`, `close relay_A`, `RelayError` and
`PhaseError` anchored the analysis, after which cross-references exposed the
actual call graph.

## 2. How PA8, PB3, PC6 and PB9 were found

The relay-control function repeatedly calls two tiny helpers:

| Address | Register effect observed in disassembly |
|---|---|
| `0x0800920E` | GPIO bit set/high |
| `0x08009212` | GPIO bit reset/low |

Immediately before those calls, ARM arguments place a GPIO port base address
in `r0` and a pin mask in `r1`. Decoding the four recurring combinations gives:

| Port address | Mask | Pin |
|---|---:|---|
| GPIOA `0x40010800` | `0x0100` | PA8 |
| GPIOB `0x40010C00` | `0x0008` | PB3 |
| GPIOC `0x40011000` | `0x0040` | PC6 |
| GPIOB `0x40010C00` | `0x0200` | PB9 |

This is a static fact about the program: those four GPIOs are manipulated by
the relay state machine. It was **not yet** a fact that PA8 equals N, PB3 equals
L1, and so on. The driver could contain shared enables, differential coil
drive, latching pulses or redundant stages. The later experiments demonstrated
that a naive one-GPIO-per-relay model was wrong.

## 3. Why a switching routine was expected

The PCB contains four power relays, but the measured coil network is not four
isolated identical loads:

| Measurement | Result |
|---|---:|
| K9 coil | 25 Ω |
| K6 coil | 25 Ω |
| K7 coil | 50 Ω |
| K8 coil | 50 Ω |
| K9 right ↔ K6 right | 0 Ω |
| K9 right ↔ K7/K8 right | 75 Ω |
| K7 right ↔ K8 right | 100 Ω |

Those values show K9/N and K6/L1 as a paired coil group, with K7/L2 and K8/L3
separately addressable. That is exactly the topology needed for one-phase
charging: close N+L1 and leave L2/L3 open.

The firmware, however, did not simply set four steady Boolean outputs. The
relay function contained timed, repeated set/reset calls at different stages.
The best working hypothesis was therefore a shared/differential pulse driver:
the physical relay state depends on the order and relative level of several
GPIOs, not on one isolated pin.

That interpretation was not trusted until it predicted real lamp behavior.

## 4. How a binary test image was produced

ARM Thumb instructions are two or four bytes long. At a known call site, a
four-byte `BL` instruction calls one GPIO helper. Keystone can assemble another
four-byte `BL` at the same address. Replacing the complete instruction keeps
instruction alignment intact.

The replacement call jumps to a short routine placed in a zero-filled area of
the original image. That unused flash area starts at `0x08037B00` and is called
a code cave. The helper can inspect a mode bit and then tail-call either the
stock GPIO function or its counterpart.

Conceptually:

```asm
ldr  r2, =0x2000402e   ; address of StartPowerMode byte
ldrb r2, [r2]          ; load one byte
tst  r2, #1            ; test bit 0
bne  one_phase
b.w  original_gpio_call
one_phase:
b.w  alternative_gpio_call
```

The builder never searches and replaces a loose byte pattern. It requires:

- exactly the known 262,144-byte source image;
- exactly the known source SHA-256;
- exactly the expected original four bytes at every hook;
- a still-zero code cave;
- no changed byte outside declared ranges;
- a byte-identical bootloader region and stock PB3 stop/open call.

If any precondition differs, it refuses to produce output.

## 5. The experiment ladder

### Baseline

Stock 1.2.460 produced the expected sequence:

- IEC A: all outputs off;
- IEC B: all outputs off;
- IEC C/charge: L1/L2/L3 on;
- stop and unplug: all off, no error.

### Changing later PA8 reset calls to set calls

All three phases became and remained energized, including after logical stop.
This proved PA8 was hardware-effective but did not prove a simple PA8→relay
mapping. It also demonstrated why logical GD state could not be trusted as
physical open proof.

### Changing later PB3 reset calls to set calls

Only L1 was on before normal charging; normal C then added L2/L3. L1 stayed on
after stop and the GD subsequently faulted. This was the first strong evidence
that the PB3-relative path controls the N+L1 group.

### Changing PC6/PB9 reset calls to set calls

L2 and L3 stayed on while L1 remained off until normal charging. This
complementary result associated those paths with the two additional phases.

### Suppressing plausible early PC6/PB9 pulses

Several sensible-looking hooks produced no change at all. The live board was
using another timing/state-machine branch. This is why decompilation alone was
not enough: a function can contain valid code that the current hardware mode
never executes.

### PB3-only differential drive

All stock PA8/PC6/PB9 closing effects were neutralized while the PB3-relative
path was retained. In IEC C, only L1 switched on for about 0.1 seconds and then
opened. L2/L3 stayed off and the GD did not fault.

That short pulse was the decisive isolation result. The later stock PB3 reset
was still cancelling it, so the next test changed only that final close-site
behavior.

### Hold PB3 through C; keep stock stop path

The final test kept the verified PB3/N+L1 differential state during C while
leaving the separate original stop/open call at `0x0801F424` byte-identical.
The physical result was exactly the target:

- A: all off;
- B: all off;
- C: L1 on, L2/L3 off;
- back to B/A: all off;
- no fault.

That converted the GPIO hypothesis into a physical proof for this board.

## 6. The selectable final patch

The final image uses bit 0 of the already existing `StartPowerMode` byte at
`0x2000402E`:

- bit 0 clear: execute the original three-phase GPIO effects;
- bit 0 set: execute the live-verified one-phase N+L1 effects.

Nine existing four-byte Thumb instructions are redirected:

- setter tail at `0x08029232` → mode/marker handler;
- seven stock set sites in `relayControl_11KW` → conditional stock helper;
- final PB3 close site `0x0801F3B8` → conditional PB3-hold helper.

The complete list of expected and replacement bytes is in
[`firmware/GD_PATCH_MANIFEST.txt`](firmware/GD_PATCH_MANIFEST.txt).

The helpers occupy only `0x08037B00…0x08037BBF`. The GD bootloader range
`0x08000000…0x08007FFF`, vector table, CP/PP logic, residual-current logic and
the complete normal opening path are not replaced.

## 7. Why marker bits exist

A protocol acknowledgement only proves that a packet was received. Early
testing showed that the GD can report a charging state before the final relay
stage has executed. Two bits therefore provide stronger evidence:

| Bit | Meaning |
|---:|---|
| `0x01` | requested one-phase mode |
| `0x20` | patched mode handler executed |
| `0x40` | patched final close hook executed |

Examples:

- `0x21`: one phase selected and handler seen;
- `0x61`: one phase selected, handler and physical close hook seen;
- `0x20`/`0x60`: equivalent three-phase markers.

The real MG4 one-phase run produced `0x61` and the separate meter then measured
current only on L1. The marker and current check are independent evidence.

## 8. What the result means—and does not mean

### Proven on the tested board

- N+L1 can be held closed without L2/L3.
- Stock three-phase operation still works in the same GD image.
- The untouched stop path opens both modes cleanly.
- The ESP can command and verify dynamic 1p↔3p transitions with the MG4.

### Strong interpretation

- PA8/PB3 participate in the paired N+L1 differential drive.
- PC6/PB9 participate in the additional L2/L3 drive.
- The multiple set/reset sites implement staged or pulse-based relay control.

The exact transistor-level driver topology has not been reconstructed into a
complete schematic, so these statements intentionally describe observed
functional groups rather than claiming a one-pin-per-coil circuit.

### Still unknown

- whether every board carrying the V1 text uses the identical driver network;
- whether other vehicles always meet the current timing limits;
- whether another GD release uses the same RAM and code layout—it should be
  assumed not to unless separately analyzed.
