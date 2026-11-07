## MODIFIED Requirements

### Requirement: Translations
The integration SHALL provide English and French UI strings for all config flow steps, errors, abort reasons, options, and entity names. Every shipped translation file SHALL have exactly the same key structure as `strings.json`.

#### Scenario: Translation files
- **WHEN** HA renders the integration UI
- **THEN** `strings.json` and `translations/en.json` SHALL provide labels for all steps, fields, errors, and entity names
- **THEN** descriptions SHALL not contain curly braces (parsed as translation placeholders) or newlines (cause MALFORMED_ARGUMENT)

#### Scenario: French UI
- **WHEN** HA renders the integration UI with its language set to French
- **THEN** `translations/fr.json` SHALL provide French labels for all steps, fields, errors, abort reasons, options, and entity names
- **THEN** each French string SHALL use the same `{placeholder}` names as its English counterpart

#### Scenario: Key parity
- **WHEN** a key is added to, renamed in, or removed from `strings.json`
- **THEN** `translations/en.json` and `translations/fr.json` SHALL be updated to the same key structure in the same change
- **THEN** the test suite SHALL fail if any of the three files has a key the others lack
