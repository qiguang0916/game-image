---
name: game-image-execution-loop
description: Execute a game-image run through a host-native image generator by emitting deterministic Host Action Packets, inspecting real outputs, routing Visual QA, and performing bounded repair/regeneration without a local image model or direct API client.
version: 0.3.0
---

# Game Image Execution Loop

## Purpose

Turn the Director's structured request into a bounded host-driven loop:

~~~text
run state
  -> next_action.py
  -> Host Action Packet
  -> host imagegen / vision action
  -> state update
  -> next_action.py
  -> ...
~~~

The deterministic scripts decide what should happen next.

The Agent/host performs the actual image generation/edit and visual inspection.

## Preferred execution backend

When OpenAI/Codex `$imagegen` or a native image tool exists:

1. load and follow the official imagegen skill;
2. use its built-in image path by default;
3. do not ask for `OPENAI_API_KEY` for built-in execution;
4. do not auto-switch to API/CLI fallback;
5. obey the Host Action Packet's exact edit target and reference list;
6. persist the selected result before advancing the run.

Read:

- `references/openai-imagegen-delegation.md`
- `references/host-action-protocol.md`

## Explicit edit target

Initial edit requests must identify the image to modify:

~~~toml
[execution]
edit_target_reference_id = "ASSEMBLED_MASTER"
~~~

Support references remain separate.

For repairs, the failed generated result automatically becomes the edit target.

For major regeneration, the approved base target automatically becomes the edit target again.

## State machine

Persistent runs use `scripts/execution_loop.py`.

States:

- `READY`
- `QA_PENDING`
- `REPAIR_READY`
- `REGENERATE_READY`
- `ACCEPTED`
- `BLOCKED`

## Host loop

### 1. Initialize

~~~bash
python3 scripts/execution_loop.py init \
  --asset <asset.toml> \
  --edit <edit.toml> \
  --output <run.json>
~~~

### 2. Get next action

~~~bash
python3 scripts/next_action.py \
  --asset <asset.toml> \
  --edit <edit.toml> \
  --run <run.json>
~~~

### 3. Execute packet

If action is:

- `imagegen_generate`: invoke host generation.
- `imagegen_edit`: edit packet `edit_target` with packet `references` and `prompt`.
- `visual_qa`: inspect actual pixels and write QA TOML.
- `deliver`: return final asset.
- `report_blocked`: stop and explain the blocker.

### 4. After image success

~~~bash
python3 scripts/execution_loop.py mark-generated \
  --run <run.json> \
  --result <persisted-result-path>
~~~

Then request the next packet.

### 5. After QA

~~~bash
python3 scripts/execution_loop.py apply-qa \
  --run <run.json> \
  --qa <qa.toml>
~~~

Then request the next packet.

## Repair policy

`REPAIR_MINOR`:

- uses failed generated result as edit target;
- stores full QA gates/directives in run state;
- compiles correction delta;
- protects passed gates.

## Major regeneration policy

`REGENERATE_MAJOR`:

- does not keep editing the failed result;
- returns to the approved base edit target;
- reuses the validated original brief.

## Stop conditions

Default:

- repair passes: 2
- regeneration passes: 1

Budget exhaustion -> `BLOCKED`.

No infinite loops.

## Dry-run verification

The repository includes a no-model E2E simulation:

~~~bash
python3 scripts/demo_e2e.py
~~~

Expected route:

~~~text
READY
 -> imagegen_edit
 -> QA_PENDING
 -> REPAIR_READY
 -> imagegen_edit(failed result)
 -> QA_PENDING
 -> ACCEPTED
 -> deliver
~~~

This validates orchestration only. A real host E2E still requires an environment with an actual image tool.
