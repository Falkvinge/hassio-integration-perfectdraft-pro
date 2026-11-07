## Why

Issue #9: product ID `48180` is missing from the bundled keg catalog, so the **Keg** sensor stays blank for it. The reporter, MThomas564, has the keg fitted and opened PR #10 against the integration and PR #2 against the companion card. Neither can be merged as-is:

- PR #10 inserts `48180` between `48061` and `48134`, which fails `test_keys_in_ascending_numeric_order`.
- PR #10 also re-pads the whole README sensor table for a one-number change.
- PR #10 bumps the integration to 0.3.5, which clashes with the version bump owned by `fix-cognito-signin`, which ships in the same release.
- Card PR #2 pins its reference snapshot to PR #10's unmerged commit and ships a `dist/` built outside our toolchain.

The name is also disputed. PR #10 says "Camden Stout", while brettjenkins' fork maps the same ID as "Camden Nitro Stout".

## What Changes

- Add `48180` to `keg_catalog.json` as the last key, after `48134`. The name defaults to "Camden Stout", as reported by the person with the keg fitted. It changes to "Camden Nitro Stout" only if MThomas564 confirms the app or keg reads that way.
- Ratchet the catalog floor from 116 to 117 in tests and the `entities` spec. Update the README count without reformatting the table.
- No integration version bump of its own. It ships in 0.4.4 with `fix-cognito-signin`.
- Companion card:
  - Add a `camden-stout` entry with `kegId: "48180"` and the keg artwork from card PR #2.
  - Re-sync `scripts/keg-catalog.reference.json` to the integration commit that adds `48180`.
  - Bump the card to 0.4.4 and rebuild `dist/`.
- Credit MThomas564 as co-author on both commits, then close PR #10, card PR #2 and issue #9 with a pointer to the release.

Not in scope:

- brettjenkins' other catalog additions (for example Fada Sunny IPA `48068`). Nobody has reported them here, and each needs its own observation.
- Issue #8 (missing Löwenbräu and Spaten artwork on the card). Both IDs are already named.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `entities`: the keg name catalog floor ratchets from 116 to 117 product IDs.

## Impact

- Users with keg `48180` see its name on the **Keg** sensor after 0.4.4, and Camden Stout branding and artwork on the card after 0.4.4.
- No entity churn, no migration, and no change for any other ID.
- Integration: `keg_catalog.json`, `tests/test_keg_catalog.py`, `README.md`.
- Card repo (`Hassio-PerfectDraftPro-Component`): `src/beer-catalog.ts`, `src/assets/kegs/camden-stout.webp`, `scripts/keg-catalog.reference.json`, `package.json`, `CARD_VERSION`, `EDITOR_VERSION`, `dist/`.
- External: PR #10, card PR #2 and issue #9 close once the joint release ships.
