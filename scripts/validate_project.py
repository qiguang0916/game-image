#!/usr/bin/env python3
"""Validate game-image TOML manifests with Python standard library only."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ALLOWED_DOCUMENT_TYPES = {"asset_manifest", "edit_request", "qa_report"}
ALLOWED_REFERENCE_STATES = {"approved", "draft", "rejected", "superseded"}
ALLOWED_OPERATIONS = {
    "create",
    "local_edit",
    "structural_edit",
    "variant",
    "repair",
    "regenerate",
}
OPERATIONS_REQUIRING_BASE_EDIT_TARGET = {
    "local_edit",
    "structural_edit",
    "variant",
    "regenerate",
}
ALLOWED_QA_STATUSES = {
    "PASS",
    "PASS_WITH_NOTES",
    "REPAIR_MINOR",
    "REGENERATE_MAJOR",
    "BLOCKED",
}
ALLOWED_GATE_SEVERITIES = {"hard", "soft"}
ALLOWED_GATE_STATUSES = {"PASS", "FAIL", "NOTE", "NOT_CHECKED", "NOT_VERIFIABLE"}
ALLOWED_TOPOLOGY_RELATIONSHIPS = {
    "integral", "continuous", "separate", "mounted_on",
    "enclosed_by", "aligned_with", "shared_centers", "interface",
}
ALLOWED_EVIDENCE = {"authoritative", "provisional", "unknown"}


@dataclass(frozen=True)
class LoadedDocument:
    path: Path
    data: dict[str, Any]


class ValidationError(ValueError):
    pass


def require(data: dict[str, Any], key: str, where: str) -> Any:
    value = data.get(key)
    if value is None or value == "" or value == []:
        raise ValidationError(f"{where}: missing required field '{key}'")
    return value


def ensure_string_list(value: Any, where: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValidationError(f"{where}: expected a list of non-empty strings")
    if not allow_empty and not value:
        raise ValidationError(f"{where}: list must not be empty")
    return value



def _gate_key(gate: dict[str, Any], where: str = "gate") -> str:
    key = gate.get("id") or gate.get("name")
    if not isinstance(key, str) or not key.strip():
        raise ValidationError(f"{where}: missing required field 'id' or 'name'")
    return key


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "gate"


def validate_topology(topology: Any, where: str) -> None:
    if topology is None:
        return
    if not isinstance(topology, dict):
        raise ValidationError(f"{where}: topology must be a table")
    components = topology.get("components", [])
    relationships = topology.get("relationships", [])
    if not isinstance(components, list):
        raise ValidationError(f"{where}: topology.components must be an array of tables")
    if not isinstance(relationships, list):
        raise ValidationError(f"{where}: topology.relationships must be an array of tables")

    seen_components: set[str] = set()
    for index, component in enumerate(components):
        cwhere = f"{where}: topology.components[{index}]"
        if not isinstance(component, dict):
            raise ValidationError(f"{cwhere}: expected table")
        component_id = require(component, "id", cwhere)
        if component_id in seen_components:
            raise ValidationError(f"{cwhere}: duplicate component id '{component_id}'")
        seen_components.add(component_id)
        if not isinstance(component.get("required", True), bool):
            raise ValidationError(f"{cwhere}: required must be boolean")
        count = component.get("count")
        if count is not None and (not isinstance(count, int) or count < 1):
            raise ValidationError(f"{cwhere}: count must be an integer >= 1")
        evidence = component.get("evidence", "authoritative")
        if evidence not in ALLOWED_EVIDENCE:
            raise ValidationError(f"{cwhere}: invalid evidence '{evidence}'")

    seen_relationships: set[str] = set()
    for index, relationship in enumerate(relationships):
        rwhere = f"{where}: topology.relationships[{index}]"
        if not isinstance(relationship, dict):
            raise ValidationError(f"{rwhere}: expected table")
        relationship_id = require(relationship, "id", rwhere)
        if relationship_id in seen_relationships:
            raise ValidationError(f"{rwhere}: duplicate relationship id '{relationship_id}'")
        seen_relationships.add(relationship_id)
        kind = require(relationship, "type", rwhere)
        if kind not in ALLOWED_TOPOLOGY_RELATIONSHIPS:
            raise ValidationError(f"{rwhere}: unsupported relationship type '{kind}'")
        members = ensure_string_list(relationship.get("members"), f"{rwhere}: members")
        if len(members) < 2:
            raise ValidationError(f"{rwhere}: relationships require at least two members")
        undeclared_members = [
            member for member in members if member not in seen_components
        ]
        if undeclared_members:
            raise ValidationError(
                f"{rwhere}: relationship member(s) must be declared components: "
                + ", ".join(undeclared_members)
            )
        if not isinstance(relationship.get("required", True), bool):
            raise ValidationError(f"{rwhere}: required must be boolean")
        evidence = relationship.get("evidence", "authoritative")
        if evidence not in ALLOWED_EVIDENCE:
            raise ValidationError(f"{rwhere}: invalid evidence '{evidence}'")
    if not isinstance(topology.get("prohibited_extra_components", False), bool):
        raise ValidationError(f"{where}: topology.prohibited_extra_components must be boolean")


def validate_reference_sufficiency(contract: Any, where: str) -> None:
    if contract is None:
        return
    if not isinstance(contract, dict):
        raise ValidationError(f"{where}: reference_sufficiency must be a table")
    ensure_string_list(
        contract.get("required_roles", []),
        f"{where}: reference_sufficiency.required_roles",
        allow_empty=True,
    )
    for key in ("authoritative_facts", "provisional_fields", "prohibited_assumptions"):
        ensure_string_list(
            contract.get(key, []),
            f"{where}: reference_sufficiency.{key}",
            allow_empty=True,
        )
    if contract.get("on_missing", "blocked") not in {"blocked", "provisional"}:
        raise ValidationError(
            f"{where}: reference_sufficiency.on_missing must be blocked or provisional"
        )


def validate_asset_manifest(data: dict[str, Any], path: Path) -> None:
    where = str(path)
    require(data, "asset_id", where)
    primary_master = require(data, "primary_master", where)

    locks = require(data, "locks", where)
    if not isinstance(locks, dict):
        raise ValidationError(f"{where}: locks must be a table")
    ensure_string_list(locks.get("hard"), f"{where}: locks.hard")
    ensure_string_list(
        locks.get("soft", []),
        f"{where}: locks.soft",
        allow_empty=True,
    )
    validate_topology(data.get("topology"), where)

    references = require(data, "references", where)
    if not isinstance(references, list):
        raise ValidationError(f"{where}: references must be an array of tables")

    ids: set[str] = set()
    reference_by_id: dict[str, dict[str, Any]] = {}
    approved = 0
    for index, ref in enumerate(references):
        rwhere = f"{where}: references[{index}]"
        if not isinstance(ref, dict):
            raise ValidationError(f"{rwhere}: expected table")
        ref_id = require(ref, "id", rwhere)
        if ref_id in ids:
            raise ValidationError(f"{rwhere}: duplicate reference id '{ref_id}'")
        ids.add(ref_id)
        reference_by_id[ref_id] = ref
        require(ref, "path", rwhere)
        state = require(ref, "state", rwhere)
        if state not in ALLOWED_REFERENCE_STATES:
            raise ValidationError(f"{rwhere}: invalid state '{state}'")
        if state == "approved":
            approved += 1
        roles = ensure_string_list(ref.get("roles"), f"{rwhere}: roles")
        if len(set(roles)) != len(roles):
            raise ValidationError(f"{rwhere}: duplicate reference roles")

    if approved == 0:
        raise ValidationError(f"{where}: at least one approved reference is required")
    if primary_master not in ids:
        raise ValidationError(
            f"{where}: primary_master '{primary_master}' does not match a reference id"
        )
    if reference_by_id[primary_master].get("state") != "approved":
        raise ValidationError(f"{where}: primary_master must be approved")

    qa = data.get("qa", {})
    if qa:
        if not isinstance(qa, dict):
            raise ValidationError(f"{where}: qa must be a table")

        repair_passes = qa.get("max_repair_passes", 2)
        if not isinstance(repair_passes, int) or not 0 <= repair_passes <= 5:
            raise ValidationError(
                f"{where}: qa.max_repair_passes must be an integer 0..5"
            )

        regeneration_passes = qa.get("max_regeneration_passes", 1)
        if (
            not isinstance(regeneration_passes, int)
            or not 0 <= regeneration_passes <= 3
        ):
            raise ValidationError(
                f"{where}: qa.max_regeneration_passes must be an integer 0..3"
            )


def validate_edit_request(data: dict[str, Any], path: Path) -> None:
    where = str(path)
    require(data, "request_id", where)
    require(data, "asset_id", where)
    operation = require(data, "operation", where)
    if operation not in ALLOWED_OPERATIONS:
        raise ValidationError(f"{where}: invalid operation '{operation}'")
    require(data, "target", where)
    require(data, "change", where)

    execution = data.get("execution", {})
    if execution and not isinstance(execution, dict):
        raise ValidationError(f"{where}: execution must be a table")
    if operation in OPERATIONS_REQUIRING_BASE_EDIT_TARGET:
        if not isinstance(execution, dict):
            raise ValidationError(f"{where}: execution must be a table")
        require(
            execution,
            "edit_target_reference_id",
            f"{where}: execution",
        )

    validate_reference_sufficiency(data.get("reference_sufficiency"), where)

    preserve = require(data, "preserve", where)
    if not isinstance(preserve, dict):
        raise ValidationError(f"{where}: preserve must be a table")
    hard = ensure_string_list(
        preserve.get("hard", []),
        f"{where}: preserve.hard",
        allow_empty=operation in {"create", "regenerate"},
    )
    ensure_string_list(
        preserve.get("soft", []),
        f"{where}: preserve.soft",
        allow_empty=True,
    )
    if operation == "local_edit" and not hard:
        raise ValidationError(
            f"{where}: local_edit requires at least one hard preserve rule"
        )

    bindings = data.get("reference_bindings", [])
    if operation != "create" and not bindings:
        raise ValidationError(
            f"{where}: non-create operations require reference_bindings"
        )
    if not isinstance(bindings, list):
        raise ValidationError(
            f"{where}: reference_bindings must be an array of tables"
        )

    seen: set[str] = set()
    for index, binding in enumerate(bindings):
        bwhere = f"{where}: reference_bindings[{index}]"
        if not isinstance(binding, dict):
            raise ValidationError(f"{bwhere}: expected table")
        ref_id = require(binding, "reference_id", bwhere)
        if ref_id in seen:
            raise ValidationError(
                f"{bwhere}: duplicate reference binding '{ref_id}'"
            )
        seen.add(ref_id)
        roles = ensure_string_list(binding.get("roles"), f"{bwhere}: roles")
        if len(set(roles)) != len(roles):
            raise ValidationError(f"{bwhere}: duplicate binding roles")


def validate_qa_report(data: dict[str, Any], path: Path) -> None:
    where = str(path)
    require(data, "report_id", where)
    require(data, "asset_id", where)
    require(data, "request_id", where)
    status = require(data, "status", where)
    if status not in ALLOWED_QA_STATUSES:
        raise ValidationError(f"{where}: invalid QA status '{status}'")

    gates = require(data, "gates", where)
    if not isinstance(gates, list):
        raise ValidationError(f"{where}: gates must be an array of tables")

    hard_gate_count = 0
    failed_hard = False
    non_pass_gate_count = 0
    seen_names: set[str] = set()

    for index, gate in enumerate(gates):
        gwhere = f"{where}: gates[{index}]"
        if not isinstance(gate, dict):
            raise ValidationError(f"{gwhere}: expected table")
        name = _gate_key(gate, gwhere)
        if name in seen_names:
            raise ValidationError(f"{gwhere}: duplicate gate name '{name}'")
        seen_names.add(name)

        severity = require(gate, "severity", gwhere)
        gate_status = require(gate, "status", gwhere)
        if severity not in ALLOWED_GATE_SEVERITIES:
            raise ValidationError(f"{gwhere}: invalid severity '{severity}'")
        if gate_status not in ALLOWED_GATE_STATUSES:
            raise ValidationError(f"{gwhere}: invalid status '{gate_status}'")

        if gate_status not in {"PASS", "NOTE"}:
            non_pass_gate_count += 1

        if severity == "hard":
            hard_gate_count += 1
            if gate_status != "PASS":
                failed_hard = True

    if hard_gate_count == 0:
        raise ValidationError(f"{where}: at least one hard gate is required")

    if status in {"PASS", "PASS_WITH_NOTES"} and failed_hard:
        raise ValidationError(
            f"{where}: PASS/PASS_WITH_NOTES cannot contain a non-PASS hard gate"
        )

    if status in {"REPAIR_MINOR", "REGENERATE_MAJOR"} and non_pass_gate_count == 0:
        raise ValidationError(
            f"{where}: {status} requires at least one failed/not-checked gate"
        )

    directives = ensure_string_list(
        data.get("repair_directives", []),
        f"{where}: repair_directives",
        allow_empty=True,
    )
    if status == "REPAIR_MINOR" and not directives:
        raise ValidationError(
            f"{where}: REPAIR_MINOR requires at least one repair directive"
        )



def compile_reference_sufficiency(
    asset: dict[str, Any],
    edit: dict[str, Any],
) -> dict[str, Any]:
    contract = edit.get("reference_sufficiency", {}) or {}
    required_roles = list(contract.get("required_roles", []))
    covered_roles: set[str] = set()
    for binding in edit.get("reference_bindings", []):
        covered_roles.update(binding.get("roles", []))
    missing_roles = [role for role in required_roles if role not in covered_roles]
    on_missing = contract.get("on_missing", "blocked")
    status = (
        "sufficient"
        if not missing_roles
        else ("provisional" if on_missing == "provisional" else "insufficient")
    )
    return {
        "status": status,
        "required_roles": required_roles,
        "covered_roles": sorted(covered_roles),
        "missing_roles": missing_roles,
        "authoritative_facts": list(contract.get("authoritative_facts", [])),
        "provisional_fields": list(contract.get("provisional_fields", [])),
        "prohibited_assumptions": list(contract.get("prohibited_assumptions", [])),
        "on_missing": on_missing,
    }


def compile_topology_contract(asset: dict[str, Any]) -> dict[str, Any]:
    topology = asset.get("topology", {}) or {}
    required_components: list[dict[str, Any]] = []
    provisional_components: list[dict[str, Any]] = []
    for component in topology.get("components", []):
        packet = {
            "id": component["id"],
            "count": component.get("count"),
            "required": component.get("required", True),
            "evidence": component.get("evidence", "authoritative"),
        }
        (
            required_components
            if packet["required"] and packet["evidence"] == "authoritative"
            else provisional_components
        ).append(packet)

    relationships: list[dict[str, Any]] = []
    provisional_relationships: list[dict[str, Any]] = []
    for relationship in topology.get("relationships", []):
        packet = {
            "id": relationship["id"],
            "type": relationship["type"],
            "members": list(relationship["members"]),
            "required": relationship.get("required", True),
            "evidence": relationship.get("evidence", "authoritative"),
        }
        (
            relationships
            if packet["required"] and packet["evidence"] == "authoritative"
            else provisional_relationships
        ).append(packet)

    return {
        "required_components": required_components,
        "provisional_components": provisional_components,
        "relationships": relationships,
        "provisional_relationships": provisional_relationships,
        "prohibited_extra_components": bool(
            topology.get("prohibited_extra_components", False)
        ),
    }


def compile_required_hard_gates(
    asset: dict[str, Any],
    edit: dict[str, Any],
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = [
        {
            "id": "asset_identity",
            "description": "The output remains the intended asset identity.",
            "severity": "hard",
            "category": "identity",
            "failure_route": "major",
        },
        {
            "id": "requested_change",
            "description": str(edit.get("change", "requested change")),
            "severity": "hard",
            "category": "requested_change",
            "failure_route": "minor",
        },
    ]
    topology = compile_topology_contract(asset)
    for component in topology["required_components"]:
        component_id = component["id"]
        gates.append({
            "id": f"topology.component.{component_id}.present",
            "description": f"Required component '{component_id}' is present.",
            "severity": "hard",
            "category": "topology_component",
            "failure_route": "major",
        })
        if component.get("count") is not None:
            gates.append({
                "id": f"topology.component.{component_id}.count",
                "description": (
                    f"Required component '{component_id}' count is {component['count']}."
                ),
                "severity": "hard",
                "category": "topology_component_count",
                "failure_route": "major",
            })
    for relationship in topology["relationships"]:
        gates.append({
            "id": f"topology.relationship.{relationship['id']}",
            "description": (
                f"Relationship '{relationship['id']}' is {relationship['type']} "
                f"across {', '.join(relationship['members'])}."
            ),
            "severity": "hard",
            "category": "topology_relationship",
            "failure_route": "major",
        })
    if topology["prohibited_extra_components"]:
        gates.append({
            "id": "topology.no_extra_components",
            "description": "No unauthorized structural components are introduced.",
            "severity": "hard",
            "category": "topology_extra_components",
            "failure_route": "major",
        })

    qa_contract = edit.get("qa_contract", {}) or {}
    if qa_contract.get("enforce_lock_gates", False):
        seen_ids = {gate["id"] for gate in gates}
        lock_texts = [
            *asset.get("locks", {}).get("hard", []),
            *edit.get("preserve", {}).get("hard", []),
        ]
        for text in lock_texts:
            gate_id = f"lock.{_slug(text)}"
            if gate_id in seen_ids:
                continue
            seen_ids.add(gate_id)
            gates.append({
                "id": gate_id,
                "description": text,
                "severity": "hard",
                "category": "preserve_lock",
                "failure_route": "major",
            })
    return gates


def enforce_qa_contract(run: dict[str, Any], qa: dict[str, Any]) -> None:
    if not run.get("enforce_hard_gate_completeness", False):
        return
    required = run.get("required_hard_gates", []) or []
    gate_by_id = {_gate_key(gate): gate for gate in qa.get("gates", [])}
    missing = [gate["id"] for gate in required if gate["id"] not in gate_by_id]
    if missing:
        raise ValidationError(
            "QA report is missing required hard gate(s): " + ", ".join(missing)
        )

    major_failed: list[str] = []
    unverifiable: list[str] = []
    for contract_gate in required:
        gate = gate_by_id[contract_gate["id"]]
        if gate.get("severity") != "hard":
            raise ValidationError(
                f"QA gate '{contract_gate['id']}' must have severity hard"
            )
        gate_status = gate.get("status")
        if gate_status not in {"PASS", "FAIL", "NOT_VERIFIABLE"}:
            raise ValidationError(
                f"required hard gate '{contract_gate['id']}' must use "
                "PASS, FAIL, or NOT_VERIFIABLE"
            )
        if gate_status == "NOT_VERIFIABLE":
            unverifiable.append(contract_gate["id"])
        if gate_status == "FAIL" and contract_gate.get("failure_route") == "major":
            major_failed.append(contract_gate["id"])

    status = qa.get("status")
    if status in {"PASS", "PASS_WITH_NOTES"}:
        non_pass = [
            gate["id"]
            for gate in required
            if gate_by_id[gate["id"]].get("status") != "PASS"
        ]
        if non_pass:
            raise ValidationError(
                "PASS requires every required hard gate to PASS: "
                + ", ".join(non_pass)
            )
    if unverifiable and status != "BLOCKED":
        raise ValidationError(
            "NOT_VERIFIABLE/NOT_CHECKED required hard gate(s) require BLOCKED: "
            + ", ".join(unverifiable)
        )
    if major_failed and status == "REPAIR_MINOR":
        raise ValidationError(
            "core topology/identity hard-gate failures require "
            "REGENERATE_MAJOR or BLOCKED: "
            + ", ".join(major_failed)
        )


def make_complete_qa_stub(
    run: dict[str, Any],
    status: str = "PASS",
) -> dict[str, Any]:
    return {
        "document_type": "qa_report",
        "schema_version": 1,
        "report_id": f"QA_{status}",
        "asset_id": run["asset_id"],
        "request_id": run["request_id"],
        "status": status,
        "summary": status,
        "repair_directives": [],
        "gates": [
            {
                "id": gate["id"],
                "severity": "hard",
                "status": "PASS",
                "note": "",
            }
            for gate in run.get("required_hard_gates", [])
        ],
    }


def validate_document(data: dict[str, Any], path: Path) -> None:
    where = str(path)
    document_type = require(data, "document_type", where)
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValidationError(
            f"{where}: unknown document_type '{document_type}'"
        )
    if data.get("schema_version") != 1:
        raise ValidationError(f"{where}: schema_version must be 1")

    if document_type == "asset_manifest":
        validate_asset_manifest(data, path)
    elif document_type == "edit_request":
        validate_edit_request(data, path)
    elif document_type == "qa_report":
        validate_qa_report(data, path)


def load_document(path: Path) -> LoadedDocument:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: TOML root must be a table")
    return LoadedDocument(path=path, data=data)


def cross_validate(documents: list[LoadedDocument]) -> None:
    assets: dict[str, dict[str, Any]] = {}
    edits: dict[str, dict[str, Any]] = {}

    for doc in documents:
        dtype = doc.data["document_type"]
        if dtype == "asset_manifest":
            asset_id = doc.data["asset_id"]
            if asset_id in assets:
                raise ValidationError(
                    f"duplicate asset manifest for '{asset_id}'"
                )
            assets[asset_id] = doc.data
        elif dtype == "edit_request":
            request_id = doc.data["request_id"]
            if request_id in edits:
                raise ValidationError(
                    f"duplicate edit request '{request_id}'"
                )
            edits[request_id] = doc.data

    for doc in documents:
        data = doc.data
        dtype = data["document_type"]

        if dtype == "edit_request":
            asset = assets.get(data["asset_id"])
            if asset is None:
                continue

            reference_by_id = {
                ref["id"]: ref for ref in asset["references"]
            }
            bound_ids: set[str] = set()

            for binding in data.get("reference_bindings", []):
                ref_id = binding["reference_id"]
                bound_ids.add(ref_id)
                ref = reference_by_id.get(ref_id)
                if ref is None:
                    raise ValidationError(
                        f"{doc.path}: reference_binding '{ref_id}' is not in asset "
                        f"'{data['asset_id']}'"
                    )
                if ref.get("state") != "approved":
                    raise ValidationError(
                        f"{doc.path}: reference_binding '{ref_id}' is not approved"
                    )

                declared_roles = set(ref.get("roles", []))
                requested_roles = set(binding.get("roles", []))
                undeclared = requested_roles - declared_roles
                if undeclared:
                    joined = ", ".join(sorted(undeclared))
                    raise ValidationError(
                        f"{doc.path}: reference_binding '{ref_id}' requests "
                        f"undeclared role(s): {joined}"
                    )

            operation = data["operation"]
            if operation in OPERATIONS_REQUIRING_BASE_EDIT_TARGET:
                target_id = data["execution"]["edit_target_reference_id"]
                target_ref = reference_by_id.get(target_id)
                if target_ref is None:
                    raise ValidationError(
                        f"{doc.path}: edit target '{target_id}' is not in asset "
                        f"'{data['asset_id']}'"
                    )
                if target_ref.get("state") != "approved":
                    raise ValidationError(
                        f"{doc.path}: edit target '{target_id}' is not approved"
                    )
                if target_id not in bound_ids:
                    raise ValidationError(
                        f"{doc.path}: edit target '{target_id}' must also appear "
                        "in reference_bindings"
                    )

        elif dtype == "qa_report":
            request = edits.get(data["request_id"])
            if request is not None and request["asset_id"] != data["asset_id"]:
                raise ValidationError(
                    f"{doc.path}: QA asset_id does not match linked edit request"
                )
            if request is not None:
                asset = assets.get(request["asset_id"])
                if asset is not None and asset.get("topology"):
                    enforce_qa_contract(
                        {
                            "required_hard_gates": compile_required_hard_gates(asset, request),
                            "enforce_hard_gate_completeness": True,
                        },
                        data,
                    )


def iter_toml_paths(inputs: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            paths.extend(sorted(path.rglob("*.toml")))
        elif path.suffix == ".toml":
            paths.append(path)
        else:
            raise ValidationError(
                f"{path}: expected a TOML file or directory"
            )
    return sorted(dict.fromkeys(paths))


def validate_paths(paths: Iterable[Path]) -> list[LoadedDocument]:
    documents: list[LoadedDocument] = []
    for path in paths:
        doc = load_document(path)
        validate_document(doc.data, doc.path)
        documents.append(doc)
    cross_validate(documents)
    return documents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=["examples"],
        help="TOML file(s) or directories. Default: examples",
    )
    args = parser.parse_args(argv)

    try:
        paths = iter_toml_paths(args.paths)
        if not paths:
            raise ValidationError("no TOML documents found")
        documents = validate_paths(paths)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for doc in documents:
        print(f"OK  {doc.path}")
    print(f"Validated {len(documents)} document(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
