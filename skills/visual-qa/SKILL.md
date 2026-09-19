---
name: game-image-visual-qa
description: Use when a generated or edited game-asset image must be inspected against approved references, requested changes, topology, or hard acceptance gates before it can enter a production reference chain.
version: 0.4.0
---

# Game Asset Visual QA

## Principle

Judge the actual pixels for the declared production purpose. Beauty cannot override a failed structural or identity gate.

## Inputs

Use the Host Action Packet as the QA contract. Inspect:

- `result_path`
- selected comparison references
- requested delta
- `required_hard_gates`
- hard/soft preserve gates
- topology/reference-sufficiency fields

If the result cannot be inspected, persist `visual_inspection_unavailable` as BLOCKED.

## Required gate discipline

For each required hard gate, write exactly one explicit result:

- `PASS`
- `FAIL`
- `NOT_VERIFIABLE`

Do not omit a required gate. Do not convert uncertainty into PASS.

Use `references/visual-qa-contract.md` for the schema and routing rules.

## Routing

- All required hard gates PASS → `PASS` or `PASS_WITH_NOTES`.
- Local requested-change/material/isolated defect → `REPAIR_MINOR` with a minimal repair directive.
- Identity, projection, silhouette, required component/count, or authoritative topology relationship failure → `REGENERATE_MAJOR`.
- Required hard gate cannot be verified → `BLOCKED`.

Repairs are delta-only and must protect every already-passed hard gate.

## Limits

This is visual QA, not CAD metrology. Do not invent dimensions or hidden structure unsupported by authoritative evidence.
