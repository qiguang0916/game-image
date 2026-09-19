# Host Failure Protocol

Host/backend failures are first-class BLOCKED events. Never represent them by manually editing run JSON or by silently switching providers.

Persist a blocker:

~~~bash
python3 scripts/execution_loop.py mark-blocked \
  --run <run.json> \
  --reason-code host_native_imagegen_unavailable \
  --action imagegen_edit \
  --message "built-in image tool unavailable"
~~~

## Supported host/runtime reasons

- `host_native_imagegen_unavailable`
- `host_native_imagegen_failed`
- `host_native_imagegen_moderation_blocked`
- `generated_result_missing`
- `generated_result_unreadable`
- `visual_inspection_unavailable`
- `required_reference_missing`
- `edit_target_missing`
- `reference_unreadable`
- `reference_image_invalid`
- `reference_sufficiency_failed`
- `reference_contract_invalid`

Budget exhaustion and QA blocking also persist explicit reason codes.

A blocked event records the action, short non-sensitive message, retryability, timestamp, and current repair/regeneration counters.

## Invariant

After BLOCKED, `next_action.py` emits `report_blocked`. It must not emit a new imagegen action and must not auto-switch to API/CLI fallback.

Never persist secrets, cookies, full private requests, or credentials in failure messages.
