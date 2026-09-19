#!/usr/bin/env python3
"""Runtime-only validation for concrete image references.

Static schema validation intentionally does not require image files to exist.
Use this module immediately before a real host image action.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import tomllib
import zlib
from pathlib import Path
from typing import Any

from validate_project import (
    ValidationError,
    compile_reference_sufficiency,
    cross_validate,
    load_document,
    validate_document,
)

SUPPORTED_EXTENSIONS = {".png"}


def _resolve_reference_path(asset_path: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return asset_path.parent / path


def _decode_png(path: Path) -> None:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValidationError("invalid PNG signature")

    offset = 8
    ihdr: bytes | None = None
    compressed = bytearray()
    seen_iend = False

    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        start = offset + 8
        end = start + length
        crc_end = end + 4
        if crc_end > len(data):
            raise ValidationError("truncated PNG chunk")
        payload = data[start:end]
        expected_crc = struct.unpack(">I", data[end:crc_end])[0]
        actual_crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise ValidationError("PNG CRC mismatch")

        if kind == b"IHDR":
            ihdr = payload
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            seen_iend = True
            break
        offset = crc_end

    if ihdr is None or len(ihdr) != 13:
        raise ValidationError("PNG missing valid IHDR")
    if not compressed:
        raise ValidationError("PNG missing IDAT")
    if not seen_iend:
        raise ValidationError("PNG missing IEND")

    (
        width,
        height,
        bit_depth,
        color_type,
        compression,
        filter_method,
        interlace,
    ) = struct.unpack(">IIBBBBB", ihdr)
    if width < 1 or height < 1:
        raise ValidationError("PNG has invalid dimensions")
    if compression != 0 or filter_method != 0:
        raise ValidationError("PNG uses unsupported compression/filter method")
    if interlace not in {0, 1}:
        raise ValidationError("PNG uses invalid interlace mode")

    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as exc:
        raise ValidationError(
            f"PNG pixel stream cannot be decoded: {exc}"
        ) from exc
    if not raw:
        raise ValidationError("PNG decoded pixel stream is empty")

    channels_by_type = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    channels = channels_by_type.get(color_type)
    if interlace == 0 and bit_depth == 8 and channels is not None:
        expected = height * (1 + width * channels)
        if len(raw) != expected:
            raise ValidationError(
                "PNG decoded scanline size mismatch: "
                f"expected {expected}, got {len(raw)}"
            )


def _validate_image(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            "unsupported runtime image format "
            f"'{path.suffix.lower() or '<none>'}'"
        )
    if path.suffix.lower() == ".png":
        _decode_png(path)


def run_preflight(
    asset_path: Path,
    edit_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    asset_path = Path(asset_path)
    edit_path = Path(edit_path)

    asset_doc = load_document(asset_path)
    edit_doc = load_document(edit_path)
    validate_document(asset_doc.data, asset_doc.path)
    validate_document(edit_doc.data, edit_doc.path)
    cross_validate([asset_doc, edit_doc])

    if dry_run:
        return {
            "status": "SKIPPED",
            "mode": "dry_run",
            "can_execute": True,
            "reason_codes": [],
            "checks": [],
            "reference_sufficiency": compile_reference_sufficiency(
                asset_doc.data,
                edit_doc.data,
            ),
        }

    asset = asset_doc.data
    edit = edit_doc.data
    refs = {ref["id"]: ref for ref in asset["references"]}
    target_id = edit.get("execution", {}).get("edit_target_reference_id")
    selected_ids = [
        binding["reference_id"]
        for binding in edit.get("reference_bindings", [])
    ]

    checks: list[dict[str, Any]] = []
    reasons: list[str] = []

    def add_reason(code: str) -> None:
        if code not in reasons:
            reasons.append(code)

    for ref_id in selected_ids:
        ref = refs[ref_id]
        path = _resolve_reference_path(asset_path, ref["path"])
        is_target = ref_id == target_id
        check = {
            "reference_id": ref_id,
            "path": str(path),
            "edit_target": is_target,
            "state": ref["state"],
            "status": "PASS",
        }

        if ref["state"] != "approved":
            check["status"] = "FAIL"
            check["reason_code"] = "reference_not_approved"
            add_reason("reference_not_approved")
        elif not path.exists():
            code = (
                "edit_target_missing"
                if is_target
                else "required_reference_missing"
            )
            check["status"] = "FAIL"
            check["reason_code"] = code
            add_reason(code)
        elif not path.is_file() or not os.access(path, os.R_OK):
            check["status"] = "FAIL"
            check["reason_code"] = "reference_unreadable"
            add_reason("reference_unreadable")
        else:
            try:
                _validate_image(path)
            except (OSError, ValidationError):
                check["status"] = "FAIL"
                check["reason_code"] = "reference_image_invalid"
                add_reason("reference_image_invalid")
        checks.append(check)

    sufficiency = compile_reference_sufficiency(asset, edit)
    if sufficiency["status"] == "insufficient":
        add_reason("reference_sufficiency_failed")

    status = "PASS" if not reasons else "BLOCKED"
    return {
        "status": status,
        "mode": "runtime",
        "can_execute": not reasons,
        "reason_codes": reasons,
        "checks": checks,
        "reference_sufficiency": sufficiency,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", required=True, type=Path)
    parser.add_argument("--edit", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = run_preflight(
            args.asset,
            args.edit,
            dry_run=args.dry_run,
        )
    except (OSError, ValidationError, tomllib.TOMLDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}))
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["can_execute"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
