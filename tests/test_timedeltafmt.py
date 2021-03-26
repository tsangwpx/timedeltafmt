from datetime import timedelta

import pytest

from timedeltafmt import (
    MICROSECOND,
    TimedeltaFormatter,
    parse_timedelta, format_timedelta,
)


def test_parse():
    assert parse_timedelta('') == timedelta()
    assert parse_timedelta('0') == timedelta()
    assert parse_timedelta('1') == timedelta(seconds=1)
    assert parse_timedelta('100s') == timedelta(seconds=100)
    assert parse_timedelta('1s1s') == timedelta(seconds=2)
    assert parse_timedelta('1s 3s') == timedelta(seconds=4)
    assert parse_timedelta('1s 3d') == timedelta(seconds=1, days=3)
    assert parse_timedelta('1w 100s') == timedelta(weeks=1, seconds=100)
    assert parse_timedelta('1y') == timedelta(days=365.25)
    assert parse_timedelta('1000y') == timedelta(days=365.25 * 1000)
    assert parse_timedelta(' 1m -10s ') == timedelta(minutes=1, seconds=-10)


def test_parse_error():
    with pytest.raises(ValueError):
        parse_timedelta('1secondz')


def easy_format(
    days: float = 0,
    seconds: float = 0,
    microseconds: float = 0,
    milliseconds: float = 0,
    minutes: float = 0,
    hours: float = 0,
    weeks: float = 0,
):
    return format_timedelta(timedelta(
        days=days,
        seconds=seconds,
        microseconds=microseconds,
        milliseconds=milliseconds,
        minutes=minutes,
        hours=hours,
        weeks=weeks,
    ))


def custom_rs1(fmt: TimedeltaFormatter, microseconds: int, seconds: int = 0) -> str:
    return fmt.format(timedelta(microseconds=microseconds, seconds=seconds), resolution=1)


def test_format():
    assert easy_format(seconds=1) == '1s'
    assert easy_format(seconds=86400) == '1d'
    assert easy_format(seconds=86399) == '23h 59m 59s'
    assert easy_format(seconds=1.1) == '1s'
    assert easy_format(weeks=1) == '7d'
    assert easy_format(days=365.25 + 10) == '1y 10d'
    assert easy_format(days=365.25 + 10) == '1y 10d'
    assert easy_format(days=-10) == '-10d'
    assert easy_format(days=1, seconds=-1) == '23h 59m 59s'
    assert easy_format(weeks=-1) == '-7d'


@pytest.mark.filterwarnings('ignore: non-integral unit')
def test_fractional_format():
    fmt = TimedeltaFormatter({
        'ms': MICROSECOND,
        'ha': 3 / 2,
    }, ('ha', 'ms'))

    assert custom_rs1(fmt, 7) == '4ha 1ms'
    assert custom_rs1(fmt, -7) == '-4ha -1ms'

    # 3 ** 35 ms = 50031545098999707 ms = 2 * 3 ** 34 ha = 33354363399333138 ha
    assert custom_rs1(fmt, 3 ** 35) == '33354363399333138ha'
    assert custom_rs1(fmt, 3 ** 35 + 1) == '33354363399333138ha 1ms'
    assert custom_rs1(fmt, 3 ** 35 + 2) == '33354363399333139ha'
    assert custom_rs1(fmt, 3 ** 35 + 3) == '33354363399333140ha'
    assert custom_rs1(fmt, 3 ** 35 + 4) == '33354363399333140ha 1ms'

    fmt = TimedeltaFormatter({
        'ms': MICROSECOND,
        'ii': 1.1,
    }, ('ii', 'ms'))

    assert custom_rs1(fmt, 10) == '9ii'
    assert custom_rs1(fmt, 11) == '10ii'
    assert custom_rs1(fmt, 12) == '10ii 1ms'
    assert custom_rs1(fmt, 13) == '11ii'
