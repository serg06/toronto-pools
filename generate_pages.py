import pickle
import re
from datetime import datetime, timedelta
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
CACHE_FNAME = 'pools.pkl'
PAGES_FOLDER = 'pool-browser'


@unique
class TimeType(Enum):
    AM = 1
    PM = 2


# A pool.
class Pool:
    def __init__(self, name):
        self.name = name
        self.availabilities = []

    def add_availability(self, date, time):
        self.availabilities.append((date, time))


def main():
    pool_info = get_pool_info()
    gen_v1(pool_info)
    gen_v2(pool_info)


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
    earliest = latest = pool_info[0].availabilities[0][0]  # first pool, availability, and date

    for pool in pool_info:
        for date, _ in pool.availabilities:
            if date < earliest:
                earliest = date
            if date > latest:
                latest = date

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


def gen_v1(pool_info: List[Pool]):
    ##### SETUP #####

    # find earliest and latest date in the list
    earliest_date, latest_date = get_earliest_latest_dates(pool_info)
    assert earliest_date <= latest_date

    # make sure they're not more than 6 months apart, since I doubt it'll work very well at that point
    assert (latest_date - earliest_date) < timedelta(days=(6 * (365 / 12)))

    ##### GENERATE SELECT DROPDOWN #####

    html_select = "<select label='date-select' id='date-select'>"

    for date in date_range(earliest_date, latest_date):
        html_select += f"<option value='{date.strftime('%Y-%m-%d')}'>{date.strftime('%Y-%m-%d')}</option>"

    html_select += "</select>"

    ##### GENERATE TABLE #####

    # TODO: do this all with a single f-string? https://docs.python.org/3/reference/lexical_analysis.html#f-strings
    # html = ""
    html_table = "<table>"

    # make thead
    html_table += "<thead><tr>"

    # add name slot
    html_table += "<th>Name</th>"

    # iterate over all dates between earliest and latest
    for date in date_range(earliest_date, latest_date):
        html_table += f"<th class='date-{date.strftime('%Y-%m-%d')} pool-date'>{date.strftime('%Y-%m-%d')}</th>"
        date += timedelta(days=1)

    html_table += "</tr></thead>"

    # make tbody
    html_table += "<tbody>"
    for pool in pool_info:
        html_table += f"<tr class='{classify_pool_name(pool.name)} pool-row'><th class='pool-name' class-name='" \
            f"{classify_pool_name(pool.name)}'>{pool.name}</th>"
        for date in date_range(earliest_date, latest_date):
            todays_times = [time2 for date2, time2 in pool.availabilities if date2 == date]
            todays_times.sort(key=timerange_sorter_start_time)
            if len(todays_times) > 0:
                html_table += f"<td class='date-{date.strftime('%Y-%m-%d')} pool-time'>{'<br>'.join(todays_times)}</td>"
            else:
                html_table += f"<td class='date-{date.strftime('%Y-%m-%d')} pool-time'>&nbsp;</td>"

        html_table += "</tr>"
    html_table += "</tbody>"

    html_table += "</table>"

    with open(f'{PAGES_FOLDER}/v1/pools-v1_template.html', 'r') as template:
        with open(f'{PAGES_FOLDER}/v1/pools-v1.html', 'w') as result:
            html_template = template.read()

            html_template = html_template.replace("{{ data_table }}", html_table)
            html_template = html_template.replace("{{ date_select }}", html_select)

            result.write(html_template)

    # with open('out.html', 'w') as f:
    #     f.write("<link rel='stylesheet' type='text/css' href='out.css'>" + html)


def gen_v2(pool_info: List[Pool]):
    """

    Example output:

        <div class="pool-card-holder">
            <div class="pool-card Albert-Campbell-Collegiate-Institute">
                <div class="pool-name">Albert Campbell Collegiate Institute</div>
                <div class="pool-time date-2019-05-26">1 - 2pm</div>
                <div class="pool-time date-2019-05-27">5 - 6pm</div>
                <div class="pool-time date-2019-06-01">2 - 5pm</div>
            </div>
            <div class="pool-card Albert-Campbell-Collegiate-Institute-Two">
                <div class="pool-name">Albert Campbell Collegiate Institute Two</div>
                <div class="pool-time date-2019-05-26">1 - 2pm</div>
                <div class="pool-time date-2019-05-28">5 - 6pm</div>
                <div class="pool-time date-2019-06-01">2 - 5pm</div>
            </div>
            <div class="pool-card Albert-Campbell-Collegiate-Institute-Three">
                <div class="pool-name">Albert Campbell Collegiate Institute Three</div>
                <div class="pool-time date-2019-05-26">1 - 2pm</div>
                <div class="pool-time date-2019-05-28">5 - 6pm</div>
                <div class="pool-time date-2019-06-01">2 - 5pm</div>
            </div>
            <div class="pool-card Albert-Campbell-Collegiate-Institute-Four">
                <div class="pool-name">Albert Campbell Collegiate Institute Four</div>
                <div class="pool-time date-2019-05-26">1 - 2pm</div>
                <div class="pool-time date-2019-05-28">5 - 6pm</div>
                <div class="pool-time date-2019-06-01">2 - 5pm</div>
            </div>
        </div>
    """

    ##### SETUP #####

    # find earliest and latest date in the list
    earliest_date, latest_date = get_earliest_latest_dates(pool_info)
    assert earliest_date <= latest_date

    # make sure they're not more than 6 months apart, since I doubt it'll work very well at that point
    assert (latest_date - earliest_date) < timedelta(days=(6 * (365 / 12)))

    ##### GENERATE SELECT DROPDOWN #####

    html_select = "<select label='date-select' id='date-select'>"

    for date in date_range(earliest_date, latest_date):
        html_select += f"<option value='{date.strftime('%Y-%m-%d')}'>{date.strftime('%Y-%m-%d')}</option>"

    html_select += "</select>"

    ##### GENERATE POOL CARDS #####

    # TODO: do this all with a single f-string? https://docs.python.org/3/reference/lexical_analysis.html#f-strings
    # html = ""
    html_pool_cards = "<div class='pool-card-holder'>"

    # make tbody
    for pool in pool_info:
        # pool.name
        # classify_pool_name(pool.name)
        # date.strftime('%Y-%m-%d')

        """
        <div class="pool-card Albert-Campbell-Collegiate-Institute">
            <div class="pool-name">Albert Campbell Collegiate Institute</div>
            <div class="pool-time date-2019-05-26">1 - 2pm</div>
            <div class="pool-time date-2019-05-27">5 - 6pm</div>
            <div class="pool-time date-2019-06-01">2 - 5pm</div>
        </div>
        """

        html_pool_cards += f"<div class='pool-card {classify_pool_name(pool.name)}'>"
        html_pool_cards += f"<span class='pool-name'>{pool.name}</span>"

        # sort availabilities by time first, so that times are sorted under each date
        pool.availabilities.sort(key=lambda date_n_time: timerange_sorter_start_time(date_n_time[1]))

        for date2, time2 in pool.availabilities:
            html_pool_cards += f"<div pool-name='{classify_pool_name(pool.name)}' class='pool-time " \
                f"date-{date2.strftime('%Y-%m-%d')}'>{time2}</div>"

        html_pool_cards += "</div>"

    html_pool_cards += "</div>"

    with open(f'{PAGES_FOLDER}/v2/pools-v2_template.html', 'r') as template:
        with open(f'{PAGES_FOLDER}/v2/pools-v2.html', 'w') as result:
            html_template = template.read()

            html_template = html_template.replace("{{ data_table }}", html_pool_cards)
            html_template = html_template.replace("{{ date_select }}", html_select)

            result.write(html_template)


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


if __name__ == '__main__':
    main()
