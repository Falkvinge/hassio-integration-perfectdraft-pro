## 1. Integration catalog

- [ ] 1.1 Add `"47792": "Camden Eazy"` to `keg_catalog.json` in numeric key order, between `47629` and `47774`
- [ ] 1.2 Bump `manifest.json` to 0.3.4
- [ ] 1.3 Ratchet `MINIMUM_ENTRIES` to 116 and assert `catalog["47792"]`
- [ ] 1.4 Update the README catalog count from 115 to 116

## 2. Companion card

Work in `Hassio-PerfectDraftPro-Component`. Do not retarget the existing `camden-eazy` / `47629` entry.

- [ ] 2.1 Add a `camden-eazy-47792` entry with `kegId: "47792"`, the same name, brewery, style, ABV, and colours as `camden-eazy`, and `imagePath: kegImage("camden-eazy")`
- [ ] 2.2 Re-sync `scripts/keg-catalog.reference.json` to the integration commit that adds `47792`
- [ ] 2.3 Bump `package.json`, `CARD_VERSION`, and `EDITOR_VERSION` to 0.4.2 and rebuild `dist/`

## 3. Verify and ship

- [ ] 3.1 `python3 -m unittest tests.test_keg_catalog` — 116 keys, including `47792`
- [ ] 3.2 In the card repo: `npm run lint`, `npm run check:catalog` (116/116), `npm run build`
- [ ] 3.3 Publish GitHub releases v0.3.4 and v0.4.2
