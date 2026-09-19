#!/usr/bin/env python3
"""Persist and route the game-image execution state machine.

This script never calls an image model. The Agent/host owns the image tool call.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_project import (
    ValidationError,
    cross_validate,
    load_document,
    validate_document,
)


STATES = {
    "READY",
    "QA_PENDING",
    "REPAIR_READY",
    "REGENERATE_READY",
    "ACCEPTED",
    "BLOCKED",
}

HOST_BLOCK_REASON_CODES = {
    "host_native_imagegen_unavailable",
    "host_native_imagegen_failed",
    "host_native_imagegen_moderation_blocked",
    "generated_result_missing",
    "generated_result_unreadable",
    "visual_inspection_unavailable",
    "required_reference_missing",
    "edit_target_missing",
    "reference_unreadable",
    "reference_image_invalid",
    "reference_sufficiency_failed",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _execution_mode(operation: str) -> str:
    return "generate" if operation == "create" else "edit"


def _next_action_for_ready(operation: str) -> str:
    return (
        "invoke_imagegen_generate"
        if _execution_mode(operation) == "generate"
        else "invoke_imagegen_edit"
    )


def init_run(
    asset: dict[str, Any],
    edit: dict[str, Any],
    run_id: str | None = None,
) -> dict[str, Any]:
    if asset["document_type"] != "asset_manifest":
        raise ValidationError("asset document must be asset_manifest")
    if edit["document_type"] != "edit_request":
        raise ValidationError("edit document must be edit_request")
    if asset["asset_id"] != edit["asset_id"]:
        raise ValidationError("asset_id mismatch between manifest and edit request")

    qa = asset.get("qa", {})
    max_repairs = qa.get("max_repair_passes", 2)
    max_regenerations = qa.get("max_regeneration_passes", 1)

    if not isinstance(max_repairs, int) or not 0 <= max_repairs <= 5:
        raise ValidationError("max_repair_passes must be an integer 0..5")
    if not isinstance(max_regenerations, int) or not 0 <= max_regenerations <= 3:
        raise ValidationError("max_regeneration_passes must be an integer 0..3")

    from topology_contract import (
        expected_hard_gates,
        expected_topology_hard_gates,
    )

    operation = edit["operation"]
    state = {
        "schema_version": 1,
        "run_id": run_id or f"{asset['asset_id']}__{edit['request_id']}",
        "asset_id": asset["asset_id"],
        "request_id": edit["request_id"],
        "state": "READY",
        "iteration": 0,
        "repair_passes": 0,
        "regeneration_passes": 0,
        "max_repair_passes": max_repairs,
        "max_regeneration_passes": max_regenerations,
        "backend_mode": "host_native_imagegen",
        "execution_mode": _execution_mode(operation),
        "current_result_path": None,
        "last_qa": None,
        "preflight": None,
        "blocker": None,
        "required_hard_gates": expected_hard_gates(asset, edit),
        "topology_hard_gates": expected_topology_hard_gates(asset),
        "next_action": _next_action_for_ready(operation),
        "history": [
            {
                "event": "initialized",
                "state": "READY",
                "operation": operation,
            }
        ],
    }
    validate_run_state(state)
    return state


def validate_run_state(run: dict[str, Any]) -> None:
    required = [
        "schema_version",
        "run_id",
        "asset_id",
        "request_id",
        "state",
        "iteration",
        "repair_passes",
        "regeneration_passes",
        "max_repair_passes",
        "max_regeneration_passes",
        "backend_mode",
        "execution_mode",
        "next_action",
        "history",
    ]
    for key in required:
        if key not in run:
            raise ValidationError(f"run state missing '{key}'")

    if run["schema_version"] != 1:
        raise ValidationError("run schema_version must be 1")
    if run["state"] not in STATES:
        raise ValidationError(f"invalid run state '{run['state']}'")
    if run["execution_mode"] not in {"generate", "edit"}:
        raise ValidationError("execution_mode must be generate or edit")

    for key in (
        "iteration",
        "repair_passes",
        "regeneration_passes",
        "max_repair_passes",
        "max_regeneration_passes",
    ):
        if not isinstance(run[key], int) or run[key] < 0:
            raise ValidationError(f"{key} must be a non-negative integer")

    if run["repair_passes"] > run["max_repair_passes"]:
        raise ValidationError("repair_passes exceeds max_repair_passes")
    if run["regeneration_passes"] > run["max_regeneration_passes"]:
        raise ValidationError(
            "regeneration_passes exceeds max_regeneration_passes"
        )
    if not isinstance(run["history"], list):
        raise ValidationError("history must be a list")

    last_qa = run.get("last_qa")
    if last_qa is not None and not isinstance(last_qa, dict):
        raise ValidationError("last_qa must be an object or null")

    blocker = run.get("blocker")
    if blocker is not None and not isinstance(blocker, dict):
        raise ValidationError("blocker must be an object or null")


def mark_blocked(
    run: dict[str, Any],
    *,
    reason_code: str,
    action: str,
    message: str,
    retryable: bool,
) -> dict[str, Any]:
    validate_run_state(run)
    if reason_code not in HOST_BLOCK_REASON_CODES:
        raise ValidationError(f"unsupported blocker reason_code '{reason_code}'")
    if run["state"] == "ACCEPTED":
        raise ValidationError("cannot block an ACCEPTED run")

    updated = deepcopy(run)
    updated["state"] = "BLOCKED"
    updated["next_action"] = "report_blocked"
    updated["blocker"] = {
        "reason_code": reason_code,
        "action": action,
        "message": message.strip(),
        "retryable": bool(retryable),
        "timestamp": _utc_now(),
        "budget_snapshot": {
            "repair_passes": updated["repair_passes"],
            "max_repair_passes": updated["max_repair_passes"],
            "regeneration_passes": updated["regeneration_passes"],
            "max_regeneration_passes": updated["max_regeneration_passes"],
        },
    }
    updated["history"].append(
        {
            "event": "blocked",
            "state": "BLOCKED",
            "reason_code": reason_code,
            "action": action,
            "retryable": bool(retryable),
            "timestamp": updated["blocker"]["timestamp"],
        }
    )
    validate_run_state(updated)
    return updated


def mark_generated(run: dict[str, Any], result_path: str) -> dict[str, Any]:
    validate_run_state(run)
    if run["state"] not in {"READY", "REPAIR_READY", "REGENERATE_READY"}:
        raise ValidationError(
            f"cannot record generation while run is {run['state']}"
        )
    if not result_path.strip():
        raise ValidationError("result_path must not be empty")

    updated = deepcopy(run)
    source_state = updated["state"]
    updated["iteration"] += 1
    updated["state"] = "QA_PENDING"
    updated["current_result_path"] = result_path
    updated["last_qa"] = None
    updated["blocker"] = None
    updated["next_action"] = "inspect_pixels_and_write_qa"
    updated["history"].append(
        {
            "event": "generated",
            "from_state": source_state,
            "state": "QA_PENDING",
            "result_path": result_path,
            "iteration": updated["iteration"],
        }
    )
    validate_run_state(updated)
    return updated


def _required_gate_statuses(
    run: dict[str, Any],
    qa: dict[str, Any],
) -> dict[str, str]:
    by_name = {
        gate["name"]: gate.get("status")
        for gate in qa.get("gates", [])
    }
    return {
        name: by_name[name]
        for name in run.get("required_hard_gates", [])
        if name in by_name
    }


def apply_qa(
    run: dict[str, Any],
    qa: dict[str, Any],
) -> dict[str, Any]:
    validate_run_state(run)
    if run["state"] != "QA_PENDING":
        raise ValidationError(f"cannot apply QA while run is {run['state']}")
    if qa["document_type"] != "qa_report":
        raise ValidationError("QA document must be qa_report")
    if qa["asset_id"] != run["asset_id"]:
        raise ValidationError("QA asset_id does not match run")
    if qa["request_id"] != run["request_id"]:
        raise ValidationError("QA request_id does not match run")

    from topology_contract import validate_qa_completeness

    validate_qa_completeness(
        list(run.get("required_hard_gates", [])),
        qa,
    )

    qa_status = qa["status"]
    updated = deepcopy(run)
    updated["last_qa"] = {
        "document_type": "qa_report",
        "schema_version": qa["schema_version"],
        "report_id": qa["report_id"],
        "asset_id": qa["asset_id"],
        "request_id": qa["request_id"],
        "status": qa_status,
        "reported_status": qa["status"],
        "summary": qa.get("summary", ""),
        "gates": deepcopy(qa.get("gates", [])),
        "repair_directives": deepcopy(qa.get("repair_directives", [])),
    }

    required_statuses = _required_gate_statuses(run, qa)
    if any(
        status == "NOT_VERIFIABLE"
        for status in required_statuses.values()
    ):
        return mark_blocked(
            updated,
            reason_code="visual_inspection_unavailable",
            action="visual_qa",
            message="A required hard gate was NOT_VERIFIABLE.",
            retryable=False,
        )

    topology_names = set(run.get("topology_hard_gates", []))
    topology_statuses = {
        name: required_statuses.get(name)
        for name in topology_names
        if name in required_statuses
    }

    if any(status == "FAIL" for status in topology_statuses.values()):
        qa_status = "REGENERATE_MAJOR"
        updated["last_qa"]["status"] = qa_status

    if qa_status in {"PASS", "PASS_WITH_NOTES"}:
        updated["state"] = "ACCEPTED"
        updated["next_action"] = "deliver_final_asset"

    elif qa_status == "REPAIR_MINOR":
        if updated["repair_passes"] < updated["max_repair_passes"]:
            updated["repair_passes"] += 1
            updated["state"] = "REPAIR_READY"
            updated["next_action"] = (
                "compile_repair_brief_and_invoke_imagegen_edit"
            )
        else:
            updated["state"] = "BLOCKED"
            updated["next_action"] = "report_repair_budget_exhausted"
            updated["blocker"] = {
                "reason_code": "repair_budget_exhausted",
                "action": "visual_qa",
                "message": "Repair budget exhausted.",
                "retryable": False,
                "timestamp": _utc_now(),
            }

    elif qa_status == "REGENERATE_MAJOR":
        if (
            updated["regeneration_passes"]
            < updated["max_regeneration_passes"]
        ):
            updated["regeneration_passes"] += 1
            updated["state"] = "REGENERATE_READY"
            updated["next_action"] = (
                "restart_from_approved_master_with_original_brief"
            )
        else:
            updated["state"] = "BLOCKED"
            updated["next_action"] = "report_regeneration_budget_exhausted"
            updated["blocker"] = {
                "reason_code": "regeneration_budget_exhausted",
                "action": "visual_qa",
                "message": "Regeneration budget exhausted.",
                "retryable": False,
                "timestamp": _utc_now(),
            }

    elif qa_status == "BLOCKED":
        return mark_blocked(
            updated,
            reason_code="visual_inspection_unavailable",
            action="visual_qa",
            message=qa.get("summary", "Visual QA blocked."),
            retryable=False,
        )

    else:
        raise ValidationError(f"unsupported QA status '{qa_status}'")

    updated["history"].append(
        {
            "event": "qa_applied",
            "qa_report_id": qa["report_id"],
            "qa_status": qa_status,
            "reported_status": qa["status"],
            "state": updated["state"],
        }
    )
    validate_run_state(updated)
    return updated


def load_run(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        run = json.load(handle)
    if not isinstance(run, dict):
        raise ValidationError("run JSON root must be an object")
    validate_run_state(run)
    return run


def save_run(path: Path, run: dict[str, Any]) -> None:
    validate_run_state(run)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(run, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def init_from_paths(
    asset_path: Path,
    edit_path: Path,
    run_id: str | None = None,
    *,
    dry_run: bool = False,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    asset_doc = load_document(asset_path)
    edit_doc = load_document(edit_path)
    validate_document(asset_doc.data, asset_doc.path)
    validate_document(edit_doc.data, edit_doc.path)
    cross_validate([asset_doc, edit_doc])

    run = init_run(asset_doc.data, edit_doc.data, run_id=run_id)

    from runtime_preflight import run_preflight

    base_dir = workspace_root or asset_path.parent
    preflight = run_preflight(
        asset_doc.data,
        edit_doc.data,
        base_dir,
        dry_run=dry_run,
    )
    run["preflight"] = preflight

    if preflight["status"] == "BLOCKED":
        run = mark_blocked(
            run,
            reason_code=preflight["reason_code"],
            action=run["next_action"],
            message=preflight.get(
                "detail",
                f"Runtime preflight blocked: {preflight['reason_code']}",
            ),
            retryable=False,
        )
    return run


def apply_qa_from_path(
    run: dict[str, Any],
    qa_path: Path,
) -> dict[str, Any]:
    qa_doc = load_document(qa_path)
    validate_document(qa_doc.data, qa_doc.path)
    return apply_qa(run, qa_doc.data)


def _record_generated_cli(
    run: dict[str, Any],
    result: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return mark_generated(run, result)

    path = Path(result)
    if not path.exists():
        return mark_blocked(
            run,
            reason_code="generated_result_missing",
            action=run["next_action"],
            message=f"Generated result does not exist: {path}",
            retryable=True,
        )
    if not path.is_file() or not os.access(path, os.R_OK):
        return mark_blocked(
            run,
            reason_code="generated_result_unreadable",
            action=run["next_action"],
            message=f"Generated result is unreadable: {path}",
            retryable=True,
        )

    from runtime_preflight import validate_image_file

    valid, detail = validate_image_file(path)
    if not valid:
        return mark_blocked(
            run,
            reason_code="generated_result_unreadable",
            action=run["next_action"],
            message=f"Generated image is invalid: {detail}",
            retryable=True,
        )
    return mark_generated(run, result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a new execution run JSON.")
    init.add_argument("--asset", required=True, type=Path)
    init.add_argument("--edit", required=True, type=Path)
    init.add_argument("--output", required=True, type=Path)
    init.add_argument("--run-id")
    init.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip real reference file checks; for tests/examples only.",
    )
    init.add_argument(
        "--workspace-root",
        type=Path,
        help="Resolve reference paths relative to this directory.",
    )

    generated = sub.add_parser(
        "mark-generated",
        help="Record the selected generated/edited image and enter QA_PENDING.",
    )
    generated.add_argument("--run", required=True, type=Path)
    generated.add_argument("--result", required=True)
    generated.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip real result-file checks; for tests/examples only.",
    )

    qa = sub.add_parser(
        "apply-qa",
        help="Apply a QA TOML report and route the next action.",
    )
    qa.add_argument("--run", required=True, type=Path)
    qa.add_argument("--qa", required=True, type=Path)

    blocked = sub.add_parser(
        "mark-blocked",
        help="Persist a host/backend blocker without editing run JSON by hand.",
    )
    blocked.add_argument("--run", required=True, type=Path)
    blocked.add_argument(
        "--reason-code",
        required=True,
        choices=sorted(HOST_BLOCK_REASON_CODES),
    )
    blocked.add_argument("--action", required=True)
    blocked.add_argument("--message", required=True)
    blocked.add_argument("--retryable", action="store_true")

    status = sub.add_parser("status", help="Print current run state.")
    status.add_argument("--run", required=True, type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            run = init_from_paths(
                args.asset,
                args.edit,
                args.run_id,
                dry_run=args.dry_run,
                workspace_root=args.workspace_root,
            )
            save_run(args.output, run)
        elif args.command == "mark-generated":
            run = load_run(args.run)
            run = _record_generated_cli(
                run,
                args.result,
                dry_run=args.dry_run,
            )
            save_run(args.run, run)
        elif args.command == "apply-qa":
            run = load_run(args.run)
            run = apply_qa_from_path(run, args.qa)
            save_run(args.run, run)
        elif args.command == "mark-blocked":
            run = load_run(args.run)
            run = mark_blocked(
                run,
                reason_code=args.reason_code,
                action=args.action,
                message=args.message,
                retryable=args.retryable,
            )
            save_run(args.run, run)
        elif args.command == "status":
            run = load_run(args.run)
            print(json.dumps(run, indent=2, ensure_ascii=False))
            return 0
        else:
            raise ValidationError(f"unknown command '{args.command}'")
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.command != "status":
        print(
            json.dumps(
                {
                    "state": run["state"],
                    "next_action": run["next_action"],
                    "iteration": run["iteration"],
                    "repair_passes": run["repair_passes"],
                    "regeneration_passes": run["regeneration_passes"],
                    "blocker": run.get("blocker"),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
