"""Validate generated discovery metadata and command/meter template definitions."""
import json
import pathlib
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[3]

class Discovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import runpy
        fake = types.ModuleType("software")
        fake.util = types.SimpleNamespace(specialize_template=lambda *a, **kw: None)
        with patch.dict("sys.modules", {"software": fake}):
            cls.module = runpy.run_path(str(ROOT / "software/src/modules/mqtt_auto_discovery/prepare.py"))
        cls.entities = cls.module["entities"]

    def test_cpp_json_roundtrip_and_unique_ids(self):
        ids = [e.object_id for e in self.entities]
        self.assertEqual(len(ids), len(set(ids)))
        for e in self.entities:
            fragment = json.loads(e.get_static_info_homeassistant_str())
            self.assertEqual(json.loads("{" + fragment + "}"),
                             e.static_info_generic | e.static_info_homeassistant)

    def test_power_number_topics_and_no_retained_commands(self):
        e = next(e for e in self.entities if e.object_id == "power_limit")
        self.assertEqual(e.path, "evse/power_manager")
        self.assertEqual(e.command_path, "evse/power_target_update")
        self.assertIs(e.static_info_homeassistant["retain"], False)
        self.assertEqual(e.static_info_homeassistant["min"], 0)
        self.assertEqual(e.static_info_homeassistant["max"], 11.04)

    def test_only_supported_phase_measurements(self):
        entries = [e for e in self.entities if e.path == "meter/all_values"]
        self.assertEqual(len(entries), 6)
        self.assertEqual({e.static_info_generic["value_template"] for e in entries},
                         {"{{ value_json[" + str(i) + "] }}" for i in range(6)})
        self.assertTrue(all(e.feature.value == "ac011k" for e in entries))

if __name__ == "__main__":
    unittest.main()
