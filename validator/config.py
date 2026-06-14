# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Validator node configuration (env-driven; secrets stay in a chmod-600 .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(os.getenv("VALIDATOR_ENV", Path.cwd() / ".env"))
load_dotenv(ENV_FILE)


class Settings:
    # ── Grid ──
    GRID_API_URL = os.getenv("GRID_API_URL", "https://grid.aipowergrid.io")
    # Grid API key whose account carries the `validator` role.
    VALIDATOR_API_KEY = os.getenv("VALIDATOR_API_KEY", "")

    # ── Identity / on-chain ──
    # The validator's wallet signs attestations AND holds the stake. The private
    # key is required to sign; keep .env at chmod 600 and never commit it.
    VALIDATOR_WALLET = os.getenv("VALIDATOR_WALLET", "").lower()
    VALIDATOR_PRIVATE_KEY = os.getenv("VALIDATOR_PRIVATE_KEY", "")

    BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
    AIPG_TOKEN_ADDR = os.getenv("AIPG_TOKEN_ADDR", "0xa1c0deCaFE3E9Bf06A5F29B7015CD373a9854608")
    VALIDATOR_STAKING_ADDR = os.getenv("VALIDATOR_STAKING_ADDR", "")  # set after deploy

    # Minimum stake (whole AIPG) required to run. Mirrors the on-chain MIN_STAKE.
    MIN_STAKE = int(os.getenv("VALIDATOR_MIN_STAKE", "50000"))
    # Skip the on-chain gate for local dev ONLY. In prod the grid enforces it too.
    REQUIRE_STAKE = os.getenv("VALIDATOR_REQUIRE_STAKE", "true").lower() == "true"

    # ── Probing ──
    MEDIA_LATENCY_BUDGET_S = float(os.getenv("MEDIA_LATENCY_BUDGET_S", "60"))
    VIDEO_LATENCY_BUDGET_S = float(os.getenv("VIDEO_LATENCY_BUDGET_S", "120"))
    PHASH_TOLERANCE = int(os.getenv("PHASH_TOLERANCE", "12"))

    PROBE_INTERVAL_S = int(os.getenv("PROBE_INTERVAL_S", "60"))
    PROBE_TIMEOUT_S = int(os.getenv("PROBE_TIMEOUT_S", "45"))
    PROBE_MAX_TOKENS = int(os.getenv("PROBE_MAX_TOKENS", "256"))
    # Latency budget: a correct-but-slower-than-this answer scores `slow`.
    LATENCY_BUDGET_S = float(os.getenv("LATENCY_BUDGET_S", "30"))

    @classmethod
    def validate(cls):
        if not cls.VALIDATOR_API_KEY:
            raise RuntimeError("VALIDATOR_API_KEY is required.")
        if cls.REQUIRE_STAKE and not cls.VALIDATOR_PRIVATE_KEY:
            raise RuntimeError("VALIDATOR_PRIVATE_KEY is required to sign attestations / prove stake.")
