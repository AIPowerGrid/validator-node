# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""On-chain stake gate.

A validator must hold >= MIN_STAKE in the ValidatorStaking contract on Base to
run. This is the sybil-resistance + skin-in-the-game primitive: attestations from
an unstaked address are rejected by the grid, and this local gate fails fast so a
misconfigured node doesn't spin uselessly.

The contract isn't deployed yet (see DESIGN.md). Until VALIDATOR_STAKING_ADDR is
set, `stake_of()` raises NotDeployed and `main` treats REQUIRE_STAKE accordingly.
"""

import logging

from .config import Settings

logger = logging.getLogger("validator.staking")

# Minimal read ABI — stakeOf(address) -> uint256 (18 decimals), isActiveValidator(address) -> bool.
STAKING_ABI = [
    {"inputs": [{"name": "a", "type": "address"}], "name": "stakeOf",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "a", "type": "address"}], "name": "isActiveValidator",
     "outputs": [{"name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
]


class NotDeployed(RuntimeError):
    pass


def _w3():
    try:
        from web3 import Web3
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("web3 not installed; `pip install web3` to use the stake gate.") from e
    return Web3(Web3.HTTPProvider(Settings.BASE_RPC_URL))


def stake_of(address: str) -> int:
    """Return the validator's staked AIPG (whole tokens)."""
    if not Settings.VALIDATOR_STAKING_ADDR:
        raise NotDeployed("VALIDATOR_STAKING_ADDR not set — contract not deployed yet.")
    w3 = _w3()
    c = w3.eth.contract(address=w3.to_checksum_address(Settings.VALIDATOR_STAKING_ADDR), abi=STAKING_ABI)
    raw = c.functions.stakeOf(w3.to_checksum_address(address)).call()
    return raw // (10 ** 18)


def assert_eligible() -> None:
    """Fail fast unless this validator is staked >= MIN_STAKE.

    Honors Settings.REQUIRE_STAKE so local dev can run before the contract ships.
    """
    if not Settings.REQUIRE_STAKE:
        logger.warning("REQUIRE_STAKE=false — running WITHOUT an on-chain stake gate (dev only).")
        return
    if not Settings.VALIDATOR_WALLET:
        raise RuntimeError("VALIDATOR_WALLET required to check stake.")
    try:
        staked = stake_of(Settings.VALIDATOR_WALLET)
    except NotDeployed:
        logger.warning(
            "ValidatorStaking contract not deployed yet; cannot verify stake. "
            "Set VALIDATOR_REQUIRE_STAKE=false to run pre-launch."
        )
        raise
    if staked < Settings.MIN_STAKE:
        raise RuntimeError(
            f"Insufficient stake: {staked} AIPG < required {Settings.MIN_STAKE}. Stake more to validate."
        )
    logger.info(f"Stake OK: {staked} AIPG staked (min {Settings.MIN_STAKE}).")
