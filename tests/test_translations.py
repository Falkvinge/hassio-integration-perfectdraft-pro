"""Verify that translation files match strings.json key structure."""
import json
from pathlib import Path
import unittest

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "perfectdraft"


def _key_paths(obj, prefix=""):
    paths = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                paths |= _key_paths(v, full)
            else:
                paths.add(full)
    return paths


class TestTranslations(unittest.TestCase):
    def test_en_and_fr_match_strings_json_keys(self):
        strings = json.loads(
            (COMPONENT_DIR / "strings.json").read_text(encoding="utf-8")
        )
        expected = _key_paths(strings)

        for lang in ("en", "fr"):
            with self.subTest(lang=lang):
                data = json.loads(
                    (COMPONENT_DIR / "translations" / f"{lang}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(_key_paths(data), expected)


if __name__ == "__main__":
    unittest.main()
