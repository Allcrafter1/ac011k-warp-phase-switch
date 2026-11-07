# Build, installation and recovery

Start with the [tested hardware and hashes](README.md). The GD patch builder
rejects a different base image. The ESP also checks the reported model and GD
version, but these checks cannot identify every PCB variation.

## ESP32 build

The project uses the community PlatformIO environment and its pinned packages.
Install the dependencies described in [software/README.md](../../software/README.md),
then run from `software/`:

```sh
pio run -e warpAC011K
```

Use a branch name without `/`: this older build system includes it in output
filenames. The web build runs npm/esbuild and may refresh generated timezone
and browser data; review those changes separately from firmware changes.

The output directory is `software/build/`. Keep the ELF for decoding future
crashes and record the source revision and SHA-256 of each deployed image.

- This WARP web updater requires `_merged.bin`, including its firmware-info page
  at file offset `0xc000`. It validates that page and skips the first `0xf000`
  bytes, writing only the application into the inactive OTA slot.
- The plain `.bin` is the raw application; this web updater rejects it. Earlier
  release filenames containing `web-ota` incorrectly labelled that raw image.
- For serial recovery, the merged image starts at flash offset `0x1000` and does
  also overwrite boot components. Web OTA and serial flashing are distinct paths.

## GD32 build

The September review leaves GD32 unchanged. For an initial installation only:

```sh
python3 -m venv .venv
.venv/bin/pip install -r extras/ac011k-phase-switch/tools/requirements.txt
.venv/bin/python extras/ac011k-phase-switch/tools/build_gd_selectable_1p_3p_1_2_460.py   AC011K-AE-25_V1.2.460.bin output
```

Use a legally obtained exact base image. Upload the resulting GD **HEX** using
the GD updater, not a vendor `.enfs` package containing a replacement ESP image.
The patch manifest records every changed range and preserved opening code.

## Deployment sequence

1. Save ESP/GD images, settings, current API state and the event log.
2. Stop charging and unplug the vehicle before the supervised update.
3. Upload the validated ESP merged image through the web updater. For an existing verified installation,
   leave GD32 alone.
4. After reboot, check the firmware version, GD fault code, release slot and
   phase-switch state. With autostart off, release must be zero.
5. Check MQTT state/discovery, then perform the tests in [TESTING.md](TESTING.md).
6. Complete HA migration only once the new firmware owns the required discovery
   topics. Do not remove working YAML controls before their replacements exist.

## Recovery

Keep the last known working ESP merged image. If the web updater remains
reachable, reinstall the matching merged image through the web updater. If GD still responds to its updater,
the known stock 1.2.460 HEX is the GD rollback route. Serial ESP recovery and a
GD debug adapter are separate physical recovery paths; an ESP OTA backup does
not back up GD option bytes or the entire physical device.

Rolling ESP back also changes its discovery vocabulary. Restore the matching
HA configuration from the pre-migration backup rather than leaving consumers
pointing to entities that the old firmware cannot publish.
