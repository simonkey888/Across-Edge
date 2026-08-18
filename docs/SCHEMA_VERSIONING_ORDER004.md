# ORDER-004 schema versioning

`CURRENT_SCHEMA_VERSION=4` is the single authoritative current Across-Edge internal schema version. It is used by run metadata, reports, and persisted `ShadowRecord` instances created by the current coordinator/observer.

`UPSTREAM_EVENT_VERSION=3` is not an alternative current application schema. It is the pinned upstream instrumentation envelope version consumed at the parser boundary. The coordinator accepts only that upstream event version and converts it into the current internal schema version 4.

Historical ORDER-001/002/003 evidence that contains older schema values is preserved and remains historical evidence; it is not rewritten or relabeled as current ORDER-004 evidence.
