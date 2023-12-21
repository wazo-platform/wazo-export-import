# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from ..exceptions import UnknownReferenceException
from ..import_set import ImportSet

data_definition = {
    "tab2": {
        "references": ["referee"],
    },
}


def test_check_references_no_missing_references():
    data = {"tab1": [["ref"], ["ref1"], ["ref2"]], "tab2": [["referee"], ["ref1"]]}

    import_set = ImportSet(data, data_definition)

    try:
        import_set.check_references()
    except Exception as e:
        pytest.fail(f"unexpected exception: {e}")


def test_check_references_with_missing_references():
    data = {"tab1": [["ref"], ["ref1"], ["ref2"]], "tab2": [["referee"], ["missing"]]}

    import_set = ImportSet(data, data_definition)

    with pytest.raises(
        UnknownReferenceException, match=r"Missing references: \['missing'\]"
    ):
        import_set.check_references()


def test_check_references_row_shorter_that_headers():
    data = {
        "tab1": [["ref"], ["1"], ["2"]],
        "tab2": [["ignored", "referee"], ["one column"], ["two column", "1"]],
    }

    import_set = ImportSet(data, data_definition)

    try:
        import_set.check_references()
    except Exception as e:
        pytest.fail(f"unexpected exception: {e}")


def test_check_references_ignore_sound():
    data = {
        "tab2": [["referee"], ["sound"]],
    }

    import_set = ImportSet(data, data_definition)

    try:
        import_set.check_references()
    except Exception as e:
        pytest.fail(f"unexpected exception: {e}")
