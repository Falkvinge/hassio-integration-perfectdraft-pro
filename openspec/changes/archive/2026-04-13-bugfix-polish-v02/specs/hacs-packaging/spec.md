## MODIFIED Requirements

### Requirement: README.md at repository root
The repository SHALL contain a README.md with installation and setup instructions.

#### Scenario: README content
- **WHEN** a user views the repository or HACS integration page
- **THEN** the README SHALL explain what the integration does
- **THEN** the README SHALL list the sensors provided
- **THEN** the README SHALL contain the exact console command for generating the verification token
- **THEN** the README SHALL explain that the token step looks more intimidating than it is

### Requirement: Correct documentation URLs
The manifest.json SHALL point to the actual repository.

#### Scenario: URL correctness
- **WHEN** HACS or HA reads the manifest
- **THEN** `documentation` SHALL point to the repo's README
- **THEN** `issue_tracker` SHALL point to the repo's issue tracker

### Requirement: Brand icon
The integration SHALL include a brand icon so HA displays it in the UI.

#### Scenario: Icon displayed
- **WHEN** the integration is installed and HA renders the device or integration page
- **THEN** the PerfectDraft glass icon SHALL be displayed
- **THEN** the icon SHALL be located at `custom_components/perfectdraft/brand/icon.png`

### Requirement: Version 0.2.0
The manifest.json version SHALL be bumped to 0.2.0.

#### Scenario: Version check
- **WHEN** HACS reads the manifest
- **THEN** the version field SHALL be `0.2.0`
