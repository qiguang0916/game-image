from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import execution_loop  # noqa: E402
import next_action  # noqa: E402
import validate_project  # noqa: E402


def asset_fixture(asset_id: str = 'PROP_001') -> dict:
    return {
        'document_type': 'asset_manifest',
        'schema_version': 1,
        'asset_id': asset_id,
        'asset_type': 'modular_prop',
        'primary_master': 'MASTER',
        'locks': {'hard': ['overall silhouette'], 'soft': ['lighting']},
        'qa': {'max_repair_passes': 2, 'max_regeneration_passes': 1},
        'topology': {
            'components': [
                {
                    'id': 'body',
                    'required': True,
                    'count': 1,
                    'evidence': 'authoritative',
                },
                {
                    'id': 'knob',
                    'required': True,
                    'count': 2,
                    'evidence': 'authoritative',
                },
                {
                    'id': 'panel',
                    'required': True,
                    'count': 1,
                    'evidence': 'authoritative',
                },
            ],
            'relationships': [
                {
                    'id': 'body_panel_integral',
                    'type': 'integral',
                    'members': ['body', 'panel'],
                    'required': True,
                    'evidence': 'authoritative',
                },
            ],
            'prohibited_extra_components': True,
        },
        'references': [
            {
                'id': 'MASTER',
                'path': 'references/master.png',
                'state': 'approved',
                'roles': ['identity', 'geometry'],
                'priority': 100,
            },
        ],
    }


def edit_fixture(asset_id: str = 'PROP_001') -> dict:
    return {
        'document_type': 'edit_request',
        'schema_version': 1,
        'request_id': 'EDIT_001',
        'asset_id': asset_id,
        'operation': 'local_edit',
        'target': 'knob finish',
        'change': 'change knob finish only',
        'execution': {'edit_target_reference_id': 'MASTER'},
        'reference_sufficiency': {
            'required_roles': ['identity', 'geometry'],
            'authoritative_facts': ['visible component layout'],
            'provisional_fields': [],
            'prohibited_assumptions': ['hidden structure is confirmed'],
        },
        'preserve': {
            'hard': ['overall silhouette'],
            'soft': ['lighting'],
        },
        'reference_bindings': [
            {
                'reference_id': 'MASTER',
                'roles': ['identity', 'geometry'],
            }
        ],
    }


class TopologyAndQaContractTests(unittest.TestCase):
    def test_topology_compiles_required_component_and_relationship_gates(self) -> None:
        gates = validate_project.compile_required_hard_gates(
            asset_fixture(),
            edit_fixture(),
        )
        ids = {g['id'] for g in gates}
        self.assertIn('topology.component.body.present', ids)
        self.assertIn('topology.component.knob.count', ids)
        self.assertIn('topology.relationship.body_panel_integral', ids)

    def test_different_assets_can_define_different_topology(self) -> None:
        radio = asset_fixture('RADIO_001')
        radio['topology']['components'] = [
            {
                'id': 'speaker_grille',
                'required': True,
                'count': 1,
                'evidence': 'authoritative',
            }
        ]
        radio['topology']['relationships'] = []
        edit = edit_fixture('RADIO_001')
        gates = validate_project.compile_required_hard_gates(radio, edit)
        ids = {g['id'] for g in gates}
        self.assertIn('topology.component.speaker_grille.present', ids)
        self.assertNotIn('topology.component.knob.count', ids)

    def test_missing_required_topology_gate_makes_qa_invalid(self) -> None:
        run = execution_loop.init_run(asset_fixture(), edit_fixture())
        run = execution_loop.mark_generated(run, 'out.png')
        qa = {
            'document_type': 'qa_report',
            'schema_version': 1,
            'report_id': 'Q',
            'asset_id': 'PROP_001',
            'request_id': 'EDIT_001',
            'status': 'PASS',
            'summary': 'incomplete',
            'repair_directives': [],
            'gates': [
                {
                    'id': 'asset_identity',
                    'severity': 'hard',
                    'status': 'PASS',
                    'note': '',
                },
                {
                    'id': 'requested_change',
                    'severity': 'hard',
                    'status': 'PASS',
                    'note': '',
                },
            ],
        }
        with self.assertRaises(validate_project.ValidationError):
            execution_loop.apply_qa(run, qa)

    def test_not_verifiable_hard_gate_cannot_accept(self) -> None:
        run = execution_loop.init_run(asset_fixture(), edit_fixture())
        run = execution_loop.mark_generated(run, 'out.png')
        qa = validate_project.make_complete_qa_stub(run, status='PASS')
        qa['gates'][0]['status'] = 'NOT_VERIFIABLE'
        with self.assertRaises(validate_project.ValidationError):
            execution_loop.apply_qa(run, qa)

    def test_core_topology_failure_routes_to_regeneration(self) -> None:
        run = execution_loop.init_run(asset_fixture(), edit_fixture())
        run = execution_loop.mark_generated(run, 'out.png')
        qa = validate_project.make_complete_qa_stub(
            run,
            status='REGENERATE_MAJOR',
        )
        gate = next(
            g
            for g in qa['gates']
            if g['id'] == 'topology.relationship.body_panel_integral'
        )
        gate['status'] = 'FAIL'
        routed = execution_loop.apply_qa(run, qa)
        self.assertEqual('REGENERATE_READY', routed['state'])

    def test_host_packet_exposes_structured_contract(self) -> None:
        asset = asset_fixture()
        edit = edit_fixture()
        run = execution_loop.init_run(asset, edit)
        packet = next_action.build_action_packet(asset, edit, run)

        self.assertEqual('local_edit', packet['operation'])
        self.assertEqual(
            'change knob finish only',
            packet['requested_delta'],
        )
        self.assertIn('required_components', packet['topology'])
        self.assertIn('relationships', packet['topology'])
        self.assertEqual(
            'sufficient',
            packet['reference_sufficiency']['status'],
        )
        self.assertEqual(
            ['hidden structure is confirmed'],
            packet['prohibited_assumptions'],
        )
        self.assertIn('repair_remaining', packet['budgets'])
        self.assertEqual(
            'mark_generated',
            packet['expected_post_action_transition'],
        )



    def test_qa_contract_can_promote_preserve_locks_to_required_gates(self) -> None:
        asset = asset_fixture()
        edit = edit_fixture()
        edit["qa_contract"] = {
            "enforce_complete_hard_gates": True,
            "enforce_lock_gates": True,
        }
        gates = validate_project.compile_required_hard_gates(asset, edit)
        ids = {gate["id"] for gate in gates}
        self.assertIn("lock.overall_silhouette", ids)

    def test_localized_requested_change_failure_can_repair(self) -> None:
        asset = asset_fixture()
        edit = edit_fixture()
        run = execution_loop.init_run(asset, edit)
        run = execution_loop.mark_generated(run, "out.png")
        qa = validate_project.make_complete_qa_stub(
            run,
            status="REPAIR_MINOR",
        )
        requested = next(
            gate for gate in qa["gates"]
            if gate["id"] == "requested_change"
        )
        requested["status"] = "FAIL"
        qa["repair_directives"] = ["Correct only the requested finish."]
        routed = execution_loop.apply_qa(run, qa)
        self.assertEqual("REPAIR_READY", routed["state"])


    def test_topology_relationship_rejects_undeclared_members(self) -> None:
        asset = asset_fixture()
        asset["topology"]["relationships"][0]["members"] = [
            "body",
            "missing_panel",
        ]
        with self.assertRaises(validate_project.ValidationError):
            validate_project.validate_document(
                asset,
                Path("asset.toml"),
            )

    def test_required_hard_gate_note_is_invalid(self) -> None:
        asset = asset_fixture()
        edit = edit_fixture()
        run = execution_loop.init_run(asset, edit)
        run = execution_loop.mark_generated(run, "out.png")
        qa = validate_project.make_complete_qa_stub(
            run,
            status="REPAIR_MINOR",
        )
        requested = next(
            gate for gate in qa["gates"]
            if gate["id"] == "requested_change"
        )
        requested["status"] = "FAIL"
        relation = next(
            gate for gate in qa["gates"]
            if gate["id"] == "topology.relationship.body_panel_integral"
        )
        relation["status"] = "NOTE"
        qa["repair_directives"] = ["Correct only the requested finish."]
        with self.assertRaises(validate_project.ValidationError):
            execution_loop.apply_qa(run, qa)

class HostFailureTests(unittest.TestCase):
    def test_imagegen_unavailable_persists_blocked_state(self) -> None:
        asset = asset_fixture()
        edit = edit_fixture()
        run = execution_loop.init_run(asset, edit)
        blocked = execution_loop.mark_blocked(
            run,
            reason_code='host_native_imagegen_unavailable',
            action='imagegen_edit',
            message='built-in image tool unavailable',
            retryable=False,
        )

        self.assertEqual('BLOCKED', blocked['state'])
        self.assertEqual(
            'host_native_imagegen_unavailable',
            blocked['blocked']['reason_code'],
        )
        self.assertEqual(0, blocked['repair_passes'])
        self.assertEqual(0, blocked['regeneration_passes'])

        packet = next_action.build_action_packet(asset, edit, blocked)
        self.assertEqual('report_blocked', packet['action'])
        self.assertNotIn(
            'fallback',
            packet.get('next_action', '').lower(),
        )

    def test_moderation_blocked_is_terminal_without_budget_consumption(self) -> None:
        run = execution_loop.init_run(asset_fixture(), edit_fixture())
        blocked = execution_loop.mark_blocked(
            run,
            reason_code='host_native_imagegen_moderation_blocked',
            action='imagegen_edit',
            message='host safety policy blocked generation',
            retryable=False,
        )
        self.assertEqual('BLOCKED', blocked['state'])
        self.assertEqual(0, blocked['repair_passes'])
        self.assertEqual(0, blocked['regeneration_passes'])


if __name__ == '__main__':
    unittest.main()
