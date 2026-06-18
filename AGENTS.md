# DOX framework

- DOX is a hierarchy of AGENTS.md files that carry the durable contracts for this repo.
- Agents must follow the DOX chain on every edit.

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees.
- Any work product must stay understandable from the nearest AGENTS.md plus every parent above it.

## Read Before Editing

1. Read this root AGENTS.md.
2. Identify every path you expect to touch.
3. Walk from repo root to each target, reading every AGENTS.md on the way.
4. The nearest AGENTS.md is the local contract; parents hold repo-wide rules.
5. If docs conflict, the closer doc controls local detail, but no child may weaken DOX.

Do not rely on memory — re-read the applicable chain in-session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done. Update the closest
owning AGENTS.md when a change affects: purpose/scope/ownership; durable structure,
contracts, or workflows; inputs/outputs/permissions/side-effects; or the Child DOX Index.
Remove stale text immediately. Refresh affected parent and child indexes.

## Style

Concise, current, operational. Stable contracts, not diary entries. Broad rules in parents,
concrete detail in children. Delete stale notes instead of explaining history.

---

# grid-validator — proactive grid health validator

## Purpose

The grid's **active, adversarial health layer**. The node stakes AIPG, probes grid workers
with unpredictable canary jobs, scores the replies (`healthy` / `slow` / `failed`), and
submits **signed attestations** to the grid. A `failed` verdict drives the same strike/evict
logic as a real job failure. Validators earn AIPG for honest, consensus-matching work and are
slashable for false attestations. CPU-only (no GPU, no local model) — validates text, image,
and video on a small always-on box. Python package: `validator/`. Entry: `validator.main`.

## Ownership

- **`validator/`** — the whole node (config, stake gate, grid client, canary probing +
  scoring, attestation signing, probe loop, CLI). Owned in its own AGENTS.md.
- **`README.md`** — operator quick start + going-live checklist.
- **`OPERATORS.md`** — plain-language run guide (install, systemd, troubleshooting, FAQ).
- **`DESIGN.md`** — source of truth for architecture, economics, threat model, rewards/slashing,
  settlement integration, and the grid-side dependencies still TODO. Read before any design change.
- **`install.sh` / `aipg-validator.service` / `.env.template`** — install + run-as-service.

## Local Contracts

- **Inherit org engineering standards:** /Users/j/fix-axios-vuln/aipg-documentation/engineering-standards/
  (core + git + the matching language file). The rules below are grid-validator specializations.
- **Early-stage / v0:** the grid does not yet expose targeted probing (`POST /v1/validator/probe`),
  the worker list (`GET /v1/validator/workers`), the attestation sink (`POST /v1/validator/attest`),
  or the `ValidatorStaking` contract. The node is written so each is best-effort: missing
  endpoints fall back to **v0 model-routed probing** (can't attribute to a single worker, but
  failed canaries still strike via grid Layer 2). Do not assume these exist; keep the fallbacks.
- **Secrets:** `.env` holds `VALIDATOR_PRIVATE_KEY` (signs attestations + controls stake) — always
  chmod 600, never commit. The key never leaves the box; the grid receives only signed payloads.
- **Pay for verified-correct work, never presence.** Any reward/scoring logic added here must track
  consensus agreement, not attestation count (DESIGN.md "Rewards & slashing").
- **Canaries must stay unpredictable** — random per-probe nonce + rotating QA — so a worker can't
  precompute answers and a validator can't fake a verdict without actually probing.
- On-chain reads (stake gate) fail fast and gate startup; they are not on the probe hot path.

## Work Guidance

- New env vars: add to `validator/config.py` `Settings` (typed, with a default), not ad-hoc `getenv`.
- Keep heavy deps (web3, eth-account, Pillow, imagehash) lazily imported so a missing optional dep
  degrades a check to skip/dev-mode rather than crashing the node.
- New grid-side endpoint dependencies must stay optional with a documented fallback (see Local Contracts).

## Verification

—

## Child DOX Index

- [validator/AGENTS.md](validator/AGENTS.md) — the node: config, stake, probing, attestation, loop, CLI.
