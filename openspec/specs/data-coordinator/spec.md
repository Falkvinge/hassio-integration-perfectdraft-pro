## Requirements

### Requirement: Single DataUpdateCoordinator per config entry
The integration SHALL use one `PerfectDraftDataUpdateCoordinator` per config entry that polls the API on a configurable interval. All entities SHALL read from the coordinator's shared data.

#### Scenario: Coordinator polls successfully
- **WHEN** the update interval elapses
- **THEN** the coordinator SHALL call `get_machine_details(machine_id)` using the machine ID from the config entry
- **THEN** it SHALL store the full response in `coordinator.data` with an added `_machine_id` key

#### Scenario: Machine ID not in config entry
- **WHEN** the config entry has no machine ID
- **THEN** the coordinator SHALL call `get_user_profile()` to discover the machine ID from `perfectdraftMachines[0].id`
- **THEN** if no machines are found, it SHALL raise `UpdateFailed`

#### Scenario: Authentication failure during poll
- **WHEN** the API client raises `AuthenticationError`
- **THEN** the coordinator SHALL raise `ConfigEntryAuthFailed` to trigger HA's reauth flow

#### Scenario: API or connection error during poll
- **WHEN** the API client raises `PerfectDraftApiError` or `PerfectDraftConnectionError`
- **THEN** the coordinator SHALL raise `UpdateFailed` so HA marks entities as unavailable and retries with backoff

### Requirement: Dynamic polling interval
The coordinator SHALL support changing the polling interval at runtime via config entry options.

#### Scenario: Options updated
- **WHEN** the user changes the polling interval in integration options
- **THEN** the coordinator SHALL update its `update_interval` to the new value
- **THEN** the minimum interval SHALL be 60 seconds
- **THEN** the default interval SHALL be 900 seconds (15 minutes)
