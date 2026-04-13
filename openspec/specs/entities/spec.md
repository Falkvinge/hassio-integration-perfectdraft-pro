## Requirements

### Requirement: HA Device per PerfectDraft machine
Each PerfectDraft machine SHALL be represented as an HA Device with manufacturer "PerfectDraft", model "Pro", firmware version, and serial number from the API.

#### Scenario: Device registration
- **WHEN** entities are created
- **THEN** each entity SHALL declare `DeviceInfo` with identifiers based on the machine ID
- **THEN** the device SHALL display the firmware version and serial number

### Requirement: Temperature sensor
The integration SHALL expose the beer temperature as a sensor with device class TEMPERATURE.

#### Scenario: Temperature reading
- **WHEN** the coordinator has data
- **THEN** the sensor SHALL report `details.displayedBeerTemperatureInCelsius` (falling back to `details.temperature`)
- **THEN** it SHALL have unit °C, state class MEASUREMENT, and suggested display precision 0

### Requirement: Keg remaining sensor
The integration SHALL expose the keg's remaining volume as a percentage.

#### Scenario: Volume calculation
- **WHEN** the coordinator has data
- **THEN** the sensor SHALL report `details.kegVolume / 6.0 * 100` rounded to 1 decimal
- **THEN** it SHALL have unit %, state class MEASUREMENT, and icon mdi:keg

### Requirement: Connection sensor
The integration SHALL expose the machine's connectivity status.

#### Scenario: Connection state
- **WHEN** `details.connectedState` is true
- **THEN** the sensor SHALL report "Connected"
- **WHEN** `details.connectedState` is false
- **THEN** the sensor SHALL report "Disconnected"

### Requirement: Door sensor
The integration SHALL expose the machine's door state.

#### Scenario: Door state
- **WHEN** `details.doorClosed` is true
- **THEN** the sensor SHALL report "Closed"
- **WHEN** `details.doorClosed` is false
- **THEN** the sensor SHALL report "Open"

### Requirement: Pours sensor
The integration SHALL expose the pour count since keg insertion.

#### Scenario: Pour count
- **WHEN** the coordinator has data
- **THEN** the sensor SHALL report `details.numberOfPoursSinceStartup` as an integer
- **THEN** it SHALL have state class TOTAL_INCREASING and icon mdi:beer

### Requirement: Last pour sensor
The integration SHALL expose the volume of the most recent pour.

#### Scenario: Last pour volume
- **WHEN** `details.volumeOfLastPour` is greater than 0
- **THEN** the sensor SHALL report the value converted from litres to millilitres (multiplied by 1000, rounded)
- **THEN** it SHALL have unit mL and icon mdi:glass-mug-variant

#### Scenario: No pour recorded
- **WHEN** `details.volumeOfLastPour` is 0 or null
- **THEN** the sensor SHALL report None

### Requirement: Mode sensor
The integration SHALL expose the current operating mode.

#### Scenario: Mode reading
- **WHEN** the coordinator has data
- **THEN** the sensor SHALL report `setting.mode` (e.g., "standard", "eco")

### Requirement: Firmware sensor
The integration SHALL expose the firmware version, disabled by default.

#### Scenario: Firmware reading
- **WHEN** the coordinator has data
- **THEN** the sensor SHALL report `details.firmwareVersion`
- **THEN** the entity SHALL be disabled by default in the entity registry

### Requirement: Keg freshness sensor
The integration SHALL track keg freshness as a 30-day countdown from insertion, detected client-side and persisted across restarts.

#### Scenario: New keg detected
- **WHEN** `details.numberOfPoursSinceStartup` is 0 AND `details.kegVolume` is greater than 5.5L AND the previous pour count was not 0
- **THEN** the sensor SHALL record the current UTC timestamp as the keg insertion date

#### Scenario: Freshness countdown
- **WHEN** a keg insertion date is known
- **THEN** the sensor SHALL report `30 - days_since_insertion`, minimum 0
- **THEN** it SHALL have unit d and icon mdi:calendar-clock

#### Scenario: No insertion date known
- **WHEN** no keg insertion has been detected since the integration was installed
- **THEN** the sensor SHALL report as unavailable

#### Scenario: HA restart
- **WHEN** Home Assistant restarts
- **THEN** the sensor SHALL restore the keg insertion date and last pour count from the previous session's state attributes

### Requirement: Entity unique IDs
All entities SHALL have stable unique IDs derived from the machine ID and entity type.

#### Scenario: Unique ID format
- **WHEN** entities are created
- **THEN** each entity's unique ID SHALL follow the pattern `{machine_id}_{entity_key}`

### Requirement: Entity name translations
All entities SHALL have translated names via `translation_key` and corresponding entries in `strings.json` and `translations/en.json`.

#### Scenario: Names displayed
- **WHEN** HA renders the entity list
- **THEN** each sensor SHALL display its translated name (Temperature, Keg Remaining, Connection, Door, Pours, Last Pour, Firmware, Mode, Keg Freshness)
