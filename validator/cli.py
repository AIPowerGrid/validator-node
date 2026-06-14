# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Operator-friendly CLI:  aipg-validator <init | check | run>

    init   one-time interactive setup → writes .env (chmod 600)
    check  verify config + grid + stake, run ONE probe round, print results
    run    start the validator loop
"""

import argparse
import asyncio
import os
import stat
import sys
from pathlib import Path


def _cmd_init(args) -> int:
    """Interactive .env creation — no prior knowledge required."""
    env_path = Path.cwd() / ".env"
    if env_path.exists() and input(f"{env_path} exists. Overwrite? [y/N] ").lower() != "y":
        print("Keeping existing .env.")
        return 0

    print("\nAIPG Validator setup — press Enter to accept [defaults].\n")
    grid = input("Grid API URL [https://grid.aipowergrid.io]: ").strip() or "https://grid.aipowergrid.io"
    api_key = input("Validator grid API key (required): ").strip()
    wallet = input("Validator wallet address 0x… (for stake/rewards, optional pre-launch): ").strip()
    staked = input("Run with on-chain stake required? [y/N] ").lower() == "y"
    pk = ""
    if staked:
        pk = input("Validator private key (kept local, chmod 600): ").strip()

    lines = [
        f"GRID_API_URL={grid}",
        f"VALIDATOR_API_KEY={api_key}",
        f"VALIDATOR_WALLET={wallet}",
        f"VALIDATOR_PRIVATE_KEY={pk}",
        f"VALIDATOR_REQUIRE_STAKE={'true' if staked else 'false'}",
        "BASE_RPC_URL=https://mainnet.base.org",
        "AIPG_TOKEN_ADDR=0xa1c0deCaFE3E9Bf06A5F29B7015CD373a9854608",
        "VALIDATOR_STAKING_ADDR=",
        "VALIDATOR_MIN_STAKE=50000",
        "PROBE_INTERVAL_S=60",
    ]
    env_path.write_text("\n".join(lines) + "\n")
    os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 — protects the private key
    print(f"\n✅ Wrote {env_path} (chmod 600). Next: `aipg-validator check`")
    return 0


def _cmd_check(args) -> int:
    """One-shot health check so an operator knows it works before running 24/7."""
    from . import staking
    from .config import Settings
    from .grid_client import GridClient
    from .main import probe_round

    try:
        Settings.validate()
    except RuntimeError as e:
        print(f"❌ Config: {e}")
        return 1
    print(f"✅ Config OK → grid {Settings.GRID_API_URL}")

    # Stake (best-effort; informational in check)
    try:
        staking.assert_eligible()
        print("✅ Stake: eligible")
    except staking.NotDeployed:
        print("ℹ️  Stake: contract not deployed yet (fine pre-launch)")
    except RuntimeError as e:
        print(f"⚠️  Stake: {e}")

    async def _go():
        grid = GridClient()
        try:
            models = await grid.list_models()
            print(f"✅ Grid reachable — models: {', '.join(models) or '(none)'}")
            print("Running one probe round...\n")
            await probe_round(grid, 0)
        finally:
            await grid.aclose()

    asyncio.run(_go())
    print("\n✅ check complete.")
    return 0


def _cmd_run(args) -> int:
    from .main import run
    asyncio.run(run())
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aipg-validator", description="AIPG validator node")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="interactive setup → .env")
    sub.add_parser("check", help="verify config/grid/stake + one probe round")
    sub.add_parser("run", help="start the validator loop")
    args = p.parse_args(argv)
    return {"init": _cmd_init, "check": _cmd_check, "run": _cmd_run}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
