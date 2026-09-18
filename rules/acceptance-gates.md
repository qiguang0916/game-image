# Acceptance Gates

## Hard gate policy

Any failed hard gate prevents PASS.

Default hard gates:

- asset identity
- required edit achieved
- view/projection
- silhouette
- part count
- critical part positions
- component interfaces
- no unauthorized structural changes

## Soft gate policy

Soft failures may produce PASS_WITH_NOTES when the image remains usable for its declared purpose.

Examples:

- tiny lighting drift
- subtle roughness difference
- minor background tone change
- harmless micro-texture variation

## Decision table

PASS:
- all hard gates pass;
- requested change is present;
- no material unrequested drift.

PASS_WITH_NOTES:
- all hard gates pass;
- only minor soft issues remain.

REPAIR_MINOR:
- core identity/composition pass;
- failure is localized;
- a surgical correction is plausible.

REGENERATE_MAJOR:
- identity, projection, silhouette, topology, or several unrelated regions fail.

BLOCKED:
- cannot inspect pixels;
- required master/reference is missing;
- backend cannot perform the required edit path and fidelity cannot be evaluated.

## Loop limit

Default repair limit is two passes.

If the same hard gate fails twice, stop and surface the limitation.
