# Runtime Reference Preflight

Static validation proves TOML structure; it does not prove runtime files exist. A real image action must pass runtime preflight first.

## Modes

- **runtime**: concrete selected references and the edit target must exist and decode.
- **dry_run**: explicitly skips concrete file checks for tests/simulation. It must never be mistaken for a real host validation.

Run:

~~~bash
python3 scripts/runtime_preflight.py --asset <asset.toml> --edit <edit.toml>
~~~

Simulation only:

~~~bash
python3 scripts/runtime_preflight.py --asset <asset.toml> --edit <edit.toml> --dry-run
~~~

## Runtime checks

For every selected production input:

- reference is approved by the static contract;
- path exists;
- path is a readable regular file;
- format is supported;
- image can be decoded;
- the declared edit target is present and valid.

The standard-library runtime decoder currently supports PNG. Unsupported formats are blocked rather than guessed.

## Blocking reasons

Typical reason codes:

- `edit_target_missing`
- `required_reference_missing`
- `reference_unreadable`
- `reference_image_invalid`
- `reference_sufficiency_failed`
- `reference_contract_invalid`

A failed runtime preflight must prevent READY/imagegen execution. Persist the blocker through the execution loop instead of hand-editing run JSON.
