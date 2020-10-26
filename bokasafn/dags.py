import pytz
import dateparser
import datetime
import re


def parse(datestr, tz=pytz.utc, ignore_past=False, allow_tbd=False, naive=False):
    if allow_tbd and datestr.lower() == "tbd":
        return dateparser.parse("9999/01/01 00:00")

    weekdaysPlural = ["mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"]
    for day in weekdaysPlural:
        if day in datestr.lower():
            datestr = re.sub(day, day[:-1], datestr.lower())

    # Athuga hvort timezone sé gefið
    tzbit = r"(UTC+\d{1,2}|UTC-\d{1,2}|GMT+\d{1,2}|GMT-\d{1,2}|[A-Za-z]{3,5})"
    nottzbit = r"(\d{1,2}:\d{2}.*)"

    timezonestr = re.findall(r"{}{}".format(nottzbit, tzbit), datestr)

    if timezonestr != []:
        # Ef tz þá gerum við fancy ass nings því dateparser er ass
        timezonestr = timezonestr[0][-1]
        datestr = re.sub(r"{}{}".format(nottzbit, tzbit), "\\1", datestr)
        date = dateparser.parse(datestr, settings={"TIMEZONE": timezonestr,
                                                   "RETURN_AS_TIMEZONE_AWARE": True,
                                                   "PREFER_DATES_FROM": "future",
                                                   "DATE_ORDER": "DMY"})

    else:
        # Ef ekki þá pörsum við eðlilega og neyðum í að vera sem gefið tz
        date = dateparser.parse(datestr, settings={"PREFER_DATES_FROM": "future",
                                                   "DATE_ORDER": "DMY"})

    if date is None:
        return False

    elif date.tzinfo is None:
        date = tz.localize(date)

    if pytz.utc.localize(datetime.datetime.utcnow()) > date and not ignore_past:
        return False

    # Skilum samsvarandi tíma í UTC
    if naive:
        date = date.replace(tzinfo=None)
    else:
        date = date.astimezone(pytz.utc)
    return date


if __name__ == "__main__":
    while 1:
        print(parse(input()))
