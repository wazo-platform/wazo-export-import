# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from setuptools import find_packages, setup

setup(
    name="wazo_export_import",
    version="1.0",
    description="Export/Import tool for Wazo",
    auth="Wazo Authors",
    author_email="dev@wazo.community",
    url="http://wazo-platform.org",
    packages=find_packages(),
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "wazo-generate-dump = wazo_export_import.main:dump",
        ],
        "wazo_export_import.dump_commands": [
            "list_resources = wazo_export_import.commands:ListResources",
            "list_fields = wazo_export_import.commands:ListFields",
            "add = wazo_export_import.commands:Add",
            "new = wazo_export_import.commands:New",
        ],
    },
)
