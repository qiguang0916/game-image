# Geometry Lock

## What geometry lock means

Geometry lock protects visible structural facts that should not change during an image edit.

Typical items:

- outer silhouette;
- major proportions;
- part count;
- hole/pin count and centers;
- relative placement of components;
- contact/mating boundaries;
- front/back/left/right identity;
- edge/spine relationship;
- openings, cutouts, guards, caps, mounts.

## Hard vs soft

Hard:
- any drift changes the modeled object or invalidates a reference view.

Soft:
- tiny perspective/rendering ambiguity that does not change the intended structure.

## Rules for generated references

- Never treat shading as new geometry without corroboration.
- Never infer hidden manufacturing details from a beauty render.
- When a dedicated orthographic/component master exists, it outranks a beauty render for that geometry.
- If geometry is already defined in Blender or another 3D source of truth, the 3D model outranks generated imagery.

## QA language

Prefer observable statements:

“rear pin center moved upward relative to the handle outline”

over invented precision:

“rear pin moved 1.7 mm”

unless calibrated dimensions exist.
