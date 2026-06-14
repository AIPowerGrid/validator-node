# Run an AIPG Validator Node

**A validator helps keep the grid honest — and earns AIPG for it.** Your node quietly
checks that the AI workers on the grid are actually working (not down, not returning
garbage), and reports what it finds. You stake AIPG to take part, and you earn AIPG for
doing the job well.

You do **not** need a GPU. The one validator node checks text, image, *and* video workers —
all with light CPU-only checks (small test prompts, and fast look-alike/structure checks on
images and video frames). A small always-on machine is plenty.

---

## System requirements

| | Minimum | Recommended |
|---|---|---|
| **CPU** | 1 core | 2 cores |
| **RAM** | 1 GB | 2 GB |
| **Disk** | 1 GB | 2 GB |
| **GPU** | none | none |
| **OS** | Linux / macOS / Windows | Linux + systemd |
| **Python** | 3.10+ | 3.11+ |
| **Network** | stable broadband (low bandwidth) | — |
| **Uptime** | runs 24/7 | systemd service |

A ~$5–10/mo VPS, a Raspberry Pi 4, or a spare always-on machine all qualify.

**Also needed:**
- A **validator API key** from the AIPG dashboard (validator role).
- To stake (at launch): a **Base wallet** + **50,000 AIPG**. Skip during the pre-launch
  test phase (`VALIDATOR_REQUIRE_STAKE=false`).

> **Pre-launch?** The staking contract isn't live yet. You can run a validator **today**
> with no stake to help test — just answer "no" to the stake question during setup.

---

## Install in 3 steps

```bash
# 1. Get the code
git clone https://github.com/AIPowerGrid/validator-node && cd validator-node

# 2. Run the installer (sets up Python, asks you a few questions)
./install.sh

# 3. Check it works
./.venv/bin/python -m validator.cli check
```

`check` connects to the grid, lists the models, sends one test prompt, and tells you the
result. If you see `✅ check complete`, you're good.

Then start it for real:

```bash
./.venv/bin/python -m validator.cli run
```

You'll see a line per check, e.g. `[Qwen3.6-27B] qa canary → healthy (9.4s)`.

---

## Keep it running (recommended)

So it survives reboots and SSH logouts, install it as a service:

```bash
sudo cp aipg-validator.service /etc/systemd/system/
sudo nano /etc/systemd/system/aipg-validator.service   # set User= and the two paths
sudo systemctl daemon-reload
sudo systemctl enable --now aipg-validator
journalctl -u aipg-validator -f                          # watch the logs
```

---

## Staking & rewards (plain version)

- **Why stake?** Your reports can get a worker kicked off the grid. Staking means you have
  skin in the game — if you lie (report a good worker as bad, or cover for a broken one),
  part of your stake gets **slashed**. Honest validators never lose stake.
- **How much?** 50,000 AIPG minimum. More stake = more weight = a bigger share of rewards.
- **Earning:** you earn AIPG continuously for honest validation work, paid from the same
  settlement as workers. Roughly: your share ∝ (your honest checks × your stake).
- **Set expectations:** validating is a **light-duty, modest-reward** role — *not* a way to
  out-earn a GPU. By design the validator pool is a small slice (~2%) of what workers earn,
  because workers carry the real cost (GPUs + power). Think of it as a fair return on your
  *staked* AIPG plus a bit for the work — comparable to staking, a touch more for the effort
  and slashing risk. If you want bigger rewards and have a GPU, run a **worker** instead.
- **Getting out:** unstaking has a short waiting period (so nobody can stake, cheat, and
  run before they're caught). Normal operators never notice it.

> Exact stake amount, reward rate, and unbonding period are finalized with the
> `ValidatorStaking` contract launch — this guide updates when it ships.

---

## Is it working? (quick checks)

```bash
./.venv/bin/python -m validator.cli check     # one-shot test, prints verdicts
systemctl status aipg-validator               # is the service up?
journalctl -u aipg-validator --since "10 min ago"   # recent activity
```

A healthy node logs `healthy` / occasionally `slow` verdicts. Lots of `failed` across
*every* model usually means **your** network or key is the problem, not the workers.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `VALIDATOR_API_KEY is required` | Run `aipg-validator init` and paste your key |
| `Grid reachable — models: (none)` | No workers online right now; not your fault |
| every model shows `failed` | Check internet + that your API key is valid/active |
| `Insufficient stake` | Stake more AIPG, or set `VALIDATOR_REQUIRE_STAKE=false` (pre-launch) |
| service won't start | `journalctl -u aipg-validator -e` — usually a wrong path in the unit file |

---

## FAQ

**Do I need a GPU?** No. Validators test workers; they don't run AI models themselves.

**How much will it cost to run?** Pennies — tiny CPU and bandwidth. The stake is the only
real capital, and you keep it (it's not spent, just locked).

**Can I run a worker *and* a validator?** Yes, on separate machines/accounts. A validator
should not validate its own worker.

**Where's my private key stored?** Only in your local `.env`, which the installer sets to
`chmod 600` (readable only by you). It never leaves your machine; it's used to sign reports.

**Is my key sent to the grid?** No. The grid only receives your *signed reports* and
verifies the signature against your staked address.

---

Questions or want to validate? Reach the team — and see [DESIGN.md](DESIGN.md) for how it
works under the hood.
