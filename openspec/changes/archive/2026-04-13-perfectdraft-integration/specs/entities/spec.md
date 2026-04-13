## ADDED Requirements

### Requirement: DataUpdateCoordinator for shared polling
The integration SHALL use a single `DataUpdateCoordinator` per config entry that polls the PerfectDraft API on a configurable interval. All entities SHALL read from the coordinator's shared data.

#### Scenario: Coordinator polls successfully
- **WHEN** the update interval elapses
- **THEN** the coordinator SHALL call the API client to fetch the user profile and machine details
- **THEN** it SHALL store the full machine details response in `coordinator.data`
- **THEN** all entities SHALL update their state from `coordinator.data`

#### Scenario: Coordinator handles API error
- **WHEN** the API returns an error during a poll
- **THEN** the coordinator SHALL raise `UpdateFailed` so HA marks entities as unavailable
- **THEN** the coordinator SHALL use HA's built-in exponential backoff for retries

#### Scenario: Coordinator handles auth failure
- **WHEN** the API client raises `AuthenticationError` during a poll (refresh token expired)
- **THEN** the coordinator SHALL trigger HA's reauth flow for the config entry

### Requirement: HA Device per PerfectDraft machine
Each PerfectDraft machine SHALL be represented as an HA Device. All entities for that machine SHALL be children of the device.

#### Scenario: Device registration
- **WHEN** the integration sets up entities
- **THEN** each entity SHALL declare a `DeviceInfo` with identifiers based on the machine ID
- **THEN** the device SHALL have manufacturer "PerfectDraft", model "Pro", and a name derived from the machine data or user email

### Requirement: Temperature sensor
The integration SHALL expose the machine's current temperature as a sensor entity.

#### Scenario: Temperature reading
- **WHEN** the coordinator has fresh data
- **THEN** the temperature sensor SHALL report the current temperature value
- **THEN** the sensor SHALL have `device_class` set to `TEMPERATURE`
- **THEN** the sensor SHALL have `native_unit_of_measurement` set to `°C`
- **THEN** the sensor SHALL have `state_class` set to `MEASUREMENT`

### Requirement: Percent remaining sensor
The integration SHALL expose the keg's remaining volume as a percentage sensor.

#### Scenario: Volume remaining reading
- **WHEN** the coordinator has fresh data
- **THEN** the percent remaining sensor SHALL report the remaining volume as a percentage (0–100)
- **THEN** the sensor SHALL have `native_unit_of_measurement` set to `%`
- **THEN** the sensor SHALL have `state_class` set to `MEASUREMENT`
- **THEN** the sensor SHALL have an appropriate icon (e.g., `mdi:keg`)

#### Scenario: No keg loaded
- **WHEN** the machine reports no keg is loaded
- **THEN** the sensor SHALL report state as `None` / unavailable

### Requirement: Days until expiry sensor
The integration SHALL expose the number of days until the current keg expires as a sensor.

#### Scenario: Expiry countdown
- **WHEN** the coordinator has fresh data and a keg is loaded
- **THEN** the days-to-expiry sensor SHALL report an integer number of days
- **THEN** the sensor SHALL have `native_unit_of_measurement` set to `d` (days)
- **THEN** the sensor SHALL have an appropriate icon (e.g., `mdi:calendar-clock`)

#### Scenario: No keg loaded
- **WHEN** the machine reports no keg is loaded
- **THEN** the sensor SHALL report state as `None` / unavailable

### Requirement: Current keg name sensor
The integration SHALL expose the name/brand of the currently loaded keg as a sensor.

#### Scenario: Keg identified
- **WHEN** the coordinator has fresh data and a keg is loaded
- **THEN** the keg name sensor SHALL report the keg's brand/name as a string state
- **THEN** the sensor SHALL have an appropriate icon (e.g., `mdi:beer`)

#### Scenario: No keg loaded
- **WHEN** the machine reports no keg is loaded
- **THEN** the sensor SHALL report state as "No keg" or `None`

### Requirement: Keg image entity
The integration SHALL expose the current keg's artwork as an HA image entity.

#### Scenario: Keg image available
- **WHEN** the coordinator has fresh data and the machine details include an image URL for the keg
- **THEN** the image entity SHALL serve that image via HA's image platform
- **THEN** the image entity SHALL update when the keg changes

#### Scenario: No keg image available
- **WHEN** no image URL is present in the machine data
- **THEN** the image entity SHALL report as unavailable

### Requirement: Entity unique IDs
All entities SHALL have stable unique IDs derived from the machine ID and entity type, so they survive HA restarts and reconfigurations.

#### Scenario: Unique ID format
- **WHEN** entities are created
- **THEN** each entity's unique ID SHALL follow the pattern `{machine_id}_{entity_type}` (e.g., `abc123_temperature`, `abc123_percent_remaining`)
