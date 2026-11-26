#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for codex_worker.py
"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import codex_worker


class TestCodexWorker(unittest.TestCase):

    def test_get_codex_binary(self):
        b = codex_worker.get_codex_binary()
        if b:
            self.assertTrue(isinstance(b, str))
            self.assertTrue("codex" in b.lower())

    def test_parse_codex_jsonl_output(self):
        sample_jsonl = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": "test-thread-123"}),
            json.dumps({"type": "turn.started"}),
            json.dumps({"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "First response part."}}),
            json.dumps({"type": "item.completed", "item": {"id": "item_2", "type": "agent_message", "text": "Second response part."}}),
            json.dumps({"type": "turn.completed", "usage": {
                "input_tokens": 1200,
                "output_tokens": 80,
                "cached_input_tokens": 500,
                "reasoning_output_tokens": 20,
            }}),
        ])

        parsed = codex_worker.parse_codex_jsonl_output(sample_jsonl)
        self.assertEqual(parsed["thread_id"], "test-thread-123")
        self.assertEqual(parsed["output"], "First response part.\n\nSecond response part.")
        self.assertEqual(parsed["usage"]["inputTokens"], 1200)
        self.assertEqual(parsed["usage"]["outputTokens"], 80)
        self.assertEqual(parsed["usage"]["cachedTokens"], 500)
        self.assertEqual(parsed["usage"]["reasoningTokens"], 20)
        self.assertEqual(parsed["usage"]["totalTokens"], 1280)
        self.assertEqual(parsed["errors"], [])

    def test_parse_codex_jsonl_output_with_error(self):
        sample_jsonl = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": "thread-err"}),
            json.dumps({"type": "error", "message": "Failed to compile prompt"}),
        ])

        parsed = codex_worker.parse_codex_jsonl_output(sample_jsonl)
        self.assertEqual(parsed["thread_id"], "thread-err")
        self.assertIn("Failed to compile prompt", parsed["errors"])

    @patch("codex_worker.get_codex_binary", return_value=None)
    def test_run_codex_task_missing_binary(self, mock_bin):
        res = codex_worker.run_codex_task("Analyze code")
        self.assertFalse(res["success"])
        self.assertIn("not installed", res["error"])

    @patch("codex_worker.get_codex_binary", return_value="codex.cmd")
    @patch("subprocess.run")
    def test_run_codex_task_success(self, mock_subproc, mock_bin):
        stdout_data = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": "thread-abc"}),
            json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "Codex result here."}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 500, "output_tokens": 50}}),
        ])
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = stdout_data
        mock_proc.stderr = "Reading additional input from stdin...\n"
        mock_subproc.return_value = mock_proc

        res = codex_worker.run_codex_task("Test prompt", read_only=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["output"], "Codex result here.")
        self.assertEqual(res["usage"]["totalTokens"], 550)
        self.assertEqual(res["stderr"], "")


if __name__ == "__main__":
    unittest.main()
