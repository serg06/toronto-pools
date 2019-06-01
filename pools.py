import pickle
import re
import time
from datetime import timedelta
from enum import Enum, unique
from typing import Tuple, List

import requests
from bs4 import BeautifulSoup
from dateutil import parser

# URL of leisure pool schedules
url = 'https://www.toronto.ca/data/parks/prd/swimming/dropin/leisure/index.html'

# Days of week as displayed on the webpage
days_of_wk = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

# Where to cache website results after first get
cache_fname = 'pools.pkl'


@unique
class TimeType(Enum):
    AM = 1
    PM = 2


# Modify this to get the pool info for any day
def main():
    pool_info = get_pool_info()
    find_pools_on("June 1", pool_info)


# Print pools open on this date
def find_pools_on(date: str, pool_info):
    available_on_date: List[Tuple[str, str]] = []

    date = parser.parse(date)
    for pool in pool_info:
        for availability in pool.availabilities:
            date2, time2 = availability

            if date.day == date2.day and date.month == date2.month:
                # Found a pool that's available today! Save it into a list first.
                available_on_date.append((pool.name, time2))

    # Now that we have a list of available pools, sort them by how long they're open, then by start time
    available_on_date.sort(key=lambda name_and_timerange: timerange_sorter(name_and_timerange[1]), reverse=True)

    for name, time2 in available_on_date:
        print(name)
        print(time2)
        print()


def split_timeranges(timeranges: str):
    """
    If you have multiple timeranges in one string, e.g. 5am-6pm8-9pm, split them into their own timeranges with this f.
    """
    return re.findall(r".*?-.*?(?:am|pm)", timeranges)


def timerange_sorter(timerange):
    # We want to sort first by length (largest to smallest, so it will be called with reverse=true)
    #                 then  by start time (since it's called reverse=true, we will sort by 24-starttime instead.

    # THIS IS OLD CODE FOR MULTIPLE TIMERANGES MESHED INTO ONE PLACE
    # if we get multiple timeranges, split them up first, then choose the one with longest length
    # starts_and_ends = [read_timerange(tr) for tr in split_timeranges(timerange)]
    # starts_and_ends.sort(key=lambda start_and_end: start_and_end[1] - start_and_end[0], reverse=True)
    # start, end = starts_and_ends[0]

    start, end = read_timerange(timerange)
    length = end - start
    reverse_start_time = timedelta(hours=24) - start
    return length, reverse_start_time


# A pool.
class Pool:
    def __init__(self, name):
        self.name = name
        self.availabilities = []

    def add_availability(self, date, time):
        self.availabilities.append((date, time))


# Caching
def load_pool_info():
    with open(cache_fname, 'rb') as p:
        return pickle.load(p)


# Caching
def save_pool_info(pool_info):
    with open(cache_fname, 'wb') as p:
        pickle.dump(pool_info, p)


def get_pool_info():
    """
    Download pool schedules from toronto.ca.
    """

    # cache
    try:
        return load_pool_info()
    except:
        pass

    pool_info_response = requests.get(url)

    if pool_info_response.status_code != 200:
        print(f"Error: Not 200, but {pool_info_response.status_code} instead.")

    soup = BeautifulSoup(pool_info_response.content)

    pools = soup.select('div.pfrListing')
    pool_objs = []

    for pool in pools:
        name = pool.h2.a.text
        pool_obj = Pool(name)

        rows = pool.select('table tbody tr')
        for row in rows:
            # Make sure it's for Leisure Swim
            sched_type = row.select_one('.coursenamemobiletable > strong').text
            if 'leisure' not in sched_type.lower():
                continue

            # Find the daterange (ex: May 26 to June 1) (Goes Sun-Sat)
            daterange = row.select_one('td > strong').text

            # Find start date
            from_date = daterange[:daterange.index(' to ')]
            date = parser.parse(from_date)

            # See if any day within 7 days of start date has time scheduled.
            for day in days_of_wk:
                timeranges = row.find("td", {"data-info": day}).text.strip()

                # if time scheduled on that day, add to our Pool's info
                if len(timeranges) > 0:
                    # split timeranges apart, then add each one! Trust, it's good for later.
                    # e.g. if the time is 5-7pm,      it'll just add that
                    #  but if it's        3-5pm6-8pm, it'll add 3-5pm and 6-8pm separately
                    for timerange in split_timeranges(timeranges):
                        pool_obj.add_availability(date, timerange)

                # add 1 day so our day of wk matches up in next loop
                date += timedelta(days=1)

        pool_objs.append(pool_obj)

    # cache
    save_pool_info(pool_objs)

    return pool_objs


def read_timerange(timerange):
    """
    Read time that a pool is open, and returns a start/end timedelta.

    Examples:
        12:30 - 8pm
        12 - 8pm
        10:30 - 11:30am
        11:30am - 8pm
        10:30am - 12pm
    """

    AM_TEXT = "am"
    PM_TEXT = "pm"

    timerange_split = timerange.split(" - ")

    # ensure we only have a single timerange
    assert len(timerange_split) == 2

    # backup in case I decide to remove previous assert
    if len(timerange_split) > 2:
        # we have more than two timeranges that this pool is open at, bug, just do 1 min
        return timedelta(minutes=1), timedelta(minutes=2)

    start_text, end_text = timerange_split
    assert AM_TEXT in end_text or PM_TEXT in end_text

    # If end has "am"
    if AM_TEXT in end_text:
        # - start has no "am", and they're both "am"
        return parse_time(start_text, TimeType.AM), parse_time(end_text, TimeType.AM)

    # If end has "pm"
    if PM_TEXT in end_text:
        # If start has "am", it's "am", else it's "pm"
        if AM_TEXT in start_text:
            return parse_time(start_text, TimeType.AM), parse_time(end_text, TimeType.PM)
        else:
            return parse_time(start_text, TimeType.PM), parse_time(end_text, TimeType.PM)


def parse_time(time_str, type: TimeType):
    """
    Read a time (in the format that you see on toronto.ca), and convert it to a timedelta

    Example:
        12:30, pm    --> timedelta(hours=12, minutes=30)
        8pm, pm      --> timedelta(hours=20)
        12, pm       --> timedelta(hours=12)
        10:30, am    --> timedelta(hours=10, minutes=30)
        11:30am, am  --> timedelta(hours=11, minutes=30)
    """

    # Remove "am" or "pm" if exists
    time_str = re.sub(r"(am|pm)", "", time_str)

    # Split into hours and minutes
    if ":" in time_str:
        hours, minutes = time_str.split(":")
        hours = int(hours)
        minutes = int(minutes)
    else:
        hours = int(time_str)
        minutes = 0

    # If it's PM, add 12 hours to make it 24-hour time, unless it's 12pm.
    if type == TimeType.PM and hours != 12:
        hours += 12

    return timedelta(hours=hours, minutes=minutes)


if __name__ == '__main__':
    main()
