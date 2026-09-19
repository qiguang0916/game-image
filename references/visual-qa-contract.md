# Visual QA Contract

Visual QA is performed by the host/agent on actual pixels. The Harness enforces report completeness and routing; it does not fake visual judgment.

## Gate statuses

For required hard gates use:

- `PASS`
- `FAIL`
- `NOT_VERIFIABLE`

A required hard gate may not be omitted.

## Acceptance rules

- Overall `PASS` / `PASS_WITH_NOTES` requires every required hard gate to be present with `severity = "hard"` and `status = "PASS"`.
- Required hard gate `NOT_VERIFIABLE` blocks acceptance.
- Missing required component, wrong required component count, or required topology relationship failure routes to `REGENERATE_MAJOR`.
- A localized non-topology defect may use `REPAIR_MINOR`.
- Backend/inspection inability uses `BLOCKED`, not a synthetic PASS.

Required gates are derived from:

1. `edit_request.qa_contract.required_hard_gates`, and
2. required topology components/relationships.

## Example

~~~toml
[[gates]]
name = "topology.component.decorative_screw.count"
severity = "hard"
status = "PASS"
note = "Three visible screws remain."

[[gates]]
name = "topology.relationship.shade_mounted_on_arm"
severity = "hard"
status = "PASS"
note = ""
~~~

Do not use keyword matching as visual evidence. The host must inspect the actual output and references.
