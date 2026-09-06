"""Format and content guards for the bundled keg name catalog.

Runs with the stdlib only (no Home Assistant): the catalog is plain JSON data
and these tests read it directly, so this file still works under
``python3 -m unittest discover -s tests``.

The catalog is hand-maintained — product IDs cannot be queried in bulk from the
PerfectDraft API, so each entry is observed from a machine with that keg fitted.
That makes mechanical guards worth having: a duplicate key or a non-numeric key
fails silently at runtime rather than loudly at review time.
"""
import json
import os
import unittest

CATALOG_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "custom_components",
    "perfectdraft",
    "keg_catalog.json",
)

# Entry count as of the 114-keg backport. A drop below this means entries were
# lost; the catalog is only ever meant to grow.
MINIMUM_ENTRIES = 114

# Shop-listing artefacts that are not part of a beer's name.
LISTING_ARTEFACTS = ("6L", "Short Date", "BBE")


def load_raw() -> str:
    with open(CATALOG_PATH, encoding="utf-8") as handle:
        return handle.read()


class TestKegCatalogFormat(unittest.TestCase):
    def test_parses_as_json_object(self):
        self.assertIsInstance(json.loads(load_raw()), dict)

    def test_no_duplicate_keys(self):
        """json.loads() silently keeps the last of a duplicated key.

        Comparing the pair count against the dict size is the only way to
        notice a duplicate, and a duplicate would mean one observed keg name
        was quietly discarded.
        """
        pairs = json.loads(load_raw(), object_pairs_hook=list)
        self.assertEqual(len(pairs), len(dict(pairs)))

    def test_keys_are_numeric(self):
        """Every key must survive int().

        ``_load_keg_catalog`` in sensor.py builds ``{int(k): v for k, v in ...}``
        and catches ValueError by returning an empty dict. So a single
        non-numeric key — an innocent-looking "_meta" or "_source" — disables
        the entire catalog and every keg silently reports no name. Adding
        metadata to this file therefore requires changing the loader first.
        """
        for key in json.loads(load_raw()):
            with self.subTest(key=key):
                int(key)

    def test_keys_in_ascending_numeric_order(self):
        keys = [int(k) for k in json.loads(load_raw())]
        self.assertEqual(keys, sorted(keys))

    def test_keys_survive_the_loader_without_collapsing(self):
        """Mirror ``_load_keg_catalog``'s ``{int(k): v}`` rebuild.

        Distinct string keys can collide once cast to int ("760" and "0760"),
        which would drop an entry with no error. Checked separately from
        test_no_duplicate_keys, which only sees literal key duplicates.
        """
        raw = json.loads(load_raw())
        self.assertEqual(len({int(k) for k in raw}), len(raw))

    def test_values_are_non_empty_strings(self):
        for key, value in json.loads(load_raw()).items():
            with self.subTest(key=key):
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip())
                self.assertEqual(value, value.strip())


class TestKegCatalogContent(unittest.TestCase):
    def test_has_at_least_the_backported_entry_count(self):
        self.assertGreaterEqual(len(json.loads(load_raw())), MINIMUM_ENTRIES)

    def test_names_carry_no_shop_listing_artefacts(self):
        """Names are the beer, not the product listing.

        Four entries used to carry a pack size, a "Short Date" prefix or a 2024
        best-before date inherited from shop listings.
        """
        for key, value in json.loads(load_raw()).items():
            for artefact in LISTING_ARTEFACTS:
                with self.subTest(key=key, artefact=artefact):
                    self.assertNotIn(artefact, value)

    def test_known_corrections_are_applied(self):
        catalog = json.loads(load_raw())
        self.assertEqual(catalog["32814"], "Romola")
        self.assertEqual(catalog["43235"], "Corona Cero (0.0% abv)")
        self.assertEqual(catalog["44331"], "Ninkasi Flower Lager")
        self.assertEqual(catalog["44536"], "Tiny Rebel Stay Puft")


if __name__ == "__main__":
    unittest.main()
