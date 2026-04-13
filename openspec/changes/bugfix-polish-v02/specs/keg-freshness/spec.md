## ADDED Requirements

### Requirement: Detect new keg insertion
The integration SHALL detect when a new keg is inserted by monitoring the coordinator data for a reset in pour count combined with a near-full keg volume.

#### Scenario: New keg detected
- **WHEN** `numberOfPoursSinceStartup` drops to 0 AND `kegVolume` is greater than 5.5L
- **THEN** the integration SHALL record the current timestamp as the keg insertion date
- **THEN** the integration SHALL persist this timestamp using HA's RestoreEntity mechanism

#### Scenario: HA restart with existing keg
- **WHEN** Home Assistant restarts and a persisted keg insertion date exists
- **THEN** the integration SHALL restore the keg insertion date from the previous session

#### Scenario: No keg history available
- **WHEN** the integration starts for the first time with no persisted insertion date
- **THEN** the keg freshness sensor SHALL report as unavailable until a new keg is detected

### Requirement: Keg freshness countdown sensor
The integration SHALL expose a sensor showing the number of days remaining until the keg's 30-day freshness period expires.

#### Scenario: Active keg with known insertion date
- **WHEN** a keg insertion date is known
- **THEN** the sensor SHALL report `30 - (days since insertion)` as an integer
- **THEN** the sensor SHALL have `native_unit_of_measurement` set to `d` (days)
- **THEN** the sensor SHALL have an appropriate icon (e.g., `mdi:calendar-clock`)

#### Scenario: Freshness expired
- **WHEN** more than 30 days have passed since keg insertion
- **THEN** the sensor SHALL report 0

#### Scenario: No insertion date known
- **WHEN** no keg insertion date has been recorded or restored
- **THEN** the sensor SHALL report as unavailable
