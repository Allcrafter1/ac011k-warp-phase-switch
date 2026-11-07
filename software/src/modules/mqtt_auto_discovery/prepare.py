import os
import sys
import importlib.util
import importlib.machinery

software_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def create_software_module():
    software_spec = importlib.util.spec_from_file_location('software', os.path.join(software_dir, '__init__.py'))
    software_module = importlib.util.module_from_spec(software_spec)

    software_spec.loader.exec_module(software_module)

    sys.modules['software'] = software_module

if 'software' not in sys.modules:
    create_software_module()

from software import util

from enum import Enum
from dataclasses import dataclass
import json

class DiscoveryType(Enum):
    STATE_ONLY = "STATE_ONLY"
    STATE_AND_UPDATE = "STATE_AND_UPDATE"
    COMMAND_ONLY = "COMMAND_ONLY"

class Component(Enum):
    BINARY_SENSOR = "binary_sensor"
    SENSOR = "sensor"
    SWITCH = "switch"
    BUTTON = "button"
    NUMBER = "number"
    SELECT = "select"

    def get_discovery_type(self) -> DiscoveryType:
        return {
            Component.BINARY_SENSOR: DiscoveryType.STATE_ONLY,
            Component.SENSOR: DiscoveryType.STATE_ONLY,
            Component.SWITCH: DiscoveryType.STATE_AND_UPDATE,
            Component.NUMBER: DiscoveryType.STATE_AND_UPDATE,
            Component.SELECT: DiscoveryType.STATE_AND_UPDATE,
            Component.BUTTON: DiscoveryType.COMMAND_ONLY
        }[self]

class Feature(Enum):
    EVSE = "evse"
    METER = "meter"
    AC011K = "ac011k"

@dataclass
class Entity:
    include_generic: bool
    component: Component
    feature: Feature
    object_id: str
    path: str
    name_de: str
    name_en: str
    static_info_generic: str
    static_info_homeassistant: str
    command_path: str = ""

    def get_json_len(self):
        return max(len(self.name_de), len(self.name_en)) + len(self.object_id) + len(self.path) + max(len(self.get_static_info_generic_str()), len(self.get_static_info_homeassistant_str()))

    def get_static_info_generic_str(self):
        if not self.include_generic:
            return "NULL"
        # Static info is not a JSON object, but only more key/value pairs, so
        # remove the braces. Encoding the complete fragment once more as JSON
        # yields a valid C++ string literal, including nested JSON templates.
        fragment = json.dumps(self.static_info_generic).strip().lstrip("{").rstrip("}")
        return json.dumps(fragment)

    def get_static_info_homeassistant_str(self):
        fragment = json.dumps(self.static_info_generic | self.static_info_homeassistant).strip().lstrip("{").rstrip("}")
        return json.dumps(fragment)

topic_template = """    {{
        .feature = "{feature}",
        .path = "{path}",
        .command_path = "{command_path}",
        .component = "{component}",
        .object_id = "{object_id}",
        .name_de = "{name_de}",
        .name_en = "{name_en}",
        .static_infos = {{
            {static_info_generic},
            {static_info_homeassistant}
        }},
        .type = MqttDiscoveryType::{discovery_type},
    }}"""






entities = [

Entity(True, Component.SENSOR, Feature.METER, "powernow", "meter/values", "Leistungsaufnahme", "Power draw",
    {"value_template":"{{value_json.power}}",
     "unit_of_measurement":"W",
     "device_class":"power",
     "state_class": "measurement"},
    {}),

Entity(True, Component.SENSOR, Feature.METER, "energyabs", "meter/values", "Stromverbrauch absolut", "Energy consumption (absolute)",
    {"value_template":"{{value_json.energy_abs}}",
     "unit_of_measurement":"kWh",
     "device_class":"energy",
     "state_class": "total"},
    {}),

Entity(True, Component.SENSOR, Feature.METER, "energyrel", "meter/values", "Stromverbrauch relativ", "Energy consumption (relative)",
    {"value_template":"{{value_json.energy_rel}}",
     "unit_of_measurement":"kWh",
     "device_class":"energy",
     "state_class": "total"},
    {}),

Entity(True, Component.SENSOR, Feature.EVSE, "chargerstate", "evse/state", "Fahrzeugstatus", "Vehicle state",
    {"value_template":"{{value_json.charger_state}}",
     "icon": "mdi:ev-plug-type2"},
    {}),

Entity(True, Component.NUMBER, Feature.EVSE, "globalcurrent", "evse/global_current", "Konfigurierter Ladestrom", "Configured charging current",
    {"value_template":"{{value_json.current}}",
     "unit_of_measurement":"mA",
     "min": 6000,
     "max": 32000,
     "step": 1000,
     "mode": "box",
     "icon": "mdi:gauge"},
    {}),

Entity(True, Component.SWITCH, Feature.EVSE, "autocharge", "evse/auto_start_charging", "Ladevorgang automatisch starten", "Start charging automatically",
    {"value_template":"{{value_json.auto_start_charging}}",
     "state_on":"true",
     "state_off":"false",
     "payload_on":"true",
     "payload_off":"false",
     "icon": "mdi:ev-plug-type2"},
    {"state_on":"True",
     "state_off":"False"}),

Entity(True, Component.BUTTON, Feature.EVSE, "startcharge", "evse/start_charging", "Ladevorgang starten", "Start charging",
    {"payload_press": "null",   # for Home Assistant
     "payload_on":"null",       # for Domoticz
     "icon": "mdi:flash"},
    {}),

Entity(True, Component.BUTTON, Feature.EVSE, "stopcharge", "evse/stop_charging", "Ladevorgang beenden", "Stop charging",
    {"payload_press": "null",   # for Home Assistant
     "payload_on":"null",       # for Domoticz
     "icon": "mdi:flash-off"},
    {}),

Entity(False, Component.BINARY_SENSOR, Feature.EVSE, "cable", "evse/state", "Wallbox Ladekabel verbunden", "Wallbox cable connected",
    {"device_class":"plug"},
    {"value_template":"{{value_json.charger_state in [1, 2, 3]}}",
     "payload_on":"True",
     "payload_off":"False"}),

Entity(False, Component.BINARY_SENSOR, Feature.EVSE, "ready", "evse/state", "Wallbox ladebereit", "Wallbox ready to charge",
    {"device_class":"power"},
    {"value_template":"{{value_json.charger_state in [2, 3]}}",
     "payload_on":"True",
     "payload_off":"False"}),

Entity(False, Component.BINARY_SENSOR, Feature.EVSE, "charging", "evse/state", "Wallbox Ladevorgang", "Wallbox charging",
    {"device_class":"battery_charging"},
    {"value_template":"{{value_json.charger_state in [3]}}",
     "payload_on":"True",
     "payload_off":"False"}),

Entity(False, Component.BINARY_SENSOR, Feature.EVSE, "error", "evse/state", "Wallbox Fehler", "Wallbox error",
    {"device_class":"problem"},
    {"value_template":"{{ value_json.charger_state == 4 or value_json.operation_state | default('') == 'phase_switch_error' }}",
     "payload_on":"True",
     "payload_off":"False"}),

Entity(False, Component.BINARY_SENSOR, Feature.EVSE, "online", "evse/low_level_state", "Wallbox verfügbar", "Wallbox online",
    {"device_class":"connectivity",
     "expire_after": "30"},
    {"value_template":"{{value_json.uptime>0}}",
     "payload_on":"True",
     "payload_off":"False"}),

Entity(False, Component.SELECT, Feature.AC011K, "phase_mode", "evse/phase_switch", "Ladephasen", "Charging phases",
    {},
    {"value_template":"{{ value_json.requested_phases | string }}",
     "command_template":"{\"phases\": {{ value | int }}}",
     "options":["1", "3"],
     "entity_category":"config",
     "icon":"mdi:sine-wave"}),

Entity(True, Component.SENSOR, Feature.AC011K, "active_phases", "evse/phase_switch", "Zuletzt verifizierte Ladephasen", "Last verified charging phases",
    {"value_template":"{{value_json.active_phases}}",
     "icon":"mdi:transmission-tower"},
    {}),

Entity(False, Component.BINARY_SENSOR, Feature.AC011K, "phase_switching", "evse/phase_switch", "Phasenumschaltung aktiv", "Phase switch active",
    {},
    {"value_template":"{{value_json.switching}}",
     "payload_on":"True",
     "payload_off":"False",
     "icon":"mdi:swap-horizontal"}),

Entity(False, Component.SELECT, Feature.AC011K, "power_rounding", "evse/power_manager_config", "Leistungsrundung", "Power rounding",
    {},
    {"value_template":"{{ {0: 'Aufrunden', 1: 'Abrunden', 2: 'Nächster Wert'}.get(value_json.rounding_mode, 'Aufrunden') }}",
     "command_template":"{\"rounding_mode\": {{ {'Aufrunden': 0, 'Abrunden': 1, 'Nächster Wert': 2}.get(value, 0) }}}",
     "options":["Aufrunden", "Abrunden", "Nächster Wert"],
     "entity_category":"config",
     "icon":"mdi:approximately-equal"}),

Entity(True, Component.SENSOR, Feature.AC011K, "power_target_effective", "evse/power_manager", "Gerundetes Leistungsziel", "Rounded charging power target",
    {"value_template":"{{ (value_json.effective_power_w / 1000) | round(2) }}",
     "unit_of_measurement":"kW",
     "device_class":"power",
     "icon":"mdi:ev-station"},
    {}),

Entity(True, Component.SENSOR, Feature.AC011K, "power_target_requested", "evse/power_manager", "Angeforderte Ladeleistung", "Requested charging power",
    {"value_template":"{{ (value_json.requested_power_w / 1000) | round(2) }}",
     "unit_of_measurement":"kW",
     "device_class":"power",
     "icon":"mdi:target"},
    {}),

Entity(True, Component.SENSOR, Feature.AC011K, "power_target_current", "evse/power_manager", "Berechneter Ladestrom", "Calculated charging current",
    {"value_template":"{{ value_json.target_current_ma }}",
     "unit_of_measurement":"mA",
     "icon":"mdi:current-ac"},
    {}),

Entity(True, Component.SENSOR, Feature.AC011K, "power_target_phases", "evse/power_manager", "Berechnete Ladephasen", "Calculated charging phases",
    {"value_template":"{{ value_json.target_phases }}",
     "icon":"mdi:transmission-tower"},
    {}),
]


# AC011K-specific, documented fields; never expose zero-filled unsupported
# all_values entries as measurements (per-phase real power, temperature, etc.).
entities.append(Entity(False, Component.NUMBER, Feature.AC011K,
    "power_limit", "evse/power_manager", "Ladeleistungsgrenze", "Charging power limit", {},
    {"value_template": "{{ (value_json.effective_power_w / 1000) | round(2) }}",
     "command_template": '{"power_w": {{ (value | float * 1000) | round(0) | int }}}',
     "min": 0, "max": 11.04, "step": 0.01, "mode": "slider",
     "unit_of_measurement": "kW", "device_class": "power", "retain": False},
    command_path="evse/power_target_update"))

entities.append(Entity(True, Component.SENSOR, Feature.AC011K,
    "power_applied_current", "evse/power_manager", "Angewendetes Stromlimit", "Applied current limit",
    {"value_template": "{{ value_json.applied_current_ma }}",
     "unit_of_measurement": "mA", "device_class": "current"}, {}))

for phase in range(3):
    for quantity, name, unit, index in [
        ("voltage", "Spannung", "V", phase),
        ("current", "Strom", "A", phase + 3),
    ]:
        entities.append(Entity(True, Component.SENSOR, Feature.AC011K,
            f"{quantity}_l{phase + 1}", "meter/all_values",
            f"{name} L{phase + 1}", f"{quantity.title()} L{phase + 1}",
            {"value_template": "{{ value_json[" + str(index) + "] }}",
             "unit_of_measurement": unit, "device_class": quantity,
             "state_class": "measurement"}, {}))

for key, name in [
    ("iec61851_state", "IEC-61851-Zustand"),
    ("contactor_state", "Schuetzstatus (logisch)"),
]:
    entities.append(Entity(True, Component.SENSOR, Feature.AC011K, key,
        "evse/state", name, key,
        {"value_template": "{{ value_json." + key + " }}",
         "entity_category": "diagnostic"}, {}))

entities.append(Entity(False, Component.SENSOR, Feature.AC011K, "gd_state",
    "evse/state", "GD-Ladezustand", "GD charging state", {},
    {"value_template": "{{ {1: 'Getrennt', 2: 'Warte auf Freigabe', 3: 'Lädt', 4: 'Suspended EVSE', 5: 'Suspended EV', 6: 'Ladebereit/Fertig', 7: 'Reserved', 8: 'Unavailable', 9: 'Fehler'}.get(value_json.GD_state, 'Unbekannt') }}"}))
entities.append(Entity(True, Component.SENSOR, Feature.AC011K, "allowed_current",
    "evse/state", "Freigegebener Ladestrom", "Allowed charging current",
    {"value_template": "{{ value_json.allowed_charging_current }}",
     "unit_of_measurement": "mA", "device_class": "current"}, {}))
entities.append(Entity(False, Component.BINARY_SENSOR, Feature.AC011K,
    "session_release", "evse/slots", "Ladefreigabe", "Charging release", {},
    {"value_template": "{{ value_json[4].active and value_json[4].max_current > 0 }}",
     "payload_on": "True", "payload_off": "False"}))
for key, path, name in [
    ("stage", "evse/phase_switch", "Phasenumschaltung Schritt"),
    ("last_error_text", "evse/phase_switch", "Phasenumschaltung Fehler"),
    ("gd_fault_code", "evse/phase_switch", "GD-Fehlercode"),
    ("cp_voltage_raw", "evse/phase_switch", "CP-Rohwert"),
    ("last_error", "evse/power_manager", "Leistungsregelung Fehler"),
]:
    entities.append(Entity(True, Component.SENSOR, Feature.AC011K,
        ("power_" if path.endswith("power_manager") else "phase_") + key,
        path, name, name,
        {"value_template": "{{ value_json." + key + " }}",
         "entity_category": "diagnostic"}, {}))
entities.append(Entity(False, Component.BINARY_SENSOR, Feature.AC011K,
    "power_pending", "evse/power_manager", "Leistungsziel ausstehend", "Power target pending", {},
    {"value_template": "{{ value_json.pending }}", "payload_on": "True",
     "payload_off": "False", "entity_category": "diagnostic"}))

topics = [topic_template.format(
            feature=x.feature.value,
            path=x.path,
            command_path=x.command_path,
            component=x.component.value,
            object_id=x.object_id,
            name_de=x.name_de,
            name_en=x.name_en,
            static_info_generic=x.get_static_info_generic_str(),
            static_info_homeassistant=x.get_static_info_homeassistant_str(),
            discovery_type=x.component.get_discovery_type().value,
            )
          for x in entities]

util.specialize_template("mqtt_discovery_topics.cpp.template", "mqtt_discovery_topics.cpp", {
    "{{{topics}}}": ",\n".join(topics),
    })

util.specialize_template("mqtt_discovery_topics.h.template", "mqtt_discovery_topics.h", {
    "{{{topic_count}}}": str(len(topics)),
    "{{{max_json_len}}}": str(max([x.get_json_len() for x in entities]))
    })
