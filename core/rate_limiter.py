# core/rate_limiter.py
"""
Thread-safe rate limiter for API calls

FDR 등 외부 API 호출 시 초당 요청 수를 제한하여 차단을 방지합니다.
"""
from __future__ import annotations
import threading
import time


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm

    Usage:
        limiter = RateLimiter(requests_per_second=5.0)

        # In worker thread
        limiter.acquire()  # Blocks until token is available
        make_api_call()
    """

    def __init__(self, requests_per_second: float):
        """
        Args:
            requests_per_second: Maximum requests allowed per second
                Example: 5.0 means 1 request every 0.2 seconds
        """
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        self.interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self.lock = threading.Lock()

    def acquire(self) -> None:
        """
        Acquire a token to make a request.
        Blocks if necessary to maintain the rate limit.
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time

            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                time.sleep(sleep_time)
                self.last_request_time = time.time()
            else:
                self.last_request_time = now

    def __repr__(self) -> str:
        return f"RateLimiter({1.0 / self.interval:.2f} req/sec)"