#!/usr/bin/env python3
"""Compile the next machine-readable host action for a game-image run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from compile_brief import compile_brief
from compile_repair import compile_repair_brief
from execution_loop import load_run, validate_run_state
from validate_project import (
    ValidationError,
    cross_validate,
    load_document,
    validate_document,
)


def _reference_packets(
    asset: dict[str, Any],
    edit: dict[str, Any],
) -> list[dict[str, Any]]:
    refs = {ref["id"]: ref for ref in asset["references"]}
    packets: list[dict[str, Any]] = []
    for binding in edit.get("reference_bindings", []):
        ref = refs[binding["reference_id"]]
        packets.append(
            {
                "reference_id": ref["id"],
                "path": ref["path"],
                "roles": list(binding["roles"]),
            }
        )
    return packets


def _base_edit_target(
    asset: dict[str, Any],
    edit: dict[str, Any],
) -> dict[str, str] | None:
    target_id = edit.get("execution", {}).get("edit_target_reference_id")
    if not target_id:
        return None

    refs = {ref["id"]: ref for ref in asset["references"]}
    ref = refs[target_id]
    return {
        "reference_id": target_id,
        "path": ref["path"],
    }


def _merged_lock_list(asset: dict[str, Any], edit: dict[str, Any], key: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in [
        *asset.get("locks", {}).get(key, []),
        *edit.get("preserve", {}).get(key, []),
    ]:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def build_action_packet(
    asset: dict[str, Any],
    edit: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    validate_run_state(run)

    if asset["asset_id"] != run["asset_id"]:
        raise ValidationError("run asset_id does not match asset manifest")
    if edit["request_id"] != run["request_id"]:
        raise ValidationError("run request_id does not match edit request")

    state = run["state"]
    references = _reference_packets(asset, edit)
    base_target = _base_edit_target(asset, edit)

    packet: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run["run_id"],
        "state": state,
        "asset_id": run["asset_id"],
        "request_id": run["request_id"],
        "backend": "host_native_imagegen",
    }

    if state == "READY":
        mode = "generate" if edit["operation"] == "create" else "edit"
        packet.update(
            {
                "action": f"imagegen_{mode}",
                "edit_target": base_target if mode == "edit" else None,
                "references": references,
                "prompt": compile_brief(asset, edit),
                "after_success": "mark_generated",
            }
        )

    elif state == "QA_PENDING":
        result_path = run.get("current_result_path")
        if not result_path:
            raise ValidationError("QA_PENDING run has no current_result_path")
        packet.update(
            {
                "action": "visual_qa",
                "result_path": result_path,
                "comparison_references": references,
                "requested_change": edit["change"],
                "hard_gates": _merged_lock_list(asset, edit, "hard"),
                "soft_gates": _merged_lock_list(asset, edit, "soft"),
                "allowed_statuses": [
                    "PASS",
                    "PASS_WITH_NOTES",
                    "REPAIR_MINOR",
                    "REGENERATE_MAJOR",
                    "BLOCKED",
                ],
                "after_success": "apply_qa",
            }
        )

    elif state == "REPAIR_READY":
        failed_result = run.get("current_result_path")
        qa = run.get("last_qa")
        if not failed_result:
            raise ValidationError("REPAIR_READY run has no failed result path")
        if not qa:
            raise ValidationError("REPAIR_READY run has no stored QA report")
        packet.update(
            {
                "action": "imagegen_edit",
                "edit_target": {
                    "kind": "failed_generated_result",
                    "path": failed_result,
                },
                "references": references,
                "prompt": compile_repair_brief(asset, edit, qa),
                "repair_pass": run["repair_passes"],
                "after_success": "mark_generated",
            }
        )

    elif state == "REGENERATE_READY":
        mode = "generate" if edit["operation"] == "create" else "edit"
        packet.update(
            {
                "action": f"imagegen_{mode}",
                "edit_target": base_target if mode == "edit" else None,
                "references": references,
                "prompt": compile_brief(asset, edit),
                "regeneration_pass": run["regeneration_passes"],
                "restart_policy": "approved_source_not_failed_result",
                "after_success": "mark_generated",
            }
        )

    elif state == "ACCEPTED":
        result_path = run.get("current_result_path")
        if not result_path:
            raise ValidationError("ACCEPTED run has no current_result_path")
        packet.update(
            {
                "action": "deliver",
                "result_path": result_path,
                "qa": run.get("last_qa"),
            }
        )

    elif state == "BLOCKED":
        packet.update(
            {
                "action": "report_blocked",
                "reason": run.get("next_action"),
                "qa": run.get("last_qa"),
                "current_result_path": run.get("current_result_path"),
            }
        )

    else:
        raise ValidationError(f"unsupported run state '{state}'")

    return packet


def build_from_paths(
    asset_path: Path,
    edit_path: Path,
    run_path: Path,
) -> dict[str, Any]:
    asset_doc = load_document(asset_path)
    edit_doc = load_document(edit_path)
    for doc in (asset_doc, edit_doc):
        validate_document(doc.data, doc.path)
    cross_validate([asset_doc, edit_doc])

    run = load_run(run_path)
    return build_action_packet(asset_doc.data, edit_doc.data, run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", required=True, type=Path)
    parser.add_argument("--edit", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        packet = build_from_paths(args.asset, args.edit, args.run)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(packet, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
