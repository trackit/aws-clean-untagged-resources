from datetime import datetime, timedelta
import pytz
from enum import Enum
import re


class LifetimeType(Enum):
    NA = 0
    DAYS = 1
    DATE = 2


def is_expired(value):
    date = pytz.utc.localize(datetime.strptime(value, '%Y-%m-%d'))
    now = pytz.utc.localize(datetime.now())
    if now < date:
        return False
    return True


def str_to_date(value):
    return pytz.utc.localize(datetime.strptime(value, '%Y-%m-%d'))


def get_expired_time(value):
    return datetime.strptime(value, '%Y-%m-%d')


def get_lifetime_type(value: str):
    if value.isnumeric():
        return LifetimeType.DAYS
    elif re.match("^\\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])", value):
        return LifetimeType.DATE


def is_expired_date(date):
    if pytz.utc.localize(datetime.now()) < date:
        return False
    return True


def check_tag_expired(tag_value, start_time=None):
    lifetime_type = get_lifetime_type(tag_value)
    if lifetime_type == LifetimeType.DAYS and start_time:
        if not is_expired_date(start_time + timedelta(int(tag_value))):
            return False
    elif lifetime_type == LifetimeType.DATE and not is_expired_date(str_to_date(tag_value)):
        return False
    return True


def get_expired_date(tag_value, start_time=None):
    lifetime_type = get_lifetime_type(tag_value)
    if lifetime_type == LifetimeType.DAYS and start_time:
        return start_time + timedelta(int(tag_value))
    elif lifetime_type == LifetimeType.DATE:
        return pytz.utc.localize(datetime.strptime(tag_value, '%Y-%m-%d'))
    else:
        return None
