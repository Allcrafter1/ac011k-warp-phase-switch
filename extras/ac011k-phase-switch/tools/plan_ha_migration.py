#!/usr/bin/env python3
"""Read-only AC011K entity migration inventory; never contacts HA or MQTT.

Input: an entity-registry JSON list (or HA WS response with result/list), plus
exported YAML/dashboard/helper files. Output contains IDs and reference locations,
not configuration contents. Keep installation-specific plans outside public Git.
"""
import argparse
import json
from pathlib import Path
import re

# Stable firmware object IDs and canonical, installation-independent suffixes.
NAMES = {
    'powernow': 'power', 'energyabs': 'energy_total', 'energyrel': 'energy_relative',
    'chargerstate': 'charger_state', 'globalcurrent': 'current_limit',
    'autocharge': 'autostart', 'startcharge': 'start', 'stopcharge': 'stop',
    'cable': 'connected', 'ready': 'ready', 'charging': 'charging', 'error': 'error',
    'online': 'online', 'phase_mode': 'phase_mode', 'active_phases': 'verified_phases',
    'phase_switching': 'phase_switching', 'power_rounding': 'power_rounding',
    'power_target_effective': 'power_effective', 'power_target_requested': 'power_requested',
    'power_target_current': 'target_current', 'power_target_phases': 'target_phases',
    'power_applied_current': 'applied_current', 'power_limit': 'power_limit', 'gd_state': 'gd_state',
    'allowed_current': 'allowed_current', 'iec61851_state': 'iec61851_state',
    'contactor_state': 'contactor_state',
    'session_release': 'session_release', 'power_pending': 'power_pending',
    'phase_stage': 'phase_stage', 'phase_last_error_text': 'phase_error',
    'phase_gd_fault_code': 'gd_fault_code', 'phase_cp_voltage_raw': 'cp_raw',
    'power_last_error': 'power_error',
    **{f'{q}_l{i}': f'{q}_l{i}' for q in ['voltage', 'current'] for i in range(1, 4)},
}
LEGACY = {
    'axitec_wallbox_start_button': ('button', 'startcharge'),
    'axitec_wallbox_stop_button': ('button', 'stopcharge'),
    'axitec_wallbox_power_limit': ('number', 'power_limit'),
    'axitec_wallbox_charger_state': ('sensor', 'chargerstate'),
    'axitec_wallbox_iec61851_state': ('sensor', 'iec61851_state'),
    'axitec_wallbox_gd_state': ('sensor', 'gd_state'),
    'axitec_wallbox_contactor_state': ('sensor', 'contactor_state'),
    'axitec_wallbox_allowed_current': ('sensor', 'allowed_current'),
}
PLACEHOLDERS = {'axitec_wallbox_error_state', 'axitec_wallbox_contactor_error', 'axitec_wallbox_lock_state',
                'axitec_wallbox_dc_fault_current_state'}


def plan(registry, client, prefix, files):
    result = {'client_name': client, 'entity_prefix': prefix,
              'required_firmware': 'September discovery revision or later',
              'changes': [], 'retire_unimplemented': [], 'unknown_objects': []}
    for entry in registry:
        uid = entry.get('unique_id', '')
        old = entry.get('entity_id', '')
        if entry.get('platform') != 'mqtt':
            continue
        if uid in PLACEHOLDERS:
            result['retire_unimplemented'].append(old)
            continue
        if uid in LEGACY:
            domain, object_id = LEGACY[uid]
        elif uid.startswith(client + '-'):
            domain = old.split('.')[0]
            object_id = uid[len(client) + 1:]
        else:
            continue
        if object_id not in NAMES:
            result['unknown_objects'].append(old)
            continue
        result['changes'].append({'old_entity_id': old,
            'discovery_unique_id': client + '-' + object_id,
            'new_entity_id': domain + '.' + prefix + '_' + NAMES[object_id],
            'old_registry_id': entry.get('id'), 'old_device_id': entry.get('device_id')})
    identifiers = {c['old_entity_id'] for c in result['changes']} | set(result['retire_unimplemented'])
    identifiers |= {c[k] for c in result['changes'] for k in ['old_registry_id', 'old_device_id'] if c[k]}
    result['references'] = []
    for file in files:
        if not file.is_file():
            continue
        text = file.read_text(errors='replace')
        for identifier in sorted(identifiers):
            pattern = re.compile(r'(?<![\w])' + re.escape(identifier) + r'(?![\w])')
            lines = [i for i, line in enumerate(text.splitlines(), 1) if pattern.search(line)]
            if lines:
                result['references'].append({'file': str(file), 'identifier': identifier, 'lines': lines})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--client-name', required=True)
    parser.add_argument('--entity-prefix', default='ac011k')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('exports', nargs='*', type=Path)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text())
    if isinstance(registry, dict):
        registry = registry.get('result', registry.get('entity_entries'))
    if not isinstance(registry, list):
        parser.error('registry must be a list or contain result/entity_entries')
    if not re.fullmatch(r'[a-z][a-z0-9_]*', args.entity_prefix):
        parser.error('entity-prefix must be a lowercase HA object-id prefix')
    files = [p for export in args.exports for p in (export.rglob('*') if export.is_dir() else [export])]
    data = plan(registry, args.client_name, args.entity_prefix, files)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(f"{len(data['changes'])} mappings, {len(data['retire_unimplemented'])} unsupported placeholders, "
          f"{len(data['references'])} reference locations. No live changes made.")


if __name__ == '__main__':
    main()
