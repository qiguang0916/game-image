---
name: game-image
description: Reference-controlled game image director for game assets. Use for generating, editing, repairing, or validating game prop, character, environment, UI, or 3D-modeling reference images where master references, local edits, consistency, and visual QA matter. Backend-neutral; no local image model is required.
version: 0.1.0
---

# Game Image Director

## Mission

Turn image generation from a one-shot prompt into a controlled game-asset production loop.

This skill does not make the underlying image model more capable. It improves orchestration:

- choose the correct approved references;
- declare what each reference controls;
- separate requested CHANGE from PRESERVE invariants;
- prefer local edits over whole-image regeneration;
- inspect the actual result;
- reject outputs that violate hard gates;
- issue a minimal correction delta when repair is possible.

## Trigger

Use this skill when the user asks to create or edit images for game production and at least one of these is true:

- an approved Master Reference exists;
- multiple reference images have different jobs;
- identity, silhouette, geometry, part position, camera, material, or style must remain stable;
- the request is a local change;
- the image will be used as a Blender / Unity / Unreal modeling reference;
- the user wants repeatable visual QA instead of subjective “looks good” review.

For disposable mood images with no continuity requirements, a normal image generation flow is sufficient.

## Required subskills

Read these when relevant:

- skills/asset-reference/SKILL.md for reference atlas and master selection.
- skills/delta-edit/SKILL.md for local-edit routing and correction prompts.
- skills/visual-qa/SKILL.md for acceptance gates and repair decisions.

Also apply:

- rules/reference-priority.md
- rules/geometry-lock.md
- rules/material-lock.md
- rules/camera-lock.md
- rules/acceptance-gates.md

## Production contract

### 1. Resolve the asset

Identify:

- asset_id;
- current approved primary master;
- component masters;
- rejected or superseded references;
- current task target.

If an asset manifest exists, treat it as the source of truth.

Never silently promote a draft or rejected image into a master.

### 2. Classify the operation

Choose exactly one:

- create: no usable master exists yet.
- local_edit: the current composition and identity are correct; only a bounded region/property changes.
- structural_edit: a component shape or arrangement must change while identity remains.
- variant: create a deliberate alternate state while preserving selected identity anchors.
- repair: a previous result failed one or more gates and can be corrected surgically.
- regenerate: core composition, identity, silhouette, projection, or structure is wrong enough that local repair is unreliable.

Do not use regenerate merely because one small detail is wrong.

### 3. Build the reference set

For every selected reference, declare:

- reference_id;
- role or roles;
- priority;
- what it must influence;
- what it must not influence.

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

Use the smallest sufficient reference set. More references are not automatically better.

### 4. Compile locks

Split constraints into:

HARD PRESERVE:
- violations make the image unacceptable.

SOFT PRESERVE:
- should remain stable, but small visual drift may be tolerable if the requested edit succeeds.

Typical hard locks for 3D modeling references:

- silhouette;
- part count;
- hole / pin centers;
- interfaces between parts;
- orthographic or specified camera;
- major proportions;
- left/right identity;
- approved component layout.

### 5. Compile a delta brief

For edits, the prompt must emphasize the delta, not re-describe the whole asset.

Use this structure:

~~~text
ASSET:
<asset id>

OPERATION:
<local_edit / structural_edit / repair / ...>

TARGET:
<exact region or property>

CHANGE:
<only what changes>

REFERENCE ROLES:
REF_1 = <job>
REF_2 = <job>

HARD PRESERVE:
<unchanged gates>

SOFT PRESERVE:
<unchanged preferences>

OUTPUT:
<view / crop / background / purpose>
~~~

Do not introduce new design ideas that were not requested.

### 6. Execute with the available image backend

This repository is backend-neutral.

If the environment provides a native image generation/editing tool, use it. For an edit request, prefer the backend's image-edit path over a fresh text-to-image generation when possible.

Pass only the relevant approved references and explicitly bind their roles in the instruction.

If the backend cannot accept all required references, reduce to the highest-priority reference set and disclose the reduced control; do not pretend equivalent fidelity.

### 7. Inspect the actual output

Do not accept an image from the prompt alone.

Look at the produced pixels and compare against:

- the requested delta;
- hard locks;
- selected masters;
- expected view and framing.

If the runtime cannot inspect the result, mark QA BLOCKED rather than claiming success.

### 8. Run Visual QA

Use skills/visual-qa/SKILL.md.

A hard-gate failure means REJECT even if the image is attractive.

### 9. Decide repair vs regenerate

Repair when:

- identity and composition remain correct;
- failures are localized;
- the requested edit is mostly achieved.

Regenerate when:

- wrong asset identity;
- wrong broad silhouette;
- wrong view/projection;
- wrong part topology/count;
- multiple unrelated regions drifted;
- local corrections repeatedly damage new areas.

Default maximum repair passes: 2.

If the same hard gate fails twice, stop looping and report the limitation instead of endlessly regenerating.

## Output to the user

When the task includes actual image generation/editing, deliver the image plus a concise status:

- operation used;
- master/reference roles used;
- QA result;
- any known limitation.

Do not dump internal orchestration unless requested.

## Structured artifacts

Use templates when persistent project state is needed:

- templates/asset-manifest.toml
- templates/edit-request.toml
- templates/qa-report.toml

Validate manifests with:

~~~bash
python3 scripts/validate_project.py
~~~
