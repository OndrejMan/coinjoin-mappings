#!/usr/bin/env python3
"""Enumerate Wasabi mappings and emit a stable machine-readable result."""
import argparse
import json
import sys
import time
from math import inf
from pathlib import Path

from cj_mappings import get_all_mappings, get_numeric_mappings
from preprocessing import preprocess
from utils import load_cj, run_with_timeout

sys.setrecursionlimit(500_000_000)
MAX_VSIZE = 10 * 69 + 10 * 58


def non_negative_int(value):
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def non_negative_float(value):
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def positive_int(value):
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args():
    parser = argparse.ArgumentParser(prog="CoinJoin mapping enumerator")
    parser.add_argument("json_filename", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-m", "--mining-fee-rate", "--mining_fee_rate", default=1, type=non_negative_int)
    parser.add_argument(
        "-c", "--coordination-fee-rate", "--coordination_fee_rate", default=0.003, type=non_negative_float
    )
    parser.add_argument(
        "-d", "--max-decomposition-fee", "--max_decomposition_fee", default=6000, type=non_negative_int
    )
    parser.add_argument("--min-mining-fee", "--min_mining_fee", type=non_negative_int)
    parser.add_argument("--max-mining-fee", "--max_mining_fee", type=non_negative_int)
    parser.add_argument("-t", "--timeout", default=60, type=positive_int)
    parser.add_argument("--retry-timeout", default=600, type=positive_int)
    parser.add_argument("--mode", choices=("numeric", "all"), default="numeric")
    parser.add_argument("--linked-addresses", "--linked_addresses")
    return parser.parse_args()


def enumerate_once(inputs, outputs, mode, max_error, timeout):
    def worker(queue):
        try:
            iterator = (get_numeric_mappings if mode == "numeric" else get_all_mappings)(
                inputs, outputs, max_error=max_error
            )
            queue.put({"count": sum(1 for _ in iterator)})
        except Exception as error:
            queue.put({"error": f"{type(error).__name__}: {error}"})
    try:
        duration, outcome = run_with_timeout(timeout, worker)
    except RuntimeError as error:
        return {"timeout_seconds": timeout, "duration_seconds": None, "status": "error",
                "mapping_count": None, "error": str(error)}
    if duration != inf and "error" in outcome:
        return {"timeout_seconds": timeout, "duration_seconds": duration, "status": "error",
                "mapping_count": None, "error": outcome["error"]}
    count = inf if duration == inf else outcome["count"]
    return {"timeout_seconds": timeout, "duration_seconds": None if duration == inf else duration,
            "status": "timeout" if duration == inf else "complete",
            "mapping_count": None if count == inf else count}


def enumerate_transaction(inputs, outputs, mode, max_error, timeout, retry_timeout):
    attempts = [enumerate_once(inputs, outputs, mode, max_error, timeout)]
    if attempts[0]["status"] == "timeout":
        attempts.append(enumerate_once(inputs, outputs, mode, max_error, retry_timeout))
    final = attempts[-1]
    result = {"status": final["status"], "mapping_count": final["mapping_count"],
              "retried": len(attempts) > 1, "attempts": attempts}
    if final["status"] == "error":
        result["error"] = final["error"]
    return result


def mapping_max_error(mode, max_decomposition_fee, min_mining_fee, max_mining_fee):
    if min_mining_fee is None:
        return max_decomposition_fee
    if max_mining_fee is None:
        raise ValueError("--max-mining-fee is required with --min-mining-fee")
    if max_mining_fee < min_mining_fee:
        raise ValueError("--max-mining-fee must be greater than or equal to --min-mining-fee")
    if mode == "all":
        return max_decomposition_fee
    return max_decomposition_fee + (max_mining_fee - min_mining_fee) * MAX_VSIZE


def main():
    args = parse_args()
    started = time.time()
    with args.json_filename.open(encoding="utf-8") as stream:
        source = json.load(stream)
    if not isinstance(source, dict) or not isinstance(source.get("coinjoins"), dict):
        raise ValueError("Expected a JSON object containing a 'coinjoins' object")
    mining_rate = args.mining_fee_rate
    if args.min_mining_fee is not None:
        mining_rate = args.min_mining_fee
    effective_max_error = mapping_max_error(
        args.mode, args.max_decomposition_fee, args.min_mining_fee, args.max_mining_fee
    )
    linked = json.loads(args.linked_addresses) if args.linked_addresses else None
    transactions = {}
    for txid, coinjoin in source["coinjoins"].items():
        try:
            inputs, outputs = load_cj(coinjoin, mining_rate, args.coordination_fee_rate)
            if linked is not None:
                inputs, outputs = preprocess(inputs, outputs, linked)
            transactions[txid] = enumerate_transaction(
                inputs, outputs, args.mode, effective_max_error, args.timeout, args.retry_timeout
            )
        except Exception as error:  # preserve other transaction results before failing stage
            transactions[txid] = {"status": "error", "error": str(error), "attempts": []}
    completed = sum(item["status"] == "complete" for item in transactions.values())
    timed_out = sum(item["status"] == "timeout" for item in transactions.values())
    errors = sum(item["status"] == "error" for item in transactions.values())
    result = {"schema_version": "1.0", "tool": "coinjoin-mapping-enumerator",
              "parameters": {"mining_fee_rate": mining_rate,
                             "coordination_fee_rate": args.coordination_fee_rate,
                             "max_decomposition_fee": args.max_decomposition_fee,
                             "effective_max_error": effective_max_error,
                             "min_mining_fee": args.min_mining_fee,
                             "max_mining_fee": args.max_mining_fee,
                             "linked_addresses": linked,
                             "mode": args.mode, "timeout_seconds": args.timeout,
                             "retry_timeout_seconds": args.retry_timeout},
              "summary": {"transactions": len(transactions), "completed": completed,
                          "timed_out": timed_out, "errors": errors,
                          "duration_seconds": time.time() - started},
              "transactions": transactions}
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
