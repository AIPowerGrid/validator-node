# AIPG Validator Node

A validator node is the **active, adversarial health layer** of the grid. Where the
worker self-health check (Layer 1) and the grid's strike/evict logic (Layer 2) are
*reactive* — they only act after a real user job fails — a validator is *proactive*:
it continuously probes workers with canary jobs, verifies the outputs are real, and
feeds the result into both grid eviction and on-chain settlement.

Validators are an economic role: they **stake AIPG** to participate, **earn AIPG** for
honest validation work, and are **slashable** for provable misbehavior.

## Why staking

Validators have power — their attestations can get a worker evicted and unpaid. That
power must be costly to abuse:

- **Stake to participate** (`MIN_STAKE`, e.g. 50,000 AIPG). No stake → the grid rejects
  the validator's attestations. This is sybil resistance: spinning up 100 fake validators
  to collude requires 100× the stake.
- **Earn** a share of grid fees / emissions proportional to honest attestation volume and
  stake. Validating is paid work, like a worker generating tokens.
- **Slash** on provable fault: signing an attestation that contradicts the majority of
  other validators on the same canary (false-fail to grief an honest worker, or false-pass
  to cover a colluding worker). Slashed stake is burned or redistributed.

## System requirements

One node, one spec. A validator does light network work (small canary prompts, fetching a
few hundred KB of probe output, perceptual-hash math) — **no GPU, no AI model runs locally.**

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 1 core | 2 cores |
| RAM | 1 GB | 2 GB |
| Disk | 1 GB (code + venv + deps) | 2 GB |
| Network | stable; ~low bandwidth (small prompts + a few hundred KB/probe) | — |
| OS | Linux / macOS / Windows, **Python 3.10+** | Linux + systemd (always-on) |
| GPU | **none** | none |
| Uptime | runs 24/7 (use the systemd unit) | — |
| To stake (at launch) | a Base wallet + **50,000 AIPG** | — |

That's it — a ~$5–10/mo VPS, a Raspberry Pi 4, or a spare always-on machine all qualify.

## Components

```
validator-node/
  validator/
    config.py       # env + constants
    staking.py      # on-chain stake gate (web3 → ValidatorStaking contract)
    grid_client.py  # grid API: list workers, probe a worker, submit attestations
    prober.py       # canary generation + output scoring
    attest.py       # build + sign (EIP-191) attestations
    main.py         # entrypoint: verify stake → probe loop
```

## Probe lifecycle (one round, every PROBE_INTERVAL_S)

1. **Stake gate** — confirm this validator's on-chain stake ≥ MIN_STAKE. If not, refuse to
   run (attestations would be rejected anyway).
2. **Enumerate** active (worker, model) pairs from the grid.
3. **Canary** each — two kinds, mixed so a worker can't special-case them:
   - *Liveness/echo*: "Reply with exactly this token and nothing else: `<nonce>`" → output
     must contain the per-probe random nonce. Proves the pipeline runs and isn't replaying.
   - *Correctness*: a small deterministic QA ("What is 7×6? Reply with only the number." →
     `42`). Catches a model that's loaded-but-wrong (corrupted weights, wrong model swapped in).
4. **Score**: `healthy` (correct + within latency budget), `slow` (correct but over budget),
   `failed` (empty / wrong / timeout).
5. **Attest**: sign `{worker_id, model, nonce, verdict, latency_ms, ts}` with the validator's
   key and POST to the grid. The grid:
   - counts a `failed` verdict as a **strike** (same mechanism as Layer 2 → evict at 3),
   - records the attestation for settlement + the worker-health dashboard.

## Validating image & video models

Text canaries don't work for generative media — output is non-deterministic pixels with no
exact-match answer. Media validation works along three axes (cheap → expensive), and a media
canary uses a **fixed seed + an unpredictable prompt** (random object/color/setting + nonce)
at small dimensions/steps (cheap to generate). The worker uploads to R2 as usual; the
validator fetches the object bytes and scores them.

**Axis 1 — structural / liveness (cheap, no ML).** Output decodes; dimensions/format match
the request; it isn't blank or pure noise (entropy/variance threshold); latency is sane for
the requested steps. This is the media equivalent of "empty completion = failure" and catches
dead backends + garbage instantly.

**Axis 2 — cross-worker perceptual consensus (cheap, the key unlock).** Send the *same*
fixed-seed canary to multiple workers on the same model. Honest workers produce perceptually
near-identical images; compare via **perceptual hash (pHash)** and flag the outlier
(model-swapper, cached-image returner). Same Schelling-point logic as text — no "correct
answer" needed, just agreement. pHash is trivial CPU (Pillow + imagehash). Tolerance accounts
for cross-GPU/library nondeterminism (compare Hamming distance, not equality).

**Video** applies axes 1–2 to sampled keyframes (the grid's probe response returns a few
preview frames, so the validator needs no video decoder), plus: correct frame count / fps /
duration, frames decode, and a **motion check** (perceptual-hash diff between first and last
frame) to confirm real animation rather than a looped still.

Both axes are **CPU-only** (Pillow + imagehash) — no GPU, no ML model — so the single
validator node validates text, image, and video on the same modest hardware (see *System
requirements*). Semantic prompt-adherence via CLIP is a possible **future** add, deliberately
left out so there's one node with one clear, light requirement.

## Targeted probing — grid dependency (Layer 3b, TODO on the grid)

The current dispatch is a shared Redis-Streams consumer group, so a job can't be aimed at a
*specific* worker — that's exactly why a single bad worker was hard to isolate. The validator
needs a **direct-probe endpoint** on the grid:

`POST /v1/validator/probe  {worker_id, payload}` → grid sends the job straight to
`_local_ws[worker_id]`, collects the reply, returns it to the validator. Validator-role +
staked only. Until this exists, `prober.py` runs in **v0 mode**: it injects canaries through
the normal model-routed path — it can't name which worker answered, but because Layer 2
strikes any worker that returns empty/wrong, canary traffic alone still drives eviction of
bad workers. Targeted attribution + per-worker scoring needs the endpoint.

## On-chain: `ValidatorStaking` contract (TODO in aipg-smart-contracts)

Standalone, Synthetix-adjacent (mirror `StakingVault.sol`), on Base:
- `stake(amount)` / `requestUnstake()` / `withdraw()` with an unbonding delay (e.g. 7d) so a
  validator can't stake → misbehave → instantly exit before being slashed.
- `slash(validator, amount, reason)` callable only by the grid's settlement authority (a
  RoleManager role), emitting an auditable event.
- `isActiveValidator(addr) → bool` and `stakeOf(addr)` read by the grid to gate attestations.
- Rewards: either funded like `StakingVault` (manual `notifyRewardAmount`) or wired into the
  grid `RewardPool` module so validator pay comes from the same emissions as worker den.

AIPG token: `0xa1c0deCaFE3E9Bf06A5F29B7015CD373a9854608` (Base).

## Threat model (what staking+slashing defends)

| Attack | Defense |
|---|---|
| Sybil validators to outvote honest ones | per-validator MIN_STAKE; influence ∝ stake |
| False-fail to grief a competitor's worker | attestation must match validator majority; minority is slashed |
| False-pass to cover a colluding worker | same majority check; canaries are unpredictable (random nonce) |
| Stake → attack → exit before slash | unbonding delay on withdraw |
| Worker hardcodes canary answers | random nonce echo + rotating QA set; targeted probe uses live job path |

## Rewards & slashing

**Golden rule: pay for *correct work verified against consensus*, never for mere presence.**
Uptime is a multiplier, not a paycheck — a node that's "up" but rubber-stamps everything is
worthless and must not earn.

**Validators are a thin security layer, not a primary earner.** Workers carry the real cost
of the network — GPU capex plus electricity — so workers must always capture the large
majority of rewards. Validating runs on a ~$5 VPS, so its pool is deliberately small (a few
percent of worker rewards). This isn't stinginess; it's supply protection: if validating ever
out-earned compute per dollar invested, capital would flee GPUs for cheap validator boxes and
starve the grid of the very compute it exists to provide. A validator's return comes mostly
from the *opportunity cost of its locked stake* (it should modestly beat passive staking to
justify the work + slashing risk), not from the work paying like a GPU.

### What earns

| Earns for | Measured as |
|---|---|
| **Validation work** (the core) | canary checks whose verdict matched epoch **consensus** |
| **Uptime / availability** | `uptime_factor` = assigned rounds delivered ÷ assigned (a *multiplier*) |
| **Catching real faults** | flat bonus per worker you correctly flagged that consensus + grid signals confirm + evict |
| **Coverage** (minor) | validating across the assigned spread of workers/models, not camping one |

### Per-epoch reward formula

```
reward_v = VALIDATOR_POOL_DEN × (score_v / Σ score_all)

score_v = correct_validations_v
        × agreement_rate_v        # your verdicts matching consensus, 0..1
        × uptime_factor_v         # assigned rounds delivered, 0..1
        × stake_weight_v          # sqrt(stake), capped (anti-plutocracy)
        + fault_bonus_v
```

### Starting constants (all tunable via the contract / grid config)

| Constant | Value | Why |
|---|---|---|
| `MIN_STAKE` | 50,000 AIPG | sybil cost; gates participation |
| `VALIDATOR_POOL_BPS` | 200 (2% of epoch worker den) | thin security tax; workers keep ~98%. Hard-capped so validators can never out-earn compute |
| `CONSENSUS_THRESHOLD` | ≥ 2/3 agreeing | what counts as "consensus" for a canary |
| `SLASH_THRESHOLD` | disagree w/ ≥ 80% consensus | only slash against *strong* consensus (avoids slashing on noise) |
| `SLASH_RATE` | 1% of stake / offense, escalating | griefing & collusion both punished |
| `STAKE_WEIGHT` | `min(sqrt(stake), sqrt(10×MIN_STAKE))` | diminishing returns; whales can't dominate |
| `UNBONDING_DELAY` | 7 days | can't stake → cheat → exit before slash |
| `FAULT_BONUS` | small flat den | points validators at workers that matter |

### Anti-gaming

- **Assigned probes, not free choice.** Each round the grid deterministically assigns each
  validator a pseudo-random subset of workers — `assignment = H(epoch, round, validator, worker) < threshold`.
  Even coverage; you can't farm one easy worker or skip a suspected-bad one.
- **Unpredictable canaries.** Random per-probe nonce (echo) + rotating QA — a worker can't
  precompute answers, and a validator can't fake a result without actually probing.
- **Consensus, not count.** Reward tracks *agreement*, so spamming attestations does nothing.
- **No self-validation.** A validator's assignments exclude workers under its own account/wallet.
- **Commit–reveal (v2 hardening).** Submit `hash(verdict, salt)` first, reveal after the round
  closes, so a lazy validator can't copy others' verdicts before committing. Not needed at
  launch (attestations are private to the grid, not a public mempool), but the upgrade path.

### Slashing

A single rule covers both failure modes: **your verdict must match strong consensus.**
- False `failed` on a worker the network says is `healthy` → **griefing** → slash.
- False `healthy` on a worker the network says is `failed` → **collusion / laziness** → slash.
- Persistent statistical bias toward one worker against consensus → escalated slash.
Slashed stake is burned (or routed to the reward pool). Going *offline* is **not** slashed —
you just stop earning and are eventually deregistered.

### Bootstrapping (before there's a quorum)

With 1–2 validators there's no consensus to score against. So early validators are graded
against the grid's **objective** signals — Layer 2 already *knows* if a worker returned
empty / timed out. Verdicts are checked against that ground truth, transitioning to
consensus-weighting as the validator set grows past `CONSENSUS_THRESHOLD`-viable size.

## Settlement integration (grid_ledger)

Validator pay rides the **existing** ledger → epoch → Merkle → on-chain rails — no parallel
system. At epoch close the settlement bot:

1. Sums worker den for the epoch → `VALIDATOR_POOL_DEN = total_worker_den × VALIDATOR_POOL_BPS/10000`.
2. Computes each validator's `score_v` from that epoch's attestations (agreement, uptime, stake, bonuses).
3. Writes one `grid_ledger` row per validator with:
   - `job_type = "validation"`, `worker_id` = validator's id, `wallet` = validator wallet,
   - `den = VALIDATOR_POOL_DEN × score_v/Σscore`, `output_units` = correct_validations,
   - `result_hash` = hash over the epoch's attestation set for this validator (audit trail).
4. These rows fold into `grid_epochs.total_den` and the **same Merkle root** → validators are
   paid AIPG pro-rata exactly like workers, in one settlement tx.

Attestations themselves are stored (a `grid_attestations` table: epoch, validator, worker,
nonce, verdict, latency, sig) so consensus, scoring, and slashing are recomputable and
auditable against the on-chain root.

## Status

- [x] Node scaffold + v0 prober (this folder)
- [x] Rewards/slashing spec + ledger integration (this doc)
- [x] Image/video validation design + media prober (structural + pHash consensus + video motion, CPU-only)
- [ ] Wire media prober into the probe loop (needs targeted probe + worker modality, Layer 3b)
- [ ] `grid_attestations` table + `POST /v1/validator/attest` (stake-gated, sig-verified)
- [ ] Grid: `POST /v1/validator/probe` (targeted) + `GET /v1/validator/workers`
- [ ] Grid: deterministic probe assignment (`H(epoch,round,validator,worker)`)
- [ ] Settlement bot: validator scoring + `job_type="validation"` ledger rows (see task #45)
- [ ] `ValidatorStaking.sol` (stake / unbond / slash / `stakeOf`) + deploy on Base
- [ ] Grid: validator-role gate keyed on on-chain stake
