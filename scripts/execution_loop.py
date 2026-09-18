#!/usr/bin/env python3
"""Persist and route the game-image execution state machine.

This script never calls an image model. The Agent/host owns the image tool call.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
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

    updated = deepcopy(run)
    qa_status = qa["status"]
    updated["last_qa"] = {
        "report_id": qa["report_id"],
        "status": qa_status,
        "summary": qa.get("summary", ""),
    }

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

    elif qa_status == "BLOCKED":
        updated["state"] = "BLOCKED"
        updated["next_action"] = "report_qa_blocker"

    else:
        raise ValidationError(f"unsupported QA status '{qa_status}'")

    updated["history"].append(
        {
            "event": "qa_applied",
            "qa_report_id": qa["report_id"],
            "qa_status": qa_status,
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
) -> dict[str, Any]:
    asset_doc = load_document(asset_path)
    edit_doc = load_document(edit_path)
    validate_document(asset_doc.data, asset_doc.path)
    validate_document(edit_doc.data, edit_doc.path)
    cross_validate([asset_doc, edit_doc])
    return init_run(asset_doc.data, edit_doc.data, run_id=run_id)


def apply_qa_from_path(
    run: dict[str, Any],
    qa_path: Path,
) -> dict[str, Any]:
    qa_doc = load_document(qa_path)
    validate_document(qa_doc.data, qa_doc.path)
    return apply_qa(run, qa_doc.data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a new execution run JSON.")
    init.add_argument("--asset", required=True, type=Path)
    init.add_argument("--edit", required=True, type=Path)
    init.add_argument("--output", required=True, type=Path)
    init.add_argument("--run-id")

    generated = sub.add_parser(
        "mark-generated",
        help="Record the selected generated/edited image and enter QA_PENDING.",
    )
    generated.add_argument("--run", required=True, type=Path)
    generated.add_argument("--result", required=True)

    qa = sub.add_parser(
        "apply-qa",
        help="Apply a QA TOML report and route the next action.",
    )
    qa.add_argument("--run", required=True, type=Path)
    qa.add_argument("--qa", required=True, type=Path)

    status = sub.add_parser("status", help="Print current run state.")
    status.add_argument("--run", required=True, type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            run = init_from_paths(args.asset, args.edit, args.run_id)
            save_run(args.output, run)
        elif args.command == "mark-generated":
            run = load_run(args.run)
            run = mark_generated(run, args.result)
            save_run(args.run, run)
        elif args.command == "apply-qa":
            run = load_run(args.run)
            run = apply_qa_from_path(run, args.qa)
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
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
