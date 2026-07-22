from __future__ import annotations

import os
import time
import threading
from collections import deque
from ipaddress import ip_address
from fastapi import Request


class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 8, window_seconds: int = 600, max_keys: int = 5000) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self.events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        stale = []
        for key, values in self.events.items():
            while values and values[0] < cutoff:
                values.popleft()
            if not values:
                stale.append(key)
        for key in stale:
            self.events.pop(key, None)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            values = self.events.get(key)
            if values is not None:
                cutoff = now - self.window_seconds
                while values and values[0] < cutoff:
                    values.popleft()
                if not values:
                    self.events.pop(key, None)
                    values = None

            if values is None:
                if len(self.events) >= self.max_keys:
                    self._prune(now)
                # If a client keeps inventing new keys, collapse excess traffic into
                # one shared bucket instead of allowing unbounded memory growth.
                if len(self.events) >= self.max_keys:
                    key = "__overflow__"
                values = self.events.setdefault(key, deque())

            if len(values) >= self.limit:
                return False
            values.append(now)
            return True


def _normalise_ip(value: str | None) -> str | None:
    try:
        return str(ip_address((value or "").strip()))
    except ValueError:
        return None


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    # Render documents the first address as the real client IP. Trust proxy
    # headers only when the platform (or an explicit local setting) is known,
    # otherwise a caller could invent an X-Forwarded-For value.
    trust_forwarded = (
        os.getenv("RENDER", "").strip().lower() == "true"
        or os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}
    )
    if trust_forwarded:
        for candidate in forwarded.split(","):
            normalised = _normalise_ip(candidate)
            if normalised:
                return normalised
    raw_direct = request.client.host if request.client else ""
    direct = _normalise_ip(raw_direct)
    if direct:
        return direct
    fallback = str(raw_direct).strip()[:64]
    return f"host:{fallback}" if fallback else "unknown"
