from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import compile_brief  # noqa: E402


class CompileBriefTests(unittest.TestCase):
    def test_compile_knife_rivet_edit(self) -> None:
        asset = ROOT / "examples" / "KNIFE_001" / "asset.toml"
        edit = (
            ROOT
            / "examples"
            / "KNIFE_001"
            / "edits"
            / "rivets-brushed-silver.toml"
        )
        brief = compile_brief.compile_from_paths(asset, edit)

        self.assertIn("ASSET: KNIFE_001", brief)
        self.assertIn("OPERATION: local_edit", brief)
        self.assertIn("EDIT TARGET:", brief)
        self.assertIn("ASSEMBLED_MASTER", brief)
        self.assertIn("REF_1: ASSEMBLED_MASTER", brief)
        self.assertIn("REF_2: HANDLE_L_OUTER_MASTER", brief)
        self.assertIn("three existing handle rivets only", brief)
        self.assertIn("Do not redesign or reinterpret unaffected regions.", brief)

    def test_asset_locks_are_merged_with_edit_preserve(self) -> None:
        asset = {
            "document_type": "asset_manifest",
            "schema_version": 1,
            "asset_id": "A",
            "primary_master": "M",
            "locks": {
                "hard": ["asset silhouette"],
                "soft": ["lighting"],
            },
            "references": [
                {
                    "id": "M",
                    "path": "master.png",
                    "state": "approved",
                    "roles": ["identity"],
                }
            ],
        }
        edit = {
            "document_type": "edit_request",
            "schema_version": 1,
            "request_id": "E",
            "asset_id": "A",
            "operation": "local_edit",
            "target": "part",
            "change": "new finish",
            "execution": {
                "edit_target_reference_id": "M",
            },
            "preserve": {
                "hard": ["part center"],
                "soft": ["background"],
            },
            "reference_bindings": [
                {"reference_id": "M", "roles": ["identity"]}
            ],
        }
        brief = compile_brief.compile_brief(asset, edit)

        self.assertIn("EDIT TARGET:", brief)
        self.assertIn("M | path=master.png", brief)
        self.assertIn("- asset silhouette", brief)
        self.assertIn("- part center", brief)
        self.assertIn("- lighting", brief)
        self.assertIn("- background", brief)


if __name__ == "__main__":
    unittest.main()
