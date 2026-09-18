---
name: game-image
description: Reference-controlled game image director and execution harness for game assets. Use for generating, editing, repairing, or validating game prop, character, environment, UI, or 3D-modeling reference images where master references, local edits, consistency, explicit edit targets, host action packets, bounded iteration, and visual QA matter. Backend-neutral; no local image model is required.
version: 0.3.0
---

# Game Image Director

## Mission

Turn image generation from a one-shot prompt into a controlled game-asset production loop:

~~~text
resolve asset
  -> classify operation
  -> bind approved references
  -> bind exact edit target
  -> compile locks + delta brief
  -> emit Host Action Packet
  -> delegate to host imagegen
  -> inspect actual output
  -> Visual QA
  -> accept / bounded repair / bounded regeneration
~~~

This skill does not replace the image model. It owns production control around that model.

## Trigger

Use this skill when game-image production needs one or more of:

- an approved Master Reference;
- multiple references with different responsibilities;
- identity, silhouette, geometry, part position, camera, material, or style continuity;
- a local edit that must not redesign the rest of the image;
- Blender / Unity / Unreal modeling references;
- repeatable Visual QA;
- automatic routing from QA failure to repair/regeneration;
- a machine-readable next action for Codex/Agent execution.

For disposable mood images with no continuity requirements, normal image generation is sufficient.

## Subskills

Read as needed:

- `skills/asset-reference/SKILL.md` — Master Reference / Reference Atlas.
- `skills/delta-edit/SKILL.md` — smallest-change routing.
- `skills/visual-qa/SKILL.md` — hard/soft acceptance gates.
- `skills/execution-loop/SKILL.md` — state machine + host execution loop.

Apply the detailed rules in `rules/`.

## 1. Resolve the asset

Identify:

- asset_id;
- approved primary master;
- role-specific component masters;
- rejected/superseded references;
- requested target.

If an asset manifest exists, it is the source of truth.

Never silently promote a draft, rejected image, or generated candidate into a master.

## 2. Classify the operation

Choose exactly one:

- `create`: no usable master exists.
- `local_edit`: bounded region/property changes; identity/composition are already correct.
- `structural_edit`: one component shape/arrangement changes while identity remains.
- `variant`: deliberate alternate state with selected anchors preserved.
- `repair`: a previous result failed localized QA gates.
- `regenerate`: identity, silhouette, projection, topology, or widespread drift makes repair unreliable.

Do not regenerate the whole asset for one small failure.

## 3. Bind the exact edit target

For initial edit-like operations, the request must declare:

~~~toml
[execution]
edit_target_reference_id = "ASSEMBLED_MASTER"
~~~

This is the image that will actually be modified.

It is different from support references.

Example:

- `ASSEMBLED_MASTER` = edit target;
- `HANDLE_L_OUTER_MASTER` = geometry/material support reference.

Never make the host guess which image is the edit target.

## 4. Bind the minimum sufficient reference set

Every selected support reference must declare:

- reference_id;
- approved state;
- role(s);
- what it controls.

Common roles:

- identity
- geometry
- silhouette
- part_layout
- interface
- material
- color
- camera
- lighting
- style
- mood

Authority is role-specific. A material reference does not automatically control geometry.

## 5. Compile locks

Split constraints into:

### HARD PRESERVE

Violation rejects the result.

Typical 3D reference locks:

- silhouette;
- part count;
- critical hole/pin centers;
- interfaces;
- required camera/projection;
- major proportions;
- left/right identity;
- approved part layout.

### SOFT PRESERVE

Continuity preferences where minor non-destructive drift may be acceptable.

## 6. Initialize the run

~~~bash
python3 scripts/execution_loop.py init \
  --asset <asset.toml> \
  --edit <edit.toml> \
  --output <run.json>
~~~

## 7. Request the next Host Action Packet

~~~bash
python3 scripts/next_action.py \
  --asset <asset.toml> \
  --edit <edit.toml> \
  --run <run.json>
~~~

The packet is the deterministic contract for the host.

Possible `action` values:

- `imagegen_generate`
- `imagegen_edit`
- `visual_qa`
- `deliver`
- `report_blocked`

Read `references/host-action-protocol.md`.

## 8. Delegate image execution

When the packet says `imagegen_generate` or `imagegen_edit`:

- read `references/openai-imagegen-delegation.md`;
- when OpenAI/Codex `$imagegen` exists, delegate actual generation/editing to it;
- use the packet's exact `edit_target`;
- attach only packet `references`;
- use packet `prompt` as the authoritative visual instruction;
- do not invent a second competing prompt;
- use the host's built-in-first path;
- do not require an API key for normal built-in execution;
- do not auto-switch to API/CLI fallback.

After persisting the selected result:

~~~bash
python3 scripts/execution_loop.py mark-generated \
  --run <run.json> \
  --result <result-path>
~~~

Then request the next packet again.

## 9. Inspect actual pixels

When the packet says `visual_qa`, compare:

- the real generated result;
- requested change;
- hard/soft gates;
- approved comparison references.

Never infer QA success from the prompt.

If the host cannot inspect the generated result, QA is BLOCKED.

## 10. Apply Visual QA

QA statuses:

- PASS
- PASS_WITH_NOTES
- REPAIR_MINOR
- REGENERATE_MAJOR
- BLOCKED

Apply:

~~~bash
python3 scripts/execution_loop.py apply-qa \
  --run <run.json> \
  --qa <qa.toml>
~~~

Then request the next Host Action Packet again.

## 11. Bounded correction

For `REPAIR_MINOR`:

- host packet uses the failed generated result as edit target;
- correction is delta-only;
- passed gates must not be disturbed.

For `REGENERATE_MAJOR`:

- host packet returns to the approved original edit target;
- failed generated result must not be used as the source.

Default budgets:

- 2 repair passes;
- 1 regeneration pass.

Never loop indefinitely.

## Output

For project-bound image work, report concisely:

- final state;
- final asset path;
- operation;
- QA outcome;
- any material limitation.

Do not dump internal state history unless requested.

## Structured artifacts

- `templates/asset-manifest.toml`
- `templates/edit-request.toml`
- `templates/qa-report.toml`
- `templates/execution-run.json`

Validate:

~~~bash
python3 scripts/validate_project.py
python3 -m unittest discover -s tests -v
python3 scripts/demo_e2e.py
~~~
