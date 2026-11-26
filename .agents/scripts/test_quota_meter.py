import datetime
import json
import os
import shutil
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys_path = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys_path:
    import sys
    sys.path.insert(0, SCRIPT_DIR)

import quota_meter


class TestQuotaMeter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.conv1 = "test-conv-1"
        self.conv2 = "test-conv-2"

        # Backup real orca-config.json
        self.real_config_path = quota_meter.CONFIG_PATH
        self.orig_config_content = None
        if os.path.exists(self.real_config_path):
            with open(self.real_config_path, "r", encoding="utf-8") as f:
                self.orig_config_content = f.read()

        # Set standard 70% threshold for test assertions
        quota_meter.set_thresholds(th_all=70.0, scope="all")

        self.log_dir1 = os.path.join(self.test_dir, self.conv1, ".system_generated", "logs")
        self.log_dir2 = os.path.join(self.test_dir, self.conv2, ".system_generated", "logs")
        os.makedirs(self.log_dir1, exist_ok=True)
        os.makedirs(self.log_dir2, exist_ok=True)

        self.t1 = os.path.join(self.log_dir1, "transcript.jsonl")
        self.t2 = os.path.join(self.log_dir2, "transcript.jsonl")

        with open(self.t1, "w", encoding="utf-8") as f:
            f.write(json.dumps({"step_index": 1, "input_tokens": 1000, "output_tokens": 200}) + "\n")
            f.write(json.dumps({"step_index": 2, "input_tokens": 2000, "output_tokens": 300}) + "\n")

        with open(self.t2, "w", encoding="utf-8") as f:
            f.write(json.dumps({"step_index": 1, "input_tokens": 5000, "output_tokens": 1500}) + "\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        # Restore real orca-config.json
        if self.orig_config_content is not None and os.path.exists(self.real_config_path):
            with open(self.real_config_path, "w", encoding="utf-8") as f:
                f.write(self.orig_config_content)

    def test_compute_conversation_tokens(self):
        tokens1 = quota_meter.compute_conversation_tokens(self.conv1, brain_dir=self.test_dir)
        self.assertEqual(tokens1, 3500)

        tokens2 = quota_meter.compute_conversation_tokens(self.conv2, brain_dir=self.test_dir)
        self.assertEqual(tokens2, 6500)

        tokens_none = quota_meter.compute_conversation_tokens("non-existent", brain_dir=self.test_dir)
        self.assertEqual(tokens_none, 0)

    def test_compute_5h_rolling_tokens(self):
        total, steps = quota_meter.compute_5h_rolling_tokens(brain_dir=self.test_dir)
        self.assertEqual(total, 10000)
        self.assertEqual(steps, 3)

    def test_dual_quota_telemetry_normal(self):
        telemetry = quota_meter.get_dual_quota_telemetry(
            conv_id=self.conv1,
            brain_dir=self.test_dir,
            five_h_override=72.0,
            weekly_override=93.0
        )
        self.assertEqual(telemetry["fiveHourRemainingPercent"], 72.0)
        self.assertEqual(telemetry["weeklyRemainingPercent"], 93.0)
        self.assertFalse(telemetry["isLow5h"])
        self.assertFalse(telemetry["isLowWeekly"])
        self.assertFalse(telemetry["isLowQuota"])
        self.assertIsNone(telemetry["recommendation"])

    def test_dual_quota_alert_5h_triggered(self):
        telemetry = quota_meter.get_dual_quota_telemetry(
            conv_id=self.conv1,
            brain_dir=self.test_dir,
            five_h_override=69.0,
            weekly_override=93.0
        )
        self.assertTrue(telemetry["isLow5h"])
        self.assertFalse(telemetry["isLowWeekly"])
        self.assertTrue(telemetry["isLowQuota"])
        self.assertIn("5h Limit(69.0%)이 기준", telemetry["recommendation"])

        md = quota_meter.format_markdown_footer(telemetry)
        self.assertIn("쿼터 현황", md)
        self.assertIn("5시간 한도: 69.0%", md)
        self.assertIn("주간 한도: 93.0%", md)

    def test_dual_quota_alert_both_triggered(self):
        telemetry = quota_meter.get_dual_quota_telemetry(
            conv_id=self.conv1,
            brain_dir=self.test_dir,
            five_h_override=65.0,
            weekly_override=60.0
        )
        self.assertTrue(telemetry["isLow5h"])
        self.assertTrue(telemetry["isLowWeekly"])
        self.assertTrue(telemetry["isLowQuota"])
        self.assertIn("모두 기준치", telemetry["recommendation"])

    def test_fetch_live_quota_fallback_when_no_daemon(self):
        empty_daemon_dir = os.path.join(self.test_dir, "empty_daemon")
        os.makedirs(empty_daemon_dir, exist_ok=True)
        live = quota_meter.fetch_live_antigravity_quota(daemon_dir=empty_daemon_dir)
        self.assertIsNone(live)

    def test_dual_quota_telemetry_with_live_or_fallback(self):
        empty_daemon_dir = os.path.join(self.test_dir, "empty_daemon")
        os.makedirs(empty_daemon_dir, exist_ok=True)
        telemetry = quota_meter.get_dual_quota_telemetry(
            conv_id=self.conv1,
            brain_dir=self.test_dir,
            daemon_dir=empty_daemon_dir
        )
        self.assertEqual(telemetry["quotaSource"], "calibrated_fallback")
        self.assertIsNotNone(telemetry["fiveHourRemainingPercent"])
        self.assertIsNotNone(telemetry["weeklyRemainingPercent"])

    def test_format_local_time(self):
        res_empty = quota_meter.format_local_time("")
        self.assertEqual(res_empty, "")
        res_iso = quota_meter.format_local_time("2026-11-25T06:34:05Z")
        self.assertTrue(len(res_iso) > 0)

    def test_alert_scope_filtering(self):
        # 1. Scope: low_only with tier='high' -> alertTriggered should be False
        quota_meter.set_thresholds(th_all=70, scope="low_only")
        t_high = quota_meter.get_dual_quota_telemetry(
            conv_id=self.conv1,
            brain_dir=self.test_dir,
            five_h_override=65.0,
            weekly_override=90.0,
            tier="high",
        )
        self.assertTrue(t_high["isLowQuota"])
        self.assertFalse(t_high["alertTriggered"])
        md_high = quota_meter.format_markdown_footer(t_high)
        self.assertNotIn("쿼터 주의", md_high)

        # 2. Scope: low_only with tier='low' -> alertTriggered should be True
        t_low = quota_meter.get_dual_quota_telemetry(
            conv_id=self.conv1,
            brain_dir=self.test_dir,
            five_h_override=65.0,
            weekly_override=90.0,
            tier="low",
        )
        self.assertTrue(t_low["isLowQuota"])
        self.assertTrue(t_low["alertTriggered"])
        md_low = quota_meter.format_markdown_footer(t_low)
        self.assertIn("쿼터 주의", md_low)
        self.assertIn("[low_only 모드]", md_low)


if __name__ == "__main__":
    unittest.main()
