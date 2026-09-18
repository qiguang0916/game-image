#!/usr/bin/env python3
"""Dry-run the full game-image host protocol without calling an image model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import execution_loop
import next_action
import validate_project


def repair_qa() -> dict:
    qa = {
        "document_type": "qa_report",
        "schema_version": 1,
        "report_id": "DEMO_QA_REPAIR",
        "asset_id": "KNIFE_001",
        "request_id": "KNIFE_001_EDIT_RIVETS_001",
        "status": "REPAIR_MINOR",
        "summary": "Rear rivet center drifted.",
        "repair_directives": [
            "Restore only the rear rivet center to the approved master position."
        ],
        "gates": [
            {
                "name": "asset_identity",
                "severity": "hard",
                "status": "PASS",
                "note": "",
            },
            {
                "name": "rivet_count_and_centers",
                "severity": "hard",
                "status": "FAIL",
                "note": "Rear rivet drifted.",
            },
        ],
    }
    validate_project.validate_document(qa, Path("demo-repair.toml"))
    return qa


def pass_qa() -> dict:
    qa = {
        "document_type": "qa_report",
        "schema_version": 1,
        "report_id": "DEMO_QA_PASS",
        "asset_id": "KNIFE_001",
        "request_id": "KNIFE_001_EDIT_RIVETS_001",
        "status": "PASS",
        "summary": "Requested edit passed all hard gates.",
        "repair_directives": [],
        "gates": [
            {
                "name": "asset_identity",
                "severity": "hard",
                "status": "PASS",
                "note": "",
            },
            {
                "name": "rivet_count_and_centers",
                "severity": "hard",
                "status": "PASS",
                "note": "",
            },
        ],
    }
    validate_project.validate_document(qa, Path("demo-pass.toml"))
    return qa


def main() -> int:
    asset = validate_project.load_document(
        ROOT / "examples" / "KNIFE_001" / "asset.toml"
    ).data
    edit = validate_project.load_document(
        ROOT
        / "examples"
        / "KNIFE_001"
        / "edits"
        / "rivets-brushed-silver.toml"
    ).data

    run = execution_loop.init_run(asset, edit)
    packet = next_action.build_action_packet(asset, edit, run)
    assert packet["action"] == "imagegen_edit"
    assert packet["edit_target"]["reference_id"] == "ASSEMBLED_MASTER"
    print("1 READY -> imagegen_edit")

    run = execution_loop.mark_generated(run, "demo/iteration-1.png")
    packet = next_action.build_action_packet(asset, edit, run)
    assert packet["action"] == "visual_qa"
    print("2 QA_PENDING -> visual_qa")

    run = execution_loop.apply_qa(run, repair_qa())
    packet = next_action.build_action_packet(asset, edit, run)
    assert packet["action"] == "imagegen_edit"
    assert packet["edit_target"]["path"] == "demo/iteration-1.png"
    print("3 REPAIR_READY -> imagegen_edit(failed result)")

    run = execution_loop.mark_generated(run, "demo/iteration-2.png")
    packet = next_action.build_action_packet(asset, edit, run)
    assert packet["action"] == "visual_qa"
    print("4 QA_PENDING -> visual_qa")

    run = execution_loop.apply_qa(run, pass_qa())
    packet = next_action.build_action_packet(asset, edit, run)
    assert packet["action"] == "deliver"
    assert packet["result_path"] == "demo/iteration-2.png"
    print("5 ACCEPTED -> deliver")
    print("E2E DRY RUN PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
