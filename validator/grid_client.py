# SPDX-FileCopyrightText: 2026 AI Power Grid
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Thin async client for the grid's validator + OpenAI-compatible endpoints."""

import logging

import httpx

from .config import Settings

logger = logging.getLogger("validator.grid")


class GridClient:
    def __init__(self):
        self._http = httpx.AsyncClient(
            base_url=Settings.GRID_API_URL.rstrip("/"),
            headers={"Authorization": f"Bearer {Settings.VALIDATOR_API_KEY}"},
            timeout=Settings.PROBE_TIMEOUT_S + 5,
        )

    async def list_models(self) -> list[str]:
        r = await self._http.get("/v1/models", timeout=10)
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]

    async def list_workers(self) -> list[dict]:
        """Active (worker, models) pairs. Needs the grid validator endpoint;
        falls back to an empty list (v0 mode probes by model instead)."""
        try:
            r = await self._http.get("/v1/validator/workers", timeout=10)
            if r.status_code == 200:
                return r.json().get("workers", [])
        except httpx.HTTPError:
            pass
        return []

    async def probe_worker(self, worker_id: str, payload: dict) -> dict | None:
        """Targeted probe of one worker (Layer 3b). Returns None if the grid
        doesn't yet expose the endpoint — caller falls back to model-routed."""
        try:
            r = await self._http.post(
                "/v1/validator/probe", json={"worker_id": worker_id, "payload": payload}
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            logger.warning(f"probe_worker failed for {worker_id}: {e}")
            return {"error": str(e)}

    async def chat(self, model: str, prompt: str) -> tuple[str, float]:
        """v0 model-routed canary via the public chat endpoint. Returns
        (text, latency_seconds). Non-streaming so we get the whole answer."""
        import time
        t0 = time.time()
        r = await self._http.post(
            "/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": Settings.PROBE_MAX_TOKENS,
                "stream": False,
            },
        )
        dt = time.time() - t0
        r.raise_for_status()
        text = r.json()["choices"][0]["message"].get("content") or ""
        return text, dt

    async def submit_attestation(self, attestation: dict) -> bool:
        """POST a signed attestation. Returns True on accept (200)."""
        try:
            r = await self._http.post("/v1/validator/attest", json=attestation, timeout=10)
            if r.status_code == 404:
                logger.warning("grid /v1/validator/attest not deployed yet — attestation dropped")
                return False
            r.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.warning(f"submit_attestation failed: {e}")
            return False

    async def aclose(self):
        await self._http.aclose()
