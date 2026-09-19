---
name: game-image-execution-loop
description: Use when a game-image task must run through a real host image tool with concrete reference files, persisted state, bounded repair/regeneration, or explicit backend failure handling.
version: 0.4.0
---

# Game Image Execution Loop

## Real run

Initialize:

~~~bash
python3 scripts/execution_loop.py init   --asset <asset.toml>   --edit <edit.toml>   --output <run.json>
~~~

Initialization performs runtime reference preflight. Missing/invalid required inputs become `BLOCKED`; they do not enter READY.

Simulation must be explicit:

~~~bash
python3 scripts/execution_loop.py init ... --dry-run
~~~

## Host loop

Get the next deterministic action:

~~~bash
python3 scripts/next_action.py --asset <asset.toml> --edit <edit.toml> --run <run.json>
~~~

Execute only the returned action:

- `imagegen_generate`
- `imagegen_edit`
- `visual_qa`
- `deliver`
- `report_blocked`

After a generated result is persisted:

~~~bash
python3 scripts/execution_loop.py mark-generated --run <run.json> --result <path>
~~~

After visual QA:

~~~bash
python3 scripts/execution_loop.py apply-qa --run <run.json> --qa <qa.toml>
~~~

## Host/runtime failure

Do not edit run JSON manually:

~~~bash
python3 scripts/execution_loop.py mark-blocked   --run <run.json>   --reason-code host_native_imagegen_failed   --action imagegen_edit   --message "short non-sensitive description"
~~~

Read `references/host-failure-protocol.md`.

## Invariants

- Repair uses the failed generated result.
- Major regeneration returns to the approved original source.
- Budget exhaustion blocks.
- BLOCKED never auto-switches to API/CLI fallback.
- Visual QA completeness is enforced when the run contract requires it.

See `references/runtime-preflight.md` and `references/host-action-protocol.md`.
