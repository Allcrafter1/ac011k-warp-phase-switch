#!/usr/bin/env python3
"""Small ARM Thumb and Intel-HEX helpers used by the AC011K GD patch builder."""

from __future__ import annotations

import hashlib
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_LITTLE_ENDIAN, CS_MODE_THUMB, Cs
from keystone import KS_ARCH_ARM, KS_MODE_THUMB, Ks


FLASH_BASE = 0x08000000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assemble(source: str, address: int) -> bytes:
    assembler = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    encoded, _ = assembler.asm(source, address)
    return bytes(encoded)


def disassemble(data: bytes, address: int) -> str:
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
    return "\n".join(
        f"0x{insn.address:08x}: {insn.bytes.hex():12} "
        f"{insn.mnemonic:8} {insn.op_str}"
        for insn in md.disasm(data, address)
    ) + "\n"


def patch_at(image: bytearray, address: int, replacement: bytes) -> bytes:
    offset = address - FLASH_BASE
    old = bytes(image[offset : offset + len(replacement)])
    image[offset : offset + len(replacement)] = replacement
    return old


def ihex_record(address: int, kind: int, payload: bytes) -> str:
    body = bytes((len(payload), address >> 8, address & 0xFF, kind)) + payload
    checksum = (-sum(body)) & 0xFF
    return ":" + (body + bytes((checksum,))).hex().upper()


def write_sparse_ihex(path: Path, image: bytes) -> None:
    lines: list[str] = []
    upper = None
    for offset in range(0, len(image), 16):
        payload = image[offset : offset + 16]
        if all(byte == 0xFF for byte in payload):
            continue
        absolute = FLASH_BASE + offset
        next_upper = absolute >> 16
        if next_upper != upper:
            lines.append(ihex_record(0, 4, next_upper.to_bytes(2, "big")))
            upper = next_upper
        lines.append(ihex_record(absolute & 0xFFFF, 0, payload))
    lines.append(ihex_record(0, 1, b""))
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
