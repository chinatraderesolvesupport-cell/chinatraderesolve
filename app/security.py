from __future__ import annotations

import time
from collections import defaultdict, deque
from fastapi import Request


class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 8, window_seconds: int = 600) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.events[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
