# Extraction Notes

This document records the extraction rules, source usage and normalisation
conventions applied when populating the capability database.

## Source usage policy

Primary sources are the Hardware Design manuals listed in `data/sources.yaml`.
For each model, its dedicated Hardware Design manual is preferred. When two
primary sources cover the same model (e.g. `SIM800H&SIM800L` combined manual
plus a dedicated `SIM800H` manual), the newer publication wins; if the
publication date is unknown, the higher document version is used.

Secondary sources (`tier: secondary`, `doc_type: at_command_manual`) are used
only when the primary Hardware Design manual is silent. This rule is a manual
extraction policy and is documented here; it is not automatically enforceable.

## Normalisation

- Temperatures are recorded in degrees Celsius as `number`.
- Voltages are recorded in Volts as `number` with the value normalised:
  `3.40` becomes `3.4`.
- Currents are recorded in milliamps as `number`.
- Frequencies are recorded in MHz as `number`.
- Humidity is recorded as `number` in percent (0-100).
- Baud rates are recorded as `integer` values in bps.

## FieldValue statuses

- `documented` - the value is stated directly in a source.
- `not_documented` - the source is silent about this capability.
- `not_supported` - the source explicitly states the capability is not present.
- `inferred` - the value is derived from an inference rule.
- `conflict` - two candidate sources disagree.
- `not_in_scope` - the capability is outside the project scope.

## `not_supported` value shapes

- boolean fields: `value: false`
- numeric fields: `value: 0`
- array fields: `value: []`
- string fields: `value: null`
- object leaf fields: `value: null`

## Empty arrays

`power.current_consumption.value: []` is allowed only when the source
explicitly states no consumption modes exist. When the source is silent,
`value: null` with `status: not_documented` is used.

## Scope split

- `pcm` (PCM hardware interface) is in scope.
- `audio` (codec / audio processing) is out of scope.
- `gnss.antenna_interface` is in scope.
- `antenna` (physical GSM/GPS antenna) is out of scope.
- `dimensions` is out of scope.