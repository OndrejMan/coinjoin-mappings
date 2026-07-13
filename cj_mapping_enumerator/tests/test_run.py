import sys
import unittest
from math import inf
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run
from Txo import P2wshOutputVirtualSize, Txo
from utils import guess_script, input_vsize, output_vsize, run_with_timeout


P2WPKH_ADDRESS = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
P2WSH_ADDRESS = "bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3"
P2TR_ADDRESS = "bc1pzj8m2jqn9f84jr3t6heyckj9geq55yglwqcy2sf3nxyq58y2vtwst50z8f"


def exits_without_result(_queue):
    return None


class EnumeratorTest(unittest.TestCase):
    def test_native_witness_script_types_are_distinguished(self):
        self.assertEqual(guess_script(P2WPKH_ADDRESS), "P2wpkh")
        self.assertEqual(guess_script(P2WSH_ADDRESS), "P2wsh")
        self.assertEqual(guess_script(P2TR_ADDRESS), "P2tr")

    def test_p2wsh_fee_math_never_uses_p2wpkh_input_size(self):
        self.assertEqual(output_vsize(P2WSH_ADDRESS), P2wshOutputVirtualSize)
        output = Txo(100_000, P2WSH_ADDRESS, "P2wsh", "output", 2)
        self.assertEqual(output.effective_value, 100_000 + 2 * P2wshOutputVirtualSize)
        with self.assertRaisesRegex(ValueError, "depends on its witness script"):
            input_vsize(P2WSH_ADDRESS)
        with self.assertRaisesRegex(ValueError, "depends on its witness script"):
            Txo(100_000, P2WSH_ADDRESS, "P2wsh", "input", 1)

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
