# Prompt Compiler

The compiled image instruction should be short enough to remain legible and structured enough to prevent accidental redesign.

## Create brief

~~~text
ASSET:
<id and purpose>

CREATE:
<what must be created>

REFERENCE ROLES:
<explicit role mapping>

HARD REQUIREMENTS:
<identity/geometry/camera gates>

MATERIAL / STYLE:
<surface and rendering requirements>

OUTPUT:
<view, framing, background, use>
~~~

## Edit brief

~~~text
ASSET:
<id>

OPERATION:
local_edit | structural_edit | repair

TARGET:
<exact target>

CHANGE:
<delta only>

REFERENCE ROLES:
<only selected references>

HARD PRESERVE:
<non-negotiable invariants>

SOFT PRESERVE:
<continuity preferences>

OUTPUT:
<same view/crop unless requested otherwise>
~~~

## Repair brief

~~~text
FAILED GATE:
<one or more exact gates>

RESTORE:
<smallest correction>

PRESERVE:
<everything that already passed>

DO NOT REDESIGN:
Keep unrelated regions unchanged.
~~~

## Prompt hygiene

- Avoid re-describing every unchanged detail during local edits.
- Avoid contradictory reference roles.
- Avoid vague “make better / more professional” language when a measurable visual change can be stated.
- Avoid long negative lists; express the intended image positively plus a concise preserve boundary.
