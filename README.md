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
