## Context

See proposal.md for why. The card resolves a fitted keg by product ID through `getBeerByKegId` and keeps its own curated name when the ID matches. So the integration's name for `29745` only reaches the **Keg** sensor state, never the card label. `npm run check:catalog` compares IDs only, not names, but `scripts/keg-catalog.reference.json` is meant to be a faithful snapshot of the integration catalog (`_upstreamCommit` is currently `8b2c4418`).

Existing keg art is WebP, capped at 800 px (`spaten.webp` is 800×800, about 25 KB), as set by the card's `card-layouts-and-imagery` design. The two sources, checked 2026-11-07:

| Beer | Source image | Size |
|---|---|---|
| Löwenbräu Oktoberfestbier | `media/catalog/product/k/e/kegs--lowenbrau--oktoberfest2023.png` | 1200×1200 PNG |
| Spaten Oktoberfestbier | `media/catalog/product/s/p/spaten_oktoberfest_6l_keg_1_1.png` | 700×700 PNG |

Both are under `https://www.perfectdraft.com/`, from the DE product pages linked in issue #8. The page thumbnails carry Magento resize parameters (`?optimize=medium&…&width=265`). Drop those to get the originals above.

## Goals / Non-Goals

**Goals:**

- Both Oktoberfest kegs render their keg photo on the card, sharp in `hero` and `vessel`.
- The integration and the card spell Löwenbräu the same way.

**Non-Goals:**

- Changing any card entry field other than `imagePath`.
- A new image pipeline or script. This is two one-off conversions.

## Decisions

**Slugs as file names.** The files are `lowenbrau-oktoberfest.webp` and `spaten-oktoberfest.webp`, so `kegImage(slug)` resolves them with no special case, as for every other entry.

**Encode to match the existing art: WebP, longest edge at most 800 px, no upscaling.** Löwenbräu goes from 1200 to 800 px. Spaten stays at its native 700 px, because upscaling adds bytes without adding detail, and CSS scales it anyway. The conversion uses Pillow (WebP support confirmed on the dev host); `cwebp` is not installed. Pick a quality setting that keeps each file in the range of the existing art (about 25–40 KB), then check it by eye at hero size. Keep the source PNGs out of the repo.

**Rename to the brand's spelling, "Löwenbräu Oktoberfestbier".** This matches the integration's own `454` entry, the card entry, the storefront page and the issue. The catalog's observation rule applies to which ID maps to which beer, and that is unchanged: the reporter's machine reports `29745` for this keg. The alternative was leaving the name alone, since the card ignores it. It was rejected because the sensor state is user-visible and inconsistent with `454`.

**Order: integration commit first, then card.** The card's reference snapshot records the integration commit (`_upstreamCommit`) and must contain the new name. Because it cites the commit, the integration commit has to exist on `agent/add-oktoberfest-keg-art` first. Re-check the hash after any rebase or merge that rewrites it.

**Versions: both packages go to 0.4.5.** Both change, so this is a joint release under the numbering rule in `PROJECT_HYGIENE.md`. The integration bumps `manifest.json`. The card bumps `package.json`, `CARD_VERSION` and `EDITOR_VERSION`, and regenerates `package-lock.json` with `npm install --package-lock-only`.

## Risks / Trade-offs

- [The Löwenbräu source file is named `oktoberfest2023`, so it may show an older keg design than the one shipping now] → The DE storefront itself shows it, so it is what owners will recognise. Swapping it later is a one-file change.
- [Users with automations matching the string "Lowenbrau Oktoberfestbier"] → Unlikely, since the card matches on ID. Call out the rename in the release notes.
- [HACS users update only one package] → Card only: artwork appears, and the sensor keeps the old spelling. Integration only: the spelling is fixed, and the card still shows the silhouette. Neither breaks anything. The release notes say to update both.
