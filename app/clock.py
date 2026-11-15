"""A clock the demo can skip forward, so hold expiry can be shown live."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


class Clock:
    def __init__(self, start: datetime | None = None):
        # With a fixed start the clock stands still (used by tests).
        self._start = start
        self._offset = timedelta(0)

    def now(self) -> datetime:
        base = self._start if self._start is not None else datetime.now(timezone.utc)
        return base + self._offset

    def skip(self, hours: float) -> None:
        self._offset += timedelta(hours=hours)

    def reset(self) -> None:
        self._offset = timedelta(0)
