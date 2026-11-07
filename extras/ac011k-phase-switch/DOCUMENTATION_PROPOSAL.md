# Documentation structure — approved

The owner approved this structure on 26 September 2026 and requested English
throughout the current documentation:

1. Root README: capabilities, tested hardware, entry points and community origin.
2. Architecture: ESP/GD split, UART, permission slots, power targets, transition
   sequence and measurement limits.
3. Installation and recovery: compatibility, build, OTA versus serial images,
   GD patch prerequisites and rollback.
4. MQTT/Home Assistant: entities, topics, units, migration and EMS integration.
5. Testing and troubleshooting: actual acceptance status, regressions and log capture.
6. Reverse engineering: retain the detailed GD evidence, addresses and patch rationale.
7. Historical records: keep dated experiments and original German field notes,
   linked explicitly as history rather than current installation instructions.

Implemented in this working branch. Existing community reference material and
historical field notes remain in their original language. The current guide
uses concrete observations, separates evidence from interpretation, and keeps
private HA configuration and household history outside public Git.
