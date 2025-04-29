import sys
import threading
import time
from unittest.mock import patch

from rate_keeper import RateKeeper, clock


def test_happy_path():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)

    @rate_keeper.decorator
    def test_func(param: str) -> str:
        return param

    assert test_func("hello") == "hello"
    assert test_func("world") == "world"


def test_remaining_calls():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)

    @rate_keeper.decorator
    def test_func(param: str) -> str:
        return param

    test_func("hello")
    test_func("world")
    assert rate_keeper.remaining == 0, "remaining_calls should be 0"


def test_remaining_period():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)

    @rate_keeper.decorator
    def test_func(param: str) -> str:
        return param

    test_func("hello")
    time.sleep(0.5)
    assert rate_keeper.remaining_period <= 0.5, (
        "remaining_period should be less than 0.5"
    )


def test_recommend_delay():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)

    @rate_keeper.decorator
    def test_func(param: str) -> str:
        return param

    assert rate_keeper.recommend_delay == 0, "recommend_delay should be 0"

    test_func("hello")
    time.sleep(0.5)
    assert rate_keeper.recommend_delay <= 0.5, "recommend_delay should be less than 0.5"


def test_delay_time():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)

    assert rate_keeper.delay_time == 0, "delay_time should be 0"


def test_update_limit():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)
    assert rate_keeper._limit == 2, "limit should be 2"

    rate_keeper.update_limit(3)
    assert rate_keeper._limit == 3, "limit should be 3"

    rate_keeper.update_limit(-1)
    assert rate_keeper._limit == 1, "limit should be 1"

    rate_keeper.update_limit(sys.maxsize)
    assert rate_keeper._limit == sys.maxsize, "limit should be sys.maxsize"


def test_update_period():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)
    assert rate_keeper._period == 1, "period should be 1"

    rate_keeper.update_period(2)
    assert rate_keeper._period == 2, "period should be 2"

    rate_keeper.update_period(-1)
    assert rate_keeper._period == 1, "period should be 1"


def test_update_used():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)

    assert rate_keeper._used == 0, "used should be 0"

    rate_keeper.update_used(1)
    assert rate_keeper._used == 1, "used should be 1"

    rate_keeper.update_used(3)
    assert rate_keeper._used == 2, "used should less than or equal to limit"

    rate_keeper.update_used(-1)
    assert rate_keeper._used == 0, "used should be 0"


def test_update_reset():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=False)

    assert rate_keeper.reset >= clock(), (
        "reset should be greater than or equal to clock"
    )

    reset = clock() + 100

    rate_keeper.update_reset(reset)
    assert rate_keeper.reset == reset, "reset should be next_reset"

    rate_keeper.update_reset(clock() - 100)
    assert rate_keeper.reset <= clock(), "reset should be greater than clock"


def test_auto_sleep():
    rate_keeper = RateKeeper(limit=2, period=1, auto_sleep=True)

    with patch("time.sleep") as mock_sleep:

        @rate_keeper.decorator
        def test_func(param: str) -> str:
            return param

        test_func("hello")
        test_func("world")
        assert mock_sleep.call_count == 1, "sleep should be called once"


def test_minimum_calls_and_period():
    rate_keeper = RateKeeper(limit=0, period=0)

    assert rate_keeper._limit == 1, "calls should be 1"
    assert rate_keeper._period == 1, "period should be 1"


def test_maximum_calls():
    rate_keeper = RateKeeper(limit=sys.maxsize)

    assert rate_keeper._limit == sys.maxsize, "calls should be sys.maxsize"


def test_negative_calls_and_period():
    rate_keeper = RateKeeper(limit=-1, period=-1)

    assert rate_keeper._limit == 1, "calls should be 1"
    assert rate_keeper._period == 1, "period should be 1"


def test_thread_safety():
    rate_keeper = RateKeeper(limit=10, period=1, auto_sleep=True)

    @rate_keeper.decorator
    def test_func(param: str) -> str:
        return param

    def run():
        for i in range(10):
            test_func(str(i))

    threads = [threading.Thread(target=run) for _ in range(2)]

    start = time.monotonic()
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    end = time.monotonic()
    step = end - start

    assert step >= 2, "step should be greater than or equal to 2"
    assert step < 3, "step should be less than 3"
