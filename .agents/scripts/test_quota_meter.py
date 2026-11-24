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

        # Create mock transcripts
        today = datetime.datetime.now(datetime.timezone.utc).date()
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

    def test_compute_conversation_tokens(self):
        tokens1 = quota_meter.compute_conversation_tokens(self.conv1, brain_dir=self.test_dir)
        self.assertEqual(tokens1, 3500)

        tokens2 = quota_meter.compute_conversation_tokens(self.conv2, brain_dir=self.test_dir)
        self.assertEqual(tokens2, 6500)

        tokens_none = quota_meter.compute_conversation_tokens("non-existent", brain_dir=self.test_dir)
        self.assertEqual(tokens_none, 0)

    def test_compute_today_tokens(self):
        total, steps = quota_meter.compute_today_tokens(brain_dir=self.test_dir)
        self.assertEqual(total, 10000)
        self.assertEqual(steps, 3)

    def test_quota_telemetry_normal(self):
        telemetry = quota_meter.get_quota_telemetry(conv_id=self.conv1, brain_dir=self.test_dir, threshold_override=10)
        self.assertEqual(telemetry["sessionTokens"], 3500)
        self.assertEqual(telemetry["dailyTokens"], 10000)
        self.assertFalse(telemetry["isLowQuota"])
        self.assertIsNone(telemetry["recommendation"])

    def test_user_defined_threshold_override(self):
        # 10,000 tokens against 5,000,000 baseline is ~99.8% remaining.
        # If user sets threshold to 100%, 99.8% <= 100% is True.
        telemetry = quota_meter.get_quota_telemetry(conv_id=self.conv1, brain_dir=self.test_dir, threshold_override=100)
        self.assertTrue(telemetry["isLowQuota"])
        self.assertEqual(telemetry["lowQuotaThreshold"], 100)
        self.assertIn("사용자 지정 알림 기준(100%) 이하", telemetry["recommendation"])

    def test_set_user_threshold_valid_and_invalid(self):
        old_val = quota_meter.load_json(quota_meter.CONFIG_PATH).get("quotaMonitoring", {}).get("lowQuotaThresholdPercent", 25)
        try:
            val = quota_meter.set_user_threshold(35)
            self.assertEqual(val, 35)
            cfg = quota_meter.load_json(quota_meter.CONFIG_PATH)
            self.assertEqual(cfg["quotaMonitoring"]["lowQuotaThresholdPercent"], 35)

            # Test invalid range
            with self.assertRaises(ValueError):
                quota_meter.set_user_threshold(150)
            with self.assertRaises(ValueError):
                quota_meter.set_user_threshold(0)
            with self.assertRaises(ValueError):
                quota_meter.set_user_threshold("invalid")
        finally:
            quota_meter.set_user_threshold(old_val)

    def test_format_markdown_footer(self):
        telemetry = {
            "conversationId": self.conv1,
            "sessionTokens": 3500,
            "dailyTokens": 10000,
            "totalStepsToday": 3,
            "dailyBaseline": 12000,
            "usedPercent": 83.3,
            "remainingPercent": 16.7,
            "isLowQuota": True,
            "lowQuotaThreshold": 30,
            "hasCarbon": True,
            "recommendation": "일일 잔여 쿼터(16.7%)가 사용자 지정 알림 기준(30%) 이하입니다. 다음 작업은 gemini-4-neon-low(경량)으로의 전환을 권장합니다.",
        }

        md = quota_meter.format_markdown_footer(telemetry)
        self.assertIn("Antigravity Quota & Telemetry", md)
        self.assertIn("사용자 지정 기준: 30% 이하", md)
        self.assertIn("gemini-4-neon-low", md)


if __name__ == "__main__":
    unittest.main()
