## Requirements

### Requirement: HA Device per PerfectDraft machine
Each PerfectDraft machine SHALL be represented as an HA Device with manufacturer "PerfectDraft", model "Pro", firmware version, and serial number from the API.

#### Scenario: Device registration
- **WHEN** entities are created
- **THEN** each entity SHALL declare `DeviceInfo` with identifiers based on the machine ID
- **THEN** the device SHALL display the firmware version and serial number

### Requirement: Temperature sensor
The integration SHALL expose the beer temperature as a sensor with device class TEMPERATURE. The sensor SHALL report a value only when the API supplies a plausible reading. A reading outside the closed range -20 °C to 50 °C SHALL be treated as a firmware sentinel rather than a measurement, because the probe reports -128 (`0x80` read as a signed 8-bit integer) before it has initialised.

#### Scenario: Temperature reading
- **WHEN** the coordinator has data AND `details.displayedBeerTemperatureInCelsius` is within the plausible range and is not 0
- **THEN** the sensor SHALL report that value
- **THEN** it SHALL have unit °C, state class MEASUREMENT, and suggested display precision 0

#### Scenario: Fallback to details.temperature
- **WHEN** `details.displayedBeerTemperatureInCelsius` is absent, 0, or outside the plausible range
- **AND** `details.temperature` is within the plausible range
- **THEN** the sensor SHALL report `details.temperature`

#### Scenario: Uninitialised probe reports a sentinel
- **WHEN** the machine's refrigeration has just started and a temperature field reads -128
- **THEN** that field SHALL NOT be reported as a measurement

#### Scenario: Both sources implausible
- **WHEN** neither `details.displayedBeerTemperatureInCelsius` nor `details.temperature` yields a value within the plausible range
- **THEN** the sensor SHALL report None, so Home Assistant records the state as unknown and excludes it from long-term statistics
- **THEN** the entity SHALL remain available, because the coordinator poll succeeded and only the reading is missing

#### Scenario: Non-numeric value
- **WHEN** a temperature field holds a value that cannot be converted to a float
- **THEN** that field SHALL be treated as absent and SHALL NOT raise an error

### Requirement: Keg remaining sensor
The integration SHALL expose the keg's remaining volume as a percentage.

#### Scenario: Volume calculation
- **WHEN** the coordinator has data
- **THEN** the sensor SHALL report `details.kegVolume / 6.0 * 100` rounded to 1 decimal
- **THEN** it SHALL have unit %, state class MEASUREMENT, and icon mdi:keg

### Requirement: Keg product ID sensor
The integration SHALL expose the numeric product ID of the keg currently fitted in the machine, extracted from the API's `kegActive.keg` resource reference.

#### Scenario: Product ID extracted from resource reference
- **WHEN** the coordinator has data AND `kegActive.keg` holds a resource reference
- **THEN** the sensor SHALL report the trailing path segment of that reference as an integer
- **THEN** it SHALL have icon mdi:barcode

#### Scenario: No keg fitted
- **WHEN** `kegActive.keg` is absent or empty
- **THEN** the sensor SHALL report no value

#### Scenario: Reference is not numeric
- **WHEN** the trailing path segment of `kegActive.keg` cannot be parsed as an integer
- **THEN** the sensor SHALL report no value and SHALL NOT raise

### Requirement: Keg name sensor
The integration SHALL expose the name of the tapped beer, resolved from the keg product ID through a catalog bundled with the integration at `keg_catalog.json`. The catalog SHALL cover every keg the PerfectDraft app can select, including discontinued kegs that may still be fitted in a machine, and SHALL contain at least 114 product IDs.

Catalog entries SHALL be observed directly from a machine reporting that product ID rather than inferred from shop listings, because the product IDs cannot be queried in bulk from the API. Entry names SHALL be the beer's name only, excluding shop-listing artefacts such as pack size, "Short Date" prefixes, or best-before dates.

#### Scenario: Known product ID resolves to a name
- **WHEN** the keg product ID is present in the catalog
- **THEN** the sensor SHALL report the catalog's name for that ID
- **THEN** it SHALL have icon mdi:beer

#### Scenario: Unknown product ID
- **WHEN** the keg product ID is not present in the catalog
- **THEN** the sensor SHALL report no value

#### Scenario: No keg fitted
- **WHEN** no keg product ID can be determined
- **THEN** the sensor SHALL report no value

#### Scenario: Catalog unreadable or malformed
- **WHEN** `keg_catalog.json` is missing or cannot be parsed
- **THEN** the integration SHALL treat the catalog as empty and continue loading
- **THEN** the keg name sensor SHALL report no value while every other entity SHALL be unaffected

#### Scenario: Catalog format
- **WHEN** the catalog file is read
- **THEN** it SHALL be a flat JSON object mapping the product ID as a string key to the display name as a string value
- **THEN** keys SHALL be ordered numerically

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
The integration SHALL track keg freshness as a 30-day countdown from insertion, detected client-side and persisted across restarts. A keg change SHALL be detected by monitoring the coordinator data for a pour-count reset OR an upward jump in keg volume between consecutive readings, so that a swap is recognized even when the pour count never reads 0 (e.g. the user pours immediately after swapping).

#### Scenario: New keg detected via pour reset
- **WHEN** `details.numberOfPoursSinceStartup` is 0 AND `details.kegVolume` is greater than 5.5L AND the previous pour count was not 0
- **THEN** the sensor SHALL record the current UTC timestamp as the keg insertion date

#### Scenario: New keg detected via refill to near-full
- **WHEN** a previous volume reading exists AND the previous remaining volume was below 80% of capacity AND the current remaining volume is at least 95% of capacity
- **THEN** the sensor SHALL record the current UTC timestamp as the keg insertion date

#### Scenario: New keg detected via large volume jump
- **WHEN** a previous volume reading exists AND the current remaining volume exceeds the previous remaining volume by at least 50 percentage points of capacity (a gain of at least 3.0L)
- **THEN** the sensor SHALL record the current UTC timestamp as the keg insertion date

#### Scenario: No false trigger on first reading
- **WHEN** the integration produces its first volume reading after install or restart and no previous volume reading is available
- **THEN** the volume-jump triggers SHALL NOT fire

#### Scenario: Detection never moves the date backward
- **WHEN** any detection trigger fires
- **THEN** the sensor SHALL set the insertion date to the current time only
- **THEN** the sensor SHALL update its tracked previous pour count and previous volume to the current readings so the same event does not re-trigger on the next update

#### Scenario: Freshness countdown
- **WHEN** a keg insertion date is known
- **THEN** the sensor SHALL report `30 - days_since_insertion`, minimum 0
- **THEN** it SHALL have unit d and icon mdi:calendar-clock

#### Scenario: No insertion date known
- **WHEN** no keg insertion has been detected since the integration was installed
- **THEN** the sensor SHALL report as unavailable

#### Scenario: HA restart
- **WHEN** Home Assistant restarts
- **THEN** the sensor SHALL restore the keg insertion date, last pour count, and last volume from the previous session's state attributes

### Requirement: Manual keg-change button
The integration SHALL expose a button entity that, when pressed, records the current time as the keg insertion date, providing a deterministic manual override for keg-change detection.

#### Scenario: Button press records insertion
- **WHEN** the user presses the "Mark Keg Changed" button
- **THEN** the keg freshness sensor SHALL set the keg insertion date to the current UTC timestamp
- **THEN** the freshness countdown SHALL report 30 days

#### Scenario: Override rebaselines detection
- **WHEN** the button is pressed
- **THEN** the sensor SHALL update its tracked previous pour count and previous volume to the latest readings so automatic detection does not immediately re-fire

#### Scenario: Button entity presentation
- **WHEN** entities are created
- **THEN** the integration SHALL register the `button` platform
- **THEN** the button SHALL belong to the same device as the machine's sensors
- **THEN** the button SHALL have a stable unique ID following the `{machine_id}_{entity_key}` pattern and a translated name "Mark Keg Changed"

### Requirement: Entity unique IDs
All entities SHALL have stable unique IDs derived from the machine ID and entity type.

#### Scenario: Unique ID format
- **WHEN** entities are created
- **THEN** each entity's unique ID SHALL follow the pattern `{machine_id}_{entity_key}`

### Requirement: Entity name translations
All entities SHALL have translated names via `translation_key` and corresponding entries in `strings.json` and `translations/en.json`.

#### Scenario: Names displayed
- **WHEN** HA renders the entity list
- **THEN** each sensor SHALL display its translated name (Temperature, Keg Remaining, Keg Product, Keg, Connection, Door, Pours, Last Pour, Firmware, Mode, Keg Freshness)
