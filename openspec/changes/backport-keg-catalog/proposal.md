## Why

The bundled keg-name catalog on `master` has 86 entries. @brettjenkins' fork has 114, and the extra 28 are kegs the PerfectDraft app can actually select — so today a user with a Kopparberg Crisp Apple, a Leffe Prestige, a Kwak Rouge or any of the three Diekirchs gets a blank `Keg` sensor. Four of the 86 names we do ship are also wrong rather than merely styled differently, including one beer that no longer exists under that name.

The data landed on the fork ten days before PR #2 was cut, so it was never part of what we merged. It is pure data with no code change, and every ID was observed directly from a machine rather than inferred.

Separately, PR #2 shipped the `Keg` and `Keg Product` sensors and the catalog file itself without ever updating `openspec/specs/entities/spec.md`. There is currently no requirement anywhere describing how a product ID resolves to a beer name, which means the catalog's behaviour — including what happens for an unmapped ID — is unspecified. That gap has to close here, because the catalog requirement has nothing to attach to otherwise.

## What Changes

- Replace `custom_components/perfectdraft/keg_catalog.json` with the fork's 114-entry version: 28 added IDs, 4 corrected names, existing formatting and numeric key order preserved, trailing newline added.
- Correct four names that are factually wrong on `master`:
  - `32814` "Birra Del Borgo Lisa" → "Romola" (the beer was renamed; we display a product that no longer exists)
  - `44331` "Short Date Ninkasi Flower Lager 6L Keg BBE June 2024" → "Ninkasi Flower Lager"
  - `44536` "Short Date Tiny Rebel Stay Puft 6L Keg BBE August 2024" → "Tiny Rebel Stay Puft"
  - `43235` "Corona Cero (0.0% abv) 6L Keg" → "Corona Cero (0.0% abv)"
- Leave the eleven styling-only differences (`Trooper`/`TROOPER`, `St`/`Saint Feuillien`) alone. These are display names and the current spellings are the ones the shop uses.
- Retrofit the missing `entities` requirements for the `Keg` and `Keg Product` sensors that PR #2 introduced, including the unmapped-ID behaviour and the catalog's provenance constraint.
- Add the stale `Keg` and `Keg Product` names to the entity-name-translations scenario, which still lists only the pre-PR-#2 sensor set.

Not in scope, and deliberately so:

- The fork's `hacs.json` without the `homeassistant: 2024.11.0` floor. That floor is ours, added by `0f3b4c2` because the reauth helpers need core 2024.11. The fork simply predates it.
- The fork's `0.4.1` manifest version. `0f3b4c2` renumbered to `0.3.1` on purpose and recorded why; the fork kept climbing from the `0.4.0` that PR #2 introduced and was never released.
- Changing what an unmapped ID reports. Making the sensor fall back to the raw product ID (so users can report unlisted kegs) is a behaviour change with its own design question and belongs in its own change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `entities`: adds a `Keg name sensor` requirement covering catalog-backed product-ID resolution, the unmapped-ID and no-keg cases, and the observed-not-inferred constraint on catalog entries; adds a `Keg product ID sensor` requirement; updates the entity-name-translations scenario to include both sensors.

## Impact

- `custom_components/perfectdraft/keg_catalog.json` — data only, 86 → 114 entries.
- `custom_components/perfectdraft/manifest.json` — version bump.
- `openspec/specs/entities/spec.md` — via the delta spec, on sync.
- No change to `sensor.py`, `keg_detection.py`, `coordinator.py`, `api.py` or `const.py`. `_load_keg_catalog` and `_get_keg_name` already read the file generically and need no edit.
- No migration and no entity churn: unique IDs, entity keys and translation keys are untouched. Users with one of the 28 previously-unmapped kegs see the `Keg` sensor change from unknown to a name on the next poll. Users with one of the 4 corrected IDs see the name change.
- Risk is confined to a wrong name in the catalog. There is no failure mode worse than a mislabelled sensor, and `_load_keg_catalog` already degrades to an empty dict on malformed JSON.
