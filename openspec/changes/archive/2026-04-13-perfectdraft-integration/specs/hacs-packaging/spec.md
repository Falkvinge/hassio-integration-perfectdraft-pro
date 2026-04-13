## ADDED Requirements

### Requirement: HACS-compliant repository structure
The repository SHALL follow the HACS custom integration layout so it can be installed via HACS "Custom repositories."

#### Scenario: Directory structure
- **WHEN** HACS scans the repository
- **THEN** the integration code SHALL be at `custom_components/perfectdraft/`
- **THEN** a `hacs.json` file SHALL exist at the repository root
- **THEN** a `manifest.json` SHALL exist at `custom_components/perfectdraft/manifest.json`

### Requirement: manifest.json with required fields
The `manifest.json` SHALL contain all fields required by both HA and HACS.

#### Scenario: Manifest contents
- **WHEN** HA loads the integration
- **THEN** `manifest.json` SHALL include: `domain` ("perfectdraft"), `name` ("PerfectDraft"), `version`, `documentation` (GitHub repo URL), `issue_tracker` (GitHub issues URL), `codeowners`, `config_flow: true`, `iot_class` ("cloud_polling"), and `requirements` (empty — aiohttp is provided by HA core)

### Requirement: hacs.json metadata
The `hacs.json` file SHALL provide HACS with integration metadata.

#### Scenario: HACS metadata contents
- **WHEN** HACS reads the repository metadata
- **THEN** `hacs.json` SHALL include `name` ("PerfectDraft"), `render_readme: true`, and `homeassistant` minimum version (if applicable)

### Requirement: Translations / strings
The integration SHALL provide English UI strings for the config flow and entities.

#### Scenario: Config flow strings
- **WHEN** the user interacts with the config flow
- **THEN** `strings.json` SHALL provide titles, descriptions, field labels, and error messages for all config flow steps (user, external, reauth)
- **THEN** `translations/en.json` SHALL mirror `strings.json`

### Requirement: Valid Python package
The `custom_components/perfectdraft/` directory SHALL be a valid Python package.

#### Scenario: Package structure
- **WHEN** HA imports the integration
- **THEN** `__init__.py` SHALL exist and define `async_setup_entry` and `async_unload_entry`
- **THEN** all platform modules (`sensor.py`, `image.py`) SHALL be importable
- **THEN** no external pip dependencies SHALL be required beyond what HA core provides
