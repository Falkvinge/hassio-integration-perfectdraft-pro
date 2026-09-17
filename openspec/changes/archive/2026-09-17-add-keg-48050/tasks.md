## 1. Integration catalog

- [x] 1.1 Add `"48050": "Anheuser-Busch Bud"` to `keg_catalog.json` in numeric key order
- [x] 1.2 Bump `manifest.json` to 0.3.3
- [x] 1.3 Ratchet `MINIMUM_ENTRIES` to 115 and assert `catalog["48050"]`
- [x] 1.4 Update README catalog count; leave Brett's 114-entry credit intact as the original mapping

## 2. Companion card

- [x] 2.1 Set `kegId: "48050"` on the existing `bud` / Anheuser-Busch Bud entry
- [x] 2.2 Re-sync `scripts/keg-catalog.reference.json` to integration commit `fc8a25c4`
- [x] 2.3 Bump `package.json`, `CARD_VERSION`, and `EDITOR_VERSION` to 0.4.1 and rebuild `dist/`

## 3. Verify and ship

- [x] 3.1 `python3 -m unittest tests.test_keg_catalog` — 9 tests, 115 keys
- [x] 3.2 `npm run lint`, `npm run check:catalog` (115/115), `npm run build`
- [x] 3.3 Publish GitHub releases v0.3.3 and v0.4.1
