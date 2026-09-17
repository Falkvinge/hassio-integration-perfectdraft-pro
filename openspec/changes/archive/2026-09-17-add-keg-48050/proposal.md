## Why

Issue #3 (closed after the La Chouffe Blonde backport in v0.3.2) received a follow-up: product ID `48050` is missing from the bundled keg catalog, so the **Keg** sensor stays blank. The reporter confirmed the keg is the DE/AT wrap **Anheuser-Busch Bud**, not the UK Budweiser SKU already listed as `31747`.

## What Changes

- Add `"48050": "Anheuser-Busch Bud"` to `keg_catalog.json` in numeric key order.
- Ratchet the catalog floor from 114 to 115 in tests and the `entities` spec.
- Patch-bump the integration to 0.3.3.
- Companion card: bind the existing `bud` catalog entry (name, colours, keg artwork already present) to `kegId: "48050"` and re-sync `scripts/keg-catalog.reference.json`. Patch-bump the card to 0.4.1.

Not in scope:

- Falling back to the raw product ID when a keg is unmapped.
- Scraping the PerfectDraft shop for names.
- Treating `31747` and `48050` as aliases of one catalog name.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `entities`: keg name catalog floor ratchets from 114 to 115 product IDs.

## Impact

- Users with keg `48050` see **Anheuser-Busch Bud** on the **Keg** sensor after updating to 0.3.3, and the matching card branding after 0.4.1.
- Users with keg `31747` are unchanged (`Budweiser`).
- No entity churn, no migration, no behaviour change for any other ID.
