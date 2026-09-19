from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_root_skill_description_is_trigger_only(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"^description:\s*(.+)$", text, flags=re.MULTILINE)
        self.assertIsNotNone(match)
        description = match.group(1).strip()
        self.assertTrue(description.startswith("Use when"))
        self.assertLess(len(description), 500)

    def test_required_reference_docs_exist(self) -> None:
        required = [
            "references/runtime-preflight.md",
            "references/topology-contract.md",
            "references/reference-sufficiency.md",
            "references/visual-qa-contract.md",
            "references/host-failure-protocol.md",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_root_skill_points_to_progressive_disclosure_docs(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for relative in (
            "references/runtime-preflight.md",
            "references/topology-contract.md",
            "references/reference-sufficiency.md",
            "references/visual-qa-contract.md",
            "references/host-failure-protocol.md",
        ):
            self.assertIn(relative, text)


if __name__ == "__main__":
    unittest.main()
