"""Offline generation checks; no model loading or dataset image access."""

import json
from pathlib import Path
import tempfile
import unittest

import yaml

from generate_supported_foods import OUTPUT, SOURCE, generate, render_catalog


class SupportedFoodTests(unittest.TestCase):
    def test_complete_catalog_and_display_only_correction(self):
        rendered = render_catalog(SOURCE.read_text(encoding="utf-8"))
        records = json.loads(rendered.split("export const supportedFoods: readonly SupportedFood[] = ")[1])
        names = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["names"]
        self.assertEqual(len(records), 72)
        self.assertEqual([record["id"] for record in records], names)
        self.assertEqual(next(record["name"] for record in records if record["id"] == "veg_briyani"), "Veg Biryani")
        self.assertEqual(rendered, OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(rendered, render_catalog(SOURCE.read_text(encoding="utf-8")))

    def test_invalid_definitions(self):
        for value in [None, [], {}, {"nc": 0, "names": []}, {"nc": 2, "names": ["idli"]},
                      {"nc": 2, "names": ["idli", "idli"]}, {"nc": 1, "names": [""]},
                      {"nc": 1, "names": [None]}, {"nc": 1, "names": [" idli"]},
                      {"nc": True, "names": ["idli"]}, {"nc": 1, "names": {0: "idli"}}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_catalog(yaml.safe_dump(value))

    def test_generation_and_read_only_drift_check(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog.ts"
            with self.assertRaisesRegex(ValueError, "stale or missing"):
                generate(output=output, check=True)
            self.assertFalse(output.exists())
            generate(output=output)
            expected = output.read_bytes()
            generate(output=output)
            self.assertEqual(output.read_bytes(), expected)
            generate(output=output, check=True)
            output.write_text("stale", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale or missing"):
                generate(output=output, check=True)
            self.assertEqual(output.read_text(encoding="utf-8"), "stale")


if __name__ == "__main__":
    unittest.main()
