import json
import pickle
import re
from datetime import datetime, timedelta
from enum import Enum, unique
from typing import Tuple, List

import requests
from bs4 import BeautifulSoup  # beautifulsoup4
from dateutil import parser  # python-dateutil

# URL of leisure pool schedules
POOL_SCHEDULES_URL = 'https://www.toronto.ca/data/parks/prd/swimming/dropin/leisure/index.html'


@unique
class PoolType(Enum):
    IndoorPool = 'indoor pool'
    OutdoorPool = 'outdoor pool'
    SplashPad = 'splash pad'
    WadingPool = 'wading pool'


POOL_ADDRESS_URLS = {
    PoolType.IndoorPool: 'https://www.toronto.ca/data/parks/prd/facilities/indoor-pools/index.html',
    PoolType.OutdoorPool: 'https://www.toronto.ca/data/parks/prd/facilities/outdoor-pools/index.html',
    PoolType.SplashPad: 'https://www.toronto.ca/data/parks/prd/facilities/splash-pads/index.html',
    PoolType.WadingPool: 'https://www.toronto.ca/data/parks/prd/facilities/wading-pools/index.html'
}

POOL_DESCRIPTIONS = {
    PoolType.IndoorPool: 'The City of Toronto offers 60 indoor pools - some varying in aquatic features and design, '
                         'but all promising a great time for the whole family. Indoor pools are open all-year round, '
                         'providing a great way to beat the heat or escape the cold.',
    PoolType.OutdoorPool: 'The City of Toronto has 58 outdoor pools and a water park for residents and visitors to '
                          'have fun in the sun and make a splash while enjoying the warm summer weather.',
    PoolType.SplashPad: 'Need a quick place for your children to enjoy the cool water on a hot and sunny day? Splash '
                        'pads are unsupervised water play areas and are conveniently located in many parks and '
                        'playgrounds. They often include engaging water features such as shower heads and spray jets '
                        'that keep children laughing for hours. Parents are reminded to supervise their children at '
                        'all times while visiting the splash pad.',
    PoolType.WadingPool: 'Looking for your kids to splash around for a while but don\'t want to go to a pool? Wading '
                         'pools are shallow water areas for children located within parks. Over 100 supervised wading '
                         'pools are in operation in summer.'
}

# Days of week as displayed on the webpage
days_of_wk = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

# Where to cache website results after first get
CACHE_FNAME = 'pools-v3.pkl'
PAGES_FOLDER = 'pool-browser'


@unique
class TimeType(Enum):
    AM = 1
    PM = 2


# A pool.
class Pool:
    def __init__(self, name, address=None, phone=None):
        self.name = name
        self.classified_name = None  # used for js

        # Map dates to lists of start/end times
        self.availabilities = dict()

        self.address = None  # TODO
        self.type = None  # Type of pool (indoor/outdoor/wading/etc)
        self.phone = None  # TODO

    def add_availability(self, date, time):
        if date not in self.availabilities:
            self.availabilities[date] = []
        start, end = read_timerange(time)
        self.availabilities[date].append((start, end))


def main():
    pool_info = get_pool_info()
    gen_v3(pool_info)  # DESTRUCTIVE function


def print_weird_letters(pool_info):
    """
    Print all non-alphabetical characters in all pool names.
    """

    letters = 'qwertyuiopasdfghjklzxcvbnm'
    chars = set()
    for pool in pool_info:
        for c in pool.name:
            chars.add(c)
    for c in letters.lower() + letters.upper():
        if c in chars:
            chars.remove(c)
    chars = sorted(list(chars))
    print(chars)


def timerange_sorter_start_time(timerange):
    # We want to sort first by length (largest to smallest, so it will be called with reverse=true)
    #                 then  by start time (since it's called reverse=true, we will sort by 24-starttime instead.

    # THIS IS OLD CODE FOR MULTIPLE TIMERANGES MESHED INTO ONE PLACE
    # if we get multiple timeranges, split them up first, then choose the one with longest length
    # starts_and_ends = [read_timerange(tr) for tr in split_timeranges(timerange)]
    # starts_and_ends.sort(key=lambda start_and_end: start_and_end[1] - start_and_end[0], reverse=True)
    # start, end = starts_and_ends[0]

    start, _ = read_timerange(timerange)
    return start


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


def get_earliest_latest_dates(pool_info: List[Pool]):
    # choose unrealistically late/early dates to ensure they get updated
    earliest = parser.parse('2069')
    latest = parser.parse('1969')

    for pool in pool_info:
        for date in pool.availabilities:
            if date < earliest:
                earliest = date
            if date > latest:
                latest = date

    assert earliest != parser.parse('2069') and latest != parser.parse('1969'), 'error: cannot find earliest/latest'

    return earliest, latest


def date_range(start: datetime, end: datetime):
    date = start
    oneday = timedelta(days=1)
    while date <= end:
        yield date
        date += oneday


def classify_pool_name(name):
    """
    Sanitize pool name so that it can be a class.
    """

    name = name.lower()

    replace = {
        ' ': '-',
        "'": "",
        ',': "",
        '-': "-",
        '.': ""
    }

    for c in set(name):
        if c in replace:
            name = name.replace(c, replace[c])

    return name


def gen_v3(pool_info: List[Pool]):
    """
    WARN: Destructive function.
    """

    version_name = 'v3'

    ##### SETUP #####

    # find earliest and latest date in the list
    earliest_date, latest_date = get_earliest_latest_dates(pool_info)
    assert earliest_date <= latest_date

    # make sure they're not more than 6 months apart, since I doubt it'll work very well at that point
    assert (latest_date - earliest_date) < timedelta(days=(6 * (365 / 12)))

    ##### GENERATE SELECT DROPDOWN #####

    html_select = "<select id='date-select'>"

    for date in date_range(earliest_date, latest_date):
        html_select += f"<option value='{date.strftime('%Y-%m-%d')}'>{date.strftime('%Y-%m-%d')}</option>"

    html_select += "</select>"

    ##### GENERATE JS OBJECT CONTAINING ALL POOL INFO #####

    # prep pool info so it's easier for frontend to use
    # map pool name -> cleaned pool info
    cleaned_pool_info = dict()
    for pool in pool_info:
        # make sure all enums are serializable
        if pool.type is not None:
            pool.type = pool.type.value
        # instead of mapping availabilities as date->[(start time, end time), ...], map as formatted_date_string->
        #   [{start time (in minutes since midnight), end time (in minutes since midnight)}, ...]

        new_availabilities = dict()

        # for each date, fix up the date and its start/end times and store in new availabilities
        dates = set(pool.availabilities.keys())
        for date in dates:
            formatted_date = date.strftime('%Y-%m-%d')

            new_availabilities[formatted_date] = []

            for start, end in pool.availabilities[date]:
                start_mins = int(start.total_seconds()) // 60
                end_mins = int(end.total_seconds()) // 60

                new_availabilities[formatted_date].append({'start': start_mins, 'end': end_mins})
                new_availabilities[formatted_date].sort(key=lambda time: time['start'])

        pool.availabilities = new_availabilities

        # store classified pool name so we don't have to generate it every time we use it on frontend
        #   (debateable usefulness...)
        pool.classified_name = classify_pool_name(pool.name)

        # finally, put it in our new pool info (except change from object -> dict to make it JSON-serializable)
        cleaned_pool_info[pool.name] = pool.__dict__

    # convert our final pool info object into json
    js_pool_info = json.dumps(cleaned_pool_info)

    ##### INJECT #####

    with open(f'{PAGES_FOLDER}/{version_name}/pools-{version_name}_template.html', 'r') as template:
        html_template = template.read()

    with open(f'{PAGES_FOLDER}/{version_name}/pools-{version_name}.html', 'w') as result:
        assert "{{ pool_info }}" in html_template
        html_template = html_template.replace("{{ pool_info }}", js_pool_info)
        assert "{{ date_select }}" in html_template
        html_template = html_template.replace("{{ date_select }}", html_select)

        result.write(html_template)


def gmaps_search_url(query):
    query = re.sub(r"\s+", "+", query)
    return f"https://www.google.ca/maps/search/{query}/"


def split_timeranges(timeranges: str):
    """
    If you have multiple timeranges in one string, e.g. 5am-6pm8-9pm, split them into their own timeranges with this f.
    """
    return re.findall(r".*?-.*?(?:am|pm)", timeranges)


# Caching
def load_pool_info():
    with open(CACHE_FNAME, 'rb') as p:
        return pickle.load(p)


# Caching
def save_pool_info(pool_info):
    with open(CACHE_FNAME, 'wb') as p:
        pickle.dump(pool_info, p)


def get_pool_info():
    # cache
    try:
        return load_pool_info()
    except:
        pass

    pools = get_pool_schedules()
    addresses, pool_types, phone_numbers = get_pool_addresses_types_phones()

    for pool in pools:
        if pool.name not in addresses:
            print(f'WARNING: Cannot find {pool.name} in addresses.')
        else:
            pool.address = addresses[pool.name]
            pool.type = pool_types[pool.name]
            pool.phone = phone_numbers[pool.name]

    save_pool_info(pools)

    return pools


def get_pool_schedules():
    """
    Download pool schedules from toronto.ca.
    Returns Pool objects with just pool name and schedule filled in.
    """

    pool_info_response = requests.get(POOL_SCHEDULES_URL)

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

        # Some pools (i.e. Douglas Snow Aquatic Centre and Jimmie Simpson Recreation Centre) have duplicate times
        #   because of a mistake on toronto.ca.
        for date in pool_obj.availabilities:
            if len(pool_obj.availabilities[date]) > len(set(pool_obj.availabilities[date])):
                print(f'WARN: pool {pool_obj.name} has duplicate times on {date}.')
                pool_obj.availabilities[date] = list(set(pool_obj.availabilities[date]))

        pool_objs.append(pool_obj)

    return pool_objs


def get_pool_addresses_types_phones():
    """
    Get map of pool name -> pool address.
    """

    # TODO; ALSO SAVE TYPE OF POOL (I.E. INDOOR/OUTDOOR/WADING/SPLASH-AND-SPRAY-PAD, AND DISPLAY IT!!

    pages = dict()

    # download pages and convert them to soups
    for pool_type, url in POOL_ADDRESS_URLS.items():
        pool_addresses_response = requests.get(url)

        if pool_addresses_response.status_code != 200:
            print(f"Error: Not 200, but {pool_addresses_response.status_code} instead. Pre-emptively quitting...")
            exit(-1)

        soup = BeautifulSoup(pool_addresses_response.content)

        pages[pool_type] = soup

    addresses = dict()
    pool_types = dict()
    phone_numbers = dict()  # future use?

    for pool_type, page in pages.items():
        location_rows = page.select('.pfrListing table tr:not([class=header])')
        print(f'found {len(location_rows)} locations...')
        for row in location_rows:
            # td data-info=Name/Address/Phone
            name = row.select_one('td[data-info="Name"]').text.strip()
            address = row.select_one('td[data-info="Address"]').text.strip()

            # Get phone (except sometimes there's no phone column)
            phone = row.select_one('td[data-info="Phone"]')
            if phone is not None:
                phone = phone.text.strip()

            addresses[name] = address
            phone_numbers[name] = phone
            pool_types[name] = pool_type

    return addresses, pool_types, phone_numbers


if __name__ == '__main__':
    main()
