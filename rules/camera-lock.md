# Camera Lock

## Camera facts to preserve

- view class: side / top / front / three-quarter / orthographic-like;
- yaw/pitch/roll appearance;
- framing and crop;
- subject scale in frame;
- perspective strength;
- background horizon or studio setup when relevant.

## Modeling-reference priority

For orthographic/modeling references, camera correctness is a hard gate.

If the task requests an edge-on top/thickness view, a broad face view is not an acceptable artistic variation.

## Local edit rule

A local material or part-finish edit must not change camera or crop unless the user explicitly requests it.

## QA

If camera drift makes shape comparison unreliable, return REGENERATE_MAJOR rather than pretending the geometry can be verified.
