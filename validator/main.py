# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Validator node entrypoint: verify stake, then probe workers in a loop.

Run:  python -m validator.main   (from the validator-node/ dir, with a .env)
"""

import asyncio
import logging
import time

from . import attest, prober, staking
from .config import Settings
from .grid_client import GridClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("validator.main")


async def _probe_model(grid: GridClient, model: str, round_index: int) -> None:
    """v0: model-routed canary (can't attribute to a single worker yet, but a
    failed canary still strikes whichever worker answered, via grid Layer 2)."""
    canary = prober.make_canary(round_index)
    try:
        text, latency = await grid.chat(model, canary["prompt"])
    except Exception as e:
        logger.warning(f"[{model}] canary errored: {e}")
        text, latency = "", Settings.PROBE_TIMEOUT_S
    verdict = prober.score(canary, text, latency)
    logger.info(f"[{model}] {canary['kind']} canary → {verdict} ({latency:.1f}s)")

    att = attest.build(
        worker_id="",  # unknown in v0 (no targeted probe yet)
        model=model, canary=canary, verdict=verdict,
        latency_ms=int(latency * 1000), ts=int(time.time()),
    )
    await grid.submit_attestation(attest.sign(att))


async def _probe_worker(grid: GridClient, worker: dict, round_index: int) -> None:
    """Layer 3b: targeted probe of a specific worker (when the grid exposes it)."""
    canary = prober.make_canary(round_index)
    wid = worker["worker_id"]
    model = (worker.get("models") or ["unknown"])[0]
    payload = {"prompt": canary["prompt"], "max_length": Settings.PROBE_MAX_TOKENS}
    t0 = time.time()
    res = await grid.probe_worker(wid, payload)
    latency = time.time() - t0
    text = (res or {}).get("text", "") if res else ""
    verdict = prober.score(canary, text, latency)
    logger.info(f"[{wid[:8]} {model}] {canary['kind']} → {verdict} ({latency:.1f}s)")
    att = attest.build(wid, model, canary, verdict, int(latency * 1000), int(time.time()))
    await grid.submit_attestation(attest.sign(att))


async def probe_round(grid: GridClient, round_index: int) -> None:
    """Run one full probe round (targeted if the grid supports it, else v0)."""
    workers = await grid.list_workers()
    if workers:  # Layer 3b: targeted, per-worker
        await asyncio.gather(
            *(_probe_worker(grid, w, round_index + i) for i, w in enumerate(workers))
        )
    else:        # v0: model-routed (text models only — see prober)
        models = [m for m in await grid.list_models() if prober.is_text_model(m)]
        await asyncio.gather(
            *(_probe_model(grid, m, round_index + i) for i, m in enumerate(models))
        )


async def run() -> None:
    Settings.validate()
    # Stake gate — refuse to run unstaked (unless REQUIRE_STAKE=false for dev).
    try:
        staking.assert_eligible()
    except staking.NotDeployed:
        if Settings.REQUIRE_STAKE:
            logger.error("Stake contract not deployed and REQUIRE_STAKE=true — exiting. "
                         "Set VALIDATOR_REQUIRE_STAKE=false to run pre-launch.")
            return

    grid = GridClient()
    logger.info(f"Validator online → {Settings.GRID_API_URL} (probe every {Settings.PROBE_INTERVAL_S}s)")
    round_index = 0
    try:
        while True:
            try:
                await probe_round(grid, round_index)
            except Exception as e:
                logger.error(f"probe round failed: {e}", exc_info=True)
            round_index += 1
            await asyncio.sleep(Settings.PROBE_INTERVAL_S)
    finally:
        await grid.aclose()


if __name__ == "__main__":
    asyncio.run(run())
