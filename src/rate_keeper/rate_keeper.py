import logging
import sys
import threading
import time
from functools import wraps
from typing import Callable

LOGGER_NAME = "rate_keeper"

logger = logging.getLogger(LOGGER_NAME)

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

        logger.info(f"RateKeeper initialized: {self}")

    @property
    def limit(self) -> int:
        """
        Get current call limit.

        :return: Maximum allowed calls
        """
        return self._limit

    @limit.setter
    @_synchronized
    def limit(self, limit: int) -> None:
        """
        Set call limit.

        :param limit: Call limit
        """
        old_limit = self._limit
        self._limit = max(1, min(sys.maxsize, limit))
        logger.debug(f"RateKeeper 'limit' updated: {old_limit} -> {self._limit}")

    @property
    def period(self) -> int:
        """
        Get current limit period.

        :return: Limit period (seconds)
        """
        return self._period

    @period.setter
    @_synchronized
    def period(self, period: int) -> None:
        """
        Set limit period.

        :param period: New limit period (seconds)
        """
        old_period = self._period
        self._period = max(1, period)
        logger.debug(f"RateKeeper 'period' updated: {old_period} -> {self._period}")

    @property
    def used(self) -> int:
        """
        Get current used call count.

        :return: Used call count
        """
        return self._used

    @used.setter
    @_synchronized
    def used(self, used: int) -> None:
        """
        Set used call count.

        :param used: New used call count
        """
        old_used = self._used
        self._used = max(0, min(self._limit, used))
        logger.debug(f"RateKeeper 'used' updated: {old_used} -> {self._used}")

    @property
    def reset(self) -> float:
        """
        Get counter reset time.

        :return: Reset time (seconds)
        """
        return self._reset

    @reset.setter
    @_synchronized
    def reset(self, reset: float) -> None:
        """
        Set counter reset time.

        :param reset: New reset time (seconds)
        """
        old_reset = self._reset
        self._reset = max(self.clock(), reset)
        logger.debug(f"RateKeeper 'reset' updated: {old_reset} -> {self._reset}")

    @property
    def delay_time(self) -> float:
        """
        Get current delay time.

        :return: Delay time (seconds)
        """
        return self._delay_time

    def update_limit(self, limit: int) -> None:
        """
        Deprecated. Use 'limit' property instead.
        """
        self.limit = limit

    def update_period(self, period: int) -> None:
        """
        Deprecated. Use 'period' property instead.
        """
        self.period = period

    def update_used(self, used: int) -> None:
        """
        Deprecated. Use 'used' property instead.
        """
        self.used = used

    def update_reset(self, reset: float) -> None:
        """
        Deprecated. Use 'reset' property instead.
        """
        self.reset = reset

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
                        logger.info(f"Auto sleeping for {self._delay_time:.2f} seconds")
                        time.sleep(self._delay_time)

                # Reset counter
                if self.remaining_period == 0:
                    old_reset = self._reset
                    self._used = 0
                    self._reset = self.clock() + self._period
                    logger.debug(
                        f"RateKeeper counter reset: {old_reset:.2f} -> {self._reset:.2f}"
                    )

                self._used += 1
                logger.debug(
                    f"Calling function {func.__name__}. Current used: {self._used}/{self._limit}"
                )
                return func(*args, **kwargs)

        return wrapper

    def __str__(self):
        return f"RateKeeper(limit={self._limit}, period={self._period}, used={self._used}, reset={self._reset})"
