## Requirements

### Requirement: HACS-compliant repository structure
The repository SHALL follow the HACS custom integration layout for installation via HACS custom repositories on GitHub.

#### Scenario: Directory structure
- **WHEN** HACS scans the repository
- **THEN** the integration code SHALL be at `custom_components/perfectdraft/`
- **THEN** `hacs.json` SHALL exist at the repository root
- **THEN** `manifest.json` SHALL exist at `custom_components/perfectdraft/manifest.json`
- **THEN** `README.md` SHALL exist at the repository root

### Requirement: manifest.json
The manifest SHALL contain all fields required by HA and HACS.

#### Scenario: Manifest contents
- **WHEN** HA loads the integration
- **THEN** `manifest.json` SHALL include: `domain` ("perfectdraft"), `name` ("PerfectDraft"), `version` (semver), `documentation` (GitHub repo URL), `issue_tracker` (GitHub issues URL), `codeowners` (["@Falkvinge"]), `config_flow: true`, `iot_class` ("cloud_polling"), and `requirements` (empty)

### Requirement: hacs.json
The `hacs.json` SHALL provide HACS with integration metadata.

#### Scenario: HACS metadata
- **WHEN** HACS reads the repository
- **THEN** `hacs.json` SHALL include `name` ("PerfectDraft") and `render_readme: true`

### Requirement: Brand icon
The integration SHALL include a brand icon so HA displays it in the UI.

#### Scenario: Icon displayed
- **WHEN** the integration is installed on HA 2026.3+
- **THEN** `custom_components/perfectdraft/brand/icon.png` SHALL exist as a 192x192 RGBA PNG
- **THEN** the icon SHALL be the PerfectDraft glass silhouette from the official app

### Requirement: README with setup instructions
The README SHALL contain complete installation and setup instructions including the token generation command.

#### Scenario: README content
- **WHEN** a user reads the README
- **THEN** it SHALL list all sensors with descriptions and units
- **THEN** it SHALL contain HACS and manual installation instructions
- **THEN** it SHALL contain the exact `grecaptcha.enterprise.execute` console command for token generation
- **THEN** it SHALL note that no login is needed on the PerfectDraft website
- **THEN** it SHALL note the 2-minute token expiry

### Requirement: GitHub mirror
The repository SHALL be mirrored to GitHub for HACS compatibility, since HACS requires the GitHub API.

#### Scenario: Dual-remote push
- **WHEN** changes are committed
- **THEN** they SHALL be pushed to both the primary Gitea repo (origin) and the GitHub mirror (github)

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
