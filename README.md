# AIPG Validator Node

Proactive worker-health validation for the AI Power Grid. Validators **stake AIPG**,
**earn AIPG** for honest validation, and are **slashable** for false attestations.

> **Running a node?** Start with the plain-language **[OPERATORS.md](OPERATORS.md)** —
> install in 3 steps, no GPU needed.
> **How it works under the hood?** See **[DESIGN.md](DESIGN.md)** (architecture, economics,
> threat model).

## What it does

Every `PROBE_INTERVAL_S`, the node sends canary jobs to grid workers, scores the
replies (`healthy` / `slow` / `failed`), and submits **signed attestations** to the
grid. A `failed` verdict feeds the grid's strike/evict logic (same as a real job
failure), so bad workers get evicted whether or not a paying user happened to hit them.

## Quick start

```bash
./install.sh                                   # sets up Python + walks you through .env
./.venv/bin/python -m validator.cli check      # verify config + grid + one probe round
./.venv/bin/python -m validator.cli run        # start validating
```

CLI: `aipg-validator init | check | run` (see [OPERATORS.md](OPERATORS.md)). Leave
`VALIDATOR_REQUIRE_STAKE=false` until the staking contract is deployed.

In dev mode the node runs **v0 probing**: canaries go through the normal model-routed
path. It can't yet name *which* worker answered (that needs the grid's targeted-probe
endpoint), but failed canaries still drive eviction via grid Layer 2.

## Going live (staked)

1. Deploy `ValidatorStaking.sol` on Base (TODO in `aipg-smart-contracts`).
2. Stake ≥ `VALIDATOR_MIN_STAKE` AIPG from `VALIDATOR_WALLET`.
3. Set `VALIDATOR_STAKING_ADDR` + `VALIDATOR_REQUIRE_STAKE=true`, set `VALIDATOR_PRIVATE_KEY`.
4. Grid-side endpoints needed: `POST /v1/validator/probe` (targeted), `POST /v1/validator/attest`
   (stake-gated), `GET /v1/validator/workers`.

## Security

- `.env` holds the validator private key — `chmod 600`, never commit. The key signs
  attestations and controls the stake.
- Run as a systemd service (don't `nohup` over SSH — it gets reaped).
