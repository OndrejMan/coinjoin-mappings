## Coinjoin mappings

This repository contains the following:

1. Coinjoin mappings enumerator -- program enumerating input-output mappings for small Wasabi 2 coinjoin transactions. 

2. Modified version of Wasabi 2 decomposition simulator Sake. The original implementation is available at https://github.com/nopara73/Sake/

## Containers

Build the independent production images with:

```bash
docker build -f Dockerfile.enumerator -t coinjoin-mappings-enumerator .
docker build -f Dockerfile.sake -t coinjoin-mappings-sake .
```

The enumerator accepts `coinjoin_tx_info.json`, retries timed-out transactions,
and writes structured JSON with `--output`. Sake accepts `--input`, `--output`,
and a deterministic `--seed` (default `20260704`).

Pushes to `main` that change either implementation or Dockerfile trigger
`.github/workflows/docker-images.yml`. The workflow publishes multi-architecture
images for `linux/amd64` and `linux/arm64` to GitHub Container Registry:

- `ghcr.io/ondrejman/coinjoin-mappings-enumerator:latest`
- `ghcr.io/ondrejman/coinjoin-mappings-sake:latest`

Each image is also published with an immutable `sha-<commit>` tag. The workflow
can be started manually with GitHub Actions `workflow_dispatch`.

## Output formats

Both tools emit deterministic JSON (`sort_keys`, stable indentation) with
`"schema_version": "1.0"` so downstream consumers can detect format changes.

### Enumerator (`enumerator.json`)

```
{
  "schema_version": "1.0",
  "tool": "coinjoin-mapping-enumerator",
  "parameters": { mining_fee_rate, coordination_fee_rate, max_decomposition_fee,
                  effective_max_error, min_mining_fee, max_mining_fee,
                  linked_addresses, mode, timeout_seconds, retry_timeout_seconds },
  "summary": { "transactions": N, "completed": N, "timed_out": N, "errors": N,
               "duration_seconds": float },
  "transactions": {
    "<txid>": {
      "status": "complete" | "timeout" | "error",
      "mapping_count": int | null,
      "retried": bool,
      "attempts": [ { "timeout_seconds", "duration_seconds", "status",
                      "mapping_count", "error"? } ],
      "error"?: "..."
    }
  }
}
```

A transaction that times out on the first attempt is retried once with
`--retry-timeout`; only the final attempt determines its status. The process
exits non-zero if any transaction ends in `error` (timeouts alone do not fail
the stage).

### Sake (`sake.json`)

```
{
  "schema_version": "1.0",
  "tool": "sake",
  "seed": int,
  "samples": int,
  "summary": { "transactions", "matched_outputs", "total_outputs",
               "output_match_rate", ... },
  "transactions": { "<txid>": { per-transaction match statistics } }
}
```

Sake replays each non-blame CoinJoin's input groups through the modified
Wasabi decomposition algorithm with a deterministic per-transaction RNG
(`seed + tx index`) and reports how closely the simulated output
decomposition matches the observed one.

### Combined stage output

The pipeline's PBS mappings stage (`coinjoin-pipeline ... --mappingsPbs`) runs
both tools against `coinjoin-analysis_data/coinjoin_tx_info.json` and merges
the results into `coinjoin-mappings_data/coinjoin_mappings.json`:

```
{
  "schema_version": "1.0",
  "status": "complete" | "partial",   // partial when the enumerator timed out on any tx
  "provenance": { enumerator_image, sake_image,
                  enumerator_image_digest, sake_image_digest },
  "enumerator": { ...enumerator.json... },
  "sake": { ...sake.json... }
}
```
