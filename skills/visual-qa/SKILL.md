---
name: game-image-visual-qa
description: Visual acceptance gate for generated game-asset images. Compares the actual output with requested changes and approved masters, then returns PASS, repair, regenerate, or blocked.
version: 0.1.0
---

# Game Asset Visual QA

## Purpose

Judge production usability, not just beauty.

A beautiful result that violates a Master Reference is a failure.

## Inputs

Required:

- actual generated/edited image;
- edit or generation brief;
- approved references used for the task;
- hard and soft locks.

If the actual image cannot be inspected, return BLOCKED.

## Check order

1. File/image readability.
2. Correct asset identity.
3. Requested change is present.
4. Hard geometry and silhouette gates.
5. Part count and part-position gates.
6. Camera/projection/framing.
7. Material/color constraints.
8. Lighting/style continuity.
9. Unrequested changes and generation artifacts.

## Default hard gates for 3D modeling reference images

- correct asset/component identity;
- correct view or projection;
- broad silhouette match;
- part count;
- critical hole/pin centers;
- component interface relationship;
- no new or missing structural parts;
- requested edit did not alter unrelated hard-locked regions.

## Default soft gates

- exact micro-texture;
- tiny highlight variation;
- minor background tonal drift;
- subtle roughness variation when geometry remains readable.

Projects may promote a soft gate to hard.

## Status

- PASS: all hard gates pass and requested change is achieved.
- PASS_WITH_NOTES: hard gates pass; only non-blocking soft deviations remain.
- REPAIR_MINOR: hard identity/composition is intact, but one or more localized failures are repairable.
- REGENERATE_MAJOR: core identity, silhouette, projection, topology, or multiple unrelated regions are wrong.
- BLOCKED: result cannot be inspected or required references/brief are unavailable.

## Repair output

Repairs must be delta-only.

Return:

~~~text
FAILED GATE:
rear_rivet_center

OBSERVED:
Rear rivet shifted toward the butt relative to HANDLE_OUTER_MASTER.

CORRECTION DELTA:
Restore only the rear rivet center to the approved master location.
Preserve rivet count, diameter, material, handle geometry, blade, camera, and lighting.
~~~

## No invented precision

This is image QA, not CAD metrology.

Do not invent millimeter tolerances from pixels unless calibrated dimensional data exists.

Use qualitative or normalized image-space judgments when exact measurements are unavailable.

## Persistent report

Use templates/qa-report.toml for project records.
