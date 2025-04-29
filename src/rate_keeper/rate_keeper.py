import sys
import threading
import time
from functools import wraps
from typing import Callable

# Prefer time.monotonic if available, otherwise fall back to time.time
clock = time.monotonic if hasattr(time, "monotonic") else time.time


def _synchronized(func):
    """
    Synchronization decorator for thread-safe access to shared resources.

    :param func: The function to be decorated
    :return: The decorator
    """

    @wraps(func)
    def wrapper(self: "RateKeeper", *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return wrapper


class RateKeeper:
    """
    Rate Keeper: Used to limit function call frequency.

    It ensures your function is called evenly within the limit rather than being called intensively in a short time.
    Moreover, it can dynamically adjust the call frequency based on remaining calls and time.
    """

    def __init__(
        self,
        limit: int = 60,
        period: int = 60,
        clock: Callable[[], float] = clock,
        auto_sleep: bool = True,
    ):
        """
        Create a rate keeper.

        :param limit: Call limit, default is 60 times
        :param period: Limit period, default is 60 seconds
        :param clock: Time function, defaults to time.monotonic or time.time
        :param auto_sleep: Whether to auto delay, default is True
        """
        self._limit = max(1, min(sys.maxsize, limit))
        self._period = max(1, period)
        self.clock = clock
        self.auto_sleep = auto_sleep

        self._reset = clock() + period
        self._used = 0
        self._delay_time = 0

        self._lock = threading.RLock()

    @property
    def limit(self) -> int:
        """
        Get current call limit.

        :return: Maximum allowed calls
        """
        return self._limit

    @property
    def period(self) -> int:
        """
        Get current limit period.

        :return: Limit period (seconds)
        """
        return self._period

    @property
    def used(self) -> int:
        """
        Get current used call count.

        :return: Used call count
        """
        return self._used

    @property
    def reset(self) -> float:
        """
        Get counter reset time.

        :return: Reset time (seconds)
        """
        return self._reset

    @property
    def delay_time(self) -> float:
        """
        Get current delay time.

        :return: Delay time (seconds)
        """
        return self._delay_time

    @_synchronized
    def update_limit(self, limit: int) -> None:
        """
        Update call limit.

        :param limit: New call limit
        """
        self._limit = max(1, min(sys.maxsize, limit))

    @_synchronized
    def update_period(self, period: int) -> None:
        """
        Update limit period.

        :param period: New limit period (seconds)
        """
        self._period = max(1, period)

    @_synchronized
    def update_used(self, used: int) -> None:
        """
        Update used call count.

        :param used: New used call count
        """
        self._used = max(0, min(self._limit, used))

    @_synchronized
    def update_reset(self, reset: float) -> None:
        """
        Update counter reset time.

        :param reset: New reset time (seconds)
        """
        self._reset = max(self.clock(), reset)

    @property
    def remaining_period(self) -> float:
        """
        Get remaining limit period.

        :return: Remaining limit period (seconds)
        """
        return max(0, self._reset - self.clock())

    @property
    def remaining(self) -> int:
        """
        Get remaining calls.

        :return: Remaining call count
        """
        return max(0, self._limit - self._used)

    @property
    def recommend_delay(self) -> float:
        """
        Recommended delay time.

        Algorithm:
        - If used count is 0, delay time is 0 seconds.
        - If remaining calls is 0, delay time is remaining period.
        - If remaining calls > 0, delay time is remaining period divided by remaining calls.

        :return: Recommended delay time in seconds.
        """
        if self._used == 0:
            return 0

        if self.remaining <= 0:
            return max(0, self.remaining_period)

        return max(0, self.remaining_period / self.remaining)

    def decorator(self, func):
        """
        Decorator for limiting function call frequency.

        :param func: The function to be decorated
        :return: The decorator
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                # Add delay
                self._delay_time = self.recommend_delay
                if self.auto_sleep:
                    if self._delay_time > 0:
                        time.sleep(self._delay_time)

                # Reset counter
                if self.remaining_period == 0:
                    self._used = 0
                    self._reset = self.clock() + self._period

                self._used += 1

                return func(*args, **kwargs)

        return wrapper

    def __str__(self):
        return f"RateKeeper(limit={self._limit}, period={self._period}, used={self._used}, reset={self._reset})"
