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
        telemetry = quota_meter.get_quota_telemetry(conv_id=self.conv1, brain_dir=self.test_dir)
        self.assertEqual(telemetry["sessionTokens"], 3500)
        self.assertEqual(telemetry["dailyTokens"], 10000)
        self.assertFalse(telemetry["isLowQuota"])
        self.assertIsNone(telemetry["recommendation"])

    def test_quota_telemetry_low_quota_alert(self):
        # Override baseline to trigger low quota alert
        today = datetime.datetime.now(datetime.timezone.utc).date()
        total, steps = quota_meter.compute_today_tokens(brain_dir=self.test_dir)
        used_percent = round((total / 12000) * 100, 1)
        remaining_percent = round(100.0 - used_percent, 1)

        # Mock config with high threshold
        telemetry = {
            "conversationId": self.conv1,
            "sessionTokens": 3500,
            "dailyTokens": total,
            "totalStepsToday": steps,
            "dailyBaseline": 12000,
            "usedPercent": used_percent,
            "remainingPercent": remaining_percent,
            "isLowQuota": True,
            "lowQuotaThreshold": 25,
            "hasCarbon": True,
            "recommendation": "일일 잔여 쿼터가 16.7%로 낮습니다. 다음 작업은 gemini-4-neon-low(경량)으로의 전환을 권장합니다.",
        }

        md = quota_meter.format_markdown_footer(telemetry)
        self.assertIn("Antigravity Quota & Telemetry", md)
        self.assertIn("쿼터 주의", md)
        self.assertIn("gemini-4-neon-low", md)


if __name__ == "__main__":
    unittest.main()
