# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


class UnknownReferenceException(Exception):
    def __init__(self, references):
        super().__init__(f"Missing references: {references}")
