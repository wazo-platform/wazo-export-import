# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from cliff import app, commandmanager


class WazoImportDump(app.App):
    def __init__(self):
        super().__init__(
            description="Dump file importer for Wazo",
            command_manager=commandmanager.CommandManager(
                "wazo_export_import.import_commands"
            ),
            version="1.0.0",
        )
