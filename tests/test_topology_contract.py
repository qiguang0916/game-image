from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    import topology_contract
except ModuleNotFoundError as exc:  # RED
    topology_contract = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

import validate_project


class TopologyContractTests(unittest.TestCase):
    def setUp(self) -> None:
        if topology_contract is None:
            self.fail(f"topology_contract module missing: {IMPORT_ERROR}")

    def _asset(self) -> dict:
        return {
            "document_type": "asset_manifest",
            "schema_version": 1,
            "asset_id": "LAMP_001",
            "primary_master": "MASTER",
            "locks": {"hard": ["identity"], "soft": []},
            "references": [
                {
                    "id": "MASTER",
                    "path": "refs/master.png",
                    "state": "approved",
                    "roles": ["identity", "geometry"],
                }
            ],
            "topology": {
                "forbid_extra_components": True,
                "components": [
                    {"id": "base", "required": True, "count": 1},
                    {"id": "arm", "required": True, "count": 1},
                    {"id": "shade", "required": True, "count": 1},
                    {"id": "decorative_screw", "required": True, "count": 3},
                ],
                "relationships": [
                    {
                        "id": "shade_mounted_on_arm",
                        "type": "mounted_on",
                        "members": ["shade", "arm"],
                        "required": True,
                    }
                ],
            },
        }

    def _edit(self) -> dict:
        return {
            "document_type": "edit_request",
            "schema_version": 1,
            "request_id": "E",
            "asset_id": "LAMP_001",
            "operation": "local_edit",
            "target": "three screws",
            "change": "change screw finish",
            "execution": {"edit_target_reference_id": "MASTER"},
            "preserve": {"hard": ["identity"], "soft": []},
            "reference_bindings": [
                {"reference_id": "MASTER", "roles": ["identity", "geometry"]}
            ],
        }

    def test_expected_hard_gates_include_component_counts_and_relationships(self) -> None:
        gates = topology_contract.expected_hard_gates(self._asset(), self._edit())
        self.assertIn("topology.component.base.count", gates)
        self.assertIn("topology.component.decorative_screw.count", gates)
        self.assertIn(
            "topology.relationship.shade_mounted_on_arm",
            gates,
        )
        self.assertIn("topology.no_forbidden_extra_components", gates)

    def test_different_asset_contract_is_not_knife_specific(self) -> None:
        gates = topology_contract.expected_hard_gates(self._asset(), self._edit())
        self.assertFalse(any("tang" in gate or "rivet" in gate for gate in gates))

    def test_missing_required_topology_gate_invalidates_qa(self) -> None:
        required = topology_contract.expected_hard_gates(
            self._asset(), self._edit()
        )
        qa = {
            "document_type": "qa_report",
            "schema_version": 1,
            "report_id": "Q",
            "asset_id": "LAMP_001",
            "request_id": "E",
            "status": "PASS",
            "summary": "",
            "repair_directives": [],
            "gates": [
                {
                    "name": gate,
                    "severity": "hard",
                    "status": "PASS",
                    "note": "",
                }
                for gate in required[:-1]
            ],
        }
        with self.assertRaises(validate_project.ValidationError):
            topology_contract.validate_qa_completeness(required, qa)

    def test_not_verifiable_required_hard_gate_cannot_pass(self) -> None:
        required = topology_contract.expected_hard_gates(
            self._asset(), self._edit()
        )
        qa = {
            "document_type": "qa_report",
            "schema_version": 1,
            "report_id": "Q",
            "asset_id": "LAMP_001",
            "request_id": "E",
            "status": "PASS",
            "summary": "",
            "repair_directives": [],
            "gates": [
                {
                    "name": gate,
                    "severity": "hard",
                    "status": (
                        "NOT_VERIFIABLE"
                        if gate == "topology.component.base.count"
                        else "PASS"
                    ),
                    "note": "",
                }
                for gate in required
            ],
        }
        with self.assertRaises(validate_project.ValidationError):
            topology_contract.validate_qa_completeness(required, qa)


if __name__ == "__main__":
    unittest.main()
