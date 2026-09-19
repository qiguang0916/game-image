#!/usr/bin/env python3
"""Compile a backend-neutral game-image brief from asset + edit TOML files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from validate_project import (
    ValidationError,
    compile_reference_sufficiency,
    compile_topology_contract,
    cross_validate,
    load_document,
    validate_document,
)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def compile_brief(asset: dict[str, Any], edit: dict[str, Any]) -> str:
    if asset["document_type"] != "asset_manifest":
        raise ValidationError("first document must be asset_manifest")
    if edit["document_type"] != "edit_request":
        raise ValidationError("second document must be edit_request")
    if asset["asset_id"] != edit["asset_id"]:
        raise ValidationError("asset_id mismatch between manifest and edit request")

    reference_by_id = {ref["id"]: ref for ref in asset["references"]}
    reference_lines: list[str] = []
    for index, binding in enumerate(edit.get("reference_bindings", []), start=1):
        ref = reference_by_id[binding["reference_id"]]
        roles = ", ".join(binding["roles"])
        reference_lines.append(
            f"REF_{index}: {ref['id']} | path={ref['path']} | roles={roles}"
        )

    asset_hard = asset.get("locks", {}).get("hard", [])
    edit_hard = edit.get("preserve", {}).get("hard", [])
    asset_soft = asset.get("locks", {}).get("soft", [])
    edit_soft = edit.get("preserve", {}).get("soft", [])

    hard_preserve = _dedupe([*asset_hard, *edit_hard])
    soft_preserve = _dedupe([*asset_soft, *edit_soft])

    output = edit.get("output", {})
    edit_target_id = edit.get("execution", {}).get("edit_target_reference_id")
    edit_target_line = None
    if edit_target_id:
        ref = reference_by_id[edit_target_id]
        edit_target_line = f"{edit_target_id} | path={ref['path']}"

    lines = [
        f"ASSET: {asset['asset_id']}",
        f"OPERATION: {edit['operation']}",
    ]

    if edit_target_line:
        lines.extend(
            [
                "",
                "EDIT TARGET:",
                edit_target_line,
            ]
        )

    lines.extend(
        [
            "",
            "TARGET:",
            str(edit["target"]),
            "",
            "CHANGE:",
            str(edit["change"]),
            "",
            "REFERENCE ROLES:",
        ]
    )
    lines.extend(reference_lines or ["(none)"])

    topology = compile_topology_contract(asset)
    if (
        topology["required_components"]
        or topology["relationships"]
        or topology["provisional_components"]
        or topology["provisional_relationships"]
    ):
        lines.extend(["", "TOPOLOGY CONTRACT:"])
        for component in topology["required_components"]:
            count = component.get("count")
            suffix = f" count={count}" if count is not None else ""
            lines.append(
                f"- REQUIRED COMPONENT: {component['id']}{suffix}"
            )
        for relationship in topology["relationships"]:
            lines.append(
                f"- REQUIRED RELATIONSHIP: {relationship['id']} | "
                f"type={relationship['type']} | "
                f"members={', '.join(relationship['members'])}"
            )
        for component in topology["provisional_components"]:
            lines.append(
                f"- PROVISIONAL COMPONENT: {component['id']}"
            )
        for relationship in topology["provisional_relationships"]:
            lines.append(
                f"- PROVISIONAL RELATIONSHIP: {relationship['id']}"
            )
        if topology["prohibited_extra_components"]:
            lines.append(
                "- No unauthorized extra structural components."
            )

    sufficiency = compile_reference_sufficiency(asset, edit)
    if (
        sufficiency["required_roles"]
        or sufficiency["authoritative_facts"]
        or sufficiency["provisional_fields"]
        or sufficiency["prohibited_assumptions"]
    ):
        lines.extend(["", "REFERENCE SUFFICIENCY:"])
        lines.append(f"- status: {sufficiency['status']}")
        if sufficiency["required_roles"]:
            lines.append(
                "- required roles: "
                + ", ".join(sufficiency["required_roles"])
            )
        for fact in sufficiency["authoritative_facts"]:
            lines.append(f"- AUTHORITATIVE FACT: {fact}")
        for field in sufficiency["provisional_fields"]:
            lines.append(f"- PROVISIONAL / UNKNOWN: {field}")
        for assumption in sufficiency["prohibited_assumptions"]:
            lines.append(
                f"- PROHIBITED ASSUMPTION: {assumption}"
            )

    lines.extend(["", "HARD PRESERVE:"])
    lines.extend(f"- {item}" for item in hard_preserve)

    lines.extend(["", "SOFT PRESERVE:"])
    lines.extend(f"- {item}" for item in soft_preserve)

    lines.extend(["", "OUTPUT:"])
    if output:
        for key in sorted(output):
            lines.append(f"- {key}: {output[key]}")
    else:
        lines.append("- preserve current framing unless the request says otherwise")

    if edit["operation"] in {"local_edit", "repair"}:
        lines.extend(
            [
                "",
                "EDIT BOUNDARY:",
                "Do not redesign or reinterpret unaffected regions.",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def compile_from_paths(asset_path: Path, edit_path: Path) -> str:
    asset_doc = load_document(asset_path)
    edit_doc = load_document(edit_path)

    validate_document(asset_doc.data, asset_doc.path)
    validate_document(edit_doc.data, edit_doc.path)
    cross_validate([asset_doc, edit_doc])

    return compile_brief(asset_doc.data, edit_doc.data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_manifest", type=Path)
    parser.add_argument("edit_request", type=Path)
    args = parser.parse_args(argv)

    try:
        brief = compile_from_paths(args.asset_manifest, args.edit_request)
    except (OSError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(brief, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
