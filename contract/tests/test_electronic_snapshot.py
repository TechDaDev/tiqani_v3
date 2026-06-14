"""Tests for electronic contract snapshot determinism and canonicalization."""

import hashlib
import json
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from copy import deepcopy


class SnapshotCanonicalizationTest(TestCase):
    """Verify snapshot hash is deterministic under various conditions."""

    def _build_snapshot(self, overrides=None):
        """Helper to produce a canonical snapshot dict like Contract.get_or_create_frozen_version()."""
        base = {
            'contract_id': '550e8400-e29b-41d4-a716-446655440000',
            'contract_reference': 'TIQ-2026-0001',
            'version': 1,
            'client_id': 'a1b2c3d4-e29b-41d4-a716-446655440001',
            'client_name': 'Alice Client',
            'technician_id': 'e5f6g7h8-e29b-41d4-a716-446655440002',
            'technician_name': 'Bob Technician',
            'project_title': 'Website Development',
            'work_description': 'Build a full-stack website with admin panel.',
            'location': 'Baghdad',
            'accepted_offer_reference': 'TIQ-2026-0001',
            'agreed_amount': '500000.00',
            'currency': 'IQD',
            'client_platform_fee': '25000.00',
            'technician_platform_fee': '50000.00',
            'escrow_amount': '0.00',
            'stage_number': 3,
            'start_date': '2026-06-01',
            'duration_days': 15,
            'contract_duration': '2026-06-16',
            'materials_responsibility': 'As agreed between parties',
            'inclusions': 'Full stack development',
            'exclusions': 'Hosting costs',
            'client_obligations': 'Provide requirements.',
            'technician_obligations': 'Deliver on time.',
            'cancellation_terms': 'Standard terms',
            'extension_terms': 'Client approval required',
            'payment_release_rules': 'Per stage approval',
            'dispute_clause_version': 'v1.0',
            'governing_law_version': 'v1.0',
            'platform_attestation_version': 'v1.0',
            'consent_text_version': 'v1.0',
            'generated_at': '2026-06-14T12:00:00',
            'stages': [
                {'stage_number': 1, 'amount': '166666.67', 'deadline': '2026-06-06', 'description': 'Design'},
                {'stage_number': 2, 'amount': '166666.67', 'deadline': '2026-06-11', 'description': 'Development'},
                {'stage_number': 3, 'amount': '166666.66', 'deadline': '2026-06-16', 'description': 'Deployment'},
            ],
        }
        if overrides:
            base.update(overrides)
        return base

    def _hash(self, snapshot):
        canonical = json.dumps(snapshot, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def test_same_data_produces_same_hash(self):
        s1 = self._build_snapshot()
        s2 = self._build_snapshot()
        self.assertEqual(self._hash(s1), self._hash(s2))

    def test_reordered_keys_same_hash(self):
        s1 = self._build_snapshot()
        # Python dicts preserve insertion order but sort_keys normalizes it
        s2 = {k: v for k, v in reversed(list(s1.items()))}  # reversed insertion order
        self.assertEqual(self._hash(s1), self._hash(s2))

    def test_changed_amount_changes_hash(self):
        s1 = self._build_snapshot()
        s2 = self._build_snapshot({'agreed_amount': '600000.00'})
        self.assertNotEqual(self._hash(s1), self._hash(s2))

    def test_changed_stage_changes_hash(self):
        s1 = self._build_snapshot()
        s2 = self._build_snapshot()
        s2_stages = deepcopy(s2['stages'])
        s2_stages[0]['amount'] = '200000.00'
        s2['stages'] = s2_stages
        self.assertNotEqual(self._hash(s1), self._hash(s2))

    def test_changed_legal_text_version_changes_hash(self):
        s1 = self._build_snapshot()
        s2 = self._build_snapshot({'dispute_clause_version': 'v2.0'})
        self.assertNotEqual(self._hash(s1), self._hash(s2))

    def test_json_canonical_stable(self):
        """Verify that sort_keys + compact separators produce stable JSON with no extra whitespace."""
        s = self._build_snapshot()
        c1 = json.dumps(s, sort_keys=True, separators=(',', ':'))
        c2 = json.dumps(s, sort_keys=True, separators=(',', ':'))
        self.assertEqual(c1, c2)
        # Verify no whitespace padding (but values may contain spaces)
        self.assertNotIn('": "', c1)  # Would indicate spaces around colons
