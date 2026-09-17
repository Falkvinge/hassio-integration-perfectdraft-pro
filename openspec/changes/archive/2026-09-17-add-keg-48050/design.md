## Context

The machine reports a numeric product ID. The integration resolves it through `keg_catalog.json`; the companion card joins on the same ID via `kegId`. `48050` sat in a hole in the 47–48xxx cluster (between Siren Lumina IPA `48024` and Northern Monk Faith `48061`) that the 114-entry snapshot never included.

`GET /api/products/{id}` still returns `{id}` only. Provenance is the reporter's fitted keg plus their confirmation of the wrap.

## Decisions

**List 48050 as "Anheuser-Busch Bud", not "Budweiser".**
The two wraps are visually distinct (Budweiser script vs Anheuser-Busch Bud on a white band). The reporter chose the DE/AT option. `31747` stays "Budweiser". Duplicate display names were considered and rejected: the sensor is "what is printed on this keg".

**Reuse the card's existing `bud` entry rather than adding a second beer.**
`src/beer-catalog.ts` already had `name: "Anheuser-Busch Bud"` with `kegs/bud.webp` and no `kegId`. Binding `48050` completes the join. The card's one-ID-per-entry model holds.

**Patch releases, not a behaviour-contract bump.**
Catalog growth does not change requirements existing users depend on. Integration `0.3.3`, card `0.4.1`.

## Risks / Trade-offs

**A later keg uses 48050 for a different beer** → Same risk as every catalog row. The ID was observed from a machine, which is the established bar.

**HACS users update only one of the two packages** → Integration-only: the **Keg** sensor names it, the card falls through to name matching and still resolves because the names now match. Card-only: the **Keg** sensor stays blank, the card can still brand `48050` if that sensor exists from an older integration that reports the ID. Release notes tell people to update both.
