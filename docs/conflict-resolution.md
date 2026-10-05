# Conflict Resolution

This document describes how conflicting capability values are resolved and
recorded in `metadata.conflicts` of each model file.

## Source priority

1. Dedicated Hardware Design manual of the same model.
2. Combined Hardware Design manual that covers the model.
3. Secondary source (`tier: secondary`) whose `applicable_models` includes
   the model (typically an AT Command Manual).
4. Inferred value via an explicit inference rule.

## Publication-date exception

If the combined Hardware Design manual (level 2) has a **newer**
`publication_date` than the dedicated Hardware Design manual (level 1), it
becomes a candidate and the decision is taken by newer date and model
coverage. Record the outcome with `resolution: chosen_newer_publication`.

## Ties within the same tier

- Newer `publication_date` wins.
- If dates are unknown, higher document `version` wins.
- If still tied, the field is marked `status: conflict` with a matching
  record in `metadata.conflicts` where `resolution: unresolved`.

## Recording rules

- Every field with `status: conflict` MUST have at least one matching record
  in `metadata.conflicts`, matched by **exact string equality** of
  `field_path` against the dotted path of the field (e.g.
  `capabilities.gpio.count.value`).
- Every conflict record with `resolution: unresolved` MUST have a matching
  field with `status: conflict`.
- Multi-way conflicts are decomposed into pairwise records.
- Old records are preserved (append-only). Records are sorted by `id` before
  hashing.

## Record shape

```yaml
- id: conflict_001
  field_path: capabilities.gpio.count.value
  old_value: 0
  new_value: 4
  old_source_id: <source_id>
  new_source_id: <source_id>
  old_source_ref: {page: <page>, section: <section>, table: <table>, figure: <figure>}
  new_source_ref: {page: <page>, section: <section>, table: <table>, figure: <figure>}
  resolution: chosen_new | chosen_old | unresolved | chosen_newer_publication
  chosen_source_id: <source_id|null>
  reason: <reason>
```

## Silent sources

A source that is silent about a capability is **not** a conflict candidate.
Conflicts are only recorded when two sources provide **different values**.