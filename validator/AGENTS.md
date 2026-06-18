# validator — the node (config, stake, probing, attestation, loop, CLI)

## Purpose

The validator implementation: load config, gate on on-chain stake, enumerate grid targets,
fire unpredictable canaries, score the replies, sign attestations, and POST them in a loop.
CPU-only — text, image, and video scoring run on Pillow + imagehash, no GPU or local model.

## Ownership

- **`config.py`** — env-driven `Settings` (grid URL + key, wallet/private key, Base RPC +
  contract addrs, `MIN_STAKE`/`REQUIRE_STAKE`, probe intervals + latency budgets, pHash tolerance).
  `Settings.validate()` enforces required fields. All env reads live here.
- **`staking.py`** — on-chain stake gate (`stake_of`, `assert_eligible`). Raises `NotDeployed`
  until `VALIDATOR_STAKING_ADDR` is set; honors `REQUIRE_STAKE=false` for pre-launch/dev.
- **`grid_client.py`** — async httpx client for grid endpoints: `list_models`, `list_workers`,
  `probe_worker` (targeted), `chat` (v0 model-routed), `submit_attestation`. Each grid-only
  endpoint degrades gracefully (empty list / `None` / `False`) when not yet deployed.
- **`prober.py`** — text canaries (`echo` nonce + rotating `qa`) and `score()`; `is_text_model`
  heuristic skips media models in v0; `_strip_think` ignores reasoning-model chain-of-thought.
- **`media_prober.py`** — image/video canaries + scoring across structural, pHash-consensus, and
  video-motion axes. Heavy deps imported lazily; missing dep → skip, never crash.
- **`attest.py`** — `build()` the canonical attestation body + `sign()` (EIP-191 over sorted-key
  compact JSON). Unsigned (`signature=None`) only when no key is configured (dev).
- **`main.py`** — entrypoint: `run()` (stake gate → probe loop), `probe_round` (targeted if the
  grid exposes workers, else v0 model-routed), `_probe_worker` / `_probe_model`.
- **`cli.py`** — `aipg-validator init | check | run` (interactive `.env` at chmod 600; one-shot
  health check; the loop).

## Local Contracts

- **Canonical attestation form is load-bearing:** `attest._canonical` uses
  `json.dumps(..., sort_keys=True, separators=(",", ":"))` so the digest the grid recovers
  matches the one signed. Do not change the field set or serialization without the grid side.
- **Stake is in whole AIPG.** `stake_of` divides the raw 18-decimal balance by 10**18; compare
  against `Settings.MIN_STAKE` (also whole tokens).
- **Scoring contract:** verdicts are exactly `healthy | slow | failed`. `failed` = empty/wrong/
  undecodable/wrong-dims/blank/pHash-outlier/static-loop; `slow` = correct but over the latency
  budget; `healthy` otherwise. pHash uses Hamming distance vs `PHASH_TOLERANCE`, never equality
  (absorbs cross-GPU nondeterminism).
- **A skipped check must not penalize a worker** — a missing optional dep returns ok/skip, not
  `failed`.
- **v0 fairness:** never send a text canary to a media model — gate model-routed probing through
  `prober.is_text_model`.

## Work Guidance

—

## Verification

—

## Child DOX Index

—
