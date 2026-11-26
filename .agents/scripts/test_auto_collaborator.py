#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for ORCA Autonomous Collaboration Pipeline
"""

import sys
import unittest
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from auto_collaborator import AutoCollaborator


class TestAutoCollaborator(unittest.TestCase):
    def test_cross_verification_trigger(self):
        res = AutoCollaborator.evaluate_task("고난도 동시성 락 경합 및 메모리 누수 분석")
        self.assertTrue(res.get("recommended"))
        self.assertEqual(res.get("action"), "cross_verification")
        self.assertEqual(res.get("target"), "codex")

    def test_git_copilot_trigger(self):
        res = AutoCollaborator.evaluate_task("이번 주 작업 브랜치 풀리퀘스트 PR 요약문 작성")
        self.assertTrue(res.get("recommended"))
        self.assertEqual(res.get("action"), "git_integration")
        self.assertEqual(res.get("target"), "copilot")

    def test_quota_offload_trigger(self):
        telemetry = {"fiveHourRemainingPercent": 5.0}  # 10% 이하
        res = AutoCollaborator.evaluate_task("단순 유틸리티 함수 구현", telemetry=telemetry)
        self.assertTrue(res.get("recommended"))
        self.assertEqual(res.get("action"), "quota_offload")

    def test_normal_task_single_execution(self):
        res = AutoCollaborator.evaluate_task("hello world 출력 함수")
        self.assertFalse(res.get("recommended"))


if __name__ == "__main__":
    unittest.main()
