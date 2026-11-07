## Why

[PR #14](https://github.com/Falkvinge/hassio-integration-perfectdraft-pro/pull/14) from @Aurel004 (aurel) adds a complete French translation, so French-language Home Assistant installs show the config flow, errors and entity names in French instead of English. The contributor runs it on his own instance and checked the AI-generated strings by hand; the maintainer had a native French speaker look at it too. It is a first contribution, so it ships exactly as submitted, with his authorship kept.

## What Changes

- Merge the PR's single commit (`704f55e`, authored by aurel) unchanged. It adds:
  - `custom_components/perfectdraft/translations/fr.json`, covering every key in `strings.json`.
  - `tests/test_translations.py`, which fails when `en.json` or `fr.json` has a different key structure from `strings.json`.
- No wording edits. "Marquer le fût changé" stays as submitted; it is correct, and shorter text suits the button label.
- Bump the integration to 0.4.6. The card has no translations and stays at 0.4.5, which the versioning rule allows (shared major.minor, patch may diverge).
- Record in `PROJECT_HYGIENE.md` that from now on every new or renamed UI string needs an English and a French entry, because the new test enforces exact key parity.
- Release v0.4.6 crediting @Aurel004.

Not in scope:

- Translated entity states or attributes. `strings.json` defines none, so there is nothing to translate.
- Other languages, or loosening the parity test to allow partial translations.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `hacs-packaging`: the "Translations" requirement covers English only. It now also requires a French translation and exact key parity between `strings.json` and every shipped translation file.

## Impact

- Users with Home Assistant set to French see French labels after updating. Existing entity IDs are kept in the entity registry and don't change; only display names do. Everyone else is unaffected.
- Contributors and agents: any change to `strings.json` must update `translations/en.json` and `translations/fr.json` in the same commit, or `tests/test_translations.py` fails.
- Files: `custom_components/perfectdraft/translations/fr.json` (new), `tests/test_translations.py` (new), `custom_components/perfectdraft/manifest.json` (version), `PROJECT_HYGIENE.md` (main checkout).
