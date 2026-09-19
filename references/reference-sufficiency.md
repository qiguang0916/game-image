# Reference Sufficiency

A reference set is sufficient only for the facts the current operation needs.

Declare the minimum roles and epistemic boundaries in the edit request:

~~~toml
[reference_sufficiency]
required_roles = ["identity", "geometry"]
authoritative_facts = ["visible assembled layout"]
provisional_fields = ["hidden rear interface"]
prohibited_assumptions = ["unseen structure is approved"]
on_missing = "blocked"
~~~

## Status

The harness compiles:

- `sufficient`: every required role is covered by the selected approved bindings.
- `provisional`: missing roles are explicitly allowed as provisional.
- `insufficient`: required roles are missing and execution must block.

## Rules

- More references are not automatically better.
- A material reference does not become a geometry authority.
- Provisional or inferred facts must not be promoted to a Master without review.
- Host Action Packets expose authoritative facts, provisional fields, and prohibited assumptions separately.
- If an operation needs a view/interface that is not covered, narrow scope, mark it provisional, or block. Do not silently invent confirmed structure.
