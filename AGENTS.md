# Repository operating contract

This repository is an Agent Skill / lightweight harness, not an image model.

## Principles

- Keep the core backend-neutral.
- Do not require ComfyUI, CUDA, local diffusion weights, or a local GPU.
- Prefer deterministic structure and validation over longer prompts.
- Keep root SKILL.md concise enough for an agent to load; move detailed rules into rules/ and skills/.
- Any new structured example must pass scripts/validate_project.py.
- Use Python standard library only unless a dependency is clearly justified.
- Never claim visual QA passed without inspecting the actual generated image.
- Hard invariants override aesthetic preference.

## Validation before reporting completion

Run:

~~~bash
python3 scripts/validate_project.py
python3 -m unittest discover -s tests -v
~~~

If adding a new document type, update both validator and tests.
