from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    import runtime_preflight
except ModuleNotFoundError as exc:  # RED: module must be implemented.
    runtime_preflight = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class RuntimePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        if runtime_preflight is None:
            self.fail(f"runtime_preflight module missing: {IMPORT_ERROR}")

    def _asset(self) -> dict:
        return {
            "document_type": "asset_manifest",
            "schema_version": 1,
            "asset_id": "A",
            "primary_master": "MASTER",
            "locks": {"hard": ["identity"], "soft": []},
            "references": [
                {
                    "id": "MASTER",
                    "path": "refs/master.png",
                    "state": "approved",
                    "roles": ["identity", "geometry"],
                },
                {
                    "id": "SUPPORT",
                    "path": "refs/support.png",
                    "state": "approved",
                    "roles": ["material"],
                },
            ],
        }

    def _edit(self) -> dict:
        return {
            "document_type": "edit_request",
            "schema_version": 1,
            "request_id": "E",
            "asset_id": "A",
            "operation": "local_edit",
            "target": "finish",
            "change": "change finish only",
            "execution": {"edit_target_reference_id": "MASTER"},
            "preserve": {"hard": ["identity"], "soft": []},
            "reference_sufficiency": {
                "required_roles": ["identity", "material"],
                "allow_provisional": False,
                "provisional_fields": [],
                "prohibited_assumptions": ["hidden geometry"],
            },
            "reference_bindings": [
                {"reference_id": "MASTER", "roles": ["identity"]},
                {"reference_id": "SUPPORT", "roles": ["material"]},
            ],
        }

    def _write_png(self, root: Path, relative: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(PNG_1X1)

    def test_missing_edit_target_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_png(root, "refs/support.png")
            result = runtime_preflight.run_preflight(
                self._asset(), self._edit(), root
            )
            self.assertEqual("BLOCKED", result["status"])
            self.assertEqual("edit_target_missing", result["reason_code"])

    def test_missing_required_support_reference_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_png(root, "refs/master.png")
            result = runtime_preflight.run_preflight(
                self._asset(), self._edit(), root
            )
            self.assertEqual("BLOCKED", result["status"])
            self.assertEqual("required_reference_missing", result["reason_code"])

    def test_invalid_image_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_png(root, "refs/master.png")
            bad = root / "refs/support.png"
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text("not an image", encoding="utf-8")
            result = runtime_preflight.run_preflight(
                self._asset(), self._edit(), root
            )
            self.assertEqual("BLOCKED", result["status"])
            self.assertEqual("reference_image_invalid", result["reason_code"])

    def test_dry_run_allows_missing_fixture_images(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = runtime_preflight.run_preflight(
                self._asset(), self._edit(), Path(td), dry_run=True
            )
            self.assertEqual("PASS", result["status"])
            self.assertTrue(result["dry_run"])

    def test_reference_sufficiency_reports_authoritative_and_prohibited(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_png(root, "refs/master.png")
            self._write_png(root, "refs/support.png")
            result = runtime_preflight.run_preflight(
                self._asset(), self._edit(), root
            )
            self.assertEqual("PASS", result["status"])
            self.assertEqual(
                ["identity", "material"],
                result["reference_sufficiency"]["covered_roles"],
            )
            self.assertEqual(
                ["hidden geometry"],
                result["reference_sufficiency"]["prohibited_assumptions"],
            )


if __name__ == "__main__":
    unittest.main()
