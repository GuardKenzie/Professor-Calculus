# Author: Tristan Ferrua
# 2020-05-25 01:04
# Filename: test.py 

import pytz
import dateparser
import datetime
import re


def parse(datestr, tz=pytz.utc):
    # Athuga hvort timezone sé gefið
    tzbit = "(UTC+\d{1,2}|UTC-\d{1,2}|GMT+\d{1,2}|GMT-\d{1,2}|[A-Za-z]{3,5})"
    nottzbit = "(\d{1,2}:\d{2}.*)"

    timezonestr = re.findall(r"{}{}".format(nottzbit, tzbit), datestr)
    print(timezonestr)

    if timezonestr != []:
        # Ef tz þá gerum við fancy ass nings því dateparser er ass
        timezonestr = timezonestr[0][-1]
        datestr = re.sub(r"{}{}".format(nottzbit, tzbit), "\\1", datestr)
        print(datestr)
        date = dateparser.parse(datestr, settings={"TIMEZONE": timezonestr, "RETURN_AS_TIMEZONE_AWARE": True, "PREFER_DATES_FROM": "future"})

    else:
        # Ef ekki þá pörsum við eðlilega og neyðum í að vera sem gefið tz
        date = dateparser.parse(datestr, settings={"PREFER_DATES_FROM": "future"})

    if date is None:
        return False

    elif date.tzinfo is None:
        date = tz.localize(date)

    if pytz.utc.localize(datetime.datetime.utcnow()) > date:
        return False

    # Skilum samsvarandi tíma í UTC
    return date.astimezone(pytz.utc)

if __name__ == "__main__":
    while 1:
        print(parse(input()))

