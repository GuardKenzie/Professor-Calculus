# Author: Tristan Ferrua
# 2020-05-25 01:04
# Filename: test.py 

import pytz
import dateparser
import re


def parse(datestr, tz=pytz.utc):
    # Athuga hvort timezone sé gefið
    timezonestr = re.findall(r"\d{1,2}:\d{2}.*([A-Za-z]{3,5})", datestr)

    if timezonestr != []:
        # Ef tz þá gerum við fancy ass nings því dateparser er ass
        timezonestr = timezonestr[0]
        datestr = re.sub(r"(\d{1,2}:\d{2}.*)[A-Za-z]{3,5}", "\\1", datestr)
        date = dateparser.parse(datestr, settings={"TIMEZONE": timezonestr, "RETURN_AS_TIMEZONE_AWARE": True})

    else:
        # Ef ekki þá pörsum við eðlilega og neyðum í að vera sem gefið tz
        date = dateparser.parse(datestr)

    if date is None:
        return False

    elif date.tzinfo is None:
        date = tz.localize(date)

    # Skilum samsvarandi tíma í UTC
    return date.astimezone(pytz.utc)

if __name__ == "__main__":
    while 1:
        print(parse(input()))

