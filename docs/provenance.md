# Provenance

This document records the shape and semantics of the data model.

## FieldValue

Every capability leaf is stored as a `FieldValue`:

```yaml
value: <scalar|array|object|null>
status: documented | not_documented | not_supported | inferred | conflict | not_in_scope
source_id: <string|null>
source_ref:
  page: <number|null>
  section: <string|null>
  table: <string|null>
  figure: <string|null>
confidence: high | medium | low | null
reason: <string|null>
notes: <string|null>
inference_source: <string|null>
inference_rule: <string|null>
applicable_firmware: <string|null>
```

## Statuses

- `documented`: value stated directly in a source.
- `not_documented`: source is silent.
- `not_supported`: source explicitly states the capability is absent.
- `inferred`: derived via an inference rule.
- `conflict`: unresolved conflict (requires `metadata.conflicts` entry).
- `not_in_scope`: capability outside project scope (all other fields null).

## Confidence guide

- `high`: direct quote from a table or explicit text.
- `medium`: extracted from continuous prose or combining sentences.
- `low`: interpretation, inference, or reading from a diagram.
- `null`: only allowed when `status: not_in_scope`.

## `not_supported` value shapes

- boolean leaf -> `value: false`
- numeric leaf -> `value: 0`
- array leaf   -> `value: []`
- string leaf  -> `value: null`
- object leaf  -> `value: null`
- group node   -> expressed by marking every leaf child as `not_supported`;
  no FieldValue is defined for the group itself.

## Inheritance rule and conditional schema

Requiredness of key sub-fields depends **only** on `supported.value`
regardless of `status`:

- If `supported.value == true` -> key sub-fields required:
  - `bluetooth`: `version`, `profiles`
  - `pcm`: `channels`, `mode`
  - `usb`: `version`, `speed`
  - `gnss`: `constellations`, `channels`
- If `supported.value == false` or `null` -> key sub-fields optional.

When optional and absent, an implicit FieldValue with the same `status` and
`value: null` (or `[]` depending on type) is assumed; `source_id`,
`source_ref`, `confidence`, `reason`, `notes` are inherited from the parent.
`applicable_firmware` is **exempt** from inheritance.

## Inference rules

`status: inferred` requires both `inference_source` and `inference_rule`.

- If inferred from a document: `inference_source: <source_id>`,
  `source_id: null`.
- If inferred from a logical rule: `inference_source: "logical_rule"`,
  `inference_rule` matching `^[a-z_]+:\s*.+$`.

`inferred` + `applicable_firmware` is forbidden.
`not_documented` + `applicable_firmware` is forbidden.

## `applicable_firmware`

Used only when a value differs between firmware revisions. Whenever set,
`notes` must be non-null and non-empty.

## Canonical ordering (before hashing)

- `metadata.conflicts` sorted ascending by `id`.
- `gprs.coding_schemes` order: `[CS1, CS2, CS3, CS4]`.
- `gnss.protocols`, `bluetooth.profiles`: enum order.
- `power.current_consumption.value`: `(mode_order, conditions)` lexicographic.
- `bands.gsm`, `bands.gprs`: ascending numeric.

## content_hash / scope_hash

`content_hash` = SHA-256 of canonical JSON of
`{"models": [<in scope order>], "sources": [<sources.yaml order>]}`.

`scope_hash` = SHA-256 of canonical JSON of
`{models, family_map, in_scope_capabilities, out_of_scope_capabilities,
excluded_models}`.

Fields `version`, `last_updated`, `rationale` are intentionally excluded
from `scope_hash` so that editorial metadata does not change the hash.

## Conventions

- Temperatures: degrees Celsius, `number`.
- Voltages: Volts, `number`, normalised (`3.40` -> `3.4`).
- Currents: milliamps, `number`.
- Frequencies: MHz, `number`.
- Humidity: percent (0..100), `number`.
- Baud rates: integer, bps.
- `bands.gsm`, `bands.gprs`: ascending numeric; both non-empty unless
  `not_supported` or `not_documented` (then `value: []` is allowed).

## Scope split

- `pcm` (hardware interface) is in scope.
- `audio` (codec / audio processing) is out of scope.
- `gnss.antenna_interface` is in scope.
- `antenna` (physical GSM/GPS antenna) is out of scope.
- `dimensions` is out of scope.