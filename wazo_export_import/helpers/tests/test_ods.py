# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from ..ods import DumpFile


def test_pre_fill_columns_no_data():
    filename = "ignored in tests"
    fields = {
        "tab1": {
            "col1": {},
            "col2": {},
            "col3": {},
        },
        "tab2": {
            "col1": {},
        },
    }
    file = DumpFile(filename, fields)

    file._pre_fill_columns()

    assert file._data == {
        "tab1": [["col1", "col2", "col3"]],
        "tab2": [["col1"]],
    }


def test_pre_fill_columns_empty_tabs():
    filename = "ignored in tests"
    fields = {
        "tab1": {
            "col1": {},
            "col2": {},
            "col3": {},
        },
    }
    file = DumpFile(filename, fields)
    file._data = {
        "tab1": [
            ["col2"],
            ["foo2"],
            ["bar2"],
        ],
    }

    file._pre_fill_columns()

    assert file._data == {
        "tab1": [
            ["col2", "col1", "col3"],
            ["foo2", "", ""],
            ["bar2", "", ""],
        ],
    }


def test_find_matching_row():
    filename = "ignored in tests"
    fields = {
        "tab1": {
            "col1": {},
            "col2": {},
            "col3": {},
        },
    }
    file = DumpFile(filename, fields)
    file._data = {
        "tab1": [
            ["col1", "col2", "col3"],
            ["foo", "bar", "foo"],
            ["bar", "foo", "baz"],
            ["bar", "foo", "bar"],
        ],
    }

    index = file.find_matching_row("tab1", [("col2", "foo"), ("col3", "bar")])

    assert index == 3


def test_add_row():
    filename = "ignored in tests"
    fields = {
        "tab1": {
            "col1": {},
            "col2": {},
            "col3": {},
        },
    }
    file = DumpFile(filename, fields)
    file._data = {
        "tab1": [
            ["col1", "col2", "col3"],
            ["foo", "bar", "foo"],
        ],
    }

    row = {"col3": "value3", "col2": "value2"}
    file.add_row("tab1", row)

    assert file._data["tab1"][2] == ["", "value2", "value3"]


def test_update_row():
    filename = "ignored in tests"
    fields = {
        "tab1": {
            "col1": {},
            "col2": {},
            "col3": {},
        },
    }
    file = DumpFile(filename, fields)
    file._data = {
        "tab1": [
            ["col1", "col2", "col3"],
            ["foo", "bar", ""],
            ["foo", "bar", "foo"],
        ],
    }

    row = {"col3": "value3", "col2": "value2"}
    file.update_row("tab1", 1, row)

    assert file._data["tab1"][1] == ["foo", "value2", "value3"]
