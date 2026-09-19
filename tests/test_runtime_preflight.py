from __future__ import annotations

import sys
import tempfile
import unittest
import zlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import execution_loop  # noqa: E402
import runtime_preflight  # noqa: E402


def write_png(path: Path) -> None:
    width = height = 1
    raw = b'\x00\xff\xff\xff\xff'

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack('>I', len(data))
            + kind
            + data
            + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
        )

    payload = b'\x89PNG\r\n\x1a\n'
    payload += chunk(
        b'IHDR',
        struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0),
    )
    payload += chunk(b'IDAT', zlib.compress(raw))
    payload += chunk(b'IEND', b'')
    path.write_bytes(payload)


def write_project(
    root: Path,
    *,
    support_exists: bool = True,
    target_exists: bool = True,
) -> tuple[Path, Path]:
    refs = root / 'references'
    refs.mkdir(parents=True)
    if target_exists:
        write_png(refs / 'master.png')
    if support_exists:
        write_png(refs / 'support.png')

    asset = root / 'asset.toml'
    asset.write_text(
        '''document_type = "asset_manifest"
schema_version = 1
asset_id = "A"
asset_type = "prop"
status = "active"
primary_master = "MASTER"

[locks]
hard = ["overall silhouette"]
soft = []

[qa]
max_repair_passes = 2
max_regeneration_passes = 1

[[references]]
id = "MASTER"
path = "references/master.png"
state = "approved"
priority = 100
roles = ["identity", "geometry"]

[[references]]
id = "SUPPORT"
path = "references/support.png"
state = "approved"
priority = 90
roles = ["material"]
''',
        encoding='utf-8',
    )

    edit = root / 'edit.toml'
    edit.write_text(
        '''document_type = "edit_request"
schema_version = 1
request_id = "E"
asset_id = "A"
operation = "local_edit"
target = "surface"
change = "change finish"

[execution]
edit_target_reference_id = "MASTER"

[reference_sufficiency]
required_roles = ["identity", "material"]
provisional_fields = []
prohibited_assumptions = ["hidden geometry is approved"]

[preserve]
hard = ["overall silhouette"]
soft = []

[[reference_bindings]]
reference_id = "MASTER"
roles = ["identity"]

[[reference_bindings]]
reference_id = "SUPPORT"
roles = ["material"]
''',
        encoding='utf-8',
    )
    return asset, edit


class RuntimePreflightTests(unittest.TestCase):
    def test_missing_edit_target_blocks_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            asset, edit = write_project(Path(td), target_exists=False)
            result = runtime_preflight.run_preflight(asset, edit)
            self.assertEqual('BLOCKED', result['status'])
            self.assertFalse(result['can_execute'])
            self.assertIn('edit_target_missing', result['reason_codes'])

    def test_missing_required_support_reference_blocks_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            asset, edit = write_project(Path(td), support_exists=False)
            result = runtime_preflight.run_preflight(asset, edit)
            self.assertEqual('BLOCKED', result['status'])
            self.assertIn('required_reference_missing', result['reason_codes'])

    def test_invalid_image_blocks_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            asset, edit = write_project(Path(td))
            (Path(td) / 'references' / 'support.png').write_text(
                'not-an-image',
                encoding='utf-8',
            )
            result = runtime_preflight.run_preflight(asset, edit)
            self.assertEqual('BLOCKED', result['status'])
            self.assertIn('reference_image_invalid', result['reason_codes'])

    def test_dry_run_explicitly_skips_real_file_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            asset, edit = write_project(
                Path(td),
                support_exists=False,
                target_exists=False,
            )
            result = runtime_preflight.run_preflight(
                asset,
                edit,
                dry_run=True,
            )
            self.assertEqual('SKIPPED', result['status'])
            self.assertTrue(result['can_execute'])
            self.assertEqual('dry_run', result['mode'])


    def test_rejected_reference_becomes_blocked_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            asset, edit = write_project(Path(td))
            text = asset.read_text(encoding="utf-8")
            text = text.replace(
                'id = "SUPPORT"\npath = "references/support.png"\nstate = "approved"',
                'id = "SUPPORT"\npath = "references/support.png"\nstate = "rejected"',
            )
            asset.write_text(text, encoding="utf-8")
            result = runtime_preflight.run_preflight(asset, edit)
            self.assertEqual("BLOCKED", result["status"])
            self.assertIn(
                "reference_contract_invalid",
                result["reason_codes"],
            )

    def test_real_init_blocks_before_ready_when_preflight_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            asset, edit = write_project(
                Path(td),
                support_exists=False,
            )
            run = execution_loop.init_from_paths(asset, edit)
            self.assertEqual('BLOCKED', run['state'])
            self.assertEqual(
                'required_reference_missing',
                run['blocked']['reason_code'],
            )

    def test_dry_run_init_preserves_legacy_ready_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            asset, edit = write_project(
                Path(td),
                support_exists=False,
                target_exists=False,
            )
            run = execution_loop.init_from_paths(
                asset,
                edit,
                dry_run=True,
            )
            self.assertEqual('READY', run['state'])
            self.assertEqual('dry_run', run['preflight']['mode'])


if __name__ == '__main__':
    unittest.main()
