# Visual QA Contract

The harness enforces report completeness; the Host/Agent supplies the actual visual judgment.

## Required hard gates

The run stores a deterministic list of required hard gate IDs derived from:

- asset identity;
- requested change;
- authoritative topology components/counts/relationships;
- optional promoted hard preserve locks.

When completeness enforcement is enabled, every required gate must be present in the QA report.

## Gate status

Required hard gates use:

- `PASS`
- `FAIL`
- `NOT_VERIFIABLE`

Legacy `NOT_CHECKED` remains parseable for v0.3 compatibility but is not acceptable for a complete hard gate.

## Acceptance

- `PASS` / `PASS_WITH_NOTES`: every required hard gate is explicitly PASS.
- Missing required hard gate: QA document is invalid.
- Required hard gate `NOT_VERIFIABLE`: overall run must be BLOCKED.
- Core identity/topology/component-count/relationship FAIL: use `REGENERATE_MAJOR` or BLOCKED.
- Local requested-change/material/small isolated defect: may use `REPAIR_MINOR` with a precise repair directive.

Never weaken the contract to make an attractive image pass.

## Example

~~~toml
[[gates]]
id = "topology.relationship.panel_mounted_on_body"
severity = "hard"
status = "PASS"
note = "Visible relationship matches the authoritative reference."
~~~

Visual QA is not CAD metrology. Do not invent dimensions that are not supported by calibrated evidence.
