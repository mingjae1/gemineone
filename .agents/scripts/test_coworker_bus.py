#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for ORCA Pluggable Coworker Event Bus & Module Specification
"""

import sys
import unittest
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from coworker_bus import CoworkerModuleSpec, CoworkerEventBus


class DummyCustomWorker(CoworkerModuleSpec):
    name = "dummy_custom"
    display_name = "Custom Pluggable Agent"
    icon = "⚡"
    version = "1.0.0"

    def __init__(self, is_logged_in=True, remaining_pct=85.0):
        self._logged_in = is_logged_in
        self._rem_pct = remaining_pct

    def probe(self):
        return {
            "installed": True,
            "loggedIn": self._logged_in,
            "user": "developer_test",
            "version": self.version,
            "status": "정상 연동" if self._logged_in else "로그인 필요",
        }

    def get_quota(self):
        if not self._logged_in:
            return None
        return {
            "available": True,
            "remainingPercent": self._rem_pct,
            "remaining": int(self._rem_pct * 10),
            "limit": 1000,
            "unit": "tokens",
            "resetDesc": "커스텀 갱신",
            "statusText": "가용 상태",
        }


class TestCoworkerBus(unittest.TestCase):
    def test_builtin_modules_registered(self):
        registered = [m.name for m in CoworkerEventBus.list_modules()]
        self.assertIn("copilot", registered)
        self.assertIn("gh", registered)
        self.assertIn("codex", registered)
        self.assertIn("claude", registered)

    def test_attach_detach_module(self):
        dummy = DummyCustomWorker(is_logged_in=True, remaining_pct=92.5)
        # 1. Attach (Register)
        CoworkerEventBus.register(dummy)
        self.assertIsNotNone(CoworkerEventBus.get_module("dummy_custom"))

        probes = CoworkerEventBus.probe_all()
        self.assertIn("dummy_custom", probes)
        self.assertTrue(probes["dummy_custom"]["installed"])
        self.assertTrue(probes["dummy_custom"]["loggedIn"])

        quotas = CoworkerEventBus.get_active_quotas()
        self.assertIn("dummy_custom", quotas)
        self.assertEqual(quotas["dummy_custom"]["remainingPercent"], 92.5)
        self.assertEqual(quotas["dummy_custom"]["unit"], "tokens")
        self.assertEqual(quotas["dummy_custom"]["displayName"], "Custom Pluggable Agent")

        # 2. Detach (Unregister)
        CoworkerEventBus.unregister("dummy_custom")
        self.assertIsNone(CoworkerEventBus.get_module("dummy_custom"))
        probes_after = CoworkerEventBus.probe_all()
        self.assertNotIn("dummy_custom", probes_after)

    def test_unconnected_module_excluded_from_active_quotas(self):
        unconnected_dummy = DummyCustomWorker(is_logged_in=False)
        CoworkerEventBus.register(unconnected_dummy)
        try:
            quotas = CoworkerEventBus.get_active_quotas()
            # 미연동 모듈은 쿼터 게이지 목록에서 자동 제외되어야 함
            self.assertNotIn("dummy_custom", quotas)
        finally:
            CoworkerEventBus.unregister("dummy_custom")


if __name__ == "__main__":
    unittest.main()
