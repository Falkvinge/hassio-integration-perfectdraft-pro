## MODIFIED Requirements

### Requirement: Keg name sensor
The integration SHALL expose the name of the tapped beer, resolved from the keg product ID through a catalog bundled with the integration at `keg_catalog.json`. The catalog SHALL cover every keg the PerfectDraft app can select, including discontinued kegs that may still be fitted in a machine, and SHALL contain at least 115 product IDs.

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
