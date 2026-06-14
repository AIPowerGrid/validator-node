# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Canary generation + output scoring.

Two canary families, mixed per round so a worker can't special-case them:
- echo:  prove liveness + that the pipeline returns prompt-derived content
- qa:    prove the model is loaded AND correct (catches corrupted/swapped weights)

Verdicts: "healthy" | "slow" | "failed".
"""

import secrets

from .config import Settings

# Deterministic QA canaries with unambiguous one-token answers. Keep the set
# small and rotate; the echo canary (random nonce) carries the anti-replay weight.
_QA = [
    ("What is 7 multiplied by 6? Reply with only the number.", "42"),
    ("What is the capital of France? Reply with only the word.", "paris"),
    ("Complete: the opposite of 'hot' is ____. Reply with only the word.", "cold"),
    ("How many days are in a week? Reply with only the number.", "7"),
]


# v0 runs against /v1/models, which doesn't carry modality, so we can't send a
# text canary to an image/video model (it would always "fail" and unfairly strike
# that worker). Skip names that look like media models. Layer 3b's worker-list
# endpoint carries real job_types and removes the need for this heuristic.
_MEDIA_HINTS = ("ltx", "stable-diffusion", "sd-", "sdxl", "flux", "comfy",
                "video", "image", "kandinsky", "pixart", "wan2", "hunyuan")


def is_text_model(name: str) -> bool:
    n = (name or "").lower()
    return not any(h in n for h in _MEDIA_HINTS)


def make_canary(round_index: int) -> dict:
    """Build one canary. Alternates echo/qa by round so both run regularly."""
    if round_index % 2 == 0:
        nonce = secrets.token_hex(4).upper()  # 8 hex chars
        return {
            "kind": "echo",
            "nonce": nonce,
            "prompt": f"Reply with exactly this token and nothing else: {nonce}",
            "expect": nonce,
        }
    prompt, answer = _QA[(round_index // 2) % len(_QA)]
    return {"kind": "qa", "nonce": secrets.token_hex(4), "prompt": prompt, "expect": answer}


def _strip_think(text: str) -> str:
    """Reasoning models wrap chain-of-thought in <think>…</think>; judge only the
    actual answer that follows."""
    import re
    return re.sub(r"<think(?:ing)?>.*?</think(?:ing)?>", "", text or "", flags=re.DOTALL).strip()


def score(canary: dict, text: str, latency_s: float) -> str:
    """Grade a worker's reply to a canary."""
    answer = _strip_think(text)
    if not answer:
        return "failed"
    correct = canary["expect"].lower() in answer.lower()
    if not correct:
        return "failed"
    if latency_s > Settings.LATENCY_BUDGET_S:
        return "slow"
    return "healthy"
