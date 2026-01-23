"""Shared time/deadline helpers."""

import time


def compute_deadline(deadline_sec: int | None) -> float | None:
    if deadline_sec is None:
        return None
    if deadline_sec <= 0:
        return None
    return time.monotonic() + deadline_sec


def time_left(deadline: float | None) -> int | None:
    if deadline is None:
        return None
    remaining = int(deadline - time.monotonic())
    return remaining


def clamp_timeout(default_timeout: int, deadline: float | None, minimum: int = 1) -> int:
    remaining = time_left(deadline)
    if remaining is None:
        return default_timeout
    if remaining <= 0:
        raise TimeoutError("Deadline exceeded")
    return max(min(default_timeout, remaining), minimum)
