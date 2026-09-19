---
name: game-image
description: Use when game-asset image work needs approved references, identity or geometry continuity, local edits, topology constraints, runtime reference checks, or Visual QA before an output can be accepted.
version: 0.4.0
---

# Game Image

## Overview

`game-image` is a backend-neutral control layer around an available image generator. The image model draws; this skill controls evidence, edit scope, structural invariants, runtime readiness, QA completeness, and bounded retries.

Do not install a local diffusion stack just to use this skill.

## Core invariants

- Approved references are authoritative only for their declared roles.
- The edit target is explicit and distinct from support references.
- Task-specific structure belongs in a topology contract; never hard-code one asset's anatomy as a global rule.
- Inferred or hidden structure stays provisional/unknown until supported.
- Real execution requires runtime preflight; dry-run must be explicit.
- A generated image is not accepted until every required hard gate is explicitly verified.
- Host/backend failures become persisted `BLOCKED` events.
- Repair edits the failed result; major regeneration returns to the approved source.
- Retry budgets are finite.
- Never auto-switch to API/CLI fallback.

## Workflow

1. Validate the asset/edit TOML.
2. For real execution, initialize the run; runtime preflight happens before READY.
3. Ask `scripts/next_action.py` for the Host Action Packet.
4. Execute exactly the packet action with the available host image tool.
5. Persist the selected result with `mark-generated`.
6. For `visual_qa`, inspect real pixels and write a complete QA TOML.
7. Apply QA and request the next packet until `deliver` or `report_blocked`.

Simulation only:

~~~bash
python3 scripts/execution_loop.py init ... --dry-run
~~~

## Read when needed

- Reference selection: `skills/asset-reference/SKILL.md`
- Delta edit/repair: `skills/delta-edit/SKILL.md`
- Visual QA: `skills/visual-qa/SKILL.md`
- Execution loop: `skills/execution-loop/SKILL.md`
- Runtime files: `references/runtime-preflight.md`
- Structure: `references/topology-contract.md`
- Reference coverage: `references/reference-sufficiency.md`
- QA completeness: `references/visual-qa-contract.md`
- Host packets: `references/host-action-protocol.md`
- Host failures: `references/host-failure-protocol.md`
- OpenAI/Codex execution: `references/openai-imagegen-delegation.md`

## Validation

~~~bash
python3 scripts/validate_project.py
python3 scripts/runtime_preflight.py --asset <asset.toml> --edit <edit.toml> --dry-run
python3 -m unittest discover -s tests -v
python3 scripts/demo_e2e.py
~~~
