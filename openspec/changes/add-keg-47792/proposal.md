## Why

Issue #7: product ID `47792` is missing from the bundled keg catalog, so the **Keg** sensor stays blank. The reporter identifies the fitted keg as **Camden Eazy**. That name is already on the companion card, but it is bound to a different product ID (`47629`, listed in the integration as Camden Eazy IPA).

## What Changes

- Add `"47792": "Camden Eazy"` to `keg_catalog.json` in numeric key order.
- Ratchet the catalog floor from 115 to 116 in tests and the `entities` spec.
- Patch-bump the integration to 0.3.4.
- Companion card: add a catalog entry for `kegId: "47792"` that reuses the existing Camden Eazy colours and `kegs/camden-eazy.webp`. Leave the `47629` entry where it is. Re-sync `scripts/keg-catalog.reference.json`. Patch-bump the card to 0.4.2.

Not in scope:

- Renaming `47629` from "Camden Eazy IPA" or moving its card binding.
- New keg artwork. The Camden Eazy graphic already exists.
- Falling back to the raw product ID when a keg is unmapped.
- Allowing one card entry to hold more than one product ID.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `entities`: keg name catalog floor ratchets from 115 to 116 product IDs.

## Impact

- Users with keg `47792` see **Camden Eazy** on the **Keg** sensor after updating to 0.3.4, and the existing Camden Eazy branding on the card after 0.4.2.
- Users with keg `47629` are unchanged.
- No entity churn, no migration, no behaviour change for any other ID.
- The name lookup lives in the integration. The card still needs its own `kegId` row: it joins on product ID first, and `check:catalog` treats an unbound integration ID as a gap. The graphic does not.
