# Host Action Protocol

The host action packet is the contract between deterministic game-image logic and the Agent/host that can actually call image tools.

Generate it with:

~~~bash
python3 scripts/next_action.py \
  --asset <asset.toml> \
  --edit <edit.toml> \
  --run <run.json>
~~~

## Why this exists

Without a host packet, an Agent has to re-infer every turn:

- generate or edit?
- which image is the actual edit target?
- which images are supporting references?
- what does each reference control?
- what prompt should be sent?
- should the next step be QA, repair, regeneration, or delivery?

The packet makes those decisions explicit and testable.

## Packet actions

### imagegen_generate

Use the host's native image generation capability.

Fields:

- `references`: selected approved support references.
- `prompt`: authoritative compiled brief.
- `after_success = mark_generated`.

### imagegen_edit

Use image editing, not fresh text-to-image.

Fields:

- `edit_target`: exact image to modify.
- `references`: support references, each with declared roles.
- `prompt`: authoritative delta or repair brief.
- `after_success = mark_generated`.

The edit target and a support reference may point to the same file; their responsibilities are still different.

### visual_qa

The host must inspect real pixels.

Fields:

- `result_path`;
- `comparison_references`;
- `requested_change`;
- `hard_gates`;
- `soft_gates`;
- allowed QA statuses.

The Agent writes a QA TOML and applies it through `execution_loop.py apply-qa`.

### deliver

The run is accepted.

Deliver `result_path`.

### report_blocked

The run exhausted its bounded loop or hit an execution/inspection blocker.

Do not silently continue regenerating.

## Edit target semantics

For initial local/structural/variant edits, the edit request contains:

~~~toml
[execution]
edit_target_reference_id = "ASSEMBLED_MASTER"
~~~

This is the image that must be modified.

`reference_bindings` are support inputs and must not be mistaken for the edit target.

For a repair pass, the edit target changes to the failed generated result. This is automatic in the host packet.

For major regeneration, the host packet switches back to the approved base edit target. It must not keep editing the failed result.

## OpenAI/Codex host behavior

If `$imagegen` is available:

1. read its official skill instructions;
2. invoke the built-in image path;
3. follow the host packet's action;
4. use the packet's edit target and references;
5. do not invent a second prompt;
6. persist the selected result;
7. mark-generated;
8. request the next packet.

The deterministic scripts do not call `image_gen` themselves.
