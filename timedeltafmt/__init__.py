import re
from datetime import timedelta
from math import isfinite, modf
from typing import Iterable, Mapping, Sequence, Tuple, Union, Optional, Dict

MICROSECOND = 1
MILLISECOND = MICROSECOND * 1000
SECOND = MILLISECOND * 1000
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24
WEEK = DAY * 7
YEAR = DAY * 365 + DAY // 4  # no truncation error
MONTH = YEAR // 12  # still no truncation error


class TimedeltaFormatter:
    """
    TimedeltaFormatter `parse` timespan `str` to `timedelta` and `format` `timedelta` to `str`

    For advanced usage, `parse_int` results in and `format_int` accepts `int` instead of `timedelta`.
    """

    def __init__(self, durations: Mapping[str, Union[int, float]], format_units: Iterable[str]):
        """

        :param durations: mapping between units and their durations (int preferred)
        :param format_units: the units used in formatting
        """
        durations = dict(durations)
        format_units = list(format_units)

        for unit, dt in durations.items():
            if dt <= 0:
                raise ValueError(f"Unit {unit} duration {dt} must be positive")
            if isinstance(dt, float):
                if not isfinite(dt):
                    raise ValueError(f"Unit {unit} duration {dt} is a not finite number")

                if dt.is_integer():
                    durations[unit] = int(dt)  # cast to int

        try:
            # sort them decreasing
            format_units.sort(key=durations.__getitem__, reverse=True)
        except KeyError:
            raise ValueError(f"Bad format unit {next((u for u in format_units if u not in durations), None)!r}") from None

        if format_units and durations[format_units[-1]] > MICROSECOND:
            import warnings
            warnings.warn("Smallest duration is greater than one microsecond, parsed timedelta may not be accurate")

        if any(isinstance(durations[s], float) for s in format_units):
            import warnings
            warnings.warn("non-integral unit may result in truncation error when formatting")

        joined_units = '|'.join(
            re.escape(s) if s else r'(?!\D)'  # empty string
            for s in sorted(durations.keys(), reverse=True)
        )

        self._parse_pattern = re.compile(r'([-+]?\d+)(%s)\s*' % joined_units)
        self._parse_durations: Mapping[str, Union[int, float]] = durations
        self._format_units: Sequence[Tuple[str, Union[int, float]]] = tuple((s, self._parse_durations[s]) for s in format_units)

    def parse(self, string: str) -> timedelta:
        """
        Parse a string into timedelta

        :param string: the string represent time duration
        """
        return timedelta(microseconds=self.parse_int(string))

    def parse_int(self, string: str) -> int:
        """
        Parse a timespan string into int
        """
        string = string.strip()
        durations = self._parse_durations

        # Though the regex currently does not match fractional numbers, unit durations may be floats.
        # There are around 15 decimal significant figures in float.
        # That means duration larger than 2**53 microseconds (~285.42yrs) will not be exact.

        us: int = 0
        carry: float = 0.0
        pos = 0

        for match in self._parse_pattern.finditer(string):
            start, end = match.span(0)
            if start != pos:
                raise ValueError(f"Invalid character at index {pos}: {string[pos:pos + 10]!r}")
            pos = end

            dt = int(match.group(1)) * durations[match.group(2)]

            if isinstance(dt, int):
                us += dt
            else:
                frac, dt = modf(dt)
                us += int(dt)
                carry += frac

        if pos != len(string):
            raise ValueError(f"Invalid character at index {pos}: {string[pos:pos + 10]!r}")

        if carry:
            frac, dt = modf(carry)
            us += int(dt)

        return us

    def format(self, delta: timedelta, resolution: int = 1, zero: str = '0') -> str:
        """
        Format a timedelta into str

        For negative value, the format first treat it as positive by using the magnitude and add minus prefix to each unit.

        :param delta: the timedelta to format
        :param zero: str to return when timedelta is 0
        :param resolution: the smallest unit duration used to format the timedelta
        """
        return self.format_int(delta.days * DAY + delta.seconds * SECOND + delta.microseconds, resolution, zero)

    def format_int(self, us: int, resolution: int = 1, zero: str = '0') -> str:
        """
        Format a timespan in int to string
        """
        units = self._format_units
        if not units:
            raise RuntimeError("No format units available")

        ten2fifteen = 10 ** 15  # 15 digit accuracy? related to sys.float_info.dig?
        frac: int = 0
        sign = 1 if us >= 0 else -1
        us *= sign

        parts = []

        for unit, duration in units:
            if us < resolution:
                break

            if abs(us) < duration:
                # If the magnitude is greater than duration
                continue

            if isinstance(duration, int):
                n, us = divmod(us, duration)
            else:
                assert isinstance(duration, float), type(duration)

                # Try to treat `duration` as a rational number that divide `us` and give integral results, that is:
                # decompose `us = q * duration + r` into two using `duration = num / dem` where q and r are non-negative integers
                # first: us * dem = n * num + r * dem = n * num + rt
                # second: rt = r * dem + z
                # This avoid quotient overshot issue and meaningless remainder even though `duration` is exact
                # in IEEE 754 representation (implies z = 0)
                num, dem = duration.as_integer_ratio()
                n, rt = divmod(us * dem, num)
                r, z = divmod(rt, dem)

                if z == 0:
                    # the remainder `r` is an int
                    # The float is actually a rational number without truncation error
                    us = r
                else:
                    # The `duration` is not exact representation or the result are not integers.
                    # Then, do it approximately using 15 significant decimal digits and hopefully this will result in nice numbers.

                    try:
                        # shift the duration left 15 decimal digits and do a bad truncation
                        n, r = divmod(us * ten2fifteen + frac, int(duration * ten2fifteen))
                        us, frac = divmod(r, ten2fifteen)
                    except OverflowError:
                        # if duration is large enough, it would be casted as int in __init__()
                        raise AssertionError("Unreachable")

            parts.append(f'{n * sign}{unit}')

        return ' '.join(parts) if parts else zero


def make_formatter(
    time_units: Mapping[Union[int, float], Union[str, Iterable[str]]],
    format_units: Optional[Iterable[str]] = None,
) -> TimedeltaFormatter:
    """
    Create TimedeltaFormatter from a mapping from durations to their units

    :param time_units:
    :param format_units:
    :return:
    """
    durations: Dict[str, Union[int, float]] = {}

    formats = list(format_units) if format_units else []

    for dt, units in time_units.items():
        units = (units,) if isinstance(units, str) else tuple(units)

        for u in units:
            if u in durations:
                raise ValueError(f"Repeated unit {u!r}")
            durations[u] = dt

        if format_units is None and units:
            formats.append(units[0])

    return TimedeltaFormatter(durations, formats)


_FORMATTER = make_formatter({
    MICROSECOND: ('us', 'usec', 'microseconds'),
    MILLISECOND: ('ms', 'msec', 'msecs', 'milliseconds'),
    SECOND: ('s', 'sec', 'secs', 'second', 'seconds', ''),
    MINUTE: ('m', 'min', 'mins', 'minute', 'minutes'),
    HOUR: ('h', 'hr', 'hrs', 'hour', 'hours'),
    DAY: ('d', 'day', 'days'),
    WEEK: ('w', 'week', 'weeks'),
    MONTH: ('M', 'month', 'months'),
    YEAR: ('y', 'yr', 'yrs', 'year', 'years'),
}, ('us', 'ms', 's', 'm', 'h', 'd', 'M', 'y'))


def parse_timedelta(string) -> timedelta:
    return _FORMATTER.parse(string)


def format_timedelta(delta: timedelta, resolution: int = MILLISECOND, zero: str = '0') -> str:
    return _FORMATTER.format(delta, resolution, zero)


parse = parse_timedelta
format = format_timedelta

__all__ = (
    'TimedeltaFormatter',
    'parse_timedelta',
    'format_timedelta',
)
