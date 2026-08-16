#!/usr/bin/env python3
"""Build selectable 1-/3-phase GD 1.2.460 from the live-verified pulse map.

StartPowerMode bit 0 selects the physical relay sequence: 0 preserves every
stock three-phase GPIO effect, while 1 reproduces the live-verified PB3-only
one-phase sequence. Bits 0x20 and 0x40 provide WARP with command-handler and
physical-close-path markers. The complete stop/open path remains stock.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gd_patch_tools import assemble, disassemble, patch_at, sha256, write_sparse_ihex


FLASH_BASE = 0x08000000
IMAGE_SIZE = 256 * 1024
BOOTLOADER_END = 0x08008000
EXPECTED_SHA256 = "181e1ba228848a778d9e5639b8732bf14659ef7e52577ce74fcecdd15fa72909"

START_POWER_MODE_RAM = 0x2000402E
SET_POWER_MODE_TAIL = 0x08029232
EXPECTED_HANDLER_TAIL = bytes.fromhex("0120bde8")

GPIO_SET_HIGH = 0x0800920E
GPIO_RESET_LOW = 0x08009212

MODE_HANDLER = 0x08037B00
CONDITIONAL_STOCK_SET = 0x08037B40
CONDITIONAL_PB3_HOLD = 0x08037B70
ROUTINES_END = 0x08037BC0

STOCK_SET_SITES = (
    (0x0801F180, "PA8_set_mode1", bytes.fromhex("eaf745f8")),
    (0x0801F214, "PC6_set_mode2", bytes.fromhex("e9f7fbff")),
    (0x0801F26A, "PB9_set_mode2", bytes.fromhex("e9f7d0ff")),
    (0x0801F274, "PA8_set_mode2", bytes.fromhex("e9f7cbff")),
    (0x0801F2E0, "PB9_set_mode3", bytes.fromhex("e9f795ff")),
    (0x0801F334, "PC6_set_mode3", bytes.fromhex("e9f76bff")),
    (0x0801F33E, "PA8_set_mode3", bytes.fromhex("e9f766ff")),
)

PB3_FINAL_SITE = (0x0801F3B8, "PB3_final_close", bytes.fromhex("e9f72bff"))

MODE_HANDLER_ASSEMBLY = rf"""
    ldrb r0, [r5]
    cmp r0, #1
    bhi mode_return
    orr r0, r0, #0x20
    ldr r1, ={START_POWER_MODE_RAM:#010x}
    strb r0, [r1]
mode_return:
    movs r0, #1
    pop.w {{r4, r5, r6, r7, r8, pc}}
"""

CONDITIONAL_STOCK_SET_ASSEMBLY = rf"""
    ldr r2, ={START_POWER_MODE_RAM:#010x}
    ldrb r2, [r2]
    tst r2, #1
    bne one_phase_reset
    b.w {GPIO_SET_HIGH:#010x}
one_phase_reset:
    b.w {GPIO_RESET_LOW:#010x}
"""

CONDITIONAL_PB3_HOLD_ASSEMBLY = rf"""
    ldr r2, ={START_POWER_MODE_RAM:#010x}
    ldrb r3, [r2]
    orr r3, r3, #0x40
    strb r3, [r2]
    tst r3, #1
    beq three_phase_original_reset
    b.w {GPIO_SET_HIGH:#010x}
three_phase_original_reset:
    b.w {GPIO_RESET_LOW:#010x}
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    source = args.source.read_bytes()
    if len(source) != IMAGE_SIZE:
        raise SystemExit(f"Unexpected image size: {len(source)}")
    source_hash = sha256(source)
    if source_hash != EXPECTED_SHA256:
        raise SystemExit(f"Refusing unknown base image: {source_hash}")

    image = bytearray(source)
    cave = image[MODE_HANDLER - FLASH_BASE : ROUTINES_END - FLASH_BASE]
    if any(cave):
        raise SystemExit("Selected code cave is not zero-filled")

    mode_handler = assemble(MODE_HANDLER_ASSEMBLY, MODE_HANDLER)
    conditional_set = assemble(CONDITIONAL_STOCK_SET_ASSEMBLY, CONDITIONAL_STOCK_SET)
    conditional_hold = assemble(CONDITIONAL_PB3_HOLD_ASSEMBLY, CONDITIONAL_PB3_HOLD)
    if MODE_HANDLER + len(mode_handler) > CONDITIONAL_STOCK_SET:
        raise SystemExit("Mode handler overlaps conditional-set helper")
    if CONDITIONAL_STOCK_SET + len(conditional_set) > CONDITIONAL_PB3_HOLD:
        raise SystemExit("Conditional-set helper overlaps PB3 helper")
    if CONDITIONAL_PB3_HOLD + len(conditional_hold) > ROUTINES_END:
        raise SystemExit("PB3 helper exceeds code cave")
    patch_at(image, MODE_HANDLER, mode_handler)
    patch_at(image, CONDITIONAL_STOCK_SET, conditional_set)
    patch_at(image, CONDITIONAL_PB3_HOLD, conditional_hold)

    handler_hook = assemble(f"b.w 0x{MODE_HANDLER:08x}", SET_POWER_MODE_TAIL)
    old_handler_tail = patch_at(image, SET_POWER_MODE_TAIL, handler_hook)
    if old_handler_tail != EXPECTED_HANDLER_TAIL:
        raise SystemExit(
            f"Unexpected SetStartPowerMode tail: {old_handler_tail.hex()}"
        )

    patch_lines: list[str] = [
        f"0x{SET_POWER_MODE_TAIL:08x} mode_handler old={old_handler_tail.hex()} "
        f"new={handler_hook.hex()} target=0x{MODE_HANDLER:08x}"
    ]
    for address, label, expected in STOCK_SET_SITES:
        replacement = assemble(f"bl 0x{CONDITIONAL_STOCK_SET:08x}", address)
        old = patch_at(image, address, replacement)
        if old != expected:
            raise SystemExit(
                f"Unexpected original bytes at 0x{address:08x}: "
                f"expected {expected.hex()}, got {old.hex()}"
            )
        patch_lines.append(
            f"0x{address:08x} {label} old={old.hex()} new={replacement.hex()} "
            f"target=0x{CONDITIONAL_STOCK_SET:08x}"
        )

    address, label, expected = PB3_FINAL_SITE
    replacement = assemble(f"bl 0x{CONDITIONAL_PB3_HOLD:08x}", address)
    old = patch_at(image, address, replacement)
    if old != expected:
        raise SystemExit(
            f"Unexpected original bytes at 0x{address:08x}: "
            f"expected {expected.hex()}, got {old.hex()}"
        )
    patch_lines.append(
        f"0x{address:08x} {label} old={old.hex()} new={replacement.hex()} "
        f"target=0x{CONDITIONAL_PB3_HOLD:08x}"
    )

    patched = bytes(image)
    allowed_ranges = [
        (MODE_HANDLER - FLASH_BASE, ROUTINES_END - FLASH_BASE),
        (SET_POWER_MODE_TAIL - FLASH_BASE, SET_POWER_MODE_TAIL - FLASH_BASE + 4),
        *(
            (address - FLASH_BASE, address - FLASH_BASE + 4)
            for address, _label, _expected in STOCK_SET_SITES
        ),
        (PB3_FINAL_SITE[0] - FLASH_BASE, PB3_FINAL_SITE[0] - FLASH_BASE + 4),
    ]
    unexpected_differences = [
        offset
        for offset, (before, after) in enumerate(zip(source, patched))
        if before != after
        and not any(start <= offset < end for start, end in allowed_ranges)
    ]
    if unexpected_differences:
        preview = ", ".join(f"0x{FLASH_BASE + offset:08x}" for offset in unexpected_differences[:8])
        raise SystemExit(f"Bytes changed outside declared patch ranges: {preview}")
    if patched[: BOOTLOADER_END - FLASH_BASE] != source[: BOOTLOADER_END - FLASH_BASE]:
        raise SystemExit("Bootloader region changed")
    if patched[0x0801F424 - FLASH_BASE : 0x0801F428 - FLASH_BASE] != source[
        0x0801F424 - FLASH_BASE : 0x0801F428 - FLASH_BASE
    ]:
        raise SystemExit("PB3 stop/open write changed")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AC011K-AE-25_V1.2.460-GD-selectable-1p-3p-test"
    binary_path = args.output_dir / f"{stem}.bin"
    hex_path = args.output_dir / f"{stem}.hex"
    disassembly_path = args.output_dir / f"{stem}.disasm.txt"
    manifest_path = args.output_dir / f"{stem}.manifest.txt"
    binary_path.write_bytes(patched)
    write_sparse_ihex(hex_path, patched)
    disassembly_path.write_text(
        "MODE HANDLER\n\n"
        + disassemble(mode_handler, MODE_HANDLER)
        + "\nCONDITIONAL STOCK SET\n\n"
        + disassemble(conditional_set, CONDITIONAL_STOCK_SET)
        + "\nCONDITIONAL PB3 HOLD\n\n"
        + disassemble(conditional_hold, CONDITIONAL_PB3_HOLD),
        encoding="utf-8",
    )
    manifest_path.write_text(
        "\n".join(
            (
                "purpose=selectable live-verified 1p/stock 3p experiment; not production firmware",
                "base=AC011K-AE-25_V1.2.460.bin",
                f"base_sha256={source_hash}",
                f"patched_sha256={sha256(patched)}",
                f"image_size={len(patched)}",
                "bootloader_0x08000000_0x08007fff=byte-identical",
                f"start_power_mode_ram=0x{START_POWER_MODE_RAM:08x}",
                "mode_0=stock_three_phase_gpio_effects",
                "mode_1=live_verified_PB3_only_one_phase_gpio_effects",
                "mode_handler_marker=0x20",
                "physical_close_marker=0x40",
                "complete_stop_open_path=byte-identical",
                "PB3_stop_open_reset_0x0801f424=byte-identical",
                "all_changed_bytes=confined_to_declared_hooks_and_zero_filled_code_cave",
                f"mode_handler_size={len(mode_handler)}",
                f"conditional_set_size={len(conditional_set)}",
                f"conditional_hold_size={len(conditional_hold)}",
                *patch_lines,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    print(manifest_path.read_text(), end="")
    print(f"binary={binary_path}")
    print(f"hex={hex_path}")


if __name__ == "__main__":
    main()
