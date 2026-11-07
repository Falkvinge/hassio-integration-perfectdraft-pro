## Why

[Issue #8](https://github.com/Falkvinge/hassio-integration-perfectdraft-pro/issues/8): reimargithub reports that the card shows no keg picture for Löwenbräu Oktoberfestbier (`29745`), and asks about Spaten Oktoberfestbier, which he has since fitted. He gave its product ID, `33918`, in a follow-up comment.

Both beers are already known to both packages. The integration's `keg_catalog.json` names both IDs, and the card has `lowenbrau-oktoberfest` and `spaten-oktoberfest` entries bound to them by `kegId`. What is missing is the artwork. Neither card entry has an `imagePath`, so the card falls back to the generated silhouette. One small inconsistency comes along with this: the integration names `29745` "Lowenbrau Oktoberfestbier", without the umlauts that its own `454` entry ("Löwenbräu") and the card both use.

## What Changes

- Companion card:
  - Add `src/assets/kegs/lowenbrau-oktoberfest.webp` and `src/assets/kegs/spaten-oktoberfest.webp`, sourced once from the PerfectDraft DE storefront pages linked in the issue.
  - Set `imagePath: kegImage(...)` on the two existing entries. Name, ABV, style, colours and `kegId` stay unchanged; the storefront ABVs (6.1% and 5.9%) already match.
  - Re-sync `scripts/keg-catalog.reference.json` to the integration commit with the rename.
  - Bump the card to 0.4.5 and rebuild `dist/`.
- Integration:
  - Rename `29745` to "Löwenbräu Oktoberfestbier" in `keg_catalog.json`. The key, its position and the count (117) stay the same.
  - Bump to 0.4.5, so the joint release puts both packages on the same version.
- Close issue #8 with a thank-you and the release link.

Not in scope:

- Other card entries without artwork, such as `leffe-winter`.
- Other ASCII-only names in the integration catalog. None are known, and checking every name against the app is a separate job.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The integration's `entities` spec already requires catalog names to be the beer's name, and the floor of 117 IDs is unchanged. The card's own `beer-imagery` spec already requires bundled keg photos for currently-sold beers. This change brings both packages into line with requirements they already have, so it sets `skip_specs: true`.

## Impact

- The **Keg** sensor for `29745` reads "Löwenbräu Oktoberfestbier" instead of "Lowenbrau Oktoberfestbier". The entity ID doesn't change. History shows the new state from the update onwards, and automations comparing against the old string need updating. Such automations are unlikely, since the card matches on product ID.
- On the card, both Oktoberfest kegs show their keg photo in every layout, including the beer picker in the editor.
- Integration: `custom_components/perfectdraft/keg_catalog.json`, `custom_components/perfectdraft/manifest.json`.
- Card repo (`Hassio-PerfectDraftPro-Component`): `src/assets/kegs/` (two new files), `src/beer-catalog.ts`, `scripts/keg-catalog.reference.json`, `package.json`, `package-lock.json`, `CARD_VERSION`, `EDITOR_VERSION`, `dist/`.
