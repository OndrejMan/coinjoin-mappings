import sys
import unittest
from math import inf
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run
from utils import run_with_timeout


def exits_without_result(_queue):
    return None


class EnumeratorTest(unittest.TestCase):
    def test_legacy_and_hyphenated_flags_are_accepted(self):
        for minimum_flag in ("--min_mining_fee", "--min-mining-fee"):
            with self.subTest(flag=minimum_flag), mock.patch.object(
                sys, "argv", ["run.py", minimum_flag, "4", "--max_mining_fee", "5", "input.json"]
            ):
                args = run.parse_args()
                self.assertEqual((args.min_mining_fee, args.max_mining_fee), (4, 5))

    def test_timeout_retry_preserves_both_attempts_when_retry_errors(self):
        timeout = {"timeout_seconds": 60, "duration_seconds": None, "status": "timeout", "mapping_count": None}
        error = {"timeout_seconds": 600, "duration_seconds": 1.0, "status": "error",
                 "mapping_count": None, "error": "failed"}
        with mock.patch.object(run, "enumerate_once", side_effect=[timeout, error]):
            result = run.enumerate_transaction([], [], "numeric", 6000, 60, 600)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["retried"])
        self.assertEqual(result["attempts"], [timeout, error])

    def test_all_mode_does_not_expand_tolerance_for_fee_range(self):
        self.assertEqual(run.mapping_max_error("all", 6000, 4, 7), 6000)
        self.assertGreater(run.mapping_max_error("numeric", 6000, 4, 7), 6000)

    def test_invalid_fee_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "greater than or equal"):
            run.mapping_max_error("numeric", 6000, 7, 4)

    def test_worker_exit_without_queue_result_raises(self):
        with self.assertRaisesRegex(RuntimeError, "without returning a result"):
            run_with_timeout(1, exits_without_result)

    def test_non_positive_timeout_is_rejected(self):
        with mock.patch.object(sys, "argv", ["run.py", "--timeout", "0", "input.json"]), \
             self.assertRaises(SystemExit):
            run.parse_args()


if __name__ == "__main__":
    unittest.main()
