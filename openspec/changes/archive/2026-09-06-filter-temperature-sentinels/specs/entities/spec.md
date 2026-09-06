## MODIFIED Requirements

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
