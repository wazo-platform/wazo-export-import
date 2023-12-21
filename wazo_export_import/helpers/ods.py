# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from copy import deepcopy

from pyexcel_ods import get_data, save_data

from .constants import RESOURCE_FIELDS


class DumpFile:
    def __init__(self, filename, fields=None, mode=None):
        self._filename = filename
        self._data = {}
        self._fields = deepcopy(fields or RESOURCE_FIELDS)
        self._mode = mode

    def __enter__(self):
        try:
            self._data = get_data(self._filename)
        except FileNotFoundError:
            self._data = {}
        self._pre_fill_columns()
        return self

    def __exit__(self, type, value, traceback):
        if self._mode == "r+w":
            save_data(self._filename, self._data)

    def add_row(self, tab_name, row):
        columns = self._get_columns(tab_name)
        values = [row.get(column, "") for column in columns]
        self._data[tab_name].append(values)

    def find_matching_row(self, tab_name, pairs):
        columns = self._get_columns(tab_name)
        for i, row in enumerate(self._data[tab_name][1:], start=1):
            if self._row_matches(columns, row, pairs):
                return i
        raise LookupError(f"No row matching {pairs}")

    def get_resources(self):
        return deepcopy(self._data)

    def update_row(self, tab_name, i, row):
        columns = self._get_columns(tab_name)
        values = self._data[tab_name][i]
        for column, value in row.items():
            j = columns.index(column)
            values[j] = value

    def _add_tab_if_missing(self, tab_name):
        if tab_name not in self._data:
            self._data[tab_name] = [[]]

    def _add_columns_to_tab_if_missing(self, tab_name, column):
        if self._data[tab_name]:
            existing_columns = set(self._data[tab_name][0])
        else:
            existing_columns = set()

        if column not in existing_columns:
            self._data[tab_name][0].append(column)
            for row in self._data[tab_name][1:]:
                row.append("")

    def _get_columns(self, tab_name):
        return self._data[tab_name][0]

    def _pre_fill_columns(self):
        for tab, column_definitions in self._fields.items():
            self._add_tab_if_missing(tab)
            for column in column_definitions["fields"].keys():
                self._add_columns_to_tab_if_missing(tab, column)

    def _row_matches(self, columns, row, pairs):
        for key, value in pairs:
            index = columns.index(key)
            if row[index] != value:
                return False
        return True
