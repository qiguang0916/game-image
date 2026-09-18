from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_project.py"
SPEC = importlib.util.spec_from_file_location("validate_project", MODULE_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ValidateProjectTests(unittest.TestCase):
    def test_repository_examples_validate(self) -> None:
        paths = validator.iter_toml_paths([str(ROOT / "examples")])
        documents = validator.validate_paths(paths)
        self.assertEqual(3, len(documents))

    def test_duplicate_reference_is_rejected(self) -> None:
        data = {
            "document_type": "asset_manifest",
            "schema_version": 1,
            "asset_id": "A",
            "primary_master": "M",
            "locks": {"hard": ["silhouette"], "soft": []},
            "references": [
                {
                    "id": "M",
                    "path": "a.png",
                    "state": "approved",
                    "roles": ["identity"],
                },
                {
                    "id": "M",
                    "path": "b.png",
                    "state": "approved",
                    "roles": ["geometry"],
                },
            ],
        }
        with self.assertRaises(validator.ValidationError):
            validator.validate_document(data, Path("asset.toml"))

    def test_local_edit_requires_hard_preserve(self) -> None:
        data = {
            "document_type": "edit_request",
            "schema_version": 1,
            "request_id": "E",
            "asset_id": "A",
            "operation": "local_edit",
            "target": "rivet",
            "change": "silver",
            "preserve": {"hard": [], "soft": []},
            "reference_bindings": [
                {"reference_id": "M", "roles": ["identity"]}
            ],
        }
        with self.assertRaises(validator.ValidationError):
            validator.validate_document(data, Path("edit.toml"))

    def test_pass_report_cannot_have_failed_hard_gate(self) -> None:
        data = {
            "document_type": "qa_report",
            "schema_version": 1,
            "report_id": "Q",
            "asset_id": "A",
            "request_id": "E",
            "status": "PASS",
            "gates": [
                {
                    "name": "silhouette",
                    "severity": "hard",
                    "status": "FAIL",
                }
            ],
            "repair_directives": [],
        }
        with self.assertRaises(validator.ValidationError):
            validator.validate_document(data, Path("qa.toml"))

    def test_unknown_reference_binding_is_rejected_cross_document(self) -> None:
        asset = {
            "document_type": "asset_manifest",
            "schema_version": 1,
            "asset_id": "A",
            "primary_master": "M",
            "locks": {"hard": ["silhouette"], "soft": []},
            "references": [
                {
                    "id": "M",
                    "path": "a.png",
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
            "change": "finish",
            "preserve": {"hard": ["silhouette"], "soft": []},
            "reference_bindings": [
                {"reference_id": "UNKNOWN", "roles": ["material"]}
            ],
        }
        docs = [
            validator.LoadedDocument(Path("asset.toml"), asset),
            validator.LoadedDocument(Path("edit.toml"), edit),
        ]
        for doc in docs:
            validator.validate_document(doc.data, doc.path)
        with self.assertRaises(validator.ValidationError):
            validator.cross_validate(docs)


if __name__ == "__main__":
    unittest.main()
