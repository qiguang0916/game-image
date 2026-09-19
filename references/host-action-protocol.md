# Host Action Protocol

`scripts/next_action.py` is the deterministic boundary between game-image logic and the Host/Agent that can actually generate/edit/inspect images.

## Common packet contract

When applicable, packets expose:

- exact `edit_target`
- selected `references` and role bindings
- `operation`
- `requested_delta`
- `hard_preserve_gates` / `soft_preserve_gates`
- structured `topology`
- `reference_sufficiency`
- `authoritative_facts`
- `provisional_fields`
- `prohibited_assumptions`
- runtime `preflight`
- remaining repair/regeneration `budgets`
- `expected_post_action_transition`

The Host must not replace these facts with a new interpretation of the natural-language request.

## Actions

### imagegen_generate

Generate a new image using packet references and authoritative prompt.

### imagegen_edit

Modify exactly `edit_target`. Other references are supporting evidence only.

For repair, the failed generated result becomes the edit target. For major regeneration, the approved original source becomes the edit target again.

### visual_qa

Inspect real pixels. The packet includes `required_hard_gates`; every one must appear in the QA report. See `visual-qa-contract.md`.

### deliver

The run is ACCEPTED. Deliver the current persisted result.

### report_blocked

Stop image execution and surface the persisted blocker. Do not auto-switch provider/API/CLI.

## OpenAI/Codex

When `$imagegen` is available, follow the official skill and use its built-in image path. The packet supplies the edit target, references, and authoritative prompt; do not invent a competing prompt.

The deterministic scripts do not call image generation themselves.
