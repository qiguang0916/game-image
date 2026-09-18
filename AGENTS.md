# Repository operating contract

This repository is an Agent Skill / lightweight image-production harness, not an image model.

## Principles

- Keep the core backend-neutral.
- Do not require ComfyUI, CUDA, local diffusion weights, or a local GPU.
- Do not add a direct OpenAI API client merely to duplicate the host's official imagegen capability.
- When an OpenAI/Codex host provides `$imagegen`, delegate actual image generation/editing to that system skill and prefer its built-in path.
- Never ask for an API key for normal host-native execution.
- Never auto-switch to API/CLI fallback; fallback must be explicitly requested by the user.
- Prefer deterministic structure, state, and validation over longer prompts.
- Keep root SKILL.md concise enough for an agent to load; move detail into rules/, references/, and subskills.
- Any new structured example must pass scripts/validate_project.py.
- Use Python standard library only unless a dependency is clearly justified.
- Never claim Visual QA passed without inspecting the actual generated image.
- Hard invariants override aesthetic preference.
- Repair/regeneration loops must be bounded.

## Runtime separation

Deterministic scripts may:

- validate manifests;
- compile briefs;
- compile repair directives;
- persist execution state;
- route QA outcomes.

Deterministic scripts must not pretend to perform visual judgment or image generation.

The Agent/host must:

- invoke the real image tool;
- inspect the real output;
- write the Visual QA decision.

## Validation before reporting completion

Run:

~~~bash
python3 scripts/validate_project.py
python3 -m unittest discover -s tests -v
~~~

If adding a new document type or state transition, update validator/state-machine tests.
