# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

# Helper functions to convert DB values for schedules to API values
# The starting point for this code can be found in xivo_dao.alchemy.schedule_times


def expand_range(multi_range):
    if not multi_range:
        return []

    result = []
    for item in multi_range.split(","):
        if "-" in item:
            start, end = map(int, item.split("-", 2))
            result += list(range(start, end + 1))
        else:
            result.append(int(item))
    return result


def hours_end(hours):
    hours = hours.split("-", 1) if hours else ""
    return hours[1] if len(hours) == 2 else None


def hours_start(hours):
    return hours.split("-", 1)[0] if hours else None
