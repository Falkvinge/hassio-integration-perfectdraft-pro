## MODIFIED Requirements

### Requirement: Token step description
The config flow token step SHALL display instructions that do not trigger HA translation errors.

#### Scenario: Token step renders correctly
- **WHEN** the user reaches the token entry step
- **THEN** the description SHALL render without MALFORMED_ARGUMENT errors
- **THEN** the description SHALL direct the user to the README for the console command
- **THEN** the description SHALL mention the 2-minute token expiry
