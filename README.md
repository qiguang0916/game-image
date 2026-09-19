# game-image

A backend-neutral **Game Image Director / Execution Harness** for ChatGPT/Codex game-art production.

It does not run ComfyUI or a local diffusion model. It controls what the host image tool is allowed to assume, which image it edits, which references are authoritative, which structural facts must survive, and whether the result is allowed to pass QA.

## v0.4 hardening

v0.4 adds the controls exposed by real Host E2E failures:

- runtime reference preflight before READY
- generic component/topology contracts
- reference sufficiency and provisional/unknown facts
- complete required hard-gate QA
- structured Host Action Packets
- persisted host/backend BLOCKED events
- bounded repair/regeneration with no automatic API fallback

## Real vs dry-run

Static validation:

~~~bash
python3 scripts/validate_project.py
~~~

Real runtime preflight:

~~~bash
python3 scripts/runtime_preflight.py --asset <asset.toml> --edit <edit.toml>
~~~

Dry-run is explicit:

~~~bash
python3 scripts/runtime_preflight.py --asset <asset.toml> --edit <edit.toml> --dry-run
~~~

A real `execution_loop.py init` runs preflight before READY. Use `--dry-run` only for simulations/tests with no concrete images.

## Host loop

~~~bash
python3 scripts/execution_loop.py init --asset <asset.toml> --edit <edit.toml> --output <run.json>
python3 scripts/next_action.py --asset <asset.toml> --edit <edit.toml> --run <run.json>
~~~

Execute the returned packet with the host image tool, persist the selected image, then:

~~~bash
python3 scripts/execution_loop.py mark-generated --run <run.json> --result <image>
~~~

On `visual_qa`, inspect real pixels and write a complete QA TOML, then:

~~~bash
python3 scripts/execution_loop.py apply-qa --run <run.json> --qa <qa.toml>
~~~

Repeat until `deliver` or `report_blocked`.

## Host failure

~~~bash
python3 scripts/execution_loop.py mark-blocked   --run <run.json>   --reason-code host_native_imagegen_moderation_blocked   --action imagegen_edit   --message "host safety policy blocked generation"
~~~

BLOCKED never auto-switches to API/CLI fallback.

## Contracts

See:

- `references/runtime-preflight.md`
- `references/topology-contract.md`
- `references/reference-sufficiency.md`
- `references/visual-qa-contract.md`
- `references/host-action-protocol.md`
- `references/host-failure-protocol.md`

## Validation

~~~bash
python3 scripts/validate_project.py
python3 scripts/runtime_preflight.py   --asset examples/KNIFE_001/asset.toml   --edit examples/KNIFE_001/edits/rivets-brushed-silver.toml   --dry-run
python3 -m unittest discover -s tests -v
python3 scripts/demo_e2e.py
~~~

The repository remains Python-standard-library-first and does not require an API key, local GPU, CUDA, ComfyUI, Stable Diffusion, or FLUX weights.
