import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import copilot_worker


class TestCopilotWorker(unittest.TestCase):
    def test_get_copilot_binary(self):
        bin_path = copilot_worker.get_copilot_binary()
        self.assertIsNotNone(bin_path, "Copilot binary should be detected on this machine")

    def test_get_copilot_db_path(self):
        db_path = copilot_worker.get_copilot_db_path()
        self.assertTrue(db_path.endswith("session-store.db"))

    def test_get_latest_event_id(self):
        db_path = copilot_worker.get_copilot_db_path()
        eid = copilot_worker.get_latest_event_id(db_path)
        self.assertIsInstance(eid, int)
        self.assertGreaterEqual(eid, 0)

    def test_get_usage_since_event_empty(self):
        usage = copilot_worker.get_usage_since_event("non_existent.db", 999999)
        self.assertEqual(usage["totalTokens"], 0)
        self.assertEqual(usage["credits"], 0.0)


if __name__ == "__main__":
    unittest.main()
