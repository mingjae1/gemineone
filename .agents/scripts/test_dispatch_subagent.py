#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for dispatch_subagent.py
"""

import os
import sys
import unittest
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import dispatch_subagent


class TestDispatchSubagent(unittest.TestCase):

    @patch("copilot_worker.run_copilot_task")
    def test_dispatch_to_copilot(self, mock_cp):
        mock_cp.return_value = {"success": True, "output": "Copilot ok", "usage": {"totalTokens": 100}}
        res = dispatch_subagent.dispatch_task("copilot", "Refactor function", files="test.py")
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "copilot")
        self.assertEqual(res["output"], "Copilot ok")
        mock_cp.assert_called_once()

    @patch("codex_worker.run_codex_task")
    def test_dispatch_to_codex(self, mock_cx):
        mock_cx.return_value = {"success": True, "output": "Codex ok", "usage": {"totalTokens": 200}}
        res = dispatch_subagent.dispatch_task("codex", "Explain algorithm", read_only=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "codex")
        self.assertEqual(res["output"], "Codex ok")
        mock_cx.assert_called_once()

    def test_dispatch_unknown_target(self):
        res = dispatch_subagent.dispatch_task("unknown_ai", "Do task")
        self.assertFalse(res["success"])
        self.assertIn("Unknown dispatch target", res["error"])


if __name__ == "__main__":
    unittest.main()
