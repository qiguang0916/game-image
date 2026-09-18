---
name: game-image-execution-loop
description: Execute a game-image brief through a host-native image generator, inspect the real output, route Visual QA, and perform bounded repair/regeneration without requiring a local image model or direct API client.
version: 0.2.0
---

# Game Image Execution Loop

## Purpose

Turn the Director's structured brief into a bounded production loop:

~~~text
compile brief
  -> delegate to host imagegen
  -> persist selected result
  -> inspect actual pixels
  -> write QA result
  -> accept / repair / regenerate / block
~~~

This skill owns orchestration. It does not own the image model.

## Preferred execution backend

When the host provides the OpenAI/Codex image generation skill or native image tool:

1. load and follow the official `$imagegen` skill;
2. use its built-in image tool path by default;
3. do not ask for `OPENAI_API_KEY` for built-in execution;
4. do not switch to API/CLI fallback automatically;
5. for edit operations, pass the current approved/edit target plus only the required references;
6. for project-bound results, persist the selected image into the project workspace.

Read `references/openai-imagegen-delegation.md`.

## Inputs

Required:

- an asset manifest;
- an edit/generation request;
- selected approved references;
- compiled brief.

For repair passes:

- the failed generated result;
- a Visual QA report with explicit repair directives.

## State machine

Persistent runs use `scripts/execution_loop.py`.

States:

- `READY`: brief and references are validated; invoke image generation/editing.
- `QA_PENDING`: a result exists; inspect it and produce QA.
- `REPAIR_READY`: result is fundamentally usable; edit the failed result with a delta-only repair brief.
- `REGENERATE_READY`: result has a major failure; restart from the approved master/original target, not from the bad result.
- `ACCEPTED`: QA passed.
- `BLOCKED`: execution or fidelity cannot be validated within limits.

## Loop

### 1. Initialize

~~~bash
python3 scripts/execution_loop.py init \
  --asset examples/KNIFE_001/asset.toml \
  --edit examples/KNIFE_001/edits/rivets-brushed-silver.toml \
  --output .game-image/runs/KNIFE_001_RIVETS.json
~~~

Then compile the normal brief:

~~~bash
python3 scripts/compile_brief.py <asset.toml> <edit.toml>
~~~

### 2. Delegate generation/editing

For `local_edit`, `structural_edit`, `repair`, and most continuity-sensitive variants, prefer image editing over fresh text-to-image generation.

Use the reference bindings exactly as validated.

Do not attach every reference from the atlas.

### 3. Record the generated result

After selecting the result that will enter QA:

~~~bash
python3 scripts/execution_loop.py mark-generated \
  --run .game-image/runs/KNIFE_001_RIVETS.json \
  --result path/to/generated-image.png
~~~

The run becomes `QA_PENDING`.

### 4. Inspect real pixels

The agent must actually inspect:

- generated result;
- approved masters used;
- requested delta.

Do not infer QA from the prompt.

Write a QA report using `templates/qa-report.toml`.

### 5. Apply QA

~~~bash
python3 scripts/execution_loop.py apply-qa \
  --run .game-image/runs/KNIFE_001_RIVETS.json \
  --qa path/to/qa-report.toml
~~~

Routing:

- PASS / PASS_WITH_NOTES -> ACCEPTED
- REPAIR_MINOR -> REPAIR_READY while repair budget remains
- REGENERATE_MAJOR -> REGENERATE_READY while regeneration budget remains
- BLOCKED -> BLOCKED

### 6. Repair

For `REPAIR_READY`:

~~~bash
python3 scripts/compile_repair.py \
  <asset.toml> <edit.toml> <qa-report.toml>
~~~

Use the failed generated result as the edit target.

Only correct failed gates. Preserve everything that already passed.

### 7. Major regeneration

For `REGENERATE_READY`:

- discard the failed result as an edit target;
- return to the approved source/master;
- re-run the original brief with the same validated reference roles;
- do not accumulate errors by editing the bad output.

### 8. Stop conditions

Never loop indefinitely.

Default budgets:

- repair passes: 2;
- regeneration passes: 1.

If the budget is exhausted, mark the run `BLOCKED` and report the specific recurring gate failure.

## Host capability degradation

If the host cannot:

- edit an existing image;
- accept the required reference set;
- persist a result;
- inspect the generated pixels;

do not pretend full fidelity.

Reduce scope only when the task remains valid, and disclose the limitation. Otherwise mark the run BLOCKED.

## Human-visible output

For normal use, keep orchestration concise.

Report:

- final status;
- final asset path when project-bound;
- operation used;
- QA outcome;
- material limitation, if any.

Do not expose internal state history unless requested.
