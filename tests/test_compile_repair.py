from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import compile_repair  # noqa: E402
import validate_project  # noqa: E402


class CompileRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.asset = validate_project.load_document(
            ROOT / "examples" / "KNIFE_001" / "asset.toml"
        ).data
        self.edit = validate_project.load_document(
            ROOT
            / "examples"
            / "KNIFE_001"
            / "edits"
            / "rivets-brushed-silver.toml"
        ).data

    def test_compile_delta_only_repair(self) -> None:
        qa = {
            "document_type": "qa_report",
            "schema_version": 1,
            "report_id": "Q_REPAIR",
            "asset_id": "KNIFE_001",
            "request_id": "KNIFE_001_EDIT_RIVETS_001",
            "status": "REPAIR_MINOR",
            "summary": "Rear rivet drifted.",
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
                    "note": "Rear rivet drift.",
                },
                {
                    "name": "wood_continuity",
                    "severity": "soft",
                    "status": "PASS",
                    "note": "",
                },
            ],
        }

        validate_project.validate_document(qa, Path("qa.toml"))
        brief = compile_repair.compile_repair_brief(
            self.asset,
            self.edit,
            qa,
        )

        self.assertIn("OPERATION: repair", brief)
        self.assertIn("rivet_count_and_centers", brief)
        self.assertIn(
            "Restore only the rear rivet center",
            brief,
        )
        self.assertIn("asset_identity", brief)
        self.assertIn("wood_continuity", brief)
        self.assertIn(
            "Use the failed generated result as the edit target.",
            brief,
        )

    def test_non_repair_status_is_rejected(self) -> None:
        qa = {
            "document_type": "qa_report",
            "schema_version": 1,
            "report_id": "Q_PASS",
            "asset_id": "KNIFE_001",
            "request_id": "KNIFE_001_EDIT_RIVETS_001",
            "status": "PASS",
            "summary": "OK",
            "repair_directives": [],
            "gates": [
                {
                    "name": "asset_identity",
                    "severity": "hard",
                    "status": "PASS",
                    "note": "",
                }
            ],
        }

        with self.assertRaises(validate_project.ValidationError):
            compile_repair.compile_repair_brief(
                self.asset,
                self.edit,
                qa,
            )


if __name__ == "__main__":
    unittest.main()
