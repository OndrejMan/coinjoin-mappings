# Input, runtime, and result contract

The mapping enumerator and Sake consume the pipeline's
`coinjoin-analysis_data/coinjoin_tx_info.json`, but they do not implement
identical script or execution models.

## Required input shape

The top level must be an object containing a `coinjoins` object keyed by
transaction id. Each transaction used by either tool is expected to contain:

- `txid` and `is_blame_round`;
- `inputs` and `outputs` objects;
- for each input/output, `value`, `address`, and `wallet_name`;
- for enumerator inputs, `mix_event_type`.

Missing per-transaction fields become an enumerator transaction-level `error`.
The enumerator writes all collected results and exits non-zero when any error
remains. Sake currently fails the process on malformed required fields.

## Script-type support

The Python enumerator distinguishes P2WPKH, P2WSH, and P2TR witness addresses.
It can account for P2WSH output size, but rejects P2WSH inputs because their
input virtual size depends on the witness script and cannot be inferred from an
address alone.

The C# Sake parser distinguishes native P2WPKH, P2WSH, and P2TR by witness
version and encoded program length. It accounts for P2WSH output size when
reading observed transaction outputs, but rejects a P2WSH when it is used as an
input because the input witness script is not recoverable from the address.
Sake's generated full-mix replay and per-wallet samples are limited to P2WPKH
and Taproot outputs. The Python enumerator therefore has a wider output model;
both tools fail explicitly on P2WSH inputs.

Enumerator schema `1.1` records the widened P2WSH output contract. Sake keeps
schema `1.0` because the JSON result shape is unchanged; consumers of the
combined result must check each nested tool's schema independently.

## Multiprocessing runtime

The enumeration process target is a module-level function and is picklable
under `fork`, `spawn`, and `forkserver`. This keeps the published Python 3.12
container path and local Python 3.14 `forkserver` path behaviorally aligned.
Inputs and outputs still need to be picklable, as required by multiprocessing.

## Repeatability

- Enumerator counts and default JSON are repeatable for the same input and
  parameters. Attempt and total `duration_seconds` fields are `null` unless
  `--include-timing` is explicitly requested; timing-enabled output is not
  byte-for-byte deterministic.
- Sake derives separate full-mix and wallet seeds from SHA-256 of the user seed,
  transaction id, and wallet/scope identifier. Reordering `coinjoins` or wallet
  properties does not change a transaction's random stream.
- A timeout is represented as `partial` by the combined PBS stage. Enumerator
  errors exit non-zero before the combined file is produced.
