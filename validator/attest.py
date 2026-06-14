# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Build and sign validator attestations.

An attestation is the validator's signed claim about one canary result. The grid
verifies the signature recovers to a *staked* validator address before counting
it toward a worker's strikes or settlement. Signing uses EIP-191 personal_sign
over the canonical JSON so the same payload always yields the same digest.
"""

import json
import logging

from .config import Settings

logger = logging.getLogger("validator.attest")


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def build(worker_id: str, model: str, canary: dict, verdict: str, latency_ms: int, ts: int) -> dict:
    """Assemble the unsigned attestation body."""
    return {
        "validator": Settings.VALIDATOR_WALLET,
        "worker_id": worker_id,
        "model": model,
        "canary_kind": canary["kind"],
        "nonce": canary["nonce"],
        "verdict": verdict,          # healthy | slow | failed
        "latency_ms": latency_ms,
        "ts": ts,
    }


def sign(attestation: dict) -> dict:
    """Return {payload, signature}. If no key is configured (dev), signature=None."""
    body = _canonical(attestation)
    if not Settings.VALIDATOR_PRIVATE_KEY:
        return {"payload": attestation, "signature": None}
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError:  # pragma: no cover
        logger.warning("eth-account not installed; sending unsigned attestation (dev only).")
        return {"payload": attestation, "signature": None}
    signed = Account.sign_message(encode_defunct(text=body), private_key=Settings.VALIDATOR_PRIVATE_KEY)
    return {"payload": attestation, "signature": signed.signature.hex()}
