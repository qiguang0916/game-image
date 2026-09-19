# Reference Sufficiency

Reference sufficiency states the minimum approved evidence required for the current operation.

## Schema

~~~toml
[reference_sufficiency]
required_roles = ["identity", "geometry", "material"]
allow_provisional = false
provisional_fields = []
prohibited_assumptions = ["hidden interior geometry"]
~~~

## Semantics

- `required_roles`: roles that selected approved bindings must cover.
- `allow_provisional`: whether missing roles may remain explicitly provisional.
- `provisional_fields`: facts the host may discuss as unconfirmed, never as Master truth.
- `prohibited_assumptions`: facts the host must not invent to complete the task.

Statuses:

- `sufficient`: all required roles are covered.
- `provisional`: coverage is incomplete but the contract explicitly allows provisional work.
- `insufficient`: required evidence is missing and the run must block.

## Host packet

The packet separates:

- authoritative facts;
- provisional fields;
- prohibited assumptions.

A host must not upgrade a provisional/inferred fact into an approved reference or structural fact.
