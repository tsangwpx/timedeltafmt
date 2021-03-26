# timedeltafmt

A tool to parse and format `timedelta`

# Examples

```python
from datetime import timedelta

from timedeltafmt import parse_timedelta, format_timedelta, make_formatter, MICROSECOND, SECOND

print(parse_timedelta('1day 24h'))  # 2 days, 0:00:00
print(parse_timedelta('10s 1m 1s'))  # 0:01:11

print(format_timedelta(timedelta(weeks=1)))  # 7d
print(format_timedelta(timedelta(days=365.25)))  # 1y

JIFFY_FMT = make_formatter({
    MICROSECOND: 'ms',
    SECOND // 50: 'jiffies',
})

print(JIFFY_FMT.format(timedelta(seconds=2)))  # 100jiffies

```
