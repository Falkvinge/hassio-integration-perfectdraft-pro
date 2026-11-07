## Context

The machine reports a numeric product ID. The integration resolves it through `keg_catalog.json`. The companion card (`hassio-component-perfectdraft-pro`) joins on the same ID via `kegId` in `src/beer-catalog.ts`, and only if that misses does it fall through to the sensor's name. `scripts/check-catalog.mjs` fails when an integration ID has no card `kegId`.

`47792` is absent from both catalogs. Issue #7 names the fitted keg Camden Eazy. The card already has that beer:

```
slug: "camden-eazy", name: "Camden Eazy", imagePath: kegs/camden-eazy.webp, kegId: "47629"
```

The integration lists that other ID as `"47629": "Camden Eazy IPA"`. The card prefers `kegId`, so a machine reporting `47629` already shows Camden Eazy with the existing graphic. `47792` follows Old Speckled Hen `47774` and precedes Corona Ligera `47816`.

`GET /api/products/{id}` still returns `{id}` only. Provenance is the reporter's fitted keg and the name in the issue title.

## Goals / Non-Goals

**Goals:**

- The **Keg** sensor reports Camden Eazy for product ID `47792`.
- The card resolves `47792` by `kegId` to that same branding and the existing keg graphic.
- `47629` keeps its current integration name and card binding.

**Non-Goals:**

- Deciding whether `47629` and `47792` are one recipe or two wraps. Only `47792` was observed for this issue.
- A second keg photo.
- A card model that stores more than one product ID on a single entry.

## Decisions

**List 47792 as "Camden Eazy", and leave 47629 as "Camden Eazy IPA".**
The reporter's name is Camden Eazy. Copying the IPA suffix from `47629` would label a different observed ID. Renaming `47629` would change a keg this issue did not report.

**Add a second card entry that reuses `kegs/camden-eazy.webp`. Do not draw a new graphic.**
`camden-eazy` already owns `kegId` `47629`, and the catalog is one ID per entry (`kegIdIndex` and `check-catalog` both assume that). A new slug, `camden-eazy-47792`, carries the same name, brewery, style, ABV, colours, and `imagePath: kegImage("camden-eazy")`. No new asset file.

Allowing `kegId` to be a list was considered and rejected. It would change the index, the coverage check, and the editor for a case the previous keg addition (`48050`) kept as a separate row.

**Name-index collision is acceptable.**
`nameIndex` keeps the last entry for a given display name, so "Camden Eazy" resolves to whichever row is registered later. That path is unused when a product ID is present: `_updateDetectedBeer` tries `getBeerByKegId` first. The beer picker will list Camden Eazy twice; both rows look the same.

**Patch releases.**
Catalog growth does not change requirements existing users depend on, aside from the floor ratchet. Integration `0.3.4`, card `0.4.2`.

## Risks / Trade-offs

**47792 is a different wrap than the existing Camden Eazy photo** → The card shows the current Camden Eazy keg until someone supplies a distinct photo. Same bar as every other reused asset.

**A later keg uses 47792 for a different beer** → Same risk as every catalog row. The ID was observed from a machine.

**HACS users update only one package** → Integration-only: the **Keg** sensor names it, and the card's name fallback still hits the existing Camden Eazy entry because the names match. Card-only: the sensor stays blank, and the card can brand `47792` once that ID is on an entity. Release notes tell people to update both.

**Two picker rows named Camden Eazy** → Accepted. Merging them would either drop `47629` or change the one-ID model.
