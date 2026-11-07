## Context

See proposal.md for why. The machine reports a numeric product ID. The integration resolves it through `keg_catalog.json`, and the card joins on the same ID via `kegId` in `src/beer-catalog.ts`. `npm run check:catalog` fails when an integration ID has no card `kegId`.

`48180` is the highest ID so far, so it goes after `48134` (Kopparberg Crisp Apple). The card has no Camden stout entry and no `camden-stout` artwork. Card PR #2 supplies both: `src/assets/kegs/camden-stout.webp`, and an entry with style Stout, ABV 4.0 and dark colours.

Two names are in circulation for the same ID:

| Source | Name |
|---|---|
| Issue #9 / PR #10 / card PR #2 (MThomas564, keg fitted) | Camden Stout |
| brettjenkins fork, commit `3e4a2cc` | Camden Nitro Stout |

The PerfectDraft shop search did not render product names when checked on 2026-11-07, so it cannot break the tie. It is not authoritative under the catalog rule in any case.

## Goals / Non-Goals

**Goals:**

- The **Keg** sensor names `48180`, and the card shows its branding and artwork.
- MThomas564's contribution lands under his name.

**Non-Goals:**

- Reconciling the rest of the fork's catalog with ours.

## Decisions

**Land the change ourselves, crediting the contributor, rather than merging PR #10 and card PR #2.**
Both PRs need edits that would amount to rewriting them: key order, the README re-pad, the version clash, and a reference snapshot pinned to an unmerged commit. Asking a first-time contributor for three rounds of fixes costs more goodwill than it saves. Both commits carry `Co-authored-by: MThomas564 <noreply address from his GitHub commits>`. The closing comments on the PRs link the commits and the release.

**Name: "Camden Stout" unless the contributor says otherwise.**
He has the keg fitted, which is the bar the catalog sets. The fork's "Nitro" may well be correct, since Camden does sell a nitro stout. So we ask him once, on PR #10, what the keg or the PerfectDraft app calls it. If he hasn't answered by the time `fix-cognito-signin` is ready to ship, we ship "Camden Stout" rather than hold the sign-in fix. A later rename is a one-line patch with no entity churn.

**Card entry: take PR #2's artwork and fields, and verify the ABV.**
We use slug `camden-stout`, brewery "Camden Town Brewery", style "Stout", colours as in PR #2, `imagePath: kegImage("camden-stout")`, and `kegId: "48180"`. The ABV of 4.0 is checked against Camden's or PerfectDraft's product page before landing. The card displays it, and a stout at exactly the session-pale ABV is worth a second look. The artwork file comes from PR #2's head commit unchanged. `dist/` is rebuilt with our `npm run build`, not taken from the PR.

**Versions: no separate integration bump; card 0.4.3.**
`fix-cognito-signin` owns the integration's 0.3.5 bump. The card bumps 0.4.2 → 0.4.3 in `package.json`, `CARD_VERSION` and `EDITOR_VERSION`. PR #2's `package-lock.json` jump from 0.3.1 is a stale lockfile, so we regenerate the lockfile rather than copy it.

## Risks / Trade-offs

- **The name is wrong.** A one-line catalog patch fixes it later. Entity IDs do not depend on the name.
- **The card snapshot is pinned before the integration commit exists.** Re-sync `_upstreamCommit` after the integration commit is made on its branch, and re-check after any rebase.
- **HACS users update only one package.** If they update only the integration, the sensor names the keg and the card falls back to the sensor's name without artwork. If they update only the card, the sensor stays blank, but the card brands `48180` once an entity reports it. The release notes tell people to update both, which they need to anyway for the sign-in fix.
