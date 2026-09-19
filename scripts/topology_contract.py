#!/usr/bin/env python3
"""Topology contract helpers for game-image."""

from __future__ import annotations

from typing import Any

from validate_project import ValidationError

ALLOWED_RELATIONSHIP_TYPES = {
    "integral",
    "separate",
    "mounted_on",
    "enclosed_by",
    "aligned_with",
    "shared_centers",
    "interfaces_with",
}


def validate_topology_schema(asset: dict[str, Any], where: str) -> None:
    topology = asset.get("topology")
    if topology is None:
        return
    if not isinstance(topology, dict):
        raise ValidationError(f"{where}: topology must be a table")

    components = topology.get("components", [])
    relationships = topology.get("relationships", [])
    if not isinstance(components, list):
        raise ValidationError(f"{where}: topology.components must be an array")
    if not isinstance(relationships, list):
        raise ValidationError(
            f"{where}: topology.relationships must be an array"
        )

    component_ids: set[str] = set()
    for index, component in enumerate(components):
        cwhere = f"{where}: topology.components[{index}]"
        if not isinstance(component, dict):
            raise ValidationError(f"{cwhere}: expected table")
        component_id = component.get("id")
        if not isinstance(component_id, str) or not component_id.strip():
            raise ValidationError(f"{cwhere}: id is required")
        if component_id in component_ids:
            raise ValidationError(
                f"{cwhere}: duplicate component id '{component_id}'"
            )
        component_ids.add(component_id)
        count = component.get("count")
        if count is not None and (
            not isinstance(count, int) or count < 0
        ):
            raise ValidationError(
                f"{cwhere}: count must be a non-negative integer"
            )

    relationship_ids: set[str] = set()
    for index, relationship in enumerate(relationships):
        rwhere = f"{where}: topology.relationships[{index}]"
        if not isinstance(relationship, dict):
            raise ValidationError(f"{rwhere}: expected table")
        relation_id = relationship.get("id")
        relation_type = relationship.get("type")
        members = relationship.get("members")
        if not isinstance(relation_id, str) or not relation_id.strip():
            raise ValidationError(f"{rwhere}: id is required")
        if relation_id in relationship_ids:
            raise ValidationError(
                f"{rwhere}: duplicate relationship id '{relation_id}'"
            )
        relationship_ids.add(relation_id)
        if relation_type not in ALLOWED_RELATIONSHIP_TYPES:
            raise ValidationError(
                f"{rwhere}: unsupported relationship type '{relation_type}'"
            )
        if (
            not isinstance(members, list)
            or len(members) < 2
            or any(member not in component_ids for member in members)
        ):
            raise ValidationError(
                f"{rwhere}: members must reference at least two known components"
            )


def expected_topology_hard_gates(asset: dict[str, Any]) -> list[str]:
    topology = asset.get("topology", {})
    gates: list[str] = []

    for component in topology.get("components", []):
        if component.get("required", False):
            gates.append(f"topology.component.{component['id']}.count")

    for relationship in topology.get("relationships", []):
        if relationship.get("required", False):
            gates.append(f"topology.relationship.{relationship['id']}")

    if topology.get("forbid_extra_components", False):
        gates.append("topology.no_forbidden_extra_components")

    return gates


def expected_hard_gates(
    asset: dict[str, Any],
    edit: dict[str, Any],
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for gate in asset.get("locks", {}).get("hard", []):
        if gate not in seen:
            seen.add(gate)
            result.append(gate)

    for gate in edit.get("preserve", {}).get("hard", []):
        if gate not in seen:
            seen.add(gate)
            result.append(gate)

    for gate in edit.get("qa_contract", {}).get(
        "required_hard_gates", []
    ):
        if gate not in seen:
            seen.add(gate)
            result.append(gate)

    for gate in expected_topology_hard_gates(asset):
        if gate not in seen:
            seen.add(gate)
            result.append(gate)

    return result


def validate_qa_completeness(
    required_hard_gates: list[str],
    qa: dict[str, Any],
) -> None:
    gate_by_name = {
        gate["name"]: gate for gate in qa.get("gates", [])
    }

    missing = [
        gate for gate in required_hard_gates if gate not in gate_by_name
    ]
    if missing:
        raise ValidationError(
            "QA missing required hard gate(s): " + ", ".join(missing)
        )

    for name in required_hard_gates:
        gate = gate_by_name[name]
        if gate.get("severity") != "hard":
            raise ValidationError(
                f"required gate '{name}' must have severity=hard"
            )

    if qa.get("status") in {"PASS", "PASS_WITH_NOTES"}:
        bad = [
            name
            for name in required_hard_gates
            if gate_by_name[name].get("status") != "PASS"
        ]
        if bad:
            raise ValidationError(
                "PASS requires every required hard gate to PASS: "
                + ", ".join(bad)
            )


def topology_route(
    asset: dict[str, Any],
    qa: dict[str, Any],
) -> str | None:
    """Return a deterministic route override for topology failures."""
    topology_gates = set(expected_topology_hard_gates(asset))
    if not topology_gates:
        return None

    gate_by_name = {
        gate["name"]: gate for gate in qa.get("gates", [])
    }
    statuses = {
        name: gate_by_name[name].get("status")
        for name in topology_gates
        if name in gate_by_name
    }

    if any(status == "NOT_VERIFIABLE" for status in statuses.values()):
        return "BLOCKED"
    if any(status == "FAIL" for status in statuses.values()):
        return "REGENERATE_MAJOR"
    return None


def packet_topology(asset: dict[str, Any]) -> dict[str, Any]:
    topology = asset.get("topology", {})
    return {
        "required_components": [
            {
                "id": component["id"],
                "count": component.get("count"),
            }
            for component in topology.get("components", [])
            if component.get("required", False)
        ],
        "structural_relationships": [
            {
                "id": relation["id"],
                "type": relation["type"],
                "members": list(relation["members"]),
            }
            for relation in topology.get("relationships", [])
            if relation.get("required", False)
        ],
        "forbid_extra_components": bool(
            topology.get("forbid_extra_components", False)
        ),
    }
