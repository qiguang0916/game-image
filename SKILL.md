---
name: game-image
description: Reference-controlled game image director and execution harness for game assets. Use for generating, editing, repairing, or validating game prop, character, environment, UI, or 3D-modeling reference images where master references, local edits, consistency, bounded iteration, and visual QA matter. Backend-neutral; no local image model is required.
version: 0.2.0
---

# Game Image Director

## Mission

Turn image generation from a one-shot prompt into a controlled game-asset production loop:

~~~text
resolve asset
  -> classify operation
  -> bind approved references
  -> compile locks + delta brief
  -> delegate to host imagegen
  -> inspect actual output
  -> Visual QA
  -> accept / bounded repair / bounded regeneration
~~~

This skill does not replace the underlying image model. It owns production control around that model.

## Trigger

Use this skill when game-image production needs one or more of:

- an approved Master Reference;
- multiple references with different responsibilities;
- identity, silhouette, geometry, part position, camera, material, or style continuity;
- a local edit that should not redesign the rest of the image;
- Blender / Unity / Unreal modeling references;
- repeatable Visual QA;
- automatic routing from QA failure to repair/regeneration.

For disposable mood images with no continuity requirements, normal image generation is sufficient.

## Subskills

Read as needed:

- `skills/asset-reference/SKILL.md` — Master Reference / Reference Atlas.
- `skills/delta-edit/SKILL.md` — smallest-change routing.
- `skills/visual-qa/SKILL.md` — hard/soft acceptance gates.
- `skills/execution-loop/SKILL.md` — actual execution state machine.

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

## 3. Bind the minimum sufficient reference set

Every selected reference must declare:

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

## 4. Compile locks

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

## 5. Compile the brief

Use:

~~~bash
python3 scripts/compile_brief.py <asset.toml> <edit.toml>
~~~

For edits, describe the delta rather than re-describing the whole asset.

Do not introduce new design ideas outside the request.

## 6. Delegate image execution

Read `references/openai-imagegen-delegation.md`.

When the host provides OpenAI/Codex `$imagegen`:

- delegate actual image generation/editing to it;
- use its built-in-first path;
- do not require an API key for normal built-in execution;
- do not implement a duplicate OpenAI API client in game-image;
- do not automatically switch to CLI/API fallback.

For edit operations, prefer image editing against the correct source/master instead of fresh text-to-image.

## 7. Persist execution state

Use `skills/execution-loop/SKILL.md` and:

~~~bash
python3 scripts/execution_loop.py init ...
python3 scripts/execution_loop.py mark-generated ...
python3 scripts/execution_loop.py apply-qa ...
~~~

A generated image is not complete until it enters QA.

## 8. Inspect actual pixels

Compare the produced image with:

- requested delta;
- hard/soft locks;
- selected masters;
- expected view/framing.

Never infer QA success from the prompt.

If the host cannot inspect the generated result, QA is BLOCKED.

## 9. Visual QA

Use `skills/visual-qa/SKILL.md`.

Hard-gate failure overrides aesthetics.

Statuses:

- PASS
- PASS_WITH_NOTES
- REPAIR_MINOR
- REGENERATE_MAJOR
- BLOCKED

## 10. Bounded correction

For `REPAIR_MINOR`:

~~~bash
python3 scripts/compile_repair.py <asset.toml> <edit.toml> <qa.toml>
~~~

Use the failed generated image as the edit target and correct only failed gates.

For `REGENERATE_MAJOR`:

- discard the bad result as an edit source;
- restart from the approved master/original target;
- re-use the validated original brief.

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
~~~
